"""Generate private server credentials and a public paid-panel configuration."""
import argparse,json,os,secrets,shlex
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def main():
 p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--api-url',required=True);p.add_argument('--panel-config',type=Path,required=True);a=p.parse_args()
 if not a.api_url.startswith('https://'):p.error('Public API URL must use HTTPS')
 a.data_dir.mkdir(parents=True,exist_ok=True);os.chmod(a.data_dir,0o700)
 key=a.data_dir/'signing.pem';env=a.data_dir/'server.env'
 if key.exists() or env.exists():p.error('Credentials already exist; preserve the original signing key')
 private=rsa.generate_private_key(public_exponent=65537,key_size=3072)
 key.write_bytes(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));os.chmod(key,0o600)
 public=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
 env.write_text('UZSCRIBE_DB='+shlex.quote(str((a.data_dir/'subscriptions.sqlite').resolve()))+'\nUZSCRIBE_SIGNING_KEY='+shlex.quote(str(key.resolve()))+'\nUZSCRIBE_ADMIN_TOKEN='+secrets.token_urlsafe(48)+'\nPAYME_TEST=1\nPAYME_MERCHANT_ID=\nPAYME_KEY=\n');os.chmod(env,0o600)
 a.panel_config.parent.mkdir(parents=True,exist_ok=True);a.panel_config.write_text(json.dumps({'mode':'subscription','api_url':a.api_url.rstrip('/'),'public_key':public},indent=2)+'\n')
 print('Server credentials saved privately. Only the public panel configuration may be shipped.')
if __name__=='__main__':main()
