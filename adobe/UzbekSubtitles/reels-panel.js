(function () {
  'use strict';
  var fs=require('fs'),path=require('path'),spawn=require('child_process').spawn,bridge=document.uzscribe;
  function el(id){return document.getElementById(id);}
  var busy=false,child=null,cancelled=false,info=null,snapshot=null,result=null,choices=[];
  var fields=['reelAudio','reelRange','reelModel','reelStrength','reelKeep','reelSilence','reelPadding','reelGap','reelWindow','reelThreshold','reelRetakes','reelRemoveSilence','reelPreviewFirst','reelProfile'];
  var tabs=['captionsTab','podcastTab','reelsTab'],saved={};
  Array.prototype.forEach.call(el('model').options,function(option){var copy=document.createElement('option');copy.value=option.value;copy.textContent=option.textContent;el('reelModel').appendChild(copy);});
  el('reelModel').value=el('model').value;
  try{saved=JSON.parse(localStorage.getItem('uzscribe.reels.v1')||'{}');}catch(e){}
  fields.forEach(function(id){var field=el(id);if(Object.prototype.hasOwnProperty.call(saved,id)){
    if(field.type==='checkbox')field.checked=!!saved[id];
    else if(field.tagName!=='SELECT' || Array.prototype.some.call(field.options,function(o){return o.value===saved[id];}))field.value=saved[id];
  }field.addEventListener('change',save);});
  function save(){fields.forEach(function(id){var f=el(id);saved[id]=f.type==='checkbox'?f.checked:f.value;});try{localStorage.setItem('uzscribe.reels.v1',JSON.stringify(saved));}catch(e){}}
  function status(message){el('reelStatus').textContent=message;}
  function phase(value){busy=value;document.uzscribeBusy=value;fields.concat(tabs,['reelRefresh','reelRun','reelImport','reelRebuild']).forEach(function(id){el(id).disabled=value;});choices.forEach(function(c){c.field.disabled=value;});el('reelCancel').hidden=!value;el('reelCancel').disabled=false;}
  function fail(message){child=null;phase(false);status(message);}
  function refresh(done){bridge.host('uzTimelineInfo('+JSON.stringify(el('reelRange').value)+')',function(error,data){
    if(error || data.host!=='PPRO'){info=null;el('reelTimeline').textContent=error?error.message:'Reels montaji uchun Premiere Pro’ni oching.';if(done)done(new Error(el('reelTimeline').textContent));return;}
    if(!data.trackCount || !data.videoCount){info=null;el('reelTimeline').textContent='Kamida bitta audio va video trek kerak.';if(done)done(new Error(el('reelTimeline').textContent));return;}
    info=data;el('reelTimeline').textContent=data.name+' · '+data.duration.toFixed(1)+' s';
    var select=el('reelAudio'),previous=select.value;select.textContent='';
    for(var i=0;i<data.trackCount;i++){var option=document.createElement('option');option.value=String(i);option.textContent='Audio '+(i+1);select.appendChild(option);}
    select.value=Number(previous)>=0 && Number(previous)<data.trackCount?previous:'0';if(done)done(null,data);
  });}
  el('reelsTab').addEventListener('click',function(){if(busy || document.uzscribeBusy)return;el('captionPage').hidden=true;el('podcastPage').hidden=true;el('reelsPage').hidden=false;tabs.forEach(function(id){el(id).setAttribute('aria-selected',String(id==='reelsTab'));});if(!info)refresh();});
  ['captionsTab','podcastTab'].forEach(function(id){el(id).addEventListener('click',function(){if(busy || document.uzscribeBusy)return;el('reelsPage').hidden=true;el('reelsTab').setAttribute('aria-selected','false');});});
  el('reelRefresh').addEventListener('click',function(){refresh();});el('reelRange').addEventListener('change',function(){refresh();});
  function settings(data){return {audio:Number(el('reelAudio').value),start:data.start,end:data.start+data.duration,model:el('reelModel').value,strength:el('reelStrength').value,keep:el('reelKeep').value,silence:Number(el('reelSilence').value),padding:Number(el('reelPadding').value),sentence_gap:Number(el('reelGap').value),window:Number(el('reelWindow').value),threshold:Number(el('reelThreshold').value),remove_retakes:el('reelRetakes').checked,remove_silence:el('reelRemoveSilence').checked,profile:el('reelProfile').value,keep_retake_ids:choices.filter(function(c){return c.field.checked;}).map(function(c){return c.id;})};}
  function review(report){if(typeof report.audio==='number')el('reelAudio').value=String(report.audio);choices=[];el('reelTakes').textContent='';
    el('reelSummary').textContent=report.output_seconds.toFixed(1)+' s natija · '+report.removed_seconds.toFixed(1)+' s olindi · '+report.removed_retakes+' takroriy dubl'+(report.warnings&&report.warnings.length?' · '+report.warnings.join(' '):'');
    report.retakes.forEach(function(take){var box=document.createElement('div');box.className='retake';var label=document.createElement('label'),field=document.createElement('input');field.type='checkbox';field.checked=!take.remove;var title=document.createElement('span');title.textContent='Bu dubl saqlansin · '+take.start.toFixed(1)+'–'+take.end.toFixed(1)+' s';label.appendChild(field);label.appendChild(title);var text=document.createElement('p');text.textContent=take.text;var kept=document.createElement('p');kept.className='hint';kept.textContent='Qoldirilgan: '+take.kept_text+(take.verified===false?' · '+take.reason:'');box.appendChild(label);box.appendChild(text);box.appendChild(kept);el('reelTakes').appendChild(box);choices.push({id:take.id,field:field});});
    el('reelFile').textContent=result.path;el('reelReview').hidden=false;el('reelImport').hidden=false;
  }
  function importResult(){if(!result || busy)return;phase(true);el('reelCancel').hidden=true;
    bridge.host('uzPodcastImport('+[result.path,result.info.name,result.info.identity].map(JSON.stringify).join(',')+')',function(error){phase(false);if(error){status('Import tugamadi: '+error.message+'\nXML saqlandi. Qayta import qilish mumkin.');return;}el('reelImport').hidden=true;status('Reels tozalandi. Project panelidagi “UzScribe Reels” sequence’ni ochib tekshiring.'+(result.warnings&&result.warnings.length?'\n'+result.warnings.join('\n'):''));});
  }
  function analyze(state){var config,output,options=settings(state.info),autoImport=!el('reelPreviewFirst').checked;
    try{var key=String(Date.now());output=path.join(path.dirname(state.source),key+'-reels.xml');config=path.join(path.dirname(state.source),key+'-settings.json');fs.writeFileSync(config,JSON.stringify(options),'utf8');}
    catch(e){fail(e.message);return;}
    var log='',logPath=output.replace(/\.xml$/,'.log');try{fs.writeFileSync(logPath,'UzScribe Reels\n','utf8');}catch(_){}status('O‘zbekcha nutq va dubllar tahlil qilinmoqda…');
    try{child=spawn(bridge.python.value,[path.join(bridge.root,'subtitles','reels.py'),'--input',state.source,'--output',output,'--settings',config],{windowsHide:true,env:Object.assign({},process.env,{PYTHONUTF8:'1',HF_HUB_OFFLINE:'1',ORT_DISABLE_TELEMETRY:'1'})});}catch(e){fail(e.message);return;}
    var processRef=child;child.stdout.on('data',function(chunk){if(!cancelled)status(String(chunk).trim());});child.stderr.on('data',function(chunk){log=(log+chunk).slice(-12000);try{fs.appendFileSync(logPath,String(chunk),'utf8');}catch(_){}});
    child.on('error',function(error){if(child===processRef)fail('Python ochilmadi: '+error.message);});
    child.on('close',function(code,signal){try{fs.appendFileSync(logPath,'\nExit: '+code+'; signal: '+(signal||'none')+'\n','utf8');}catch(_){}if(child!==processRef)return;child=null;if(cancelled){fail('Bekor qilindi. Asl sequence saqlandi.');return;}if(code!==0){var specific=log.match(/Reels montaji tugamadi:\s*([^\r\n]+)/g);var reason=specific?specific[specific.length-1].replace(/^Reels montaji tugamadi:\s*/, ''):signal?'Tahlil jarayoni '+signal+' bilan to‘xtadi.':'Tahlil jarayoni xato kodi '+code+' bilan to‘xtadi.';fail('Reels montaji tugamadi:\n'+reason+'\nTo‘liq jurnal: '+logPath);return;}
      try{var report=JSON.parse(fs.readFileSync(output.replace(/\.xml$/,'.json'),'utf8'));result={path:output,info:state.info,warnings:report.warnings||[]};review(report);phase(false);status('Tozalash tayyor. Dubllarni tekshirib, keraklisini saqlash mumkin.');if(autoImport)importResult();}
      catch(e){fail('Natija o‘qilmadi: '+e.message);}
    });
  }
  el('reelRun').addEventListener('click',function(){if(busy || document.uzscribeBusy)return;save();cancelled=false;result=null;snapshot=null;choices=[];el('reelReview').hidden=true;el('reelImport').hidden=true;phase(true);status('Timeline tekshirilmoqda…');
    refresh(function(error,data){if(error){fail(error.message);return;}if(cancelled){fail('Bekor qilindi.');return;}
      var directory=path.join(bridge.root,'exports','reels'),source;
      try{bridge.mkdir(directory);source=path.join(directory,String(Date.now())+'-source.xml');}catch(e){fail(e.message);return;}
      bridge.host('uzPodcastExport('+[source,data.name,data.identity].map(JSON.stringify).join(',')+')',function(err){if(err){fail(err.message);return;}if(cancelled){fail('Bekor qilindi.');return;}snapshot={source:source,info:data};analyze(snapshot);});
    });
  });
  el('reelRebuild').addEventListener('click',function(){if(busy || document.uzscribeBusy || !snapshot)return;save();cancelled=false;phase(true);refresh(function(error,data){if(error){fail(error.message);return;}if(cancelled){fail('Bekor qilindi.');return;}if(data.name!==snapshot.info.name || data.identity!==snapshot.info.identity){fail('Avvalgi sequence’ni oching yoki yangi Reels tahlilini boshlang.');return;}snapshot.info=data;analyze(snapshot);});});
  el('reelImport').addEventListener('click',importResult);
  el('reelCancel').addEventListener('click',function(){if(!busy)return;cancelled=true;el('reelCancel').disabled=true;status('Bekor qilinmoqda…');if(child)child.kill();});
}());
