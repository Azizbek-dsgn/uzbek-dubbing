// AE intentionally has no app.name. Assert native composition/render-queue behavior.
const assert=require('assert'),fs=require('fs'),vm=require('vm');
function fixture(formats={'AIFF 48kHz':'AIFF'}) {
  function CompItem(){}
  const comp=Object.assign(new CompItem(),{name:'Test "O‘zbek"',id:42,duration:20,workAreaStart:3,workAreaDuration:5,frameRate:29.97,width:1080,height:1920});
  const layers=[{id:7,index:1,name:'Selected video',source:{id:70,hasVideo:true},hasAudio:true,audioEnabled:false,solo:false,locked:true,guideLayer:true,inPoint:2,outPoint:12,startTime:-1,stretch:125,timeRemapEnabled:false},{index:2,hasAudio:true,audioEnabled:true,solo:true,locked:false}];
  comp.selectedLayers=[layers[0]];let copy=null;
  comp.duplicate=()=>{copy={name:comp.name,numLayers:2,layers:layers.map(l=>({...l})),layer(i){return this.layers[i-1]},remove(){this.removed=true}};return copy;};
  const files={},existing={render:true},done={render:false},entries=[existing,done];let added=null,renders=0,fail=false;
  function File(p){this.fsName=p;Object.defineProperty(this,'exists',{get:()=>!!files[p]});Object.defineProperty(this,'length',{get:()=>files[p]||0});this.remove=()=>delete files[p];}
  const queue={rendering:false,get numItems(){return entries.length},item:i=>entries[i-1],items:{add:renderComp=>{
    assert.strictEqual(renderComp,copy);
    let generation=0,format='',output=null;
    added={render:false,timeSpanStart:0,timeSpanDuration:0,remove(){entries.splice(entries.indexOf(this),1)},outputModule(){
      const token=generation;function valid(){assert.equal(token,generation,'Output Module object was not reacquired');}
      return {templates:Object.keys(formats),applyTemplate(n){valid();format=formats[n];generation++},getSettings(){valid();return {Format:format}},setSetting(){valid();generation++},get file(){valid();return output},set file(f){valid();output=f}};
    }};entries.push(added);return added;
  }},render(){renders++;assert.equal(copy.layer(1).audioEnabled,true);assert.equal(copy.layer(2).audioEnabled,false);assert.equal(copy.layer(2).solo,false);assert.equal(copy.layer(1).guideLayer,false);assert.equal(copy.layer(1).stretch,layers[0].stretch);assert.equal(copy.layer(1).startTime,-1);assert.equal(existing.render,false);assert.equal(done.render,false);assert.equal(added.render,true);if(fail)throw Error('render failure');files[added.outputModule(1).file.fsName]=4000;}};
  const context={app:{project:{activeItem:comp,renderQueue:queue}},CompItem,File,GetSettingsFormat:{STRING:1},Number,String,Math,isFinite};
  vm.createContext(context);vm.runInContext(fs.readFileSync('adobe/UzbekSubtitles/host/editor.jsx','utf8'),context);vm.runInContext(fs.readFileSync('adobe/UzbekSubtitles/host/after_effects.jsx','utf8'),context);
  return {context,comp,queue,entries,existing,done,layers,get copy(){return copy},get added(){return added},get renders(){return renders},set fail(v){fail=v}};
}
let f=fixture();assert.equal(f.context.uzIsAE(),true);
let info=JSON.parse(f.context.uzAeTimelineInfo('auto'));assert.equal(info.host,'AEFT');assert.equal(info.name,f.comp.name);assert.equal(info.start,2);assert.equal(info.duration,10);assert.equal(info.layer_name,'Selected video');assert(info.layer_token);assert.equal(info.fps,29.97);
info=JSON.parse(f.context.uzAeTimelineInfo('full'));assert.equal(info.start,2);assert.equal(info.duration,10);assert.equal(info.marked,false);
let result=JSON.parse(f.context.uzAeExportAudio('inout','/tmp/audio.wav',f.comp.name,'42'));assert.equal(result.path,'/tmp/audio.aif');assert.equal(result.template,'AIFF 48kHz');assert.equal(f.added.timeSpanStart,3);assert.equal(f.added.timeSpanDuration,5);assert.equal(f.entries.length,2);assert.equal(f.existing.render,true);assert.equal(f.done.render,false);
f=fixture({'Son':'AIFF','Custom Uzbek':'WAV'});result=JSON.parse(f.context.uzAeExportAudio('full','/tmp/full.wav',f.comp.name,'42'));assert.equal(result.path,'/tmp/full.wav');assert.equal(result.template,'Custom Uzbek');assert.equal(f.added.timeSpanDuration,10);
f=fixture();f.fail=true;result=JSON.parse(f.context.uzAeExportAudio('auto','/tmp/fail.wav',f.comp.name,'42'));assert(result.error.includes('render failure'));assert.equal(f.entries.length,2);assert.equal(f.existing.render,true);
f=fixture({'Lossless':'QuickTime'});result=JSON.parse(f.context.uzAeExportAudio('auto','/tmp/missing.wav',f.comp.name,'42'));assert(result.error.includes('Output Module'));assert.equal(f.renders,0);assert.equal(f.entries.length,2);assert.equal(f.existing.render,true);
f=fixture();assert(JSON.parse(f.context.uzAeExportAudio('auto','/tmp/wrong.wav',f.comp.name,'99')).error);assert.equal(f.added,null);assert.equal(f.existing.render,true);
f.queue.rendering=true;assert(JSON.parse(f.context.uzAeExportAudio('auto','/tmp/busy.wav',f.comp.name,'42')).error);assert.equal(f.added,null);
f=fixture();f.comp.workAreaStart=0;f.comp.workAreaDuration=20;assert.equal(JSON.parse(f.context.uzAeTimelineInfo('inout')).duration,10);assert.equal(JSON.parse(f.context.uzAeTimelineInfo('auto')).duration,10);
for(const selection of [[],f.layers]){f.comp.selectedLayers=selection;assert(JSON.parse(f.context.uzAeTimelineInfo('auto')).error);}f.comp.selectedLayers=[f.layers[0]];
f.layers[0].hasAudio=false;assert(JSON.parse(f.context.uzAeTimelineInfo('auto')).error);f.layers[0].hasAudio=true;
f.layers[0].source.hasVideo=false;assert(JSON.parse(f.context.uzAeTimelineInfo('auto')).error);f.layers[0].source.hasVideo=true;
f.comp.workAreaStart=13;f.comp.workAreaDuration=2;assert(JSON.parse(f.context.uzAeTimelineInfo('inout')).error);
f=fixture();info=JSON.parse(f.context.uzAeTimelineInfo('auto'));f.layers[0].startTime=0;assert(JSON.parse(f.context.uzAeExportAudio('auto','/tmp/stale.wav',f.comp.name,'42',info.layer_token,info.start,info.duration)).error);assert.equal(f.copy,null);
f=fixture();info=JSON.parse(f.context.uzAeTimelineInfo('auto'));const original=JSON.stringify(f.layers);result=JSON.parse(f.context.uzAeExportAudio('auto','/tmp/isolated.wav',f.comp.name,'42',info.layer_token,info.start,info.duration));assert.equal(result.layer_token,info.layer_token);assert.equal(JSON.stringify(f.layers),original);assert.equal(f.copy.removed,true);
f=fixture();f.fail=true;result=JSON.parse(f.context.uzAeExportAudio('auto','/tmp/fail2.wav',f.comp.name,'42'));assert(result.error);assert.equal(f.copy.removed,true);

// Ordinary file footage skips Render Queue and uses source-relative trim.
f=fixture();f.layers[0].stretch=100;f.layers[0].source.file={fsName:'C:\\Media\\voice.mov',exists:true};
f.layers[0].property=name=>name==='ADBE Effect Parade'?{numProperties:0}:{property:()=>({numKeys:0,expressionEnabled:false,value:[0,0]})};
info=JSON.parse(f.context.uzAeTimelineInfo('inout'));
result=JSON.parse(f.context.uzAeExportAudio('inout','/tmp/direct.wav',f.comp.name,'42',info.layer_token,info.start,info.duration));
assert.equal(result.direct,true);assert.equal(result.seek,4);assert.equal(result.duration,5);assert.equal(result.path,'C:\\Media\\voice.mov');assert.equal(f.renders,0);assert.equal(f.copy,null);assert.equal(f.existing.render,true);
f.layers[0].stretch=200;
f.layers[0].property=name=>name==='ADBE Effect Parade'?{numProperties:1,property:()=>({matchName:'ADBE Lumetri',enabled:true})}:{property:()=>({numKeys:0,expressionEnabled:false,value:[0,0]})};
result=JSON.parse(f.context.uzAeExportAudio('inout','/tmp/stretch.wav',f.comp.name,'42'));assert.equal(result.direct,true);assert.equal(result.seek,2);assert.equal(result.tempo,.5);assert.equal(result.duration,5);assert.equal(f.renders,0);
f.layers[0].property=name=>name==='ADBE Effect Parade'?{numProperties:1}:{property:()=>({numKeys:0,expressionEnabled:false,value:[0,0]})};
result=JSON.parse(f.context.uzAeExportAudio('inout','/tmp/effected.wav',f.comp.name,'42'));assert(!result.direct);assert.equal(f.renders,1);

f.context.app.project.activeItem={};assert(JSON.parse(f.context.uzAeTimelineInfo('auto')).error);
console.log('AE host without app.name, selected layer isolation, trims, Work Area intersection, WAV/AIFF formats, Output Module lifetime, queue recovery and identity guards OK');
