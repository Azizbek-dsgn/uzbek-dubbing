import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
try:
 from billing.service import create_app, DAY, TIMEOUT_MS
 from cryptography.hazmat.primitives import serialization
 from cryptography.hazmat.primitives.asymmetric import rsa
 AVAILABLE=True
except ImportError:
 AVAILABLE=False

@unittest.skipUnless(AVAILABLE,'Separate billing server dependencies are not installed')
class BillingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.now=[int(time.time())]
  key=rsa.generate_private_key(public_exponent=65537,key_size=2048);self.private=key
  pem=Path(self.tmp.name)/'private.pem';pem.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
  self.app=create_app({'TESTING':True,'DB_PATH':str(Path(self.tmp.name)/'db.sqlite'),'SIGNING_KEY':str(pem),'ADMIN_TOKEN':'a'*40,'PAYME_KEY':'test-key','PAYME_MERCHANT_ID':'merchant-id','CLOCK':lambda:self.now[0]})
  self.client=self.app.test_client();self.admin={'Authorization':'Bearer '+'a'*40};self.auth={'Authorization':'Basic '+base64.b64encode(b'Paycom:test-key').decode()}
 def order(self,license_key=None,plan='monthly'):
  r=self.client.post('/api/orders',json={'plan_id':plan},headers={'Authorization':'Bearer '+license_key} if license_key else {})
  self.assertEqual(r.status_code,200);return r.json
 def rpc(self,method,params):return self.client.post('/webhooks/payme',json={'id':7,'method':method,'params':params},headers=self.auth).json
 def pay(self,o,identity='pay-1'):
  p={'id':identity,'time':self.now[0]*1000,'amount':o['amount_uzs']*100,'account':{'order_id':o['order_id']}}
  self.assertIn('result',self.rpc('CreateTransaction',p));self.assertIn('result',self.rpc('PerformTransaction',{'id':identity}));return p
 def activate(self,key,device='1'*64):return self.client.post('/api/activate',json={'device_id':device,'label':'Windows'},headers={'Authorization':'Bearer '+key})
 def test_payment_amount_checkout_and_activation(self):
  o=self.order();self.assertEqual(o['amount_uzs'],49000)
  text=base64.b64decode(o['checkout_url'].rsplit('/',1)[1]).decode();self.assertIn('a=4900000',text);self.assertIn('ac.order_id='+o['order_id'],text)
  self.assertEqual(self.activate(o['license_key']).status_code,403);self.pay(o);r=self.activate(o['license_key']);self.assertEqual(r.status_code,200)
  self.assertEqual(r.json['expires_at'],self.now[0]+30*DAY)
 def test_payme_auth_cannot_grant_access(self):
  o=self.order();r=self.client.post('/webhooks/payme',json={'method':'PerformTransaction','params':{'id':'x'}});self.assertEqual(r.json['error']['code'],-32504);self.assertEqual(self.activate(o['license_key']).status_code,403)
 def test_wrong_amount_and_missing_account(self):
  o=self.order();p={'amount':1,'account':{'order_id':o['order_id']}}
  self.assertEqual(self.rpc('CheckPerformTransaction',p)['error']['code'],-31001)
  self.assertEqual(self.rpc('CheckPerformTransaction',{'amount':1,'account':{}})['error']['code'],-31050)
 def test_parallel_duplicate_perform_extends_once(self):
  o=self.order();p=self.pay(o)
  with ThreadPoolExecutor(max_workers=6) as executor:responses=list(executor.map(lambda _:self.app.store.payme('PerformTransaction',{'id':'pay-1'}),range(12)))
  self.assertTrue(all(r['result']['state']==2 for r in responses));self.assertIn('result',self.rpc('CreateTransaction',p))
  self.assertEqual(self.activate(o['license_key']).json['expires_at'],self.now[0]+30*DAY)
 def test_one_order_cannot_have_two_payments(self):
  o=self.order();p=self.pay(o);p['id']='other';self.assertEqual(self.rpc('CreateTransaction',p)['error']['code'],-31008)
 def test_refund_revokes_only_corresponding_period(self):
  o=self.order();self.pay(o);next_order=self.order(o['license_key']);self.pay(next_order,'pay-2')
  self.assertEqual(self.activate(o['license_key']).json['expires_at'],self.now[0]+60*DAY)
  result=self.rpc('CancelTransaction',{'id':'pay-1','reason':1});self.assertEqual(result['result']['state'],-2)
  self.assertEqual(self.activate(o['license_key']).json['expires_at'],self.now[0]+30*DAY)
  self.rpc('CancelTransaction',{'id':'pay-1','reason':1});self.assertEqual(self.activate(o['license_key']).json['expires_at'],self.now[0]+30*DAY)
  self.rpc('CancelTransaction',{'id':'pay-2','reason':1});self.assertEqual(self.activate(o['license_key']).status_code,403)
 def test_timeout_reservation_is_persistent_and_repayable(self):
  o=self.order();p={'id':'expired','time':self.now[0]*1000,'amount':4900000,'account':{'order_id':o['order_id']}}
  self.rpc('CreateTransaction',p);self.now[0]+=TIMEOUT_MS//1000+1
  self.assertEqual(self.rpc('PerformTransaction',{'id':'expired'})['error']['code'],-31008)
  state=self.rpc('CheckTransaction',{'id':'expired'})['result'];self.assertEqual(state['state'],-1);self.assertEqual(state['reason'],4)
  self.pay(o,'new-payment');self.assertEqual(self.activate(o['license_key']).status_code,200)
 def test_cancel_unpaid_allows_new_transaction(self):
  o=self.order();p={'id':'unpaid','time':self.now[0]*1000,'amount':4900000,'account':{'order_id':o['order_id']}};self.rpc('CreateTransaction',p)
  self.assertEqual(self.rpc('CancelTransaction',{'id':'unpaid','reason':1})['result']['state'],-1);self.pay(o,'retry')
 def test_statement_inclusive_time_and_fiscal_storage(self):
  o=self.order();self.pay(o)
  statement=self.rpc('GetStatement',{'from':self.now[0]*1000,'to':self.now[0]*1000})['result']['transactions'];self.assertEqual(len(statement),1);self.assertEqual(statement[0]['amount'],4900000)
  self.assertTrue(self.rpc('SetFiscalData',{'id':'pay-1','fiscal_data':{'receipt_id':'synthetic'}})['result']['success'])
 def test_price_change_does_not_mutate_pending_order(self):
  o=self.order();r=self.client.post('/api/admin/plans/monthly',json={'title':'Pro','price_uzs':79000,'days':30,'seats':2,'enabled':1},headers=self.admin);self.assertEqual(r.status_code,200)
  self.pay(o);self.assertEqual(self.order()['amount_uzs'],79000)
 def test_device_limit_release_and_admin_block(self):
  o=self.order();self.pay(o);key=o['license_key'];self.assertEqual(self.activate(key,'1'*64).status_code,200);self.assertEqual(self.activate(key,'2'*64).status_code,200);self.assertEqual(self.activate(key,'3'*64).status_code,403)
  self.client.post('/api/devices/remove',json={'device_id':'1'*64},headers={'Authorization':'Bearer '+key});self.assertEqual(self.activate(key,'3'*64).status_code,200)
  identity=self.client.get('/api/license',headers={'Authorization':'Bearer '+key}).json['license_id'];self.client.post('/api/admin/licenses/'+identity,json={'action':'block','blocked':1},headers=self.admin);self.assertEqual(self.activate(key).status_code,403)
 def test_admin_auth_and_grant(self):
  self.assertEqual(self.client.get('/api/admin/overview').status_code,401)
  self.assertEqual(self.client.post('/api/admin/licenses',json={'days':10}).status_code,401)
  key=self.client.post('/api/admin/licenses',json={'label':'test','days':3,'seats':1},headers=self.admin).json['license_key'];self.assertEqual(self.activate(key).status_code,200)
  self.assertNotIn(key,json.dumps(self.client.get('/api/admin/overview',headers=self.admin).json))
 def test_unconfigured_service_fails_closed(self):
  app=create_app({'TESTING':True,'DB_PATH':str(Path(self.tmp.name)/'missing.sqlite'),'PAYME_KEY':'','SIGNING_KEY':''});r=app.test_client().post('/api/orders',json={'plan_id':'monthly'});self.assertEqual(r.status_code,503)
 def test_expiry_and_invalid_input(self):
  o=self.order();self.pay(o);self.now[0]+=31*DAY;self.assertEqual(self.activate(o['license_key']).status_code,403)
  self.assertEqual(self.client.post('/api/orders',json={'plan_id':[]}).status_code,400)
 def test_node_verifies_actual_server_signature(self):
  node=os.environ.get('UZSCRIBE_NODE') or shutil.which('node')
  if not node:self.skipTest('Node is unavailable')
  o=self.order();self.pay(o);token=self.activate(o['license_key']).json['token'];public=self.private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
  fixture=Path(self.tmp.name)/'token.json';fixture.write_text(json.dumps({'token':token,'public':public,'now':self.now[0]}))
  script="const fs=require('fs'),assert=require('assert'),core=require('./adobe/UzbekSubtitles/license-core.js'),f=JSON.parse(fs.readFileSync(process.argv[1]));assert(core.validate(f.token,f.public,'1'.repeat(64),f.now,0,'captions'));assert.throws(()=>core.validate(f.token+'X',f.public,'1'.repeat(64),f.now,0));assert.throws(()=>core.validate(f.token,f.public,'2'.repeat(64),f.now,0));assert.throws(()=>core.validate(f.token,f.public,'1'.repeat(64),f.now+259201,0));assert.throws(()=>core.validate(f.token,f.public,'1'.repeat(64),f.now,f.now+600));"
  subprocess.run([node,'-e',script,str(fixture)],check=True)

 def test_release_rejects_obsolete_paid_configuration(self):
  from tools import build_release
  with self.assertRaisesRegex(ValueError,'Obuna distributivi olib tashlangan'):
   build_release.build(Path(self.tmp.name)/'model',Path(self.tmp.name)/'buyer.zip',license_config=Path('old-config.json'))
