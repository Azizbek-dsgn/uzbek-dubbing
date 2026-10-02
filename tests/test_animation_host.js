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
const created=[];let keys=0,groups=0;
function property(){return {value:{},numKeys:0,setValue(v){this.value=JSON.parse(JSON.stringify(v))},setValueAtTime(t,v){assert.ok(Number.isFinite(t));this.value=JSON.parse(JSON.stringify(v));this.numKeys++;keys++},setInterpolationTypeAtKey(){},canAddToMotionGraphicsTemplate:()=>true,addToMotionGraphicsTemplateAs(){},property(){return property()},addProperty(){return property()}}}
function CompItem(){}
const comp=new CompItem();Object.assign(comp,{name:'Test',id:'id',width:320,height:568,duration:10,layers:{addText(t){const source=property(),transform=property(),layer={text:t,sourceRectAtTime:()=>({left:0,top:-20,width:80,height:28}),property:n=>n==='ADBE Text Properties'?{property:()=>source}:transform};created.push(layer);return layer},addShape(){return {property:()=>property()}}}});
const ae={app:{project:{activeItem:comp},beginUndoGroup(){groups++},endUndoGroup(){groups--}},CompItem,File,ParagraphJustification:{LEFT_JUSTIFY:1},KeyframeInterpolationType:{HOLD:1,LINEAR:2},JSON,Math,Number,String,Date,isFinite};
vm.runInNewContext(fs.readFileSync('adobe/UzbekSubtitles/host/after_effects.jsx','utf8'),ae);
for(const preset of ['karaoke','pop','pill','reveal','slide','emphasis']){plan.theme.preset=preset;assert.ok(ae.uzImportAnimatedCaptions('/tmp/plan.json',5,'Test','id').startsWith('2 ta'));assert.equal(groups,0)}
assert.ok(keys>0);assert.ok(created.every(l=>l.inPoint>=5&&l.outPoint===6));assert.ok(ae.uzImportAnimatedCaptions('/tmp/plan.json',0,'Test','wrong').includes('o‘zgargan'));
// Force the legacy parser and verify it handles strings without evaluating code.
ae.JSON=undefined;assert.equal(ae.uzAnimationRead('/tmp/plan.json').cues[0].runs[0].text,'Salom');
plan={evil:'line\n"quoted" \\ slash',array:[true,false,null,-1.5]};assert.equal(ae.uzAnimationRead('/tmp/plan.json').evil,plan.evil);
console.log('Empty-track protection, MOGRT dispatch, six native AE presets and legacy JSON parser OK');
