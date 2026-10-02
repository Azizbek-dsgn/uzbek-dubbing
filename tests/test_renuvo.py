"""Contract tests with a fake transport; not a provider acceptance test."""
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock
try:
    from billing.service import create_app, DAY
    from billing.renuvo import RenuvoError, safe_link
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Billing dependencies unavailable')
class RenuvoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = int(time.time())
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = Path(self.tmp.name) / 'key.pem'
        pem.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self.app = create_app({'TESTING': True, 'DB_PATH': str(Path(self.tmp.name) / 'db'),
                              'SIGNING_KEY': str(pem), 'ADMIN_TOKEN': 'a' * 40,
                              'CLOCK': lambda: self.now, 'BILLING_PROVIDER': 'renuvo',
                              'RENUVO_API_KEY': 'fake-key', 'RENUVO_TENANT_ID': 'tenant',
                              'RENUVO_WEBHOOK_SECRET': 'w' * 40,
                              'RENUVO_PLAN_IDS': {'monthly': 'plan-month'}})
        self.client = self.app.test_client()
        self.app.renuvo.client.call = Mock(side_effect=self.api)
        self.state = 'PENDING'
        self.end = self.now + 30 * DAY
        self.invoice = 'invoice-one'
        self.snapshot_override = {}
        self.order = self.client.post('/api/orders', json={'plan_id': 'monthly'}).json
        self.auth = {'Authorization': 'Bearer ' + self.order['license_key']}

    def api(self, method, route, body=None):
        if route == '/v1/customers':
            return {'customerId': 'customer-one'}
        if route == '/v1/subscriptions' and method == 'POST':
            return {'subscriptionId': 'sub-one', 'hostedPageUrl': 'https://test.renuvo.uz/pay/test'}
        if route.endswith('/portal-sessions'):
            return {'portalUrl': 'https://test.renuvo.uz/portal/test'}
        if route == '/v1/subscriptions/sub-one':
            from datetime import datetime, timezone
            return dict({'id': 'sub-one', 'tenantId': 'tenant', 'customerId': 'customer-one',
                         'planId': 'plan-month', 'status': self.state,
                         'currentPeriodEnd': datetime.fromtimestamp(self.end, timezone.utc).isoformat(),
                         'latestInvoice': {'id': self.invoice, 'status': 'PAID', 'amountMinor': 4900000, 'currency': 'UZS'}}, **self.snapshot_override)
        raise AssertionError((method, route))

    def activate(self):
        return self.client.post('/api/activate', json={'device_id': '1' * 64}, headers=self.auth)

    def webhook(self, event='invoice.paid', **override):
        raw = json.dumps(dict({'type': event, 'tenantId': 'tenant', 'subscriptionId': 'sub-one'}, **override)).encode()
        signature = hmac.new(b'w' * 40, raw, hashlib.sha256).hexdigest()
        return self.client.post('/webhooks/renuvo', data=raw, content_type='application/json', headers={'X-Webhook-Signature': signature})

    def test_checkout_does_not_grant_pending_access(self):
        self.assertEqual(self.order['provider'], 'renuvo')
        self.assertEqual(self.activate().status_code, 403)
        self.assertNotIn('fake-key', json.dumps(self.order))
        plans = self.client.get('/api/plans').json
        self.assertEqual(plans['renewal'], 'automatic')
        self.assertEqual(len(plans['plans']), 1)

    def test_paid_duplicate_webhooks_and_renewal_use_absolute_period(self):
        self.state = 'ACTIVE'
        for _ in range(3):
            self.assertEqual(self.webhook().status_code, 200)
        self.assertEqual(self.activate().json['expires_at'], self.end)
        self.end += 30 * DAY
        self.invoice = 'invoice-two'
        self.assertEqual(self.activate().json['expires_at'], self.end)  # missed webhook recovery
        overview = self.client.get('/api/admin/overview', headers={'Authorization': 'Bearer ' + 'a' * 40})
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.json['revenue_uzs'], 98000)

    def test_tampered_signature_and_wrong_tenant(self):
        r = self.client.post('/webhooks/renuvo', json={'type': 'invoice.paid'}, headers={'X-Webhook-Signature': 'wrong'})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.webhook(tenantId='another-tenant').status_code, 403)

    def test_delayed_paid_event_cannot_reactivate_canceled_subscription(self):
        self.state = 'ACTIVE'
        self.assertEqual(self.activate().status_code, 200)
        self.state = 'CANCELED'
        self.assertEqual(self.webhook('invoice.paid').status_code, 200)
        self.assertEqual(self.activate().status_code, 403)

    def test_past_due_trial_and_expiry_deny_access(self):
        for state in ('TRIALING', 'PAST_DUE', 'SCHEDULED'):
            self.state = state
            self.assertEqual(self.activate().status_code, 403)
        self.state = 'ACTIVE'
        self.end = self.now - 1
        self.assertEqual(self.activate().status_code, 403)

    def test_ownership_currency_and_plan_verified(self):
        self.state = 'ACTIVE'
        for override in ({'customerId': 'foreign-customer'}, {'tenantId': 'foreign-tenant'},
                         {'planId': 'foreign-plan'}, {'latestInvoice': {'status': 'PAID', 'currency': 'USD'}}):
            self.snapshot_override = override
            self.assertEqual(self.activate().status_code, 503)

    def test_provider_outage_does_not_issue_new_lease(self):
        self.state = 'ACTIVE'
        self.assertEqual(self.activate().status_code, 200)
        self.app.renuvo.client.call.side_effect = RenuvoError()
        self.assertEqual(self.activate().status_code, 503)

    def test_existing_subscriber_gets_portal_without_duplicate_charge(self):
        self.state = 'ACTIVE'
        def existing(method, route, body=None):
            if method == 'POST' and route == '/v1/subscriptions':
                raise RenuvoError(409, {'existingSubscriptionId': 'sub-one'})
            return self.api(method, route, body)
        self.app.renuvo.client.call.side_effect = existing
        response = self.client.post('/api/orders', json={'plan_id': 'monthly'}, headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertIn('/portal/', response.json['checkout_url'])
        self.assertIsNone(response.json['license_key'])

    def test_portal_requires_license_and_links_are_restricted(self):
        self.assertEqual(self.client.post('/api/subscription/portal', json={}).status_code, 403)
        self.assertEqual(self.client.post('/api/subscription/portal', json={}, headers=self.auth).status_code, 200)
        self.assertFalse(safe_link('https://pay.renuvo.uz.evil.test/pay', False))
        self.assertFalse(safe_link('https://user@pay.renuvo.uz/pay', False))
        self.assertFalse(safe_link('https://pay.renuvo.uz/pay', True))

    def test_payme_route_disabled_and_admin_prices_not_misleading(self):
        self.assertEqual(self.client.post('/webhooks/payme', json={}).json['error']['code'], -32504)
        self.assertEqual(self.client.post('/api/admin/plans/monthly', json={}, headers={'Authorization': 'Bearer ' + 'a' * 40}).status_code, 409)


if __name__ == '__main__':
    unittest.main()
