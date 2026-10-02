(function () {
  'use strict';
  var bridge = document.uzscribe;
  if (!bridge) return;
  var fs = require('fs'), path = require('path'), cp = require('child_process');
  function el(id) {return document.getElementById(id);}
  var fields = {font:'animFont',size:'animSize',color:'animColor',active:'animActive',position:'animPosition',safe:'animSafe',speed:'animSpeed',keywords:'animKeywords'};
  var presets = /^(karaoke|pop|pill|reveal|slide|emphasis)$/;
  var key = 'uzscribe.animation.v1', stylesKey = 'uzscribe.styles.v1', phase = 'idle', host = '', rows = [];
  function read(key, fallback) {try {return JSON.parse(localStorage.getItem(key)) || fallback;} catch (_) {return fallback;}}
  function lex(s) {return String(s).toLowerCase().replace(/[‘’ʻʼ]/g,"'").replace(/[.,!?;:…\s]/g,'');}
  function theme() {
    var value = {preset:el('animation').value};
    Object.keys(fields).forEach(function (k) {var input=el(fields[k]);value[k]=k==='safe'?input.checked:input.value;});
    value.size=Number(value.size);value.speed=Number(value.speed);
    value.keywords=value.keywords.split(',').map(function(s){return s.trim();}).filter(Boolean);
    return value;
  }
  function restore(t) {
    Object.keys(fields).forEach(function (k) {if(t[k]===undefined)return;var input=el(fields[k]);if(k==='safe')input.checked=!!t[k];else input.value=k==='keywords'?(Array.isArray(t[k])?t[k].join(', '):t[k]):t[k];});
    if(t.preset && presets.test(t.preset))el('animation').value=t.preset;
    if(el('animFont').value && !fs.existsSync(el('animFont').value))el('animFont').value='';
    preview();
  }
  function save() {el('actualAnimationPreview').hidden=true;localStorage.setItem(key,JSON.stringify(theme()));preview();}
  var fontDirs = process.platform==='win32'?[path.join(process.env.WINDIR || 'C:/Windows','Fonts')]:['/System/Library/Fonts/Supplemental','/Library/Fonts'];
  fontDirs.forEach(function(dir){try {fs.readdirSync(dir).filter(function(n){return /\.(ttf|otf)$/i.test(n);}).sort().forEach(function(n){var option=document.createElement('option');option.value=path.join(dir,n);option.textContent=n.replace(/\.(ttf|otf)$/i,'');el('animFont').appendChild(option);});}catch(_){}});
  function stylesList() {var input=el('animLoadStyle');while(input.options.length>1)input.remove(1);Object.keys(read(stylesKey,{})).sort().forEach(function(n){var o=document.createElement('option');o.value=n;o.textContent=n;input.appendChild(o);});}
  el('animSaveStyle').onclick=function(){if(phase!=='idle'&&phase!=='review')return;var name=el('animStyleName').value.trim();if(!name)return bridge.show('Uslub nomini kiriting.');var styles=read(stylesKey,{});if(name==='__proto__'||name==='constructor')return;styles[name]=theme();localStorage.setItem(stylesKey,JSON.stringify(styles));stylesList();bridge.show('Uslub saqlandi: '+name);};
  el('animLoadStyle').onchange=function(){var t=read(stylesKey,{})[this.value];if(t){restore(t);save();}};
  var sample=['Bugun','yangi','imkoniyatlar','haqida','gaplashamiz.'], previewWords=[], tick=0;
  function preview() {
    var area=el('animationPreview'),t=theme();area.innerHTML='';previewWords=[];
    area.hidden=!presets.test(t.preset);area.style.fontSize=Math.max(12,Math.min(28,t.size/3))+'px';area.style.fontFamily=t.font?path.basename(t.font).replace(/\.(ttf|otf)$/i,''):'Arial';el('animationStyle').hidden=!presets.test(t.preset);
    sample.forEach(function(w){var span=document.createElement('span');span.textContent=w;span.style.color=t.color;area.appendChild(span);previewWords.push(span);});
    tick=0;area.style.alignItems=t.position==='top'?'flex-start':t.position==='bottom'?'flex-end':'center';area.style.paddingBottom=t.position==='bottom'&&t.safe?'22px':'12px';paintPreview();
  }
  function paintPreview() {
    var t=theme(),index=Math.floor(tick/6)%sample.length;
    previewWords.forEach(function(span,i){span.style.transitionDuration=t.speed+'s';var active=i===index;span.style.color=(t.preset==='karaoke'||t.preset==='pop')&&active||t.preset==='emphasis'&&(i===1||t.keywords.some(function(w){return lex(w)===lex(sample[i]);}))?t.active:t.color;
      span.style.background=t.preset==='pill'&&active?t.active+'b0':'transparent';
      span.style.opacity=t.preset==='reveal'&&i>index?'0':'1';
      span.style.transform=t.preset==='pop'&&active?'scale(1.14)':t.preset==='slide'?'translateY('+Math.max(0,14-tick*3)+'px)':'scale(1)';
    });tick=(tick+1)%30;
  }
  Object.keys(fields).forEach(function(k){el(fields[k]).onchange=save;});el('animation').addEventListener('change',save);
  restore(read(key,{}));stylesList();preview();setInterval(paintPreview,100);
  function state() {var s=bridge.state();if(!s.run || !s.run.review)throw Error('Avval subtitr yarating va natijani tekshirish oynasini oching.');return s;}
  function normalizeMetadata(s) {
    if(!s.run||!s.run.metadata||!s.run.metadata.words)return;
    var ordered=s.run.metadata.words.slice().sort(function(a,b){return a.start-b.start;}),result=[];ordered.forEach(function(source){var word=Object.assign({},source),raw=String(word.text),part=raw.trim().replace(/[‘’ʻʼ]/g,"'");if(!part)return;
      var attached=/^[,.!?:;)\]}]/.test(part)||(/^[\'-]/.test(part)&&!/^\s/.test(raw));
      if(attached&&result.length){var previous=result[result.length-1];previous.text+=part;previous.end=Math.max(previous.end,word.end);if(typeof word.confidence==='number')previous.confidence=typeof previous.confidence==='number'?Math.min(previous.confidence,word.confidence):word.confidence;}
      else {word.text=part;result.push(word);}
    });
    var targets=[];s.cues.forEach(function(c){targets=targets.concat(c.text.trim().split(/\s+/).map(lex));});
    s.run.metadata.words=JSON.stringify(targets)===JSON.stringify(result.map(function(w){return lex(w.text);}))?result:ordered;
  }
  function matching(s) {var c=s.cues[s.selected],words=s.run.metadata&&s.run.metadata.words||[],offset=0;for(var i=0;i<s.selected;i++)offset+=s.cues[i].text.trim().split(/\s+/).length;var tokens=c?c.text.trim().split(/\s+/):[],candidate=words.slice(offset,offset+tokens.length);if(candidate.length===tokens.length&&tokens.every(function(t,i){return lex(t)===lex(candidate[i].text);}))return candidate;return c && s.run.metadata && s.run.metadata.words?s.run.metadata.words.filter(function(w){return w.start<c.end&&w.end>c.start;}):[];}
  function metadataCues(s,cues) {var md=s.run.metadata||{words:[]},previous=md.cues||[];md.cues=cues.map(function(c,i){var copy={};Object.keys(previous[i]||{}).forEach(function(k){copy[k]=previous[i][k];});copy.start=c.start;copy.end=c.end;copy.text=c.text;return copy;});return md;}
  function guard(fn) {return function(){if(phase!=='review')return;try {fn();}catch(e){bridge.show(e.message);}};}
  el('mergeCue').onclick=guard(function(){var s=state(),i=s.selected,c=s.cues;if(i+1>=c.length)throw Error('Keyingi subtitr yo‘q.');var md=s.run.metadata||{words:[],cues:[]};if(md.cues){var sp=md.cues[i]&&md.cues[i].speaker,sp2=md.cues[i+1]&&md.cues[i+1].speaker;if(sp!==sp2 && md.cues[i])delete md.cues[i].speaker;md.cues.splice(i+1,1);}
    c.splice(i,2,{start:c[i].start,end:c[i+1].end,text:c[i].text.trim()+' '+c[i+1].text.trim()});bridge.edit(c,metadataCues(s,c),i);});
  el('splitCue').onclick=guard(function(){var s=state(),c=s.cues[s.selected],tokens=c.text.trim().split(/\s+/),words=matching(s),caret=el('cueText').selectionStart || 0;
    if(tokens.length<2||words.length!==tokens.length||tokens.some(function(t,i){return lex(t)!==lex(words[i].text);}))throw Error('Bo‘lish uchun matn va so‘z vaqtlarini moslang.');
    var position=0,split=0;tokens.forEach(function(t,i){if(i>0 && position<=caret)split=i;position+=t.length+1;});if(split<1)throw Error('Kursorni bo‘linadigan so‘z oldiga qo‘ying.');
    var at=words[split].start;if(!(at>c.start&&at<c.end)||words[split-1].end>at+.001)throw Error('Bo‘linish joyida so‘z vaqtlari to‘qnashgan. Vaqtlarni tekshiring.');
    s.cues.splice(s.selected,1,{start:c.start,end:at,text:tokens.slice(0,split).join(' ')},{start:at,end:c.end,text:tokens.slice(split).join(' ')});
    if(s.run.metadata&&s.run.metadata.cues)s.run.metadata.cues.splice(s.selected+1,0,{speaker:(s.run.metadata.cues[s.selected]||{}).speaker});bridge.edit(s.cues,metadataCues(s,s.cues),s.selected);});
  bridge.onReviewChanged=function(){var s=bridge.state();el('wordList').innerHTML='';rows=[];el('actualAnimationPreview').hidden=true;el('animationPreview').hidden=!presets.test(el('animation').value);if(!s.run)return;normalizeMetadata(s);if(s.run.info&&bridge.onHost)bridge.onHost(s.run.info);
    matching(s).forEach(function(w){var row=document.createElement('div');row.className='word-row';var text=document.createElement('input');text.value=w.text;text.setAttribute('aria-label','So‘z matni');
      var start=document.createElement('input'),end=document.createElement('input');[start,end].forEach(function(input){input.type='number';input.step='0.01';input.min='0';});start.value=w.start.toFixed(3);end.value=w.end.toFixed(3);start.setAttribute('aria-label',w.text+' boshlanishi');end.setAttribute('aria-label',w.text+' tugashi');
      var button=document.createElement('button');button.type='button';button.textContent='★';button.title='So‘zga urg‘u berish';button.onclick=function(){var current=theme().keywords;if(!current.some(function(t){return lex(t)===lex(text.value);}))current.push(text.value);el('animKeywords').value=current.join(', ');el('animation').value='emphasis';save();bridge.show('Urg‘u berildi: '+text.value);};
      [text,start,end,button].forEach(function(input){row.appendChild(input);});el('wordList').appendChild(row);rows.push({word:w,text:text,start:start,end:end});});
  };
  el('saveWordTimes').onclick=guard(function(){var s=state(),cue=s.cues[s.selected],changes=rows.map(function(r){var a=Number(r.start.value),b=Number(r.end.value),t=r.text.value.trim();if(!t||/\s/.test(t)||!isFinite(a+b)||a<cue.start-.001||b>cue.end+.001||b<=a)throw Error('So‘z matni yoki vaqti subtitrga mos emas.');return {text:t,start:a,end:b};});
    if(!changes.length)throw Error('So‘z vaqtlari yo‘q. Qayta taning.');changes.forEach(function(w,i){if(i&&changes[i-1].end>w.start+.001)throw Error('So‘z vaqtlari to‘qnashgan.');});
    changes.forEach(function(w,i){rows[i].word.start=w.start;rows[i].word.end=w.end;rows[i].word.text=w.text;});s.cues[s.selected].text=changes.map(function(w){return w.text;}).join(' ');bridge.edit(s.cues,metadataCues(s,s.cues),s.selected);bridge.show('So‘z vaqtlari saqlandi.');});
  function pythonJob(s,args,callback) {
    var child,error='',closed=false;
    try {child=cp.spawn(bridge.python.value,[path.join(bridge.root,'subtitles','animations.py')].concat(args),{env:Object.assign({},process.env,{HF_HUB_OFFLINE:'1'})});}catch(e){callback(e);return;}
    s.run.child=child;
    if(process.platform==='win32'){child.kill=function(){try {cp.spawn('taskkill',['/PID',String(child.pid),'/T','/F']);return true;}catch(_){return false;}};}
    if(child.stdout)child.stdout.on('data',function(chunk){if(s.run.cancelled)return;var lines=String(chunk).trim().split(/\r?\n/);bridge.show('Animatsiya / vaqt: '+lines[lines.length-1]);});
    child.stderr.on('data',function(chunk){error=(error+chunk.toString()).slice(-2500);});
    function done(e){if(closed)return;closed=true;if(bridge.state().run!==s.run)return;s.run.child=null;if(s.run.cancelled){s.run.cancelled=false;bridge.phase('review');bridge.show('Bekor qilindi. Tahriringiz saqlandi.');return;}callback(e);}
    child.on('error',done);child.on('close',function(code){done(code===0?null:Error(error||'Animatsiya tayyorlanmadi.'));});
  }
  function config(s) {normalizeMetadata(s);var t=theme();if(!presets.test(t.preset))throw Error('Avval animatsiya presetini tanlang.');var info=s.run.info;if(s.cues.length&&s.cues[s.cues.length-1].end>info.duration+.05)throw Error('Subtitr vaqti tanlangan oraliqdan chiqdi. SRT vaqtini tuzating.');if(!info.width||!info.height)throw Error('Video o‘lchami aniqlanmadi. Timeline’ni yangilang.');return {schema:1,width:info.width,height:info.height,fps:info.fps,theme:t,cues:s.cues,words:s.run.metadata&&s.run.metadata.words||[]};}
  function files(s) {var base=s.run.srt.replace(/\.srt$/i,'')+'-animation';return {input:base+'.input.json',mov:base+'.mov',plan:base+'.plan.json'};}
  function build(s,onlyPlan,callback) {var f=files(s);try {fs.writeFileSync(f.input,JSON.stringify(config(s)), 'utf8');}catch(e){callback(e);return;}bridge.phase('working');bridge.show(onlyPlan?'Animatsiya qatlamlarini tayyorlayapman...':'Shaffof animatsiyani tayyorlayapman...');var args=['--input',f.input,'--output',f.mov];if(onlyPlan)args.push('--plan-only');pythonJob(s,args,function(err){callback(err,f);});}
  bridge.animateImport=function(srt,info){var s=bridge.state();normalizeMetadata(s);build(s,info.host==='AEFT',function(err,f){if(err)return bridge.problem(err.message,srt);
      bridge.phase('importing');if(info.host==='AEFT'){bridge.aeHost('uzImportAnimatedCaptions('+[f.plan,Number(info.start),info.name,info.identity||''].map(JSON.stringify).join(',')+')',function(e,raw){if(e)return bridge.problem(e.message,srt);var m=/^(\d+) ta vaqtli matn qatlami yaratildi\.$/.exec(String(raw).trim());if(!m||Number(m[1])<1)return bridge.problem(String(raw),srt);bridge.finish(raw+'\nSRT: '+srt);});}
      else bridge.host('uzImportCaptionOverlay('+[f.mov,Number(info.start),info.name,info.identity||'',Math.ceil(s.cues[s.cues.length-1].end*info.fps)/info.fps].map(JSON.stringify).join(',')+')',function(e){if(e)return bridge.problem(e.message+'\nMOV: '+f.mov,srt);bridge.finish('Animatsiya timeline’ga qo‘shildi.\nMOV: '+f.mov);});
    });};
  el('previewAnimation').onclick=guard(function(){var s=state(),f=files(s),output=f.mov.replace(/\.mov$/,'.preview.png');fs.writeFileSync(f.input,JSON.stringify(config(s)),'utf8');bridge.phase('working');bridge.show('Tanlangan subtitr animatsiyasi tayyorlanmoqda...');
    pythonJob(s,['--input',f.input,'--output',output,'--preview','--cue-index',String(s.selected)],function(err){bridge.phase('review');if(err)return bridge.show(err.message);
      var image=el('actualAnimationPreview');image.src='file:///'+output.replace(/\\/g,'/').replace(/^\//,'').split('/').map(encodeURIComponent).join('/').replace(/^([A-Za-z])%3A\//,'$1:/')+'?v='+Date.now();image.hidden=false;el('animationPreview').hidden=true;bridge.show('Tanlangan subtitrning haqiqiy animatsiyasi. Preview: dastlabki 6 soniyagacha.');
    });
  });
  el('exportAnimation').onclick=guard(function(){var s=state();build(s,false,function(err,f){bridge.phase('review');bridge.show(err?err.message:'Shaffof MOV: '+f.mov);});});
  el('exportMogrt').onclick=guard(function(){var s=state();if(s.run.info.host!=='AEFT')throw Error('MOGRT yaratish uchun subtitrni After Effects’da tayyorlang.');build(s,true,function(err,f){if(err){bridge.phase('review');return bridge.show(err.message);}var dir=f.mov.replace(/\.mov$/,'-mogrt');bridge.mkdir(dir);bridge.phase('importing');bridge.aeHost('uzExportCaptionMogrts('+[f.plan,dir,s.run.info.name,s.run.info.identity||''].map(JSON.stringify).join(',')+')',function(e,raw){bridge.phase('review');bridge.show(e?e.message:String(raw));});});});
  el('importMogrt').onclick=guard(function(){var s=state(),name=el('mogrtManifest').value.trim();if(s.run.info.host!=='PPRO')throw Error('MOGRT importi Premiere Pro uchun.');var manifest=JSON.parse(fs.readFileSync(name,'utf8'));if(manifest.schema!==1||!Array.isArray(manifest.clips)||!manifest.clips.length)throw Error('MOGRT manifesti noto‘g‘ri.');if(Number(manifest.width)!==Number(s.run.info.width)||Number(manifest.height)!==Number(s.run.info.height))throw Error('MOGRT o‘lchami sequence’ga mos emas.');var last=0;manifest.clips.forEach(function(c){if(typeof c.path==='string'&&!path.isAbsolute(c.path))c.path=path.resolve(path.dirname(name),c.path);if(!isFinite(c.start+c.end)||c.start<last||c.end<=c.start||!fs.existsSync(c.path)||! /\.mogrt$/i.test(c.path))throw Error('MOGRT fayli yoki vaqti noto‘g‘ri.');last=c.end;});if(last>s.run.info.duration+.05)throw Error('MOGRT tanlangan oraliqqa sig‘madi.');bridge.phase('importing');bridge.host('uzImportCaptionMogrts('+JSON.stringify(manifest.clips)+','+[Number(s.run.info.start),s.run.info.name,s.run.info.identity||''].map(JSON.stringify).join(',')+')',function(err){bridge.phase('review');bridge.show(err?err.message:'MOGRT’lar timeline’ga qo‘shildi.');});});
  el('refineTimes').onclick=guard(function(){var s=state();if(!s.run.audio||!fs.existsSync(s.run.audio))throw Error('Tekshirish audiosi topilmadi. Subtitrni qayta yarating.');var md=s.run.metadata;if(!md||!md.words||!md.words.length)throw Error('So‘z vaqtlari yo‘q.');normalizeMetadata(s);var cursor=0;var groups=s.cues.map(function(c){var tokens=c.text.trim().split(/\s+/),indices=[];tokens.forEach(function(t){if(!md.words[cursor]||lex(t)!==lex(md.words[cursor].text))throw Error('Vaqtni tekshirishdan oldin matn va so‘zlarni moslang.');indices.push(cursor++);});return indices;});var f=files(s),out=f.mov.replace(/\.mov$/,'.refined.json');fs.writeFileSync(f.input,JSON.stringify({words:md.words}),'utf8');bridge.phase('working');bridge.show('Global modeli bilan so‘z vaqtlarini tekshiryapman...');pythonJob(s,['--input',f.input,'--output',out,'--refine-audio',s.run.audio],function(err){bridge.phase('review');if(err)return bridge.show(err.message);try {var result=JSON.parse(fs.readFileSync(out,'utf8'));var cues=s.cues.map(function(c,i){var indices=groups[i];return {text:c.text,start:indices.length?Math.floor(result.words[indices[0]].start*1000)/1000:c.start,end:indices.length?Math.ceil(result.words[indices[indices.length-1]].end*1000)/1000:c.end};});var nextMd=JSON.parse(JSON.stringify(md));nextMd.words=result.words;bridge.edit(cues,nextMd,s.selected);bridge.show(result.matched+'/'+result.total+' so‘z vaqti tekshirildi.');}catch(e){bridge.show('Vaqtlar saqlanmadi: '+e.message);}});});
  bridge.onHost=function(info){host=info.host;el('exportMogrt').hidden=host!=='AEFT';el('importMogrt').hidden=host!=='PPRO';el('mogrtManifest').parentNode.hidden=host!=='PPRO';var composer=Array.prototype.filter.call(el('animation').options,function(o){return o.value==='composer';})[0];if(composer)composer.disabled=host!=='AEFT';if(host!=='AEFT'&&el('animation').value==='composer')el('animation').value='none';};
  bridge.onPhase=function(p){phase=p;var busy=p!=='idle'&&p!=='review';Object.keys(fields).forEach(function(k){el(fields[k]).disabled=busy;});['animation','animSaveStyle','animLoadStyle','animStyleName','mergeCue','splitCue','saveWordTimes','refineTimes','exportAnimation','exportMogrt','importMogrt','mogrtManifest','previewAnimation','cueText','srtEditor'].forEach(function(id){el(id).disabled=busy;});el('previewAnimation').hidden=p!=='review';el('workActions').hidden=!busy;el('cancel').disabled=p==='importing';};
  bridge.onPhase('idle');
}());
