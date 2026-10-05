const assert=require('assert'),fs=require('fs'),vm=require('vm');
function fixture(host){
 const ids=['hostBadge','captionGuide','captionsTab','textToolsTab','podcastTab','reelsTab','subscription','model','modelSummary'],els={},events={};let observer;
 ids.forEach(id=>els[id]={id,hidden:false,disabled:false,attrs:{},handlers:{},textContent:'',addEventListener(k,f){this.handlers[k]=f},getAttribute(k){return this.attrs[k]},setAttribute(k,v){this.attrs[k]=v},focus(){this.focused=true},click(){['captionsTab','textToolsTab','podcastTab','reelsTab'].forEach(id=>els[id].attrs['aria-selected']=String(id===this.id));if(this.handlers.click)this.handlers.click();}});
 els.captionsTab.attrs['aria-selected']='true';els.textToolsTab.hidden=host!=='AEFT';els.podcastTab.hidden=els.reelsTab.hidden=host==='AEFT';
 const summary={focus(){this.focused=true}};els.subscription.querySelector=()=>summary;els.subscription.contains=t=>t===summary;
 els.model.options=[{textContent:'Scribe Giga'},{textContent:'Scribe Nav'}];els.model.selectedIndex=0;
 const nav={addEventListener(k,f){events['nav-'+k]=f}};
 const doc={uzscribeBusy:false,body:{attrs:{},setAttribute(k,v){this.attrs[k]=v}},getElementById:id=>els[id],querySelector:()=>nav,addEventListener(k,f){events[k]=f}};
 vm.runInNewContext(fs.readFileSync('adobe/UzbekSubtitles/panel-ui.js','utf8'),{document:doc,__adobe_cep__:{getHostEnvironment:()=>JSON.stringify({appName:host})},JSON,MutationObserver:function(cb){observer=cb;this.observe=()=>{}}});
 return {els,events,doc,summary,observer};
}
for(const host of ['PPRO','AEFT']){
 const f=fixture(host);assert.equal(f.doc.body.attrs['data-host'],host);assert.equal(f.els.hostBadge.textContent,host==='AEFT'?'After Effects':'Premiere Pro');assert.equal(f.els.modelSummary.textContent,'Scribe Giga');f.els.model.selectedIndex=1;f.els.model.handlers.change();assert.equal(f.els.modelSummary.textContent,'Scribe Nav');
 assert.equal(f.els.captionsTab.tabIndex,0);const target=host==='AEFT'?f.els.textToolsTab:f.els.podcastTab;
 let prevented=false;f.events['nav-keydown']({key:'ArrowRight',target:f.els.captionsTab,preventDefault(){prevented=true}});assert(prevented&&target.focused);assert.equal(target.tabIndex,0);assert.equal(f.els.captionsTab.tabIndex,-1);
 f.doc.uzscribeBusy=true;target.focused=false;f.events['nav-keydown']({key:'Home',target,preventDefault(){throw Error('busy navigation')}});assert(!target.focused);f.doc.uzscribeBusy=false;
 f.els.subscription.open=true;f.events.keydown({key:'Escape'});assert(!f.els.subscription.open&&f.summary.focused);
 f.els.subscription.open=true;f.events.click({target:f.summary});assert(f.els.subscription.open);f.events.click({target:{}});assert(!f.els.subscription.open);
 f.els.subscription.open=true;target.click();assert(!f.els.subscription.open);f.observer();
}
console.log('Panel UI: host labels, model summary, keyboard tabs, busy guard and account dismiss OK');
