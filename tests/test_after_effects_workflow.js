// AE intentionally has no app.name. Assert native composition/render-queue behavior.
const assert=require('assert'),fs=require('fs'),vm=require('vm');
function fixture(formats={'AIFF 48kHz':'AIFF'}) {
  function CompItem(){}
  const comp=Object.assign(new CompItem(),{name:'Test "O‘zbek"',id:42,duration:20,workAreaStart:3,workAreaDuration:5,frameRate:29.97,width:1080,height:1920});
  const files={},existing={render:true},done={render:false},entries=[existing,done];let added=null,renders=0,fail=false;
  function File(p){this.fsName=p;Object.defineProperty(this,'exists',{get:()=>!!files[p]});Object.defineProperty(this,'length',{get:()=>files[p]||0});this.remove=()=>delete files[p];}
  const queue={rendering:false,get numItems(){return entries.length},item:i=>entries[i-1],items:{add:()=>{
    let generation=0,format='',output=null;
    added={render:false,timeSpanStart:0,timeSpanDuration:0,remove(){entries.splice(entries.indexOf(this),1)},outputModule(){
      const token=generation;function valid(){assert.equal(token,generation,'Output Module object was not reacquired');}
      return {templates:Object.keys(formats),applyTemplate(n){valid();format=formats[n];generation++},getSettings(){valid();return {Format:format}},setSetting(){valid();generation++},get file(){valid();return output},set file(f){valid();output=f}};
    }};entries.push(added);return added;
  }},render(){renders++;assert.equal(existing.render,false);assert.equal(done.render,false);assert.equal(added.render,true);if(fail)throw Error('render failure');files[added.outputModule(1).file.fsName]=4000;}};
  const context={app:{project:{activeItem:comp,renderQueue:queue}},CompItem,File,GetSettingsFormat:{STRING:1},Number,String,Math,isFinite};
  vm.createContext(context);vm.runInContext(fs.readFileSync('adobe/UzbekSubtitles/host/editor.jsx','utf8'),context);vm.runInContext(fs.readFileSync('adobe/UzbekSubtitles/host/after_effects.jsx','utf8'),context);
  return {context,comp,queue,entries,existing,done,get added(){return added},get renders(){return renders},set fail(v){fail=v}};
}
let f=fixture();assert.equal(f.context.uzIsAE(),true);
let info=JSON.parse(f.context.uzAeTimelineInfo('auto'));assert.equal(info.host,'AEFT');assert.equal(info.name,f.comp.name);assert.equal(info.start,3);assert.equal(info.duration,5);assert.equal(info.fps,29.97);
info=JSON.parse(f.context.uzAeTimelineInfo('full'));assert.equal(info.start,0);assert.equal(info.duration,20);assert.equal(info.marked,false);
let result=JSON.parse(f.context.uzAeExportAudio('inout','/tmp/audio.wav',f.comp.name,'42'));assert.equal(result.path,'/tmp/audio.aif');assert.equal(result.template,'AIFF 48kHz');assert.equal(f.added.timeSpanStart,3);assert.equal(f.added.timeSpanDuration,5);assert.equal(f.entries.length,2);assert.equal(f.existing.render,true);assert.equal(f.done.render,false);
f=fixture({'Son':'AIFF','Custom Uzbek':'WAV'});result=JSON.parse(f.context.uzAeExportAudio('full','/tmp/full.wav',f.comp.name,'42'));assert.equal(result.path,'/tmp/full.wav');assert.equal(result.template,'Custom Uzbek');assert.equal(f.added.timeSpanDuration,20);
f=fixture();f.fail=true;result=JSON.parse(f.context.uzAeExportAudio('auto','/tmp/fail.wav',f.comp.name,'42'));assert(result.error.includes('render failure'));assert.equal(f.entries.length,2);assert.equal(f.existing.render,true);
f=fixture({'Lossless':'QuickTime'});result=JSON.parse(f.context.uzAeExportAudio('auto','/tmp/missing.wav',f.comp.name,'42'));assert(result.error.includes('Output Module'));assert.equal(f.renders,0);assert.equal(f.entries.length,2);assert.equal(f.existing.render,true);
f=fixture();assert(JSON.parse(f.context.uzAeExportAudio('auto','/tmp/wrong.wav',f.comp.name,'99')).error);assert.equal(f.added,null);assert.equal(f.existing.render,true);
f.queue.rendering=true;assert(JSON.parse(f.context.uzAeExportAudio('auto','/tmp/busy.wav',f.comp.name,'42')).error);assert.equal(f.added,null);
f=fixture();f.comp.workAreaStart=0;f.comp.workAreaDuration=20;assert(JSON.parse(f.context.uzAeTimelineInfo('inout')).error);assert.equal(JSON.parse(f.context.uzAeTimelineInfo('auto')).duration,20);
f.context.app.project.activeItem={};assert(JSON.parse(f.context.uzAeTimelineInfo('auto')).error);
console.log('AE host without app.name, Work Area/full composition, WAV/AIFF formats, Output Module lifetime, queue recovery and identity guards OK');
