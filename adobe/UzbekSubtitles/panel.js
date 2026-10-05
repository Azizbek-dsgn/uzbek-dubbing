/* global __adobe_cep__ */
(function () {
  'use strict';
  var fs = require('fs');
  var os = require('os');
  var path = require('path');
  var spawn = require('child_process').spawn;
  var devRoot = path.resolve(fs.realpathSync(__dirname), '..', '..');
  var userData = process.platform === 'win32'
    ? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'), 'UzbekSubtitles')
    : path.join(os.homedir(), 'Library', 'Application Support', 'UzbekSubtitles');
  var root = fs.existsSync(path.join(userData, 'subtitles', 'cli.py')) ? userData : devRoot;
  var hostScript = path.join(__dirname, 'host', 'editor.jsx');
  var aeScript = path.join(__dirname, 'host', 'after_effects.jsx');
  var python = document.getElementById('python');
  var premierePreset = document.getElementById('premierePreset');
  var batchDir = document.getElementById('batchDir');
  var batchRun = document.getElementById('batchRun');
  var model = document.getElementById('model');
  var compareModel = document.getElementById('compareModel');
  var retryModel = document.getElementById('retryModel');
  var scriptChoice = document.getElementById('script');
  var captionMode = document.getElementById('captionMode');
  var animation = document.getElementById('animation');
  var animationField = document.getElementById('animationField');
  var animationHint = document.getElementById('animationHint');
  var exportVtt = document.getElementById('exportVtt');
  var exportAss = document.getElementById('exportAss');
  var detectSpeakers = document.getElementById('detectSpeakers');
  var speakerCount = document.getElementById('speakerCount');
  var speakerChoice = document.getElementById('speakerChoice');
  var assignSpeaker = document.getElementById('assignSpeaker');
  var modelHint = document.getElementById('modelHint');
  var fps = document.getElementById('fps');
  var range = document.getElementById('range');
  var audioTrack = document.getElementById('audioTrack');
  var style = document.getElementById('style');
  var lines = document.getElementById('lines');
  var words = document.getElementById('words');
  var chars = document.getElementById('chars');
  var duration = document.getElementById('duration');
  var pause = document.getElementById('pause');
  var splitSentences = document.getElementById('splitSentences');
  var splitCommas = document.getElementById('splitCommas');
  var splitPauses = document.getElementById('splitPauses');
  var startPad = document.getElementById('startPad');
  var endPad = document.getElementById('endPad');
  var minCue = document.getElementById('minCue');
  var glossary = document.getElementById('glossary');
  var preview = document.getElementById('preview');
  var boundaryPreview = document.getElementById('boundaryPreview');
  var run = document.getElementById('run');
  var cancel = document.getElementById('cancel');
  var reviewSection = document.getElementById('reviewSection');
  var reviewInfo = document.getElementById('reviewInfo');
  var srtEditor = document.getElementById('srtEditor');
  var cueText = document.getElementById('cueText');
  var cueList = document.getElementById('cueList');
  var waveform = document.getElementById('waveform');
  var retryCue = document.getElementById('retryCue');
  var compareText = document.getElementById('compareText');
  var applyReview = document.getElementById('applyReview');
  var discardReview = document.getElementById('discardReview');
  var mainActions = document.getElementById('mainActions');
  var workActions = document.getElementById('workActions');
  var reviewActions = document.getElementById('reviewActions');
  var refresh = document.getElementById('refresh');
  var timeline = document.getElementById('timeline');
  var status = document.getElementById('status');
  var advanced = document.getElementById('advanced');
  var activeRun = null;
  var selectedCue = 0;
  var undoReview = document.getElementById('undoReview'), redoReview = document.getElementById('redoReview');
  var resumeReview = document.getElementById('resumeReview'), reviewHistory = [], historyAt = -1, historyRestoring = false;
  var draftPath = path.join(root, 'exports', 'review-draft.json');
  function historyControls() {
    var available = !!(activeRun && activeRun.review && !reviewSection.hidden);
    if (undoReview) undoReview.disabled = !available || historyAt <= 0;
    if (redoReview) redoReview.disabled = !available || historyAt >= reviewHistory.length - 1;
    if (resumeReview) resumeReview.hidden = !fs.existsSync(draftPath);
  }
  function recordReview() {
    if (!activeRun || !activeRun.review || historyRestoring) return;
    var snapshot = {text:srtEditor.value, metadata:JSON.parse(JSON.stringify(activeRun.metadata || null)), selected:selectedCue};
    var previous = reviewHistory[historyAt];
    if (!previous || previous.text !== snapshot.text || JSON.stringify(previous.metadata) !== JSON.stringify(snapshot.metadata)) {
      reviewHistory = reviewHistory.slice(0, historyAt + 1); reviewHistory.push(snapshot);
      if (reviewHistory.length > 40) reviewHistory.shift(); historyAt = reviewHistory.length - 1;
    }
    try {
      validateSrt(snapshot.text); ensureDirectory(path.dirname(draftPath));
      fs.writeFileSync(draftPath + '.tmp', JSON.stringify({schema:1,srt:activeRun.srt,audio:activeRun.audio,info:activeRun.info,
        text:snapshot.text,metadata:snapshot.metadata,selected:selectedCue}), 'utf8');
      fs.renameSync(draftPath + '.tmp', draftPath);
    } catch (_) {} // Keep the last valid draft while the user is typing incomplete SRT.
    historyControls();
  }
  function moveHistory(delta) {
    if (!activeRun || !activeRun.review || reviewSection.hidden) return;
    var next = historyAt + delta; if (next < 0 || next >= reviewHistory.length) return;
    var snapshot = reviewHistory[next]; historyAt = next; historyRestoring = true;
    try {srtEditor.value = snapshot.text; activeRun.metadata = JSON.parse(JSON.stringify(snapshot.metadata)); selectedCue = snapshot.selected; renderCues();}
    finally {historyRestoring = false;}
    recordReview(); historyControls(); show(delta < 0 ? 'Tahrir ortga qaytarildi.' : 'Tahrir qayta qo‘llandi.');
  }
  if (undoReview) undoReview.onclick = function () {moveHistory(-1);};
  if (redoReview) redoReview.onclick = function () {moveHistory(1);};
  if (resumeReview) resumeReview.onclick = function () {
    if (activeRun) return;
    var draft;
    try {draft = JSON.parse(fs.readFileSync(draftPath, 'utf8'));validateSrt(draft.text);
      if (draft.schema !== 1 || !draft.info || !draft.srt || path.dirname(path.resolve(draft.srt)) !== path.join(root,'exports') || !fs.existsSync(draft.srt))
        throw new Error('Oxirgi tahrir fayli topilmadi yoki noto‘g‘ri.');
    } catch (e) {show('Tahrir tiklanmadi: ' + e.message);return;}
    getInfo(function (error, current) {
      if (activeRun) return;
      if (error) {show(error.message);return;}
      if (current.host !== draft.info.host || current.identity !== draft.info.identity || current.name !== draft.info.name ||
          Number(current.width) !== Number(draft.info.width) || Number(current.height) !== Number(draft.info.height) ||
          Math.abs(current.fps - draft.info.fps) > .001 || draft.info.start < 0 || draft.info.start + draft.info.duration > current.duration + .05) {
        show('Oxirgi tahrir uchun '+draft.info.name+' loyihasini oching. Timeline o‘lchami yoki vaqti o‘zgargan.');return;
      }
      activeRun = {review:true,cancelled:false,child:null,srt:draft.srt,info:draft.info,metadata:draft.metadata,
        audio:draft.audio && fs.existsSync(draft.audio) ? draft.audio : null};
      srtEditor.value = draft.text; selectedCue = Number(draft.selected) || 0; reviewHistory = []; historyAt = -1;
      setPhase('review');renderCues();reviewInfo.textContent = 'Oxirgi tahrir tiklandi.';
      show(activeRun.audio ? 'Oxirgi tahriringiz tiklandi.' : 'Tahrir tiklandi. Audio vaqtinchalik fayli yo‘q; qayta tanish uchun subtitrni yangidan yarating.');
    }, 'full');
  };
  var localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  python.value = fs.existsSync(localPython) ? localPython : (process.platform === 'win32' ? 'python' : 'python3');
  if (fs.existsSync(path.join(root, 'models', 'navai-medium', 'model.bin'))) {
    var option = document.createElement('option');
    option.value = 'navai-medium';
    option.textContent = 'Scribe Nav';
    model.insertBefore(option, model.firstChild);
    model.value = 'navai-medium';
  }
  if (fs.existsSync(path.join(root, 'models', 'gigaam-uzbek', 'checkpoints', 'large_full_600m', 'best.pt')) &&
      fs.existsSync(path.join(root, 'models', 'gigaam-base-large', 'config.json')) &&
      fs.existsSync(path.join(root, 'models', 'gigaam-base-large', 'modeling_gigaam.py'))) {
    var gigaamOption = document.createElement('option');
    gigaamOption.value = 'gigaam-uzbek';
    gigaamOption.textContent = 'Scribe Giga';
    model.insertBefore(gigaamOption, model.firstChild);
    model.value = 'gigaam-uzbek';
  }
  Array.prototype.forEach.call(model.options, function (item) {
    var second = document.createElement('option');
    second.value = item.value; second.textContent = item.textContent;
    compareModel.appendChild(second);
    var retry = document.createElement('option');
    retry.value = item.value; retry.textContent = item.textContent;
    retryModel.appendChild(retry);
  });
  var savedFields = {
    range: range, audioTrack: audioTrack, model: model, style: style, lines: lines, words: words,
    chars: chars, duration: duration, pause: pause,
    literary: document.getElementById('literary'),
    restoreSentences: document.getElementById('restoreSentences'), splitSentences: splitSentences,
    splitCommas: splitCommas, splitPauses: splitPauses, startPad: startPad,
    endPad: endPad, minCue: minCue, glossary: glossary, python: python,
    premierePreset: premierePreset,
    compareModel: compareModel, script: scriptChoice, captionMode: captionMode, aeLayerMode: document.getElementById('aeLayerMode'),
    exportVtt: exportVtt, exportAss: exportAss, detectSpeakers: detectSpeakers,
    speakerCount: speakerCount, batchDir: batchDir, animation: animation
  };
  function saveSettings() {
    var values = {};
    Object.keys(savedFields).forEach(function (key) {
      var field = savedFields[key];
      values[key] = field.type === 'checkbox' ? field.checked : field.value;
    });
    values.advanced = advanced.open;
    try { localStorage.setItem('uzbekSubtitles.settings.v1', JSON.stringify(values)); } catch (e) {}
  }
  try {
    var saved = JSON.parse(localStorage.getItem('uzbekSubtitles.settings.v1') || '{}');
    Object.keys(savedFields).forEach(function (key) {
      var field = savedFields[key];
      if (!Object.prototype.hasOwnProperty.call(saved, key)) return;
      if (key === 'python' && fs.existsSync(localPython) && !fs.existsSync(saved[key] || '')) return;
      if (field.type === 'checkbox') field.checked = !!saved[key];
      else if (field.tagName !== 'SELECT' || Array.prototype.some.call(field.options, function (item) { return item.value === saved[key]; })) {
        field.value = saved[key];
      }
    });
    advanced.open = !!saved.advanced;
  } catch (e) {}
  Object.keys(savedFields).forEach(function (key) {
    savedFields[key].addEventListener('change', saveSettings);
    if (savedFields[key].type !== 'checkbox') savedFields[key].addEventListener('input', saveSettings);
  });
  advanced.addEventListener('toggle', saveSettings);
  function updateModelHint() {
    modelHint.textContent = model.value === 'gigaam-uzbek'
      ? 'GigaAM Uzbek 600M · o‘zbekcha suhbat nutqi.'
      : model.value === 'navai-medium' ? 'NavAI Uzbek medium · o‘zbekchaga moslashtirilgan.'
      : 'Whisper large-v3 · katta ko‘p tilli model. Subtitr tili: o‘zbekcha.';
  }
  model.addEventListener('change', updateModelHint);
  updateModelHint();

  var styles = {
    short: [1, 4, 36, 3.0, 0.45],
    medium: [2, 3, 42, 5.0, 0.65],
    long: [2, 6, 50, 7.0, 0.8]
  };
  function updatePreview() {
    var sample = ['Bugun', 'o‘zbekcha', 'subtitrlar', 'aniq', 'vaqt', 'bilan', 'ekranda', 'chiqadi',
      'Har', 'bir', 'qatordagi', 'so‘zlar', 'sonini', 'o‘zingiz', 'tanlab', 'olishingiz',
      'mumkin', 'Bu', 'namuna', 'sozlamalarni', 'oldindan', 'ko‘rishga', 'yordam', 'beradi'];
    var count = Math.max(1, Math.min(8, Number(words.value) || 1));
    var rows = Math.max(1, Math.min(3, Number(lines.value) || 1));
    var width = Math.max(8, Math.min(80, Number(chars.value) || 42));
    var result = [], index = 0;
    for (var i = 0; i < rows; i++) {
      var line = [], length = 0;
      while (line.length < count && index < sample.length) {
        var next = sample[index];
        if (line.length && length + next.length + 1 > width) break;
        line.push(next); length += next.length + (line.length > 1 ? 1 : 0); index++;
      }
      if (line.length) result.push(line.join(' '));
    }
    preview.textContent = result.join('\n');
    var example = 'Bugun, havo yaxshi. Ertaga uchrashamiz.';
    if (splitCommas.checked) example = example.replace(/, /g, ',\n');
    if (splitSentences.checked) example = example.replace(/([.!?]) /g, '$1\n');
    boundaryPreview.textContent = example;
  }
  function applyStyle() {
    var values = styles[style.value];
    if (!values) return;
    [lines, words, chars, duration, pause].forEach(function (field, i) { field.value = values[i]; });
    updatePreview();
    saveSettings();
  }
  style.onchange = applyStyle;
  [lines, words, chars, duration, pause].forEach(function (field) {
    field.oninput = function () { style.value = 'custom'; updatePreview(); saveSettings(); };
  });
  splitPauses.onchange = function () { pause.disabled = !splitPauses.checked; };
  pause.disabled = !splitPauses.checked;
  splitSentences.onchange = updatePreview;
  splitCommas.onchange = updatePreview;
  updatePreview();
  function validNumber(field, minimum, maximum) {
    var value = Number(field.value);
    return isFinite(value) && value >= minimum && value <= maximum ? value : null;
  }
  function glossaryRules() {
    var rules = [];
    glossary.value.replace(/\r/g, '').split('\n').forEach(function (raw, index) {
      var line = raw.trim();
      if (!line) return;
      var separator = line.indexOf('=>') !== -1 ? '=>' : '=';
      var position = line.indexOf(separator);
      var source = position >= 0 ? line.slice(0, position).trim() : '';
      var target = position >= 0 ? line.slice(position + separator.length).trim() : '';
      if (!source || !target || /\s/.test(source) || /\s/.test(target)) {
        throw new Error('Lug‘atning ' + (index + 1) + '-qatorini tekshiring: bitta so‘z = bitta so‘z.');
      }
      rules.push(source + '=' + target);
    });
    return rules;
  }

  function show(message) { status.textContent = message; }
  function hostCall(script, expression, callback) {
    __adobe_cep__.evalScript('$.evalFile(new File(' + JSON.stringify(script) + '));' + expression, function (raw) {
      if (raw === 'EvalScript error.') { callback(new Error('Adobe host skripti ishga tushmadi.')); return; }
      callback(null, raw);
    });
  }
  function jsonCall(expression, callback, adapter) {
    hostCall(adapter || hostScript, expression, function (err, raw) {
      if (err) { callback(err); return; }
      try {
        var result = JSON.parse(raw);
        callback(result.error ? new Error(result.error) : null, result);
      } catch (e) { callback(new Error('Adobe javobi o‘qilmadi: ' + raw)); }
    });
  }
  function ensureDirectory(directory) {
    if (fs.existsSync(directory)) {
      if (!fs.statSync(directory).isDirectory()) throw new Error('Papka o‘rnida fayl bor: ' + directory);
      return;
    }
    var parent = path.dirname(directory);
    if (parent !== directory) ensureDirectory(parent);
    try { fs.mkdirSync(directory); }
    catch (error) { if (!fs.existsSync(directory)) throw error; }
  }
  document.uzscribe = {host:jsonCall, root:root, python:python, mkdir:ensureDirectory,
    aeHost:function(expression, callback) {hostCall(aeScript, expression, callback);},
    state:function() {return {run:activeRun, selected:selectedCue, cues:cueData()};},
    edit:function(cues, metadata, selected) {
      function stamp(t) {var ms=Math.round(t*1000),h=Math.floor(ms/3600000);ms-=h*3600000;var m=Math.floor(ms/60000);ms-=m*60000;var sec=Math.floor(ms/1000);ms-=sec*1000;
        function pad(n,l) {return ('0000'+n).slice(-l);}return pad(h,2)+':'+pad(m,2)+':'+pad(sec,2)+','+pad(ms,3);}
      var value=cues.map(function(c,i) {return (i+1)+'\n'+stamp(c.start)+' --> '+stamp(c.end)+'\n'+c.text;}).join('\n\n')+'\n\n';
      srtEditor.value=validateSrt(value).text;if(activeRun) activeRun.metadata=metadata;
      selectedCue=selected||0;renderCues();
    }, phase:setPhase, show:show, finish:finish, problem:importProblem, authorize:allowLicense};
  function adobeHost() {
    try {var environment=JSON.parse(__adobe_cep__.getHostEnvironment());return environment.appName;}
    catch (_) {return '';}
  }
  function getInfo(callback, selectedRange) {
    var ae=adobeHost()==='AEFT';
    jsonCall((ae?'uzAeTimelineInfo(':'uzTimelineInfo(') + JSON.stringify(selectedRange || range.value) + ')', callback, ae?aeScript:hostScript);
  }
  function hostUi(host) {
      document.getElementById('aeLayerModeField').hidden=host!=='AEFT';
      Array.prototype.forEach.call(range.options,function(option){
        if(option.value==='auto')option.textContent=host==='AEFT'?'Tanlangan video layer':'In/Out yoki to‘liq video';
        if(option.value==='full')option.textContent=host==='AEFT'?'Tanlangan layer · to‘liq':'To‘liq video';
        if(option.value==='inout')option.textContent=host==='AEFT'?'Tanlangan layer · Work Area B/N':'Faqat In/Out · I/O';
      });
      if(premierePreset.parentNode)premierePreset.parentNode.hidden=host==='AEFT';
      if(audioTrack.parentNode)audioTrack.parentNode.hidden=host==='AEFT';
      ['podcastTab','reelsTab'].forEach(function(id){var tab=document.getElementById(id);if(tab)tab.hidden=host==='AEFT';});
  }
  function refreshTimeline() {
    var host=adobeHost();if(host)hostUi(host);
    getInfo(function (err, info) {
      if (activeRun) return;
      if (err) { timeline.textContent = err.message; return; }
      timeline.textContent = (info.host==='AEFT'&&info.layer_name ? info.layer_name : info.name) + ' · ' + info.duration.toFixed(2) + ' s · ' +
        (info.marked ? ('boshlanish ' + info.start.toFixed(2) + ' s') : 'to‘liq') +
        ' · ' + info.fps.toFixed(3) + ' fps';
      fps.value = info.fps.toFixed(3);
      hostUi(info.host);
      var wanted = audioTrack.value;
      while (audioTrack.options.length > 1) audioTrack.remove(1);
      if (info.host === 'PPRO') {
        for (var i = 0; i < Number(info.trackCount || 0); i++) {
          var option = document.createElement('option');
          option.value = String(i); option.textContent = 'Audio ' + (i + 1);
          audioTrack.appendChild(option);
        }
      }
      audioTrack.value = Array.prototype.some.call(audioTrack.options, function (o) {
        return o.value === wanted;
      }) ? wanted : 'all';
      audioTrack.disabled = info.host !== 'PPRO';
      animationField.hidden = false;
      animation.disabled = false;
      animationHint.textContent = info.host === 'AEFT' ? 'Subtitr yoki alohida so‘z layerlarini tanlang. Qator joylashuvi saqlanadi.' : 'Shaffof animatsiya klipi uchun bo‘sh video trek kerak.';
      if (document.uzscribe.onHost) document.uzscribe.onHost(info);
    });
  }
  function presetPath() {
    if (premierePreset.value.trim() && fs.existsSync(premierePreset.value.trim()))
      return premierePreset.value.trim();
    var name = 'WAV_Mono_16bit_16kHz.epr';
    var roots = process.platform === 'win32'
      ? [process.env.ProgramFiles, process.env['ProgramFiles(x86)']]
      : ['/Applications'];
    var versions = [];
    for (var year = new Date().getFullYear() + 1; year >= 2020; year--)
      versions.push(String(year));
    for (var r = 0; r < roots.length; r++) {
      if (!roots[r]) continue;
      for (var i = 0; i < versions.length; i++) {
        var folder = 'Adobe Premiere Pro ' + versions[i];
        var base = process.platform === 'win32'
          ? path.join(roots[r], 'Adobe', folder)
          : path.join(roots[r], folder, folder + '.app', 'Contents');
        var locations = [path.join(base, 'Settings', 'EncoderPresets', name),
          path.join(base, 'Plug-ins', 'Common', 'Exporter', name)];
        for (var j = 0; j < locations.length; j++) {
          if (fs.existsSync(locations[j])) return locations[j];
        }
      }
    }
    return '';
  }
  function setPhase(phase) {
    document.uzscribeBusy = phase !== 'idle';
    mainActions.hidden = phase !== 'idle';
    workActions.hidden = phase !== 'working';
    reviewActions.hidden = phase !== 'review';
    reviewSection.hidden = phase !== 'review';
    refresh.disabled = phase !== 'idle';
    batchRun.disabled = phase !== 'idle';
    Object.keys(savedFields).forEach(function (key) {
      savedFields[key].disabled = phase !== 'idle' || (key === 'pause' && !splitPauses.checked) ||
        (key === 'animation' && animationField.hidden) ||
        ((key === 'audioTrack' || key === 'premierePreset') && adobeHost()==='AEFT');
    });
    cancel.disabled = false;
    historyControls();
    if (document.uzscribe.onPhase) document.uzscribe.onPhase(phase);
  }
  function finish(message) {
    if (activeRun && activeRun.review) {removeTemp(draftPath);removeTemp(draftPath+'.tmp');}
    if (activeRun && activeRun.audio) removeTemp(activeRun.audio);
    activeRun = null; setPhase('idle'); show(message);
  }
  function removeTemp(filename) { if (!filename) return; try { fs.unlinkSync(filename); } catch (e) {} }
  function validateSrt(input) {
    var blocks = input.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim().split(/\n\s*\n/);
    if (!blocks.length || !blocks[0]) throw new Error('SRT bo‘sh.');
    var result = [], previousEnd = 0;
    function millis(stamp) {
      var m = /^(\d{2}):(\d{2}):(\d{2}),(\d{3})$/.exec(stamp);
      if (!m || Number(m[2]) > 59 || Number(m[3]) > 59) return null;
      return ((Number(m[1]) * 60 + Number(m[2])) * 60 + Number(m[3])) * 1000 + Number(m[4]);
    }
    blocks.forEach(function (block, index) {
      var lines = block.split('\n');
      var span = lines.length > 1 && /^(\S+) --> (\S+)$/.exec(lines[1]);
      var start = span && millis(span[1]), end = span && millis(span[2]);
      if (!/^\d+$/.test(lines[0]) || start === null || end === null || !span ||
          end <= start || start < previousEnd || !lines.slice(2).join('').trim()) {
        throw new Error((index + 1) + '-subtitrning raqami, vaqti yoki matnini tekshiring.');
      }
      previousEnd = end;
      result.push((index + 1) + '\n' + span[1] + ' --> ' + span[2] + '\n' + lines.slice(2).join('\n').trim());
    });
    return {text: result.join('\n\n') + '\n\n', count: result.length};
  }
  function cueBlocks() {
    var text = srtEditor.value.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim();
    return text ? text.split(/\n\s*\n/) : [];
  }
  function cueData() {
    return cueBlocks().map(function (block, index) {
      var lines = block.split('\n');
      var span = lines[1] && /^(\S+) --> (\S+)$/.exec(lines[1]);
      function seconds(value) {
        var m = /^(\d\d):(\d\d):(\d\d),(\d{3})$/.exec(value || '');
        return m ? Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]) + Number(m[4]) / 1000 : 0;
      }
      return {index:index, start:seconds(span && span[1]), end:seconds(span && span[2]),
        text:lines.slice(2).join('\n')};
    });
  }
  function writeEditedFormats(srtPath) {
    var cues = cueData();
    if (exportVtt.checked) {
      var vtt = 'WEBVTT\n\n' + cues.map(function (cue) {
        var block = cueBlocks()[cue.index].split('\n');
        return block[1].replace(/,/g, '.') + '\n' + block.slice(2).join('\n');
      }).join('\n\n') + '\n\n';
      fs.writeFileSync(srtPath.replace(/\.srt$/, '.vtt'), vtt, 'utf8');
    }
    if (exportAss.checked) {
      function time(s) {
        var m = /^(\d\d):(\d\d):(\d\d),(\d{3})$/.exec(s);
        return Number(m[1]) + ':' + m[2] + ':' + m[3] + '.' + ('0' + Math.floor(Number(m[4]) / 10)).slice(-2);
      }
      var ass = '[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n' +
        '[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n' +
        'Style: Default,Arial,56,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,80,80,75,1\n\n' +
        '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n';
      cueBlocks().forEach(function (block, index) {
        var lines = block.split('\n'), span = lines[1].split(' --> ');
        var speaker = activeRun && activeRun.metadata && activeRun.metadata.cues &&
          activeRun.metadata.cues[index] && activeRun.metadata.cues[index].speaker || '';
        ass += 'Dialogue: 0,' + time(span[0]) + ',' + time(span[1]) + ',Default,' +
          String(speaker).replace(/[^A-Za-z0-9_-]/g, '') + ',0,0,0,,' +
          lines.slice(2).join('\\N').replace(/[{}]/g, '') + '\n';
      });
      fs.writeFileSync(srtPath.replace(/\.srt$/, '.ass'), ass, 'utf8');
    }
  }
  function drawWaveform() {
    if (!waveform || !waveform.getContext || !activeRun || !activeRun.audio) return;
    var ctx = waveform.getContext('2d');
    if (!ctx) return;
    var width = waveform.width, height = waveform.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#132033'; ctx.fillRect(0, 0, width, height);
    var file = activeRun.audio, size = 0;
    try { size = fs.statSync(file).size; } catch (e) { return; }
    var handle;
    try {
      handle = fs.openSync(file, 'r');
      var head = Buffer.alloc(12); fs.readSync(handle, head, 0, 12, 0);
      if (head.toString('ascii', 0, 4) !== 'RIFF' || head.toString('ascii', 8, 12) !== 'WAVE') return;
      var channels = 1, bits = 16, format = 1, dataAt = -1, dataSize = 0, at = 12;
      while (at + 8 <= size) {
        var chunk = Buffer.alloc(8); fs.readSync(handle, chunk, 0, 8, at);
        var length = chunk.readUInt32LE(4), kind = chunk.toString('ascii', 0, 4);
        if (kind === 'fmt ' && length >= 16) {
          var fmt = Buffer.alloc(16); fs.readSync(handle, fmt, 0, 16, at + 8);
          format = fmt.readUInt16LE(0); channels = fmt.readUInt16LE(2); bits = fmt.readUInt16LE(14);
        }
        if (kind === 'data') { dataAt = at + 8; dataSize = Math.min(size - dataAt, length); break; }
        at += 8 + length + (length % 2);
      }
      if (dataAt < 0 || channels < 1 || (format !== 1 && format !== 3) ||
          (bits !== 16 && bits !== 32)) return;
      var sampleBytes = bits / 8 * channels;
      var column = Buffer.alloc(Math.max(sampleBytes, 4096));
      ctx.fillStyle = '#70b6ff';
      for (var x = 0; x < width; x++) {
        var pos = dataAt + Math.floor(x / width * dataSize / sampleBytes) * sampleBytes;
        var count = Math.min(column.length, Math.max(0, size - pos));
        count -= count % sampleBytes;
        if (!count) continue;
        fs.readSync(handle, column, 0, count, pos);
        var peak = 0;
        for (var j = 0; j < count; j += sampleBytes) {
          var sample = format === 3 ? column.readFloatLE(j) :
            bits === 16 ? column.readInt16LE(j) / 32768 : column.readInt32LE(j) / 2147483648;
          peak = Math.max(peak, Math.min(1, Math.abs(sample)));
        }
        var bar = Math.max(1, peak * height * 0.44);
        ctx.fillRect(x, height / 2 - bar, 1, bar * 2);
      }
    } catch (e) { show('Audio to‘lqini o‘qilmadi: ' + e.message); }
    finally { if (handle !== undefined) fs.closeSync(handle); }
    var cues = cueData(), total = Number(activeRun.info && activeRun.info.duration) || 1;
    cues.forEach(function (cue, index) {
      var x = Math.max(0, cue.start / total * width), end = Math.min(width, cue.end / total * width);
      ctx.fillStyle = index === selectedCue ? 'rgba(255,194,89,.32)' : 'rgba(120,190,255,.12)';
      ctx.fillRect(x, 0, Math.max(1, end - x), height);
    });
  }
  function renderCues() {
    if (!cueList || !cueList.appendChild) return;
    var cues = cueData(), metadata = activeRun && activeRun.metadata;
    cueList.innerHTML = '';
    cues.forEach(function (cue, index) {
      var matching = metadata && metadata.words ? metadata.words.filter(function (w) {
        return w.start < cue.end && w.end > cue.start && typeof w.confidence === 'number';
      }) : [];
      var score = matching.length ? matching.reduce(function (sum, w) { return sum + w.confidence; }, 0) / matching.length : null;
      var other = metadata && metadata.comparison_words ? metadata.comparison_words.filter(function (w) {
        return w.start < cue.end && w.end > cue.start;
      }).map(function (w) { return w.text.trim(); }).join(' ') : '';
      var item = document.createElement('button'); item.type = 'button';
      item.className = 'cue-item' + (index === selectedCue ? ' selected' : '');
      var stamp = document.createElement('span'); stamp.className = 'time';
      stamp.textContent = cue.start.toFixed(2) + '–' + cue.end.toFixed(2);
      var label = document.createElement('span'); label.textContent = cue.text;
      var speakerName = metadata && metadata.cues && metadata.cues[index] && metadata.cues[index].speaker;
      if (speakerName) label.textContent = 'S' + (Number(String(speakerName).replace(/\D/g, '')) + 1) + ' · ' + cue.text;
      if ((score !== null && score < 0.55) ||
          (other && other.toLowerCase().replace(/[^a-z0-9']/g, '') !==
           cue.text.toLowerCase().replace(/[^a-z0-9']/g, ''))) label.className = 'weak';
      item.appendChild(stamp); item.appendChild(label);
      item.onclick = function () {
        selectedCue = index; renderCues(); drawWaveform();
        speakerChoice.value = speakerName || '';
        var blocks = cueBlocks(), before = blocks.slice(0, index).join('\n\n');
        var from = before.length + (index ? 2 : 0);
        if (srtEditor.setSelectionRange) srtEditor.setSelectionRange(from, from + blocks[index].length);
        if (srtEditor.focus) srtEditor.focus();
        var alternatives = metadata && metadata.comparison_words;
        var text = alternatives ? alternatives.filter(function (w) {
          return w.start < cue.end && w.end > cue.start;
        }).map(function (w) { return w.text.trim(); }).join(' ') : '';
        compareText.textContent = text ? (metadata.comparison_model + ': ' + text) : '';
      };
      cueList.appendChild(item);
    });
    if (selectedCue >= cues.length) selectedCue = Math.max(0, cues.length - 1);
    speakerChoice.value = metadata && metadata.cues && metadata.cues[selectedCue] &&
      metadata.cues[selectedCue].speaker || '';
    var cue = cues[selectedCue], alternatives = metadata && metadata.comparison_words;
    cueText.value = cue ? cue.text : '';
    var alternativeText = cue && alternatives ? alternatives.filter(function (w) {
      return w.start < cue.end && w.end > cue.start;
    }).map(function (w) { return w.text.trim(); }).join(' ') : '';
    compareText.textContent = alternativeText ? (metadata.comparison_model + ': ' + alternativeText) : '';
    drawWaveform();
    if (document.uzscribe.onReviewChanged) document.uzscribe.onReviewChanged();
    recordReview();
  }
  cueText.oninput = function () {
    var blocks = cueBlocks();
    if (!blocks[selectedCue]) return;
    var lines = blocks[selectedCue].split('\n');
    blocks[selectedCue] = lines.slice(0, 2).concat(cueText.value.replace(/\r/g, '').split('\n')).join('\n');
    srtEditor.value = blocks.join('\n\n') + '\n\n';
    recordReview();
  };
  cueText.onchange = renderCues;
  if (waveform) waveform.onclick = function (event) {
    var cues = cueData(); if (!cues.length) return;
    var bounds = waveform.getBoundingClientRect();
    var moment = (event.clientX - bounds.left) / bounds.width * Number(activeRun.info.duration);
    var best = 0, distance = Infinity;
    cues.forEach(function (cue, i) {
      var d = moment < cue.start ? cue.start - moment : moment > cue.end ? moment - cue.end : 0;
      if (d < distance) { distance = d; best = i; }
    });
    selectedCue = best; renderCues();
  };
  function prepareReview(srt, info, audio) {
    try {
      srtEditor.value = fs.readFileSync(srt, 'utf8').replace(/^\uFEFF/, '');
      reviewInfo.textContent = validateSrt(srtEditor.value).count + ' ta subtitr tayyor. Matn va vaqtni tahrirlashingiz mumkin.';
      var metadataPath = srt.replace(/\.srt$/, '.json');
      activeRun.metadata = fs.existsSync(metadataPath) ? JSON.parse(fs.readFileSync(metadataPath, 'utf8')) : null;
    } catch (e) { finish('SRT ko‘rib chiqilmadi: ' + e.message); return; }
    activeRun.srt = srt;
    activeRun.info = info;
    activeRun.review = true; reviewHistory = []; historyAt = -1;
    setPhase('review');
    selectedCue = 0; retryModel.value = model.value; renderCues();
    if (reviewSection.scrollIntoView) reviewSection.scrollIntoView({block:'start', behavior:'smooth'});
    show('Subtitrlarni tekshirib, keyin timeline’ga joylang.');
  }
  function importProblem(message, srt) {
    if (activeRun && activeRun.review) {
      setPhase('review');
      show(message + '\nSRT saqlandi: ' + srt);
    } else finish(message + '\nSRT saqlandi: ' + srt);
  }
  function importCaptions(srt, info, audio) {
    if (document.uzscribe.animateImport && (/^(karaoke|pop|pill|reveal|slide|emphasis)$/.test(animation.value) || (info.host==='AEFT' && document.getElementById('aeLayerMode').value==='words'))) {document.uzscribe.animateImport(srt, info);return;}
    var speakerLabels = activeRun && activeRun.metadata && activeRun.metadata.cues ?
      activeRun.metadata.cues.map(function (cue) { return cue.speaker || ''; }) : [];
    var expression = info.host === 'AEFT'
      ? 'importUzbekSrt(' + JSON.stringify(srt) + ',' + Number(info.start) + ',' + JSON.stringify(info.name) + ',' + JSON.stringify(info.identity || '') + ',' + JSON.stringify(captionMode.value) + ',' + JSON.stringify(speakerLabels) + ',' + (animation.value === 'composer') + ')'
      : 'uzImportCaptions(' + JSON.stringify(srt) + ',' + Number(info.start) + ',' + JSON.stringify(info.name) + ',' + JSON.stringify(info.identity || '') + ')';
    hostCall(info.host === 'AEFT' ? aeScript : hostScript, expression, function (err, raw) {
      removeTemp(audio);
      if (err) { importProblem(err.message, srt); return; }
      if (info.host === 'AEFT') {
        var aeResult = /^(\d+) ta vaqtli matn qatlami yaratildi\.$/.exec(String(raw).trim());
        if (aeResult && Number(aeResult[1]) > 0) {
          if (animation.value === 'composer' && typeof __adobe_cep__.requestOpenExtension === 'function') {
            try { __adobe_cep__.requestOpenExtension('com.misterhorse.animationcomposer.browser', ''); }
            catch (e) { finish(raw + '\nAnimation Composer’ni Window > Extensions menyusidan oching.\nSRT: ' + srt); return; }
            finish(raw + '\nTanlangan qatlamlarga Animation Composer’dan preset tanlang.\nSRT: ' + srt);
          } else finish(raw + '\nSRT: ' + srt);
        }
        else importProblem('After Effects importi tasdiqlanmadi: ' + raw, srt);
        return;
      }
      try {
        var result = JSON.parse(raw);
        if (result.error) importProblem(result.error, srt);
        else finish('Caption track timeline’ga qo‘shildi.\nSRT: ' + srt);
      } catch (e) { importProblem('Import javobi o‘qilmadi: ' + raw, srt); }
    });
  }
  function transcribe(audio, srt, info, reviewFirst, runState) {
    var script = path.join(root, 'subtitles', 'cli.py');
    if (!fs.existsSync(script)) { removeTemp(audio); finish('Python moduli topilmadi.'); return; }
    show('O‘zbekcha nutq va so‘z vaqtlarini aniqlayapman...');
    var args = [script, '--input', audio, '--output', srt, '--model', model.value, '--fps', fps.value,
      '--lines', lines.value, '--words-per-line', words.value, '--max-chars', chars.value,
      '--max-duration', duration.value, '--pause', pause.value, '--start-pad-ms', startPad.value,
      '--end-pad-ms', endPad.value, '--min-cue-duration', minCue.value, '--script', scriptChoice.value];
    if (compareModel.value && compareModel.value !== model.value) args.push('--compare-model', compareModel.value);
    if (exportVtt.checked) args.push('--export-vtt');
    if (exportAss.checked) args.push('--export-ass');
    if (captionMode.value === 'word' && !(adobeHost()==='AEFT' && document.getElementById('aeLayerMode').value==='words')) args.push('--word-mode');
    if (detectSpeakers.checked) {
      args.push('--speakers');
      if (speakerCount.value !== 'auto') args.push('--num-speakers', speakerCount.value);
    }
    if (!splitSentences.checked) args.push('--no-sentence-split');
    if (!savedFields.restoreSentences.checked) args.push('--no-sentence-restore');
    if (savedFields.literary.checked) args.push('--literary');
    if (splitCommas.checked) args.push('--split-commas');
    if (!splitPauses.checked) args.push('--no-pause-split');
    runState.rules.forEach(function (rule) { args.push('--replace', rule); });
    var child = spawn(python.value.trim(), args, {cwd: root});
    runState.child = child;
    var stderr = '', ended = false;
    child.stderr.on('data', function (data) {
      stderr = (stderr + String(data)).slice(-5000);
      if (runState.cancelled) return;
      var matches = stderr.match(/UZPROGRESS (\d+)\/(\d+)/g);
      if (matches && matches.length) {
        var last = /UZPROGRESS (\d+)\/(\d+)/.exec(matches[matches.length - 1]);
        show('Nutq aniqlanmoqda: ' + Math.min(100, Math.round(Number(last[1]) / Number(last[2]) * 100)) + '%');
      } else show('Model ishga tushmoqda va audio tayyorlanmoqda...');
    });
    child.on('error', function (err) {
      if (ended) return;
      ended = true; removeTemp(audio); finish(runState.cancelled ? 'Bekor qilindi.' : 'Python ishga tushmadi: ' + err.message);
    });
    child.on('close', function (code) {
      if (ended) return;
      ended = true;
      runState.child = null;
      if (runState.cancelled) {
        removeTemp(audio);
        removeTemp(srt);
        finish('Bekor qilindi.');
        return;
      }
      if (code !== 0 || !fs.existsSync(srt)) {
        removeTemp(audio); finish('Transkripsiya xatosi: ' + stderr.slice(-2500)); return;
      }
      try {
        var sidecar = srt.replace(/\.srt$/, '.json');
        runState.metadata = fs.existsSync(sidecar) ? JSON.parse(fs.readFileSync(sidecar, 'utf8')) : null;
      } catch (e) { runState.metadata = null; }
      if (reviewFirst || (compareModel.value && compareModel.value !== model.value)) {
        prepareReview(srt, info, audio); return;
      }
      setPhase('importing');
      show('Subtitrlar timeline’ga qo‘yilmoqda...');
      importCaptions(srt, info, audio);
    });
  }
  function normalizeAeAudio(source,destination,state,callback) {
    if(source===destination){callback(null);return;}
    show('AE audiosi WAV formatiga tayyorlanmoqda...');
    var code='import sys,subprocess,signal,imageio_ffmpeg\n'+
      'p=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),"-nostdin","-v","error","-y","-i",sys.argv[1],"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",sys.argv[2]])\n'+
      'def stop(*args):\n p.terminate()\n raise KeyboardInterrupt\n'+
      'signal.signal(signal.SIGTERM,stop)\n'+
      'try: sys.exit(p.wait())\n'+
      'finally:\n if p.poll() is None: p.kill();p.wait()\n';
    var child=spawn(python.value,['-c',code,source,destination]),error='',closed=false;state.child=child;
    if(process.platform==='win32')child.kill=function(){spawn('taskkill',['/PID',String(child.pid),'/T','/F']);};
    child.stderr.on('data',function(data){error=(error+String(data)).slice(-1500);});
    function done(problem){if(closed)return;closed=true;state.child=null;removeTemp(source);if(activeRun!==state)return;
      callback(problem);}
    child.on('error',function(e){done(e);});child.on('close',function(code){done(code===0 && fs.existsSync(destination) && fs.statSync(destination).size>44?null:new Error(state.cancelled?'Bekor qilindi.':'AE audio tayyorlanmadi: '+error));});
  }
  function allowLicense(feature) {
    if(document.uzscribeLicense)return document.uzscribeLicense.allow(feature);
    try {if(JSON.parse(fs.readFileSync(path.join(__dirname,'license-config.json'),'utf8')).mode==='community')return true;}catch(e){}
    show('Obuna moduli yuklanmadi. UzScribe’ni yangilang.');return false;
  }
  function start(reviewFirst) {
    if(!allowLicense("captions"))return;
    var rate = Number(fps.value);
    if (!isFinite(rate) || rate <= 0 || rate > 120) { show('FPS 1–120 oralig‘ida bo‘lsin.'); return; }
    if (validNumber(lines, 1, 3) === null || validNumber(words, 1, 8) === null ||
        validNumber(chars, 8, 80) === null || validNumber(duration, 1, 10) === null ||
        validNumber(pause, 0.1, 2) === null || validNumber(startPad, 0, 500) === null ||
        validNumber(endPad, 0, 500) === null || validNumber(minCue, 0, 3) === null ||
        Number(lines.value) % 1 || Number(words.value) % 1 || Number(chars.value) % 1 ||
        Number(startPad.value) % 1 || Number(endPad.value) % 1) {
      show('Qator, so‘z, belgi va vaqt sozlamalarini tekshiring.'); return;
    }
    if (!python.value.trim()) { show('Python yo‘lini kiriting.'); return; }
    var rules;
    try { rules = glossaryRules(); }
    catch (e) { show(e.message); return; }
    var requestedRange = range.value;
    activeRun = {cancelled:false, child:null, audio:null, srt:null, info:null, rules:rules};
    var runState = activeRun;
    setPhase('working');
    show('Faol timeline tekshirilmoqda...');
    getInfo(function (err, info) {
      if (runState.cancelled) { finish('Bekor qilindi.'); return; }
      if (err) { finish(err.message); return; }
      var unique = Date.now() + '-' + Math.random().toString(36).slice(2, 8);
      var audio = path.join(os.tmpdir(), 'uzbek-subtitles-' + unique + '.wav');
      runState.audio = audio;
      var exportDir = path.join(root, 'exports');
      try { ensureDirectory(exportDir); }
      catch (e) { finish('SRT papkasi yaratilmadi: ' + e.message); return; }
      var safeName = info.name.replace(/[^a-zA-Z0-9_-]+/g, '_').slice(0, 55) || 'timeline';
      var srt = path.join(exportDir, safeName + '-' + unique + '.uz.srt');
      var preset = info.host === 'PPRO' ? presetPath() : '';
      if (info.host === 'PPRO' && !preset) {
        advanced.open = true;
        finish('Premiere WAV preset’i topilmadi. Qo‘shimcha sozlamalarda .epr fayl yo‘lini kiriting.');
        return;
      }
      show('Timeline ovozi eksport qilinmoqda...');
      var exportExpression=info.host==='AEFT'
        ? 'uzAeExportAudio('+[requestedRange,audio,info.name,info.identity||'',info.layer_token||'',Number(info.start),Number(info.duration)].map(JSON.stringify).join(',')+')'
        : 'uzExportAudio(' + JSON.stringify(requestedRange) + ',' + JSON.stringify(audio) + ',' + JSON.stringify(preset) + ',' + JSON.stringify(audioTrack.value) + ')';
      jsonCall(exportExpression,
        function (exportError, result) {
          if (runState.cancelled) { removeTemp(audio); finish('Bekor qilindi.'); return; }
          if (exportError) { removeTemp(audio); finish(exportError.message); return; }
          if (result.name !== info.name || result.identity !== info.identity || (info.host==='AEFT' && info.layer_token && result.layer_token!==info.layer_token)) {
            removeTemp(audio); finish('Faol timeline eksport vaqtida o‘zgargan. Qayta urinib ko‘ring.'); return;
          }
          if(info.host==='AEFT') {
            normalizeAeAudio(result.path,audio,runState,function(error){
              if(error){finish(error.message);return;}
              if(runState.cancelled){removeTemp(audio);finish('Bekor qilindi.');return;}
              transcribe(audio,srt,info,reviewFirst,runState);
            });
          } else transcribe(result.path, srt, info, reviewFirst, runState);
        },info.host==='AEFT'?aeScript:hostScript);
    }, requestedRange);
  }
  run.onclick = function () { start(true); };
  batchRun.onclick = function () {
    if(!allowLicense("captions"))return;
    var input = batchDir.value.trim();
    if (!input || !fs.existsSync(input) || !fs.statSync(input).isDirectory()) {
      show('Media papkasini to‘g‘ri kiriting.'); return;
    }
    var output = path.join(root, 'exports', 'batch');
    try { ensureDirectory(output); }
    catch (e) { show('Natija papkasi yaratilmadi: ' + e.message); return; }
    var args = [path.join(root, 'subtitles', 'batch.py'), '--input-dir', input,
      '--output-dir', output, '--model', model.value, '--script', scriptChoice.value,
      '--fps', fps.value];
    if (exportVtt.checked) args.push('--export-vtt');
    if (exportAss.checked) args.push('--export-ass');
    if (captionMode.value === 'word' && !(adobeHost()==='AEFT' && document.getElementById('aeLayerMode').value==='words')) args.push('--word-mode');
    if (savedFields.literary.checked) args.push('--literary');
    if (detectSpeakers.checked) {
      args.push('--speakers');
      if (speakerCount.value !== 'auto') args.push('--num-speakers', speakerCount.value);
    }
    activeRun = {cancelled:false, child:null, audio:null};
    var state = activeRun; setPhase('working');
    show('Papkadagi fayllar tanilmoqda...');
    var child = spawn(python.value.trim(), args, {cwd:root}); state.child = child;
    var outputText = '';
    child.stdout.on('data', function (data) {
      outputText = (outputText + String(data)).slice(-1500);
      var m = /UZBATCH (\d+)\/(\d+) ([^\n]+)/g, last, current;
      while ((current = m.exec(outputText))) last = current;
      if (last && !state.cancelled) show('Fayl ' + last[1] + '/' + last[2] + ': ' + last[3]);
    });
    child.stderr.on('data', function (data) { outputText = (outputText + String(data)).slice(-1500); });
    child.on('error', function (err) { if (activeRun === state) finish('Batch xatosi: ' + err.message); });
    child.on('close', function (code) {
      if (activeRun !== state) return;
      finish(state.cancelled ? 'Bekor qilindi.' : code ? 'Batch xatosi: ' + outputText.slice(-900) :
        'Papkadagi subtitrlar tayyor: ' + output);
    });
  };
  cancel.onclick = function () {
    if (!activeRun) return;
    activeRun.cancelled = true;
    cancel.disabled = true;
    if (activeRun.child) {
      activeRun.child.kill();
      show('Transkripsiya bekor qilinmoqda...');
    } else show('Audio eksporti tugagach bekor qilinadi...');
  };
  discardReview.onclick = function () {
    var savedPath = activeRun && activeRun.srt;
    if (!savedPath) return;
    try {
      var edited = validateSrt(srtEditor.value);
      fs.writeFileSync(savedPath, '\uFEFF' + edited.text, 'utf8');
      writeEditedFormats(savedPath);
      if (activeRun.metadata) fs.writeFileSync(savedPath.replace(/\.srt$/, '.json'),
        JSON.stringify(activeRun.metadata, null, 2), 'utf8');
    } catch (e) { show('SRT saqlanmadi: ' + e.message); return; }
    finish('SRT saqlandi: ' + savedPath);
  };
  applyReview.onclick = function () {
    if (!activeRun || !activeRun.srt) return;
    var edited;
    try { edited = validateSrt(srtEditor.value); }
    catch (e) { show(e.message); return; }
    try {
      fs.writeFileSync(activeRun.srt, '\uFEFF' + edited.text, 'utf8');
      writeEditedFormats(activeRun.srt);
      if (activeRun.metadata) fs.writeFileSync(activeRun.srt.replace(/\.srt$/, '.json'),
        JSON.stringify(activeRun.metadata, null, 2), 'utf8');
    }
    catch (e) { show('SRT saqlanmadi: ' + e.message); return; }
    var srt = activeRun.srt, info = activeRun.info;
    setPhase('importing');
    show(edited.count + ' ta subtitr timeline’ga qo‘yilmoqda...');
    importCaptions(srt, info, null);
  };
  srtEditor.addEventListener('input', function () { if (activeRun && activeRun.review) renderCues(); });
  assignSpeaker.onclick = function () {
    if (!activeRun || !activeRun.review) return;
    if (!activeRun.metadata) activeRun.metadata = {words:[], cues:[]};
    if (!activeRun.metadata.cues) activeRun.metadata.cues = [];
    while (activeRun.metadata.cues.length <= selectedCue) activeRun.metadata.cues.push({});
    activeRun.metadata.cues[selectedCue].speaker = speakerChoice.value || null;
    renderCues(); show('So‘zlovchi belgisi yangilandi.');
  };
  retryCue.onclick = function () {
    if (!activeRun || !activeRun.review) return;
    if (!activeRun.audio) {show('Qayta tanish audiosi saqlanmagan. Subtitrni yangidan yarating.');return;}
    var cues;
    try { validateSrt(srtEditor.value); cues = cueData(); }
    catch (e) { show(e.message); return; }
    var cue = cues[selectedCue];
    if (!cue) { show('Qayta tanish uchun subtitr tanlang.'); return; }
    var start = Math.max(0, cue.start - 0.25), end = Math.min(Number(activeRun.info.duration), cue.end + 0.25);
    var file = path.join(os.tmpdir(), 'uzbek-retry-' + Date.now() + '.srt');
    var args = [path.join(root, 'subtitles', 'cli.py'), '--input', activeRun.audio,
      '--output', file, '--model', retryModel.value || model.value,
      '--fps', fps.value, '--start-seconds', String(start), '--end-seconds', String(end),
      '--script', scriptChoice.value, '--min-cue-duration', '0'];
    retryCue.disabled = true; show('Tanlangan subtitr qayta aniqlanmoqda...');
    var child = spawn(python.value.trim(), args, {cwd:root}), errorText = '';
    activeRun.child = child;
    child.stderr.on('data', function (data) { errorText = (errorText + String(data)).slice(-1500); });
    child.on('error', function (err) { retryCue.disabled = false; show('Qayta tanish xatosi: ' + err.message); });
    child.on('close', function (code) {
      retryCue.disabled = false;
      if (!activeRun || activeRun.cancelled) return;
      activeRun.child = null;
      try {
        if (code || !fs.existsSync(file)) throw new Error(errorText || 'Nutq topilmadi');
        var changed = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '').trim();
        var retryMetadata = file.replace(/\.srt$/, '.json');
        var newWords = fs.existsSync(retryMetadata) ?
          (JSON.parse(fs.readFileSync(retryMetadata, 'utf8')).words || []).filter(function (w) {
            return w.start < cue.end && w.end > cue.start;
          }) : [];
        var newText = newWords.length ? newWords.map(function (w) { return w.text.trim(); }).join(' ')
          .replace(/\s+([,.:;!?])/g, '$1').replace(/\s+([-'])/g, '$1') :
          changed.split(/\n\s*\n/).map(function (block) {
            return block.split('\n').slice(2).join(' ');
          }).join(' ').trim();
        if (!newText) throw new Error('Nutq topilmadi');
        var blocks = cueBlocks(), lines = blocks[selectedCue].split('\n');
        blocks[selectedCue] = lines.slice(0, 2).join('\n') + '\n' + newText;
        srtEditor.value = blocks.join('\n\n') + '\n\n';
        if (activeRun.metadata && fs.existsSync(retryMetadata)) {
          activeRun.metadata.words = activeRun.metadata.words.filter(function (w) {
            return !(w.start < cue.end && w.end > cue.start);
          }).concat(newWords);
        }
        renderCues(); show('Tanlangan subtitr qayta tanildi. Importdan oldin matnni tekshiring.');
      } catch (e) { show('Qayta tanish xatosi: ' + e.message); }
      finally { removeTemp(file); removeTemp(file.replace(/\.srt$/, '.json')); }
    });
  };
  refresh.onclick = refreshTimeline;
  range.onchange = refreshTimeline;
  historyControls();
  refreshTimeline();
}());
