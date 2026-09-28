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
  var preview = document.getElementById('preview');
  var boundaryPreview = document.getElementById('boundaryPreview');
  var run = document.getElementById('run');
  var refresh = document.getElementById('refresh');
  var timeline = document.getElementById('timeline');
  var status = document.getElementById('status');
  var localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  python.value = fs.existsSync(localPython) ? localPython : (process.platform === 'win32' ? 'python' : 'python3');
  if (fs.existsSync(path.join(root, 'models', 'navai-medium', 'model.bin'))) {
    var option = document.createElement('option');
    option.value = 'navai-medium';
    option.textContent = 'NavAI Uzbek medium — o‘zbekchaga mos';
    model.insertBefore(option, model.firstChild);
    model.value = 'navai-medium';
  }

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
  }
  style.onchange = applyStyle;
  [lines, words, chars, duration, pause].forEach(function (field) {
    field.oninput = function () { style.value = 'custom'; updatePreview(); };
  });
  splitPauses.onchange = function () { pause.disabled = !splitPauses.checked; };
  splitSentences.onchange = updatePreview;
  splitCommas.onchange = updatePreview;
  updatePreview();
  function validNumber(field, minimum, maximum) {
    var value = Number(field.value);
    return isFinite(value) && value >= minimum && value <= maximum ? value : null;
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
  function getInfo(callback) {
    jsonCall('uzTimelineInfo(' + JSON.stringify(range.value) + ')', callback);
  }
  function refreshTimeline() {
    getInfo(function (err, info) {
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
  function finish(message) { run.disabled = false; refresh.disabled = false; show(message); }
  function removeTemp(filename) { try { fs.unlinkSync(filename); } catch (e) {} }
  function importCaptions(srt, info, audio) {
    var expression = info.host === 'AEFT'
      ? 'importUzbekSrt(' + JSON.stringify(srt) + ',' + Number(info.start) + ')'
      : 'uzImportCaptions(' + JSON.stringify(srt) + ',' + Number(info.start) + ')';
    hostCall(info.host === 'AEFT' ? aeScript : hostScript, expression, function (err, raw) {
      removeTemp(audio);
      if (err) { finish(err.message + '\nSRT saqlandi: ' + srt); return; }
      if (info.host === 'AEFT') { finish(raw + '\nSRT: ' + srt); return; }
      try {
        var result = JSON.parse(raw);
        finish(result.error ? result.error + '\nSRT saqlandi: ' + srt : 'Caption track timeline’ga qo‘shildi.\nSRT: ' + srt);
      } catch (e) { finish('Import javobi o‘qilmadi: ' + raw + '\nSRT: ' + srt); }
    });
  }
  function transcribe(audio, srt, info) {
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
    var child = spawn(python.value.trim(), args, {cwd: root});
    var stderr = '', ended = false;
    child.stderr.on('data', function (data) { stderr += String(data); show(stderr.slice(-1500)); });
    child.on('error', function (err) {
      if (ended) return;
      ended = true; removeTemp(audio); finish('Python ishga tushmadi: ' + err.message);
    });
    child.on('close', function (code) {
      if (ended) return;
      ended = true;
      if (code !== 0 || !fs.existsSync(srt)) {
        removeTemp(audio); finish('Transkripsiya xatosi: ' + stderr.slice(-2500)); return;
      }
      show('Subtitrlar timeline’ga qo‘yilmoqda...');
      importCaptions(srt, info, audio);
    });
  }
  run.onclick = function () {
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
    run.disabled = true; refresh.disabled = true;
    show('Faol timeline tekshirilmoqda...');
    getInfo(function (err, info) {
      if (err) { finish(err.message); return; }
      var unique = Date.now() + '-' + Math.random().toString(36).slice(2, 8);
      var audio = path.join(os.tmpdir(), 'uzbek-subtitles-' + unique + '.wav');
      var exportDir = path.join(root, 'exports');
      try { fs.mkdirSync(exportDir, {recursive: true}); }
      catch (e) { finish('SRT papkasi yaratilmadi: ' + e.message); return; }
      var safeName = info.name.replace(/[^a-zA-Z0-9_-]+/g, '_').slice(0, 55) || 'timeline';
      var srt = path.join(exportDir, safeName + '-' + unique + '.uz.srt');
      var preset = info.host === 'PPRO' ? presetPath() : '';
      if (info.host === 'PPRO' && !preset) { finish('Premiere WAV eksport preset’i topilmadi.'); return; }
      show('Timeline ovozi eksport qilinmoqda...');
      jsonCall('uzExportAudio(' + JSON.stringify(range.value) + ',' + JSON.stringify(audio) + ',' + JSON.stringify(preset) + ')',
        function (exportError, result) {
          if (exportError) { removeTemp(audio); finish(exportError.message); return; }
          transcribe(result.path, srt, info);
        });
    });
  };
  refresh.onclick = refreshTimeline;
  range.onchange = refreshTimeline;
  refreshTimeline();
}());
