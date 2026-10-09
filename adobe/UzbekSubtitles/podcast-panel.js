/* global __adobe_cep__ */
(function () {
  'use strict';
  var fs = require('fs'), path = require('path'), spawn = require('child_process').spawn;
  var bridge = document.uzscribe;
  function el(id) { return document.getElementById(id); }
  var page = el('podcastPage'), captions = el('captionPage'), tab = el('podcastTab'), captionTab = el('captionsTab');
  var info = null, rows = [], child = null, busy = false, result = null, cancelled = false;
  var fields = ['podRange','podMode','podShot','podReaction','podSilence','podPadding','podThreshold','podMargin','podWideEvery','podRemove','podProfile'];
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem('uzscribe.podcast.v1') || '{}'); } catch (e) {}
  fields.forEach(function (id) {
    var field = el(id);
    if (Object.prototype.hasOwnProperty.call(saved, id)) {
      if (field.type === 'checkbox') field.checked = !!saved[id];
      else if (field.tagName !== 'SELECT' || Array.prototype.some.call(field.options, function(o) { return o.value === saved[id]; })) field.value = saved[id];
    }
    field.addEventListener('change', save);
  });
  function status(message) { el('podStatus').textContent = message; }
  function save() {
    fields.forEach(function(id) { var f=el(id); saved[id]=f.type==='checkbox'?f.checked:f.value; });
    saved.rows = rows.map(function(r) { return {audio:Number(r.audio.value), video:Number(r.video.value)}; });
    saved.wide = el('podWide').value;
    try { localStorage.setItem('uzscribe.podcast.v1', JSON.stringify(saved)); } catch (e) {}
  }
  function phase(working) {
    busy = working; document.uzscribeBusy = working;
    fields.concat(['podWide','podAdd','podRefresh']).forEach(function(id){el(id).disabled=working;});
    rows.forEach(function(r){r.audio.disabled=r.video.disabled=r.remove.disabled=working;});
    tab.disabled=captionTab.disabled=working;
    el('podRun').hidden=working || !!result;
    el('podCancel').hidden=!working;
    el('podCancel').disabled=false;
    el('podImport').hidden=working || !result;
    el('podReset').hidden=working || !result;
  }
  function choices(select, count, prefix, value) {
    for (var i=0;i<count;i++) { var o=document.createElement('option'); o.value=String(i); o.textContent=prefix+' '+(i+1); select.appendChild(o); }
    select.value=String(value>=0 && value<count?value:0);
  }
  function addRow(mapping) {
    if (!info || rows.length>=10) return;
    var box=document.createElement('div'); box.className='pod-row';
    var label=document.createElement('span'); label.className='field-label'; label.textContent='Odam '+(rows.length+1);
    var audio=document.createElement('select'), video=document.createElement('select'), remove=document.createElement('button');
    audio.setAttribute('aria-label','Mikrofon treki'); video.setAttribute('aria-label','Kamera treki');
    choices(audio,info.trackCount,'Audio',mapping.audio); choices(video,info.videoCount,'Video',mapping.video);
    remove.textContent='×'; remove.type='button'; remove.setAttribute('aria-label','Moslikni olib tashlash');
    var row={audio:audio,video:video,remove:remove,box:box};
    remove.addEventListener('click',function(){if(rows.length<=1)return;rows.splice(rows.indexOf(row),1);box.parentNode.removeChild(box);save();});
    audio.addEventListener('change',save);video.addEventListener('change',save);
    [label,audio,video,remove].forEach(function(node){box.appendChild(node);});el('podMappings').appendChild(box);rows.push(row);
  }
  function refresh(done) {
    bridge.host('uzTimelineInfo('+JSON.stringify(el('podRange').value)+')',function(err,data){
      if(err || data.host!=='PPRO') { info=null; el('podTimeline').textContent=err?err.message:'Podcast montaji uchun Premiere Pro’ni oching.'; if(done)done(new Error(el('podTimeline').textContent));return; }
      info=data; el('podTimeline').textContent=data.name+' · '+data.duration.toFixed(1)+' s · '+data.trackCount+' audio / '+data.videoCount+' kamera';
      if(!data.trackCount || !data.videoCount){if(done)done(new Error('Kamida bitta audio va video trek kerak.'));return;}
      // Explicit refresh validates every saved mapping against the new timeline.
      var mappings=rows.length?rows.map(function(r){return {audio:Number(r.audio.value),video:Number(r.video.value)};}):saved.rows;
      el('podMappings').textContent='';rows=[];
      (mappings && mappings.length?mappings:[{audio:0,video:0}]).slice(0,10).forEach(addRow);
      var wide=el('podWide'), previous=wide.value || saved.wide || '';wide.textContent='';var none=document.createElement('option');none.value='';none.textContent='Yo‘q';wide.appendChild(none);
      choices(wide,data.videoCount,'Video',-1);wide.value=previous!=='' && Number(previous)<data.videoCount?previous:'';
      if(done)done(null,data);
    });
  }
  function open(podcast) {
    if(busy || document.uzscribeBusy)return;
    captions.hidden=podcast;page.hidden=!podcast;tab.setAttribute('aria-selected',String(podcast));captionTab.setAttribute('aria-selected',String(!podcast));
    if(podcast && !info)refresh();
  }
  tab.addEventListener('click',function(){open(true);});captionTab.addEventListener('click',function(){open(false);});
  el('podRefresh').addEventListener('click',function(){refresh();});el('podRange').addEventListener('change',function(){refresh();});el('podWide').addEventListener('change',save);
  el('podAdd').addEventListener('click',function(){addRow({audio:rows.length,video:rows.length});save();});
  function fail(message) { child=null;phase(false);status(message); }
  el('podRun').addEventListener('click',function(){
    if(busy || document.uzscribeBusy)return;
    save();cancelled=false;result=null;el('podReview').hidden=true;phase(true);status('Timeline tekshirilmoqda…');
    refresh(function(err,data){
      if(err){fail(err.message);return;}if(cancelled){fail('Bekor qilindi.');return;}
      // refresh rebuilt the row controls while working; lock them again.
      phase(true);
      var outputDir=path.join(bridge.root,'exports','podcast'), source, output, config;
      try {bridge.mkdir(outputDir);var key=String(Date.now());source=path.join(outputDir,key+'-source.xml');output=path.join(outputDir,key+'-edit.xml');config=path.join(outputDir,key+'-settings.json');
        var settings={speakers:rows.map(function(r,i){return {audio:Number(r.audio.value),video:Number(r.video.value),name:'Odam '+(i+1)};}),wide_track:el('podWide').value===''?null:Number(el('podWide').value),start:data.start,end:data.start+data.duration,switch_cameras:el('podMode').value==='cameras',remove_silence:el('podRemove').checked,profile:el('podProfile').value};
        [['minimum_shot','podShot'],['reaction','podReaction'],['silence','podSilence'],['padding','podPadding'],['threshold','podThreshold'],['margin','podMargin'],['wide_every','podWideEvery']].forEach(function(p){settings[p[0]]=Number(el(p[1]).value);});
        fs.writeFileSync(config,JSON.stringify(settings),'utf8');
      }catch(e){fail(e.message);return;}
      bridge.host('uzPodcastExport('+[source,data.name,data.identity].map(JSON.stringify).join(',')+')',function(error){
        if(error){fail(error.message);return;}if(cancelled){fail('Bekor qilindi.');return;}
        status('Nutq va kamera almashishi tahlil qilinmoqda…');
        var log='';
        try { child=spawn(bridge.python.value,[path.join(bridge.root,'subtitles','podcast.py'),'--input',source,'--output',output,'--settings',config],{windowsHide:true,env:Object.assign({},process.env,{PYTHONUTF8:'1',HF_HUB_OFFLINE:'1'})}); }catch(e){fail(e.message);return;}
        var processRef=child;
        child.stdout.on('data',function(chunk){if(!cancelled)status(String(chunk).trim());});
        child.stderr.on('data',function(chunk){log=(log+chunk).slice(-4000);});
        child.on('error',function(e){if(child===processRef)fail('Python ochilmadi: '+e.message);});
        child.on('close',function(code){if(child!==processRef)return;child=null;
          if(cancelled){fail('Bekor qilindi. Asl sequence saqlandi.');return;}
          if(code!==0){fail('Montaj tugamadi:\n'+log);return;}
          try {var report=JSON.parse(fs.readFileSync(output.replace(/\.xml$/,'.json'),'utf8'));result={path:output,info:data,report:report};
            el('podSummary').textContent=report.output_seconds.toFixed(1)+' s natija · '+report.removed_seconds.toFixed(1)+' s pauza olindi · '+report.cuts.length+' bo‘lak'+(report.warnings&&report.warnings.length?' · '+report.warnings.join(' '):'');
            el('podCuts').textContent='';report.cuts.slice(0,200).forEach(function(cut){var row=document.createElement('div');row.className='cue-item';row.textContent=(cut.start/report.fps).toFixed(1)+'–'+(cut.end/report.fps).toFixed(1)+' s → '+(cut.camera===null?'Asl kameralar':'Video '+(cut.camera+1));el('podCuts').appendChild(row);});
            el('podFile').textContent=output;el('podReview').hidden=false;phase(false);status('XML tayyor. Yangi sequence qo‘shib tekshiring.');
          }catch(e){fail('Natija o‘qilmadi: '+e.message);}
        });
      });
    });
  });
  el('podCancel').addEventListener('click',function(){if(!busy)return;cancelled=true;el('podCancel').disabled=true;status('Bekor qilinmoqda…');if(child)child.kill();});
  el('podImport').addEventListener('click',function(){if(!result || busy)return;phase(true);el('podCancel').hidden=true;
    bridge.host('uzPodcastImport('+[result.path,result.info.name,result.info.identity].map(JSON.stringify).join(',')+')',function(err){phase(false);status(err?'Import tugamadi: '+err.message:'Yangi sequence qo‘shildi. Premiere’da kesishlarni tekshiring.');if(!err)el('podImport').hidden=true;});
  });
  el('podReset').addEventListener('click',function(){if(busy)return;result=null;el('podReview').hidden=true;phase(false);status('');});
}());
