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
  var run = document.getElementById('run');
  var refresh = document.getElementById('refresh');
  var timeline = document.getElementById('timeline');
  var status = document.getElementById('status');
  var localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  python.value = fs.existsSync(localPython) ? localPython : (process.platform === 'win32' ? 'python' : 'python3');

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
    var args = [script, '--input', audio, '--output', srt, '--model', model.value, '--fps', fps.value];
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
