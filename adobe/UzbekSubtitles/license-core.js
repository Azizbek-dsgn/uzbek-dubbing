'use strict';
var crypto=require('crypto');
function decode(s){if(!/^[A-Za-z0-9_-]+$/.test(s))throw Error('Litsenziya formati noto‘g‘ri.');return Buffer.from(s.replace(/-/g,'+').replace(/_/g,'/'),'base64');}
exports.validate=function(token,publicKey,device,now,lastSeen,feature){
  if(!publicKey || typeof token!=='string' || token.length>12000)throw Error('Obunani faollashtiring.');
  var parts=token.split('.');if(parts.length!==2)throw Error('Litsenziya formati noto‘g‘ri.');
  var verifier=crypto.createVerify('RSA-SHA256');verifier.update(parts[0]);verifier.end();
  if(!verifier.verify(publicKey,decode(parts[1])))throw Error('Litsenziya imzosi noto‘g‘ri.');
  var c=JSON.parse(decode(parts[0]).toString('utf8'));
  if(c.v!==1 || c.device_id!==device || !Array.isArray(c.features) || typeof c.issued_at!=='number' || typeof c.expires_at!=='number' || c.expires_at>c.subscription_expires_at || c.expires_at-c.issued_at>259200)throw Error('Litsenziya mos kelmadi.');
  if(now<c.issued_at-300 || now<Number(lastSeen||0)-300)throw Error('Kompyuter vaqtini to‘g‘rilab, obunani yangilang.');
  if(now>=c.expires_at)throw Error('Obunani internet orqali yangilang yoki uzaytiring.');
  if(feature && c.features.indexOf(feature)<0)throw Error('Bu imkoniyat tarifingizda yo‘q.');
  return c;
};
