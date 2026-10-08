const assert=require('assert'),fs=require('fs'),vm=require('vm');
const script=fs.readFileSync('adobe/UzbekSubtitles/donation-panel.js','utf8'),DAY=86400000,KEY='uzscribe.donation.v1';
function fixture(memory, now=100*DAY, opts={}){
 const els={};for(const id of ['donationNotice','support','donationNever','donateLink','donationStatus','donationDismiss','donationShow'])els[id]={hidden:id==='donationNotice',open:false,checked:false,textContent:'',focus(){this.focused=true}};
 let opened='',clicks=0;const storage={getItem(k){if(opts.failRead)throw Error('blocked');return memory[k]||null},setItem(k,v){if(opts.failWrite)throw Error('quota');memory[k]=v}};
 const doc={getElementById:id=>els[id],uzscribeBusy:!!opts.busy};
 const context={document:doc,localStorage:storage,Date:{now:()=>now},JSON,Math,isFinite,window:{innerHeight:opts.height||700}};
 if(!opts.browser)context.__adobe_cep__={openURLInDefaultBrowser(u){if(opts.failOpen)throw Error('unavailable');opened=u;clicks++}};
 vm.runInNewContext(script,context);return {els,doc,opened:()=>opened,clicks:()=>clicks};
}
let memory={},f=fixture(memory);
assert(!f.els.donationNotice.hidden,'first opening shows an inline invitation');
f=fixture(memory);assert(f.els.donationNotice.hidden,'reopening without dismissing must not repeat it');
f=fixture(memory,131*DAY);assert(!f.els.donationNotice.hidden,'next monthly slot is available');f.els.donationDismiss.onclick();assert(f.els.donationNotice.hidden);
assert(fixture(memory,132*DAY).els.donationNotice.hidden);
f=fixture(memory,162*DAY);let stopped=false;f.els.donationShow.onclick({stopPropagation(){stopped=true}});assert(stopped&&f.els.support.open&&f.els.donateLink.focused&&f.els.donationNotice.hidden);
f.els.donationNever.checked=true;f.els.donationNever.onchange();assert(JSON.parse(memory[KEY]).never);assert(fixture(memory,900*DAY).els.donationNotice.hidden);
f=fixture(memory,901*DAY);assert(f.els.donationNever.checked);f.els.donationShow.onclick();assert(f.els.support.open,'manual support remains available after opting out');
let prevented=false;f.els.donateLink.onclick({preventDefault(){prevented=true}});assert(prevented);assert.equal(f.opened(),'https://taps.uz/fikrosfera/d');assert.equal(f.clicks(),1);
assert(JSON.parse(memory[KEY]).never,'opening Taps must not undo the permanent opt-out');
f.els.donationNever.checked=false;f.els.donationNever.onchange();assert(!JSON.parse(memory[KEY]).never);
assert(fixture(memory,950*DAY).els.donationNotice.hidden,'opening the link snoozes for 90 days');
for(const opts of [{failRead:true},{failWrite:true},{height:300},{busy:true}])assert(fixture({},100*DAY,opts).els.donationNotice.hidden);
f=fixture({[KEY]:'broken JSON'});assert(f.els.donationNotice.hidden);f.els.donationShow.onclick();assert(f.els.support.open);
f=fixture({},100*DAY,{failOpen:true});f.els.donateLink.onclick({preventDefault(){}});assert(f.els.donationStatus.textContent.includes('QR'));assert.equal(f.clicks(),0);
f=fixture({},100*DAY,{browser:true});f.els.donateLink.onclick({preventDefault(){throw Error('keep normal browser link')}});assert(f.els.donationNotice.hidden);
const html=fs.readFileSync('adobe/UzbekSubtitles/index.html','utf8');assert(html.includes('assets/donation-qr.svg'));assert(html.includes('href="https://taps.uz/fikrosfera/d"'));assert(!html.includes('license-panel.js'));assert(!html.includes('id="subscription"'));
for(const name of ['panel.js','animation-panel.js','podcast-panel.js','reels-panel.js'])assert(!/uzscribeLicense|license-config|allowLicense|bridge\.authorize/.test(fs.readFileSync('adobe/UzbekSubtitles/'+name,'utf8')),name+' must have no subscription gate');
console.log('Donations: monthly limits, persistent opt-out, no blocking, storage failures, offline UI and exact Taps browser handoff OK');
