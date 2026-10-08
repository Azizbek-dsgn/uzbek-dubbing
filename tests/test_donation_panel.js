const assert=require('assert'),fs=require('fs'),vm=require('vm'),path=require('path');
const source=fs.readFileSync('adobe/UzbekSubtitles/donation-panel.js','utf8');
function fixture(memory={},options={}){
 const elements={};for(const id of ['donationNotice','support','donateLink','donationStatus','donationShow'])elements[id]={hidden:true,open:false,textContent:'',focus(){this.focused=true}};
 let opened='',calls=[];
 const ctx={document:{getElementById:id=>elements[id]},JSON,Math,isFinite,localStorage:{getItem:k=>memory[k]||null,setItem(k,v){if(options.blocked)throw Error('blocked');memory[k]=v}},window:{},process:{platform:options.platform||'darwin',env:{SystemRoot:'C:\\Windows'}}};
 if(!options.browser){ctx.__adobe_cep__={};ctx.require=n=>n==='path'?path.win32:{execFile(...args){calls.push(args);if(options.error)args[args.length-1](Error('failed'));else args[args.length-1](null)}};
 if(options.bridge)ctx.window.cep={util:{openURLInDefaultBrowser(u){opened=u;return options.code||0}}};}
 vm.runInNewContext(source,ctx);return {elements,opened:()=>opened,calls};
}
let memory={};for(let i=1;i<=15;i++){const f=fixture(memory);assert(!f.elements.donationNotice.hidden);assert.equal(f.elements.support.open,i%5===0);}
let f=fixture({'uzscribe.donation.v1':JSON.stringify({never:true,nextNoticeAt:9999999999999})});assert(!f.elements.donationNotice.hidden,'old opt-out is removed');
f.elements.donationShow.onclick({stopPropagation(){}});assert(f.elements.support.open&&f.elements.donateLink.focused);
f=fixture({}, {bridge:true});f.elements.donateLink.onclick({preventDefault(){}});assert.equal(f.opened(),'https://taps.uz/fikrosfera/d');assert.equal(f.calls.length,0);
for(const platform of ['darwin','win32']){
 f=fixture({}, {platform,bridge:true,code:201});f.elements.donateLink.onclick({preventDefault(){}});assert.equal(f.calls.length,1);assert(f.calls[0][1].includes('https://taps.uz/fikrosfera/d'));assert.equal(f.calls[0][0],platform==='darwin'?'/usr/bin/open':'C:\\Windows\\System32\\rundll32.exe');
}
f=fixture({}, {error:true});f.elements.donateLink.onclick({preventDefault(){}});assert(f.elements.donationStatus.textContent.includes('QR'));
f=fixture({}, {browser:true});f.elements.donateLink.onclick({preventDefault(){throw Error('keep normal anchor')}});
f=fixture({}, {blocked:true});assert(!f.elements.donationNotice.hidden);assert(!f.elements.support.open);
const html=fs.readFileSync('adobe/UzbekSubtitles/index.html','utf8');assert(!html.includes('donationNever'));assert(!html.includes('donationDismiss'));assert(!html.includes('.donation-notice{display:none'));assert(html.includes('assets/donation-qr.svg'));
console.log('Pinned notice, every fifth opening, removed opt-out, correct CEP bridge, macOS/Windows fallback and browser errors OK');
