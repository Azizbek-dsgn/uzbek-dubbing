const fs = require('fs');
const vm = require('vm');
const script = fs.readFileSync('adobe/UzbekSubtitles/host/after_effects.jsx', 'utf8');
const srt = '1\n00:00:00,000 --> 00:00:01,000\nSalom\n\n2\n00:00:01,200 --> 00:00:02,000\nDunyo\n';
const created = [];
const previous = {selected:true};
let animated = 0;
function CompItem() {}
const comp = new CompItem();
comp.name = 'Test'; comp.id = 7; comp.duration = 10; comp.width = 1080; comp.height = 1920;
comp.selectedLayers = [previous];
comp.layers = {addText: value => {
  const text = {fontSize:0, fillColor:null, applyFill:false, applyStroke:false, justification:null};
  const layer = {selected:true, property: name => {
    if (name === 'ADBE Text Properties') return {property:n=>{if(n!=='ADBE Text Document')throw Error(n);return {value:text,setValue(){}}}};
    if (name === 'ADBE Transform Group') return {property:n => n==='ADBE Position'?{setValue(){}}:({setValueAtTime(){animated++}})};
    throw Error(name);
  }};
  layer.text = value; created.push(layer); return layer;
}};
function File() {this.exists=true;this.open=()=>true;this.read=()=>srt;this.close=()=>{}}
const app = {project:{activeItem:comp},beginUndoGroup(){},endUndoGroup(){}};
const context = {app,CompItem,File,ParagraphJustification:{CENTER_JUSTIFY:1},Number,String,Math,isFinite};
vm.runInNewContext(script,context);
const result = context.importUzbekSrt('/tmp/test.srt',0,'Test','7','word',[],true);
if (created.some(l=>l.startTime!==l.inPoint || !l.name.startsWith('UzScribe '))) throw Error('Cue layer start/name missing');
if (!result.startsWith('2 ta') || previous.selected || created.length !== 2 ||
    created.some(layer => !layer.selected) || animated) throw Error('Composer layers were not selected cleanly');
console.log('After Effects Composer layer selection OK');
