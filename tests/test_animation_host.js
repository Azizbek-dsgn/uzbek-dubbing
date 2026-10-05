const fs=require('fs'),vm=require('vm'),assert=require('assert');
let imported=0;const occupied={clips:{numItems:1,0:{start:{seconds:0},end:{seconds:20}}},overwriteClip(){throw Error('must never overwrite source')}};
const empty={clips:{numItems:0},overwriteClip(item,ticks){this.clips.numItems++;this.ticks=ticks;imported++}};
const seq={name:'Test',sequenceID:'id',videoTracks:{numTracks:2,0:occupied,1:empty},importMGT(p,t,i){assert.equal(i,1);return {end:null}}};
function File(p){this.fsName=p;this.exists=true;this.open=()=>true;this.read=()=>JSON.stringify(plan);this.close=()=>{};}
const context={app:{project:{activeSequence:seq,rootItem:{getMediaPath:()=>'/tmp/overlay.mov'},importFiles:()=>true}},File,Time:function(){},String,Number,Math,isFinite};
vm.runInNewContext(fs.readFileSync('adobe/UzbekSubtitles/host/editor.jsx','utf8'),context);
assert.ok(JSON.parse(context.uzImportCaptionOverlay('/tmp/overlay.mov',5,'Test','id',2)).success);assert.equal(imported,1);assert.equal(empty.ticks,String(5*254016000000));
seq.videoTracks[1]=occupied;assert.ok(JSON.parse(context.uzImportCaptionOverlay('/tmp/overlay.mov',5,'Test','id',2)).error.includes('bo‘sh'));assert.equal(imported,1);
assert.ok(JSON.parse(context.uzImportCaptionOverlay('/tmp/overlay.mov',5,'Test','other',2)).error.includes('o‘zgargan'));
seq.videoTracks[1]=empty;empty.clips.numItems=0;assert.ok(JSON.parse(context.uzImportCaptionMogrts([{path:'/tmp/1.mogrt',start:0,end:1},{path:'/tmp/2.mogrt',start:1,end:2}],5,'Test','id')).success);
let plan={schema:1,width:320,height:568,fps:25,theme:{preset:'karaoke',fontFamily:'Arial',color:'#FFFFFF',active:'#F5D76E',speed:.16},cues:[{start:0,end:1,size:28,runs:[{text:'Salom',start:0,end:.5,x:50,y:350,width:80,height:38},{text:'dunyo',start:.5,end:1,x:140,y:350,width:80,height:38,emphasis:true}]}]};
const created=[];let keys=0,groups=0,failOnText=null;
function property(){return {value:{},numKeys:0,setValue(v){this.value=JSON.parse(JSON.stringify(v))},setValueAtTime(t,v){assert.ok(Number.isFinite(t));this.value=JSON.parse(JSON.stringify(v));this.numKeys++;keys++},setInterpolationTypeAtKey(){},canAddToMotionGraphicsTemplate:()=>true,addToMotionGraphicsTemplateAs(){},property(){return property()},addProperty(){return property()}}}
function CompItem(){}
const comp=new CompItem();Object.assign(comp,{name:'Test',id:'id',width:320,height:568,duration:10,layers:{addText(t){const source=property(),transformProps={},transform={property:n=>transformProps[n]||(transformProps[n]=property())},layer={text:t,sourceRectAtTime:()=>({left:0,top:-20,width:80,height:28}),property:n=>{if(t===failOnText)throw Error('simulated native text failure');return n==='ADBE Text Properties'?{property:()=>source}:transform;},remove(){created.splice(created.indexOf(this),1)}};created.push(layer);return layer},addShape(){const shape={property:()=>property(),moveAfter(){},remove(){created.splice(created.indexOf(this),1)}};created.push(shape);return shape}}});
Object.defineProperty(comp,'numLayers',{get:()=>created.length});comp.layer=()=>created[created.length-1];
const ae={app:{project:{activeItem:comp},beginUndoGroup(){groups++},endUndoGroup(){groups--}},CompItem,File,ParagraphJustification:{LEFT_JUSTIFY:1,CENTER_JUSTIFY:2},KeyframeInterpolationType:{HOLD:1,LINEAR:2},JSON,Math,Number,String,Date,isFinite};
vm.runInNewContext(fs.readFileSync('adobe/UzbekSubtitles/host/after_effects.jsx','utf8'),ae);
for(const preset of ['karaoke','pop','pill','reveal','slide','emphasis']){
 plan.theme.preset=preset;const before=created.length;
 assert.ok(ae.uzImportAnimatedCaptions('/tmp/plan.json',5,'Test','id').startsWith('1 ta'));
 const added=created.slice(before),texts=added.filter(l=>typeof l.text==='string');
 assert.equal(texts.length,1,'one whole cue text layer for '+preset);
 assert.equal(texts[0].text,'Salom dunyo');assert.equal(texts[0].startTime,5);
 assert.equal(texts[0].inPoint,5);assert.equal(texts[0].outPoint,6);assert(texts[0].name.includes('001'));
 assert.equal(added.length,preset==='pill'?2:1,'pill has only one shape helper');assert.equal(groups,0);
}

for(const preset of ['none','karaoke','pop','pill','reveal','slide','emphasis']){
 plan.theme.preset=preset;const before=created.length;
 assert.ok(ae.uzImportAnimatedCaptions('/tmp/plan.json',5,'Test','id','words',false,preset).startsWith('2 ta'));
 const texts=created.slice(before).filter(l=>typeof l.text==='string');assert.equal(texts.length,2);
 assert.deepEqual(texts.map(l=>l.text),['Salom','dunyo']);
 assert.deepEqual(Array.from(texts[0].property('ADBE Transform Group').property('ADBE Position').value),[90,364]);assert.deepEqual(Array.from(texts[1].property('ADBE Transform Group').property('ADBE Position').value),[180,364]);
 for(const l of texts){assert.equal(l.startTime,5);assert.equal(l.inPoint,5);assert.equal(l.outPoint,6);assert(l.name.includes('001'));}
}
plan.theme.preset='none';const originalRuns=plan.cues[0].runs;
plan.cues[0].runs=['Bir','ikki','uch','to‘rt'].map((text,i)=>({text,start:i/4,end:(i+1)/4,x:20+i*70,y:350,width:60,height:38}));
const fourBefore=created.length;assert(ae.uzImportAnimatedCaptions('/tmp/plan.json',5,'Test','id','words',false,'none').startsWith('4 ta'));
const four=created.slice(fourBefore);assert.equal(four.length,4);assert(four.every(l=>l.inPoint===5&&l.outPoint===6));assert.equal(new Set(four.map(l=>l.property('ADBE Transform Group').property('ADBE Position').value[1])).size,1);
plan.cues[0].runs=originalRuns;
plan.theme.preset='none';plan.cues[0].runs[1].y=388;
let beforeWords=created.length;ae.uzImportAnimatedCaptions('/tmp/plan.json',5,'Test','id','words',false,'none');assert.equal(created.length-beforeWords,2);assert.deepEqual(Array.from(created[created.length-1].property('ADBE Transform Group').property('ADBE Position').value),[180,402]);plan.cues[0].runs[1].y=350;
beforeWords=created.length;failOnText='dunyo';assert(ae.uzImportAnimatedCaptions('/tmp/plan.json',5,'Test','id','words',false,'none').includes('import qilinmadi'));assert.equal(created.length,beforeWords);assert.equal(groups,0);failOnText=null;

const layout=ae.uzCaptionLayout({runs:[{text:'O‘zb',y:0},{text:'tili',y:0},{text:'zo‘r',y:76}]});
assert.equal(layout.text,'O‘zb tili\rzo‘r');assert.deepEqual(Array.from(layout.ranges,r=>[r.start,r.end]),[[0,4],[5,9],[9,13]]);

const beforeFailure=created.length;failOnText='Salom dunyo';assert.ok(ae.uzImportAnimatedCaptions('/tmp/plan.json',5,'Test','id').includes('import qilinmadi'));assert.equal(created.length,beforeFailure);assert.equal(groups,0);failOnText=null;
assert.ok(keys>0);assert.ok(created.every(l=>l.inPoint>=5&&l.outPoint===6));assert.ok(ae.uzImportAnimatedCaptions('/tmp/plan.json',0,'Test','wrong').includes('o‘zgargan'));
// Force the legacy parser and verify it handles strings without evaluating code.
ae.JSON=undefined;assert.equal(ae.uzAnimationRead('/tmp/plan.json').cues[0].runs[0].text,'Salom');
plan={evil:'line\n"quoted" \\ slash',array:[true,false,null,-1.5]};assert.equal(ae.uzAnimationRead('/tmp/plan.json').evil,plan.evil);
console.log('Empty-track protection, MOGRT dispatch, six native AE presets and legacy JSON parser OK');
