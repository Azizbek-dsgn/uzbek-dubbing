/* global __adobe_cep__ */
(function () {
  'use strict';
  var fs = require('fs');
  var path = require('path');
  var spawn = require('child_process').spawn;
  var media = document.getElementById('media');
  var python = document.getElementById('python');
  var model = document.getElementById('model');
  var fps = document.getElementById('fps');
  var run = document.getElementById('run');
  var status = document.getElementById('status');

  function show(message) { status.textContent = message; }
  function evalHost(script, callback) { __adobe_cep__.evalScript(script, callback); }
  function literal(value) { return JSON.stringify(value); }
  function importResult(srt) {
    var host = __adobe_cep__.getHostEnvironment();
    var appId = JSON.parse(host).appId;
    if (appId === 'PPRO') {
      evalHost('(function(){try{return app.project.importFiles([' + literal(srt) + '],true,app.project.rootItem,false)?"SRT loyiha ichiga import qilindi. Uni timeline’ga torting.":"Import muvaffaqiyatsiz"}catch(e){return "Import xatosi: "+e}})()', show);
    } else if (appId === 'AEFT') {
      var jsx = path.join(__dirname, 'host', 'after_effects.jsx');
      evalHost('$.evalFile(new File(' + literal(jsx) + ')); importUzbekSrt(' + literal(srt) + ')', show);
    } else {
      show('SRT tayyor: ' + srt);
    }
  }

  run.onclick = function () {
    var selected = media.files && media.files[0];
    if (!selected || !selected.path) { show('Lokal media faylni tanlang.'); return; }
    var rate = Number(fps.value);
    if (!isFinite(rate) || rate <= 0 || rate > 120) { show('FPS 1–120 oralig‘ida bo‘lsin.'); return; }
    var extensionRoot = fs.realpathSync(__dirname);
    var repo = path.resolve(extensionRoot, '..', '..');
    var script = path.join(repo, 'subtitles', 'cli.py');
    if (!fs.existsSync(script)) { show('Python moduli topilmadi: ' + script); return; }
    var input = selected.path;
    var output = path.join(path.dirname(input), path.basename(input, path.extname(input)) + '.uz.srt');
    var args = [script, '--input', input, '--output', output, '--model', model.value, '--fps', String(rate)];
    var executable = python.value.trim();
    if (!executable) { show('Python yo‘lini kiriting.'); return; }
    run.disabled = true;
    show('Transkripsiya boshlandi. Birinchi marta model yuklanishi mumkin...');
    var child = spawn(executable, args, {cwd: repo});
    var stderr = '';
    child.stderr.on('data', function (data) { stderr += String(data); show(stderr.slice(-3000)); });
    child.on('error', function (err) { run.disabled = false; show('Python ishga tushmadi: ' + err.message); });
    child.on('close', function (code) {
      run.disabled = false;
      if (code !== 0) { show('Xato (' + code + '): ' + stderr.slice(-3000)); return; }
      show('SRT tayyor: ' + output);
      importResult(output);
    });
  };
}());
