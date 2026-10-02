"""UZS subscriptions, Payme Merchant API and signed device leases."""
from __future__ import annotations
import base64
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

DAY = 86400
TIMEOUT_MS = 43_200_000

class PaymentError(Exception):
    def __init__(self, code, message, data=None):
        self.code, self.message, self.data = code, message, data

def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()

def b64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()

class Store:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = str(path), clock
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,title TEXT,price_uzs INTEGER,days INTEGER,seats INTEGER,enabled INTEGER);
            CREATE TABLE IF NOT EXISTS licenses(id TEXT PRIMARY KEY,key_hash TEXT UNIQUE,label TEXT,blocked INTEGER DEFAULT 0,created INTEGER);
            CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,license_id TEXT,plan_id TEXT,amount INTEGER,days INTEGER,seats INTEGER,status TEXT,created INTEGER);
            CREATE TABLE IF NOT EXISTS payments(id TEXT PRIMARY KEY,order_id TEXT,payme_time INTEGER,create_time INTEGER,perform_time INTEGER DEFAULT 0,cancel_time INTEGER DEFAULT 0,state INTEGER,reason INTEGER,fiscal TEXT);
            CREATE TABLE IF NOT EXISTS grants(id TEXT PRIMARY KEY,license_id TEXT,order_id TEXT UNIQUE,at INTEGER,days INTEGER,seats INTEGER,revoked INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS devices(license_id TEXT,device_id TEXT,label TEXT,seen INTEGER,PRIMARY KEY(license_id,device_id));
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,at INTEGER,action TEXT,subject TEXT);
            ''')
            db.executemany('INSERT OR IGNORE INTO plans VALUES(?,?,?,?,?,1)', [('monthly','UzScribe Pro · 30 kun',49000,30,2),('yearly','UzScribe Pro · 365 kun',490000,365,2)])

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('BEGIN IMMEDIATE')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def audit(self, db, action, subject):
        db.execute('INSERT INTO audit(at,action,subject) VALUES(?,?,?)',(int(self.clock()),action,subject))

    def issue(self, db, label=''):
        key = 'UZS-' + secrets.token_urlsafe(32)
        identity = secrets.token_hex(12)
        db.execute('INSERT INTO licenses(id,key_hash,label,created) VALUES(?,?,?,?)',(identity,fingerprint(key),label,int(self.clock())))
        self.audit(db,'license.issue',identity)
        return identity, key

    def license(self, db, key):
        row = db.execute('SELECT * FROM licenses WHERE key_hash=?',(fingerprint(key),)).fetchone()
        if not row or row['blocked']:
            raise PaymentError(403,'Litsenziya topilmadi yoki bloklangan.')
        return row

    def entitlement(self, db, identity):
        end, seats = 0, 0
        for g in db.execute('SELECT * FROM grants WHERE license_id=? AND revoked=0 ORDER BY at,rowid',(identity,)):
            end = max(end,g['at']) + g['days'] * DAY
            seats = g['seats']
        return {'active':end > self.clock(),'expires_at':end,'seats':seats}

    def order(self, db, params):
        account=params.get('account')
        if not isinstance(account,dict) or not isinstance(account.get('order_id'),str):
            raise PaymentError(-31050,'Buyurtma topilmadi.','order_id')
        row=db.execute('SELECT * FROM orders WHERE id=?',(account['order_id'],)).fetchone()
        if not row:raise PaymentError(-31050,'Buyurtma topilmadi.','order_id')
        if type(params.get('amount')) is not int or params['amount'] != row['amount']:
            raise PaymentError(-31001,'To‘lov summasi noto‘g‘ri.')
        return row

    def transaction(self, db, identity):
        row=db.execute('SELECT * FROM payments WHERE id=?',(identity,)).fetchone()
        if not row:raise PaymentError(-31003,'Tranzaksiya topilmadi.')
        if row['state']==1 and self.clock()*1000-row['payme_time']>=TIMEOUT_MS:
            db.execute('UPDATE payments SET state=-1,reason=4,cancel_time=? WHERE id=?',(int(self.clock()*1000),identity))
            db.execute("UPDATE orders SET status='pending' WHERE id=?",(row['order_id'],))
            row=db.execute('SELECT * FROM payments WHERE id=?',(identity,)).fetchone()
        return row

    @staticmethod
    def transaction_result(row):
        return {k:row[k] for k in ('create_time','perform_time','cancel_time','state','reason')} | {'transaction':row['id']}

    def payme(self, method, params):
        with self.db() as db:
            try:
                return {'result':self._payme(db,method,params)}
            except PaymentError as e:
                error={'code':e.code,'message':{'uz':e.message,'ru':e.message,'en':e.message}}
                if e.data is not None:error['data']=e.data
                return {'error':error}

    def _payme(self, db, method, p):
        now=int(self.clock()*1000)
        if method=='GetStatement':
            if type(p.get('from')) is not int or type(p.get('to')) is not int:raise PaymentError(-32602,'Vaqt oralig‘i noto‘g‘ri.')
            rows=db.execute('SELECT * FROM payments WHERE payme_time BETWEEN ? AND ? ORDER BY payme_time,id',(p['from'],p['to'])).fetchall()
            items=[]
            for row in rows:
                row=self.transaction(db,row['id']);o=db.execute('SELECT * FROM orders WHERE id=?',(row['order_id'],)).fetchone()
                items.append(self.transaction_result(row)|{'id':row['id'],'time':row['payme_time'],'amount':o['amount'],'account':{'order_id':o['id']}})
            return {'transactions':items}
        if method in ('CheckPerformTransaction','CreateTransaction'):
            o=self.order(db,p)
            if method=='CreateTransaction':
                identity=p.get('id');created=p.get('time')
                if not isinstance(identity,str) or not identity or len(identity)>128 or type(created) is not int or created<0 or created>now+300000:raise PaymentError(-32602,'Tranzaksiya parametrlari noto‘g‘ri.')
                duplicate=db.execute('SELECT id FROM payments WHERE id=?',(identity,)).fetchone()
                if duplicate:
                    row=self.transaction(db,identity)
                    if row['order_id']!=o['id'] or row['payme_time']!=created:raise PaymentError(-31008,'Tranzaksiya mos kelmadi.')
                    if row['state']<0:raise PaymentError(-31008,'Tranzaksiya bekor qilingan.')
                    return {'create_time':row['create_time'],'transaction':identity,'state':row['state']}
            # Expire all previous reservations before deciding if this order can be paid.
            for row in db.execute('SELECT id FROM payments WHERE order_id=? AND state=1',(o['id'],)).fetchall():self.transaction(db,row['id'])
            status=db.execute('SELECT status FROM orders WHERE id=?',(o['id'],)).fetchone()['status']
            if status in ('paid','refunded'):raise PaymentError(-31008,'Buyurtma allaqachon yakunlangan.')
            lic=db.execute('SELECT blocked FROM licenses WHERE id=?',(o['license_id'],)).fetchone()
            if lic['blocked']:raise PaymentError(-31050,'Litsenziya bloklangan.','order_id')
            if method=='CheckPerformTransaction':return {'allow':True}
            if now-created>=TIMEOUT_MS:raise PaymentError(-31008,'Tranzaksiya vaqti tugagan.')
            if db.execute('SELECT id FROM payments WHERE order_id=? AND state=1',(o['id'],)).fetchone():raise PaymentError(-31008,'Buyurtma uchun boshqa tranzaksiya mavjud.')
            db.execute('INSERT INTO payments(id,order_id,payme_time,create_time,state) VALUES(?,?,?,?,1)',(identity,o['id'],created,now))
            db.execute("UPDATE orders SET status='reserved' WHERE id=?",(o['id'],))
            return {'create_time':now,'transaction':identity,'state':1}
        if method not in ('PerformTransaction','CancelTransaction','CheckTransaction','SetFiscalData'):
            raise PaymentError(-32601,'Usul topilmadi.')
        if not isinstance(p.get('id'),str):raise PaymentError(-32602,'Tranzaksiya ID noto‘g‘ri.')
        row=self.transaction(db,p['id'])
        if method=='PerformTransaction':
            if row['state']<0:raise PaymentError(-31008,'Bekor qilingan tranzaksiya.')
            if row['state']==1:
                o=db.execute('SELECT * FROM orders WHERE id=?',(row['order_id'],)).fetchone()
                if db.execute('SELECT blocked FROM licenses WHERE id=?',(o['license_id'],)).fetchone()['blocked']:raise PaymentError(-31008,'Litsenziya bloklangan.')
                db.execute('INSERT INTO grants VALUES(?,?,?,?,?,?,0)',(secrets.token_hex(12),o['license_id'],o['id'],int(self.clock()),o['days'],o['seats']))
                db.execute('UPDATE payments SET state=2,perform_time=? WHERE id=?',(now,row['id']))
                db.execute("UPDATE orders SET status='paid' WHERE id=?",(o['id'],));self.audit(db,'payment.paid',o['id'])
            row=self.transaction(db,p['id'])
            return {'transaction':row['id'],'perform_time':row['perform_time'],'state':row['state']}
        if method=='CancelTransaction':
            if type(p.get('reason')) is not int or p['reason'] not in range(1,6):raise PaymentError(-32602,'Bekor qilish sababi noto‘g‘ri.')
            if row['state']>0:
                new_state=-2 if row['state']==2 else -1
                db.execute('UPDATE payments SET state=?,cancel_time=?,reason=? WHERE id=?',(new_state,now,p['reason'],row['id']))
                db.execute('UPDATE grants SET revoked=1 WHERE order_id=?',(row['order_id'],))
                db.execute('UPDATE orders SET status=? WHERE id=?',('refunded' if new_state==-2 else 'pending',row['order_id']))
                self.audit(db,'payment.cancel',row['order_id'])
            row=self.transaction(db,p['id']);return {'transaction':row['id'],'cancel_time':row['cancel_time'],'state':row['state']}
        if method=='SetFiscalData':
            db.execute('UPDATE payments SET fiscal=? WHERE id=?',(json.dumps(p,ensure_ascii=False),row['id']))
            return {'success':True}
        return self.transaction_result(row)


def create_app(config=None):
    app=Flask(__name__,static_folder='static')
    app.config.update(DB_PATH=os.environ.get('UZSCRIBE_DB','billing-data/subscriptions.sqlite'),ADMIN_TOKEN=os.environ.get('UZSCRIBE_ADMIN_TOKEN',''),SIGNING_KEY=os.environ.get('UZSCRIBE_SIGNING_KEY',''),PAYME_KEY=os.environ.get('PAYME_KEY',''),PAYME_MERCHANT_ID=os.environ.get('PAYME_MERCHANT_ID',''),PAYME_TEST=os.environ.get('PAYME_TEST','1')=='1',MAX_CONTENT_LENGTH=32*1024,CLOCK=time.time)
    if config:app.config.update(config)
    if os.environ.get('UZSCRIBE_TRUST_PROXY')=='1':app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1)
    merchant=app.config['PAYME_MERCHANT_ID']
    if merchant and not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',merchant):raise ValueError('Invalid Payme merchant identifier')
    store=Store(app.config['DB_PATH'],app.config['CLOCK']);app.store=store
    private=None
    if app.config['SIGNING_KEY']:
        private=serialization.load_pem_private_key(Path(app.config['SIGNING_KEY']).read_bytes(),password=None)
        if private.key_size<2048:raise ValueError('RSA signing key must be at least 2048 bits')
    limits={},threading.Lock()

    def bearer():
        h=request.headers.get('Authorization','')
        return h[7:] if h.startswith('Bearer ') else ''
    def admin():
        token=app.config['ADMIN_TOKEN']
        if len(token)<32 or not hmac.compare_digest(token,bearer()):raise PaymentError(401,'Boshqaruv kaliti noto‘g‘ri.')
    def body():
        if not request.is_json:raise PaymentError(400,'JSON so‘rov kerak.')
        value=request.get_json(silent=True)
        if not isinstance(value,dict):raise PaymentError(400,'So‘rov noto‘g‘ri.')
        return value
    def bounded(value,low,high):
        if type(value) is not int or not low<=value<=high:raise PaymentError(400,'Qiymat oralig‘i noto‘g‘ri.')
        return value
    def clock():return int(app.config['CLOCK']())

    @app.before_request
    def rate_limit():
        if request.path.startswith('/api/'):
            bucket=(request.remote_addr,request.path,clock()//600)
            with limits[1]:
                if len(limits[0])>10000:limits[0].clear()
                limits[0][bucket]=limits[0].get(bucket,0)+1
                if limits[0][bucket]>100:raise PaymentError(429,'Ko‘p so‘rov. Biroz kuting.')

    @app.after_request
    def headers(response):
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.errorhandler(PaymentError)
    def problem(e):return jsonify(error=e.message),e.code if 400<=e.code<=599 else 400

    @app.get('/')
    def checkout_page():return send_from_directory(app.static_folder,'checkout.html')
    @app.get('/admin')
    def admin_page():return send_from_directory(app.static_folder,'admin.html')
    @app.get('/health')
    def health():return jsonify(status='ok',payments_configured=bool(app.config['PAYME_KEY'] and app.config['PAYME_MERCHANT_ID']),signing_configured=bool(private))
    @app.get('/api/plans')
    def plans():
        with store.db() as db:rows=[dict(r) for r in db.execute('SELECT * FROM plans WHERE enabled=1 ORDER BY price_uzs')]
        return jsonify(plans=rows,currency='UZS',renewal='manual',payments_ready=bool(app.config['PAYME_KEY'] and app.config['PAYME_MERCHANT_ID'] and private),sandbox=app.config['PAYME_TEST'])

    @app.post('/api/orders')
    def purchase():
        p=body()
        if not isinstance(p.get('plan_id'),str):raise PaymentError(400,'Tarif ID noto‘g‘ri.')
        if not private or not app.config['PAYME_KEY'] or not app.config['PAYME_MERCHANT_ID']:raise PaymentError(503,'To‘lov tizimi hali ulanmagan.')
        with store.db() as db:
            plan=db.execute('SELECT * FROM plans WHERE id=? AND enabled=1',(p.get('plan_id'),)).fetchone()
            if not plan:raise PaymentError(400,'Tarif topilmadi.')
            raw=None
            if bearer():identity=store.license(db,bearer())['id']
            else:identity,raw=store.issue(db)
            order=secrets.token_hex(16);amount=plan['price_uzs']*100
            db.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)',(order,identity,plan['id'],amount,plan['days'],plan['seats'],'pending',clock()))
            text=f"m={app.config['PAYME_MERCHANT_ID']};ac.order_id={order};a={amount};l=uz;cr=860"
            origin='https://checkout.test.paycom.uz/' if app.config['PAYME_TEST'] else 'https://checkout.paycom.uz/'
            checkout=origin+base64.b64encode(text.encode()).decode()
            store.audit(db,'order.create',order)
        return jsonify(order_id=order,license_key=raw,checkout_url=checkout,amount_uzs=plan['price_uzs'],sandbox=app.config['PAYME_TEST'])

    @app.get('/api/license')
    def status():
        with store.db() as db:
            lic=store.license(db,bearer());ent=store.entitlement(db,lic['id'])
            devices=[dict(r) for r in db.execute('SELECT device_id,label,seen FROM devices WHERE license_id=?',(lic['id'],))]
        return jsonify(license_id=lic['id'],**ent,devices=devices,renewal='manual')

    @app.post('/api/activate')
    def activate():
        p=body();device=p.get('device_id','')
        if not isinstance(device,str) or not re.fullmatch(r'[a-f0-9]{64}',device):raise PaymentError(400,'Qurilma ID noto‘g‘ri.')
        if not private:raise PaymentError(503,'Litsenziya serveri sozlanmagan.')
        with store.db() as db:
            lic=store.license(db,bearer());ent=store.entitlement(db,lic['id'])
            if not ent['active']:raise PaymentError(403,'Obuna muddati tugagan yoki to‘lov kutilmoqda.')
            existing=db.execute('SELECT 1 FROM devices WHERE license_id=? AND device_id=?',(lic['id'],device)).fetchone()
            count=db.execute('SELECT COUNT(*) FROM devices WHERE license_id=?',(lic['id'],)).fetchone()[0]
            if not existing and count>=ent['seats']:raise PaymentError(403,'Qurilmalar limiti. Keraksiz qurilmani uzing.')
            db.execute('INSERT OR REPLACE INTO devices VALUES(?,?,?,?)',(lic['id'],device,str(p.get('label','Kompyuter'))[:60],clock()))
            claims={'v':1,'license_id':lic['id'],'device_id':device,'issued_at':clock(),'expires_at':min(ent['expires_at'],clock()+3*DAY),'subscription_expires_at':ent['expires_at'],'features':['captions','animations','podcast','reels'],'seats':ent['seats']}
            payload=b64url(json.dumps(claims,sort_keys=True,separators=(',',':')).encode());signature=private.sign(payload.encode(),padding.PKCS1v15(),hashes.SHA256())
        return jsonify(token=payload+'.'+b64url(signature),**ent)

    @app.post('/api/devices/remove')
    def remove_device():
        p=body()
        if not isinstance(p.get('device_id'),str):raise PaymentError(400,'Qurilma ID kerak.')
        with store.db() as db:
            lic=store.license(db,bearer());db.execute('DELETE FROM devices WHERE license_id=? AND device_id=?',(lic['id'],p.get('device_id')));store.audit(db,'device.remove',lic['id'])
        return jsonify(success=True)

    @app.post('/webhooks/payme')
    def payme():
        p=request.get_json(silent=True)
        identity=p.get('id') if isinstance(p,dict) else None
        key=app.config['PAYME_KEY'];expected='Basic '+base64.b64encode(('Paycom:'+key).encode()).decode()
        if not key or not hmac.compare_digest(request.headers.get('Authorization',''),expected):return jsonify(id=identity,error={'code':-32504,'message':'Authorization failed'})
        if not isinstance(p,dict) or not isinstance(p.get('params'),dict):return jsonify(id=identity,error={'code':-32600,'message':'Invalid Request'})
        return jsonify(id=identity,**store.payme(p.get('method'),p['params']))

    @app.get('/api/admin/overview')
    def overview():
        admin()
        with store.db() as db:
            licenses=[]
            for row in db.execute('SELECT id,label,blocked,created FROM licenses ORDER BY created DESC LIMIT 500'):
                licenses.append(dict(row)|store.entitlement(db,row['id']))
            orders=[dict(r) for r in db.execute('SELECT * FROM orders ORDER BY created DESC LIMIT 500')]
            plans=[dict(r) for r in db.execute('SELECT * FROM plans ORDER BY price_uzs')]
            audit=[dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]
            revenue=db.execute("SELECT COALESCE(SUM(amount),0)/100 FROM orders WHERE status='paid'").fetchone()[0]
        return jsonify(licenses=licenses,orders=orders,plans=plans,audit=audit,revenue_uzs=revenue,sandbox=app.config['PAYME_TEST'],payments_ready=bool(private and app.config['PAYME_KEY'] and app.config['PAYME_MERCHANT_ID']))

    @app.post('/api/admin/plans/<identity>')
    def edit_plan(identity):
        admin();p=body()
        if not re.fullmatch('[a-z0-9_-]{1,32}',identity):raise PaymentError(400,'Tarif ID noto‘g‘ri.')
        title=str(p.get('title','')).strip()[:80]
        if not title:raise PaymentError(400,'Tarif nomi kerak.')
        price=bounded(p.get('price_uzs'),1000,100000000);days=bounded(p.get('days'),1,730);seats=bounded(p.get('seats'),1,20);enabled=bounded(p.get('enabled'),0,1)
        with store.db() as db:
            db.execute('INSERT OR REPLACE INTO plans VALUES(?,?,?,?,?,?)',(identity,title,price,days,seats,enabled));store.audit(db,'plan.edit',identity)
        return jsonify(success=True)

    @app.post('/api/admin/licenses')
    def issue_license():
        admin();p=body();days=bounded(p.get('days',0),0,730);seats=bounded(p.get('seats',2),1,20)
        with store.db() as db:
            identity,key=store.issue(db,str(p.get('label',''))[:80])
            if days:db.execute('INSERT INTO grants VALUES(?,?,NULL,?,?,?,0)',(secrets.token_hex(12),identity,clock(),days,seats))
        return jsonify(license_id=identity,license_key=key)

    @app.post('/api/admin/licenses/<identity>')
    def edit_license(identity):
        admin();p=body()
        with store.db() as db:
            if not db.execute('SELECT 1 FROM licenses WHERE id=?',(identity,)).fetchone():raise PaymentError(404,'Litsenziya topilmadi.')
            action=p.get('action')
            if action=='block':db.execute('UPDATE licenses SET blocked=? WHERE id=?',(bounded(p.get('blocked'),0,1),identity))
            elif action=='extend':db.execute('INSERT INTO grants VALUES(?,?,NULL,?,?,?,0)',(secrets.token_hex(12),identity,clock(),bounded(p.get('days'),1,730),bounded(p.get('seats',2),1,20)))
            elif action=='reset_devices':db.execute('DELETE FROM devices WHERE license_id=?',(identity,))
            else:raise PaymentError(400,'Amal topilmadi.')
            store.audit(db,'license.'+action,identity)
        return jsonify(success=True)
    return app
