/* global __adobe_cep__ */
(function () {
  'use strict';
  var fs = require('fs');
  var os = require('os');
  var path = require('path');
  var spawn = require('child_process').spawn;
  var root = path.resolve(fs.realpathSync(__dirname), '..', '..');
  var hostScript = path.join(__dirname, 'host', 'editor.jsx');
  var aeScript = path.join(__dirname, 'host', 'after_effects.jsx');
  var python = document.getElementById('python');
  var model = document.getElementById('model');
  var modelHint = document.getElementById('modelHint');
  var fps = document.getElementById('fps');
  var range = document.getElementById('range');
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
  var reviewRun = document.getElementById('reviewRun');
  var cancel = document.getElementById('cancel');
  var reviewSection = document.getElementById('reviewSection');
  var reviewInfo = document.getElementById('reviewInfo');
  var srtEditor = document.getElementById('srtEditor');
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
  var localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  python.value = fs.existsSync(localPython) ? localPython : (process.platform === 'win32' ? 'python' : 'python3');
  if (fs.existsSync(path.join(root, 'models', 'navai-medium', 'model.bin'))) {
    var option = document.createElement('option');
    option.value = 'navai-medium';
    option.textContent = 'NavAI Uzbek medium — o‘zbekchaga mos';
    model.insertBefore(option, model.firstChild);
    model.value = 'navai-medium';
  }
  if (fs.existsSync(path.join(root, 'models', 'gigaam-uzbek', 'checkpoints', 'large_full_600m', 'best.pt')) &&
      fs.existsSync(path.join(root, 'models', 'gigaam-base-large', 'config.json'))) {
    var gigaamOption = document.createElement('option');
    gigaamOption.value = 'gigaam-uzbek';
    gigaamOption.textContent = 'GigaAM Uzbek 600M — suhbat nutqi';
    model.insertBefore(gigaamOption, model.firstChild);
    model.value = 'gigaam-uzbek';
  }
  var savedFields = {
    range: range, model: model, style: style, lines: lines, words: words,
    chars: chars, duration: duration, pause: pause, splitSentences: splitSentences,
    splitCommas: splitCommas, splitPauses: splitPauses, startPad: startPad,
    endPad: endPad, minCue: minCue, glossary: glossary, python: python
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
      ? 'Tabiiy nutq uchun. So‘z va tinish belgilari vaqtini aniqlaydi.'
      : model.value === 'navai-medium'
        ? 'O‘zbekchaga mos NavAI modeli. Natijalarni GigaAM bilan solishtirish mumkin.'
        : 'Umumiy Whisper modeli. Birinchi ishlatishda model yuklanishi mumkin.';
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
  function jsonCall(expression, callback) {
    hostCall(hostScript, expression, function (err, raw) {
      if (err) { callback(err); return; }
      try {
        var result = JSON.parse(raw);
        callback(result.error ? new Error(result.error) : null, result);
      } catch (e) { callback(new Error('Adobe javobi o‘qilmadi: ' + raw)); }
    });
  }
  function getInfo(callback, selectedRange) {
    jsonCall('uzTimelineInfo(' + JSON.stringify(selectedRange || range.value) + ')', callback);
  }
  function refreshTimeline() {
    getInfo(function (err, info) {
      if (activeRun) return;
      if (err) { timeline.textContent = err.message; return; }
      timeline.textContent = info.name + ' · ' + info.duration.toFixed(2) + ' s · ' +
        (info.marked ? ('boshlanish ' + info.start.toFixed(2) + ' s') : 'to‘liq') +
        ' · ' + info.fps.toFixed(3) + ' fps';
      fps.value = info.fps.toFixed(3);
    });
  }
  function presetPath() {
    if (process.platform !== 'darwin') return '';
    var applications = '/Applications';
    var versions = ['2026', '2025', '2024'];
    for (var i = 0; i < versions.length; i++) {
      var v = versions[i];
      var candidate = path.join(applications, 'Adobe Premiere Pro ' + v,
        'Adobe Premiere Pro ' + v + '.app', 'Contents', 'Settings', 'EncoderPresets',
        'WAV_Mono_16bit_16kHz.epr');
      if (fs.existsSync(candidate)) return candidate;
    }
    return '';
  }
  function setPhase(phase) {
    mainActions.hidden = phase !== 'idle';
    workActions.hidden = phase !== 'working';
    reviewActions.hidden = phase !== 'review';
    reviewSection.hidden = phase !== 'review';
    refresh.disabled = phase !== 'idle';
    Object.keys(savedFields).forEach(function (key) {
      savedFields[key].disabled = phase !== 'idle' || (key === 'pause' && !splitPauses.checked);
    });
    cancel.disabled = false;
  }
  function finish(message) { activeRun = null; setPhase('idle'); show(message); }
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
  function prepareReview(srt, info, audio) {
    removeTemp(audio);
    if (activeRun) activeRun.audio = null;
    try {
      srtEditor.value = fs.readFileSync(srt, 'utf8').replace(/^\uFEFF/, '');
      reviewInfo.textContent = validateSrt(srtEditor.value).count + ' ta subtitr tayyor. Matn va vaqtni tahrirlashingiz mumkin.';
    } catch (e) { finish('SRT ko‘rib chiqilmadi: ' + e.message); return; }
    activeRun.srt = srt;
    activeRun.info = info;
    activeRun.review = true;
    setPhase('review');
    show('Subtitrlarni tekshirib, keyin timeline’ga joylang.');
  }
  function importProblem(message, srt) {
    if (activeRun && activeRun.review) {
      setPhase('review');
      show(message + '\nSRT saqlandi: ' + srt);
    } else finish(message + '\nSRT saqlandi: ' + srt);
  }
  function importCaptions(srt, info, audio) {
    var expression = info.host === 'AEFT'
      ? 'importUzbekSrt(' + JSON.stringify(srt) + ',' + Number(info.start) + ',' + JSON.stringify(info.name) + ',' + JSON.stringify(info.identity || '') + ')'
      : 'uzImportCaptions(' + JSON.stringify(srt) + ',' + Number(info.start) + ',' + JSON.stringify(info.name) + ',' + JSON.stringify(info.identity || '') + ')';
    hostCall(info.host === 'AEFT' ? aeScript : hostScript, expression, function (err, raw) {
      removeTemp(audio);
      if (err) { importProblem(err.message, srt); return; }
      if (info.host === 'AEFT') {
        var aeResult = /^(\d+) ta vaqtli matn qatlami yaratildi\.$/.exec(String(raw).trim());
        if (aeResult && Number(aeResult[1]) > 0) finish(raw + '\nSRT: ' + srt);
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
      '--end-pad-ms', endPad.value, '--min-cue-duration', minCue.value];
    if (!splitSentences.checked) args.push('--no-sentence-split');
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
      if (reviewFirst) { prepareReview(srt, info, audio); return; }
      setPhase('importing');
      show('Subtitrlar timeline’ga qo‘yilmoqda...');
      importCaptions(srt, info, audio);
    });
  }
  function start(reviewFirst) {
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
      try { fs.mkdirSync(exportDir, {recursive: true}); }
      catch (e) { finish('SRT papkasi yaratilmadi: ' + e.message); return; }
      var safeName = info.name.replace(/[^a-zA-Z0-9_-]+/g, '_').slice(0, 55) || 'timeline';
      var srt = path.join(exportDir, safeName + '-' + unique + '.uz.srt');
      var preset = info.host === 'PPRO' ? presetPath() : '';
      if (info.host === 'PPRO' && !preset) { finish('Premiere WAV eksport preset’i topilmadi.'); return; }
      show('Timeline ovozi eksport qilinmoqda...');
      jsonCall('uzExportAudio(' + JSON.stringify(requestedRange) + ',' + JSON.stringify(audio) + ',' + JSON.stringify(preset) + ')',
        function (exportError, result) {
          if (runState.cancelled) { removeTemp(audio); finish('Bekor qilindi.'); return; }
          if (exportError) { removeTemp(audio); finish(exportError.message); return; }
          if (result.name !== info.name || result.identity !== info.identity) {
            removeTemp(audio); finish('Faol timeline eksport vaqtida o‘zgargan. Qayta urinib ko‘ring.'); return;
          }
          transcribe(result.path, srt, info, reviewFirst, runState);
        });
    }, requestedRange);
  }
  run.onclick = function () { start(false); };
  reviewRun.onclick = function () { start(true); };
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
    finish('SRT saqlandi: ' + savedPath);
  };
  applyReview.onclick = function () {
    if (!activeRun || !activeRun.srt) return;
    var edited;
    try { edited = validateSrt(srtEditor.value); }
    catch (e) { show(e.message); return; }
    try { fs.writeFileSync(activeRun.srt, '\uFEFF' + edited.text, 'utf8'); }
    catch (e) { show('SRT saqlanmadi: ' + e.message); return; }
    var srt = activeRun.srt, info = activeRun.info;
    setPhase('importing');
    show(edited.count + ' ta subtitr timeline’ga qo‘yilmoqda...');
    importCaptions(srt, info, null);
  };
  refresh.onclick = refreshTimeline;
  range.onchange = refreshTimeline;
  refreshTimeline();
}());
