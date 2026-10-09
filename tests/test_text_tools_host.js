const assert=require('assert'),fs=require('fs'),vm=require('vm');
function fixture(text='Bir ikki uch to‘rt besh\rolti yetti sakkiz to‘qqiz o‘n.'){
 function CompItem(){};let undo=0,attempt=0,failAt=0;const copies=[];
 const source={value:{text,font:'Arial',fontSize:56,tracking:23,justification:2,boxText:true},numKeys:0,expressionEnabled:false};
 const original={name:'Mening matnim',enabled:true,selected:true,locked:true,parent:{name:'Parent'},position:[23,85,10],scale:[90,110,100],rotation:13,inPoint:2,outPoint:20,startTime:-3,source,
  property(n){return n==='ADBE Text Properties'?{property:()=>source}:null;},
  duplicate(){attempt++;if(attempt===failAt)throw Error('duplicate failure');const copy={...this,source:{...source,value:{...source.value}},ranges:[],remove(){copies.splice(copies.indexOf(this),1)}};copies.push(copy);return copy;}};
 const comp=new CompItem();comp.selectedLayers=[original];
 const context={app:{project:{activeItem:comp},beginUndoGroup(){undo++},endUndoGroup(){undo--}},CompItem,Number,String,Math,isFinite};
 vm.runInNewContext(fs.readFileSync('adobe/UzbekSubtitles/host/after_effects.jsx','utf8'),context);
 context.uzCaptionAnimator=(copy,range,property,value)=>{assert.equal(property,'ADBE Text Opacity');assert.equal(value,0);copy.ranges.push(range);return {setValue(v){assert.equal(v,100)}}};
 return {context,comp,original,source,copies,get undo(){return undo},set failAt(v){failAt=v}};
}
let f=fixture();assert.equal(JSON.parse(f.context.uzTextSplitInfo()).words,10);
const before=JSON.stringify(f.source.value),result=JSON.parse(f.context.uzSplitTextWords());assert.equal(result.count,10);assert.equal(f.copies.length,10);assert.equal(f.original.enabled,false);assert.equal(f.original.selected,false);assert.equal(f.original.locked,true);assert.equal(f.undo,0);
const words=f.source.value.text.split(/\s+/),visibleText=f.source.value.text.replace(/[\r\n]/g,'');
f.copies.forEach((l,i)=>{assert.equal(JSON.stringify(l.source.value),before);assert.strictEqual(l.parent,f.original.parent);assert.deepEqual(l.position,f.original.position);assert.deepEqual(l.scale,f.original.scale);assert.equal(l.rotation,13);assert.equal(l.startTime,-3);assert.equal(l.inPoint,2);assert.equal(l.outPoint,20);assert(l.name.includes(words[i]));assert(l.selected);assert(!l.locked);
 const visible=visibleText.split('').filter((_,index)=>!l.ranges.some(r=>index>=r.start&&index<r.end)).join('');assert.equal(visible,words[i]);});
f=fixture('  O‘zbekcha,  matn.\r\nYangi\tqator!  ');assert.equal(JSON.parse(f.context.uzSplitTextWords()).count,4);assert.equal(f.copies.length,4);
f=fixture();f.failAt=4;assert(JSON.parse(f.context.uzSplitTextWords()).error.includes('duplicate failure'));assert.equal(f.copies.length,0);assert(f.original.enabled&&f.original.selected);assert.equal(f.undo,0);
for(const setup of [f=>f.source.expressionEnabled=true,f=>f.source.numKeys=1,f=>f.source.value.text='   ',f=>f.comp.selectedLayers=[],f=>f.comp.selectedLayers=[f.original,f.original],f=>f.original.hasTrackMatte=true,f=>f.original.enabled=false,f=>f.original.property=()=>null]){f=fixture();setup(f);assert(JSON.parse(f.context.uzSplitTextWords()).error);assert.equal(f.copies.length,0);assert.equal(f.undo,0);}
console.log('Text split: ten words, paragraph spacing, native layout preservation, selection guards and rollback OK');
