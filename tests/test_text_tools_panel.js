const assert=require('assert'),fs=require('fs'),vm=require('vm');
function fixture(host='AEFT'){
 const ids=['captionsTab','podcastTab','reelsTab','textToolsTab','captionPage','podcastPage','reelsPage','textToolsPage','textToolsInfo','textToolsRefresh','textToolsSplit','textToolsStatus'],els={};
 ids.forEach(id=>els[id]={hidden:false,disabled:false,events:{},attrs:{},addEventListener(k,f){this.events[k]=f},setAttribute(k,v){this.attrs[k]=v}});
 const pending=[];const document={getElementById:id=>els[id],uzscribe:{aeHost:(expr,cb)=>pending.push({expr,cb})}};
 vm.runInNewContext(fs.readFileSync('adobe/UzbekSubtitles/text-tools-panel.js','utf8'),{document,__adobe_cep__:{getHostEnvironment:()=>JSON.stringify({appName:host})},JSON,String,Error});
 return {els,document,pending};
}
let f=fixture();assert(!f.els.textToolsTab.hidden);f.els.textToolsTab.events.click();assert.equal(f.pending[0].expr,'uzTextSplitInfo()');f.pending.shift().cb(null,'{"name":"Matn","words":10}');assert(f.els.textToolsInfo.textContent.includes('10 ta'));assert(f.els.captionPage.hidden);assert(!f.els.textToolsPage.hidden);
f.els.textToolsSplit.onclick();assert(f.document.uzscribeBusy);assert(f.els.captionsTab.disabled);assert.equal(f.pending[0].expr,'uzSplitTextWords()');f.els.textToolsSplit.onclick();assert.equal(f.pending.length,1);f.pending.shift().cb(null,'{"success":true,"count":10}');assert(!f.document.uzscribeBusy);assert(!f.els.captionsTab.disabled);assert(f.els.textToolsStatus.textContent.includes('10 ta'));
f.els.captionsTab.events.click();assert(f.els.textToolsPage.hidden);f.els.textToolsSplit.onclick();f.pending.shift().cb(null,'{"error":"Matn tanlang"}');assert.equal(f.els.textToolsStatus.textContent,'Matn tanlang');assert(!f.document.uzscribeBusy);
f=fixture('PPRO');assert(f.els.textToolsTab.hidden);f.els.textToolsSplit.onclick();assert.equal(f.pending.length,0);
console.log('AE-only text tools navigation, count, busy guard, errors and completion OK');
