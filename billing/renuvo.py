"""Renuvo Tenant API adapter. Secrets and card processing stay server-side.

Contract: https://renuvo.uz/en/docs (checked 2026-10-03).
POSTs are never retried automatically: the API documents no idempotency key.
"""
import hashlib
import hmac
import json
import re
import threading
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler


class RenuvoError(Exception):
    def __init__(self, status=503, data=None):
        self.status, self.data = status, data or {}
        super().__init__('Renuvo javob bermadi yoki ulanish sozlanmagan.')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_link(value, sandbox):
    parsed = urlparse(value if isinstance(value, str) else '')
    hosts = {'test.renuvo.uz'} if sandbox else {'pay.renuvo.uz'}
    return (parsed.scheme == 'https' and parsed.hostname in hosts
            and parsed.port in (None, 443) and not parsed.username
            and not parsed.password)


class Client:
    def __init__(self, config):
        self.key = config['RENUVO_API_KEY']
        self.base = config['RENUVO_API_URL'].rstrip('/')
        if self.base not in ('https://api.renuvo.uz', 'https://test.renuvo.uz'):
            raise ValueError('Renuvo API host must be an official production or sandbox host')
        self.sandbox = self.base == 'https://test.renuvo.uz'
        self.opener = build_opener(NoRedirect())

    def call(self, method, route, body=None):
        if not self.key:
            raise RenuvoError()
        req = Request(self.base + route, method=method,
                      data=json.dumps(body).encode() if body is not None else None,
                      headers={'Authorization': 'Bearer ' + self.key,
                               'Content-Type': 'application/json'})
        try:
            with self.opener.open(req, timeout=10) as response:
                raw = response.read(65537)
                if len(raw) > 65536:
                    raise RenuvoError()
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise RenuvoError()
                return value
        except HTTPError as exc:
            try:
                data = json.loads(exc.read(65536))
            except (ValueError, OSError):
                data = {}
            raise RenuvoError(exc.code, data if isinstance(data, dict) else {}) from None
        except (URLError, OSError, ValueError):
            raise RenuvoError() from None


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
        raise RenuvoError()
    return value


class Integration:
    def __init__(self, app, store, error):
        self.app, self.store, self.error = app, store, error
        mapping = app.config['RENUVO_PLAN_IDS']
        for local, remote in mapping.items():
            if not isinstance(local,str) or not re.fullmatch('[a-z0-9_-]{1,32}',local):
                raise ValueError('Invalid local Renuvo plan identifier')
            identifier(remote)
        if len(set(mapping.values())) != len(mapping):
            raise ValueError('Renuvo plan identifiers must be unique')
        self.client = Client(app.config)
        self.lock = threading.RLock()
        with store.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS renuvo_customers(license_id TEXT PRIMARY KEY,customer_id TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS renuvo_subscriptions(id TEXT PRIMARY KEY,license_id TEXT,plan_id TEXT,status TEXT,expires_at INTEGER,seats INTEGER,checked INTEGER);
            CREATE TABLE IF NOT EXISTS renuvo_invoices(id TEXT PRIMARY KEY,subscription_id TEXT,amount INTEGER,status TEXT);
            ''')

    def ready(self):
        c = self.app.config
        return bool(c['RENUVO_API_KEY'] and c['RENUVO_TENANT_ID']
                    and len(c['RENUVO_WEBHOOK_SECRET']) >= 32 and c['RENUVO_PLAN_IDS'])

    def sync(self, subscription_id):
        """Fetch authoritative current state; delayed/replayed events cannot add days."""
        with self.lock:
            sid = identifier(subscription_id)
            value = self.client.call('GET', '/v1/subscriptions/' + sid)
            if value.get('id') != sid or value.get('tenantId') != self.app.config['RENUVO_TENANT_ID']:
                raise RenuvoError()
            pid = value.get('planId')
            local = next((k for k, v in self.app.config['RENUVO_PLAN_IDS'].items() if v == pid), None)
            if not local:
                raise RenuvoError()
            state = value.get('status')
            if state not in ('PENDING', 'TRIALING', 'ACTIVE', 'PAST_DUE', 'CANCELED', 'SCHEDULED'):
                raise RenuvoError()
            end = 0
            if value.get('currentPeriodEnd'):
                try:
                    dt = datetime.fromisoformat(value['currentPeriodEnd'].replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        raise ValueError()
                    end = int(dt.timestamp())
                except (ValueError, TypeError, AttributeError):
                    raise RenuvoError() from None
            invoice = value.get('latestInvoice') or {}
            if not isinstance(invoice, dict):
                raise RenuvoError()
            # Trials do not grant paid access. A redirect or event alone is never proof.
            if state == 'ACTIVE' and (invoice.get('status') != 'PAID' or invoice.get('currency') != 'UZS' or not end):
                raise RenuvoError()
            if invoice.get('status') == 'PAID':
                identifier(invoice.get('id'))
                if type(invoice.get('amountMinor')) is not int or invoice['amountMinor'] <= 0:
                    raise RenuvoError()
            with self.store.db() as db:
                customer = db.execute('SELECT license_id FROM renuvo_customers WHERE customer_id=?', (value.get('customerId'),)).fetchone()
                plan = db.execute('SELECT seats FROM plans WHERE id=?', (local,)).fetchone()
                if not customer or not plan:
                    raise RenuvoError()
                previous = db.execute('SELECT license_id FROM renuvo_subscriptions WHERE id=?', (sid,)).fetchone()
                if previous and previous['license_id'] != customer['license_id']:
                    raise RenuvoError()
                db.execute('INSERT OR REPLACE INTO renuvo_subscriptions VALUES(?,?,?,?,?,?,?)',
                           (sid, customer['license_id'], local, state, end, plan['seats'], int(self.store.clock())))
                if invoice.get('status') == 'PAID':
                    db.execute('INSERT INTO renuvo_invoices VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status',
                               (invoice['id'], sid, invoice['amountMinor'], 'PAID'))
                self.store.audit(db, 'renuvo.sync.' + state.lower(), sid)
            return value

    def refresh_license(self, identity):
        with self.store.db() as db:
            rows = db.execute('SELECT id FROM renuvo_subscriptions WHERE license_id=?', (identity,)).fetchall()
        # Poll also recovers missed renewals; do not issue a lease on a stale snapshot.
        for row in rows:
            self.sync(row['id'])

    def link(self, value, field):
        link = value.get(field)
        try:
            valid = safe_link(link, self.client.sandbox)
        except ValueError:
            valid = False
        if not valid:
            raise RenuvoError()
        return link

    def purchase(self, plan_id, key):
        if not self.ready() or plan_id not in self.app.config['RENUVO_PLAN_IDS']:
            raise self.error(503, 'Renuvo hali ulanmagan yoki tarif bog‘lanmagan.')
        with self.lock:
            with self.store.db() as db:
                plan = db.execute('SELECT * FROM plans WHERE id=? AND enabled=1', (plan_id,)).fetchone()
                if not plan:
                    raise self.error(400, 'Tarif topilmadi.')
                raw = None
                if key:
                    identity = self.store.license(db, key)['id']
                else:
                    identity, raw = self.store.issue(db)
                existing = db.execute('SELECT customer_id FROM renuvo_customers WHERE license_id=?', (identity,)).fetchone()
            if existing:
                customer = existing['customer_id']
            else:
                customer = identifier(self.client.call('POST', '/v1/customers', {'externalRef': identity}).get('customerId'))
                with self.store.db() as db:
                    db.execute('INSERT INTO renuvo_customers VALUES(?,?)', (identity, customer))
            try:
                result = self.client.call('POST', '/v1/subscriptions',
                                          {'customerId': customer, 'planId': self.app.config['RENUVO_PLAN_IDS'][plan_id]})
                sid = identifier(result.get('subscriptionId'))
                with self.store.db() as db:
                    db.execute('INSERT OR IGNORE INTO renuvo_subscriptions VALUES(?,?,?,?,?,?,?)',
                               (sid, identity, plan_id, 'PENDING', 0, plan['seats'], 0))
                url = self.link(result, 'hostedPageUrl')
            except RenuvoError as exc:
                if exc.status != 409:
                    raise
                # Existing subscriber: open portal to manage/switch, never double-charge.
                sid = identifier(exc.data.get('existingSubscriptionId'))
                value = self.sync(sid)
                if value.get('customerId') != customer:
                    raise RenuvoError()
                url = self.portal(identity)
            return dict(order_id=sid, license_key=raw, checkout_url=url,
                        amount_uzs=plan['price_uzs'], sandbox=self.client.sandbox,
                        provider='renuvo', renewal='automatic')

    def portal(self, identity):
        with self.store.db() as db:
            row = db.execute('SELECT customer_id FROM renuvo_customers WHERE license_id=?', (identity,)).fetchone()
        if not row:
            raise self.error(404, 'Renuvo obunasi hali yaratilmagan.')
        result = self.client.call('POST', '/v1/customers/' + identifier(row['customer_id']) + '/portal-sessions')
        return self.link(result, 'portalUrl')

    def webhook(self, raw, signature):
        secret = self.app.config['RENUVO_WEBHOOK_SECRET']
        expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if len(secret) < 32 or not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
            raise self.error(401, 'Webhook imzosi noto‘g‘ri.')
        try:
            event = json.loads(raw)
        except ValueError:
            raise self.error(400, 'Webhook JSON noto‘g‘ri.') from None
        if not isinstance(event, dict) or event.get('tenantId') != self.app.config['RENUVO_TENANT_ID']:
            raise self.error(403, 'Webhook tenant mos emas.')
        if event.get('type') not in ('invoice.paid', 'invoice.failed', 'subscription.activated', 'subscription.past_due', 'subscription.canceled'):
            raise self.error(400, 'Webhook turi noma’lum.')
        self.sync(event.get('subscriptionId'))
