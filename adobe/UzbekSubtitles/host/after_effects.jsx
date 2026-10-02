function importUzbekSrt(srtPath, offsetSeconds, expectedName, expectedIdentity, captionMode, speakerLabels, selectForComposer) {
    if (!app.project || !app.project.activeItem || !(app.project.activeItem instanceof CompItem)) {
        return "Avval After Effects kompozitsiyasini oching. SRT: " + srtPath;
    }
    var file = new File(srtPath);
    if (!file.exists) { return "SRT topilmadi: " + srtPath; }
    file.encoding = "UTF-8";
    if (!file.open("r")) { return "SRT o'qilmadi: " + srtPath; }
    var contents = file.read().replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n");
    file.close();
    var comp = app.project.activeItem;
    if (comp.name !== expectedName) { return "Faol kompozitsiya o'zgargan. Avvalgi kompozitsiyani oching."; }
    if (expectedIdentity && String(comp.id) !== expectedIdentity) {
        return "Faol kompozitsiya o'zgargan. Avvalgi kompozitsiyani oching.";
    }
    var blocks = contents.split(/\n\s*\n/);
    var count = 0;
    function seconds(stamp) {
        var m = /^(\d+):(\d+):(\d+),(\d+)$/.exec(stamp);
        if (!m) { return null; }
        return Number(m[1])*3600 + Number(m[2])*60 + Number(m[3]) + Number(m[4])/1000;
    }
    app.beginUndoGroup("O'zbekcha subtitr importi");
    try {
        var composerLayers = [];
        for (var i = 0; i < blocks.length; i++) {
            var lines = blocks[i].split("\n");
            if (lines.length < 3) { continue; }
            var range = /^(\S+) --> (\S+)$/.exec(lines[1]);
            if (!range) { continue; }
            var start = seconds(range[1]);
            var end = seconds(range[2]);
            if (start === null || end === null || end <= start || start >= comp.duration) { continue; }
            start += Number(offsetSeconds) || 0;
            end += Number(offsetSeconds) || 0;
            if (start >= comp.duration) { continue; }
            var layer = comp.layers.addText(lines.slice(2).join("\r"));
            var text = layer.property("Source Text").value;
            text.fontSize = Math.max(28, Math.round(comp.width / 32));
            var speaker = speakerLabels && speakerLabels[i];
            var palette = [[1, 1, 1], [1, 0.77, 0.37], [0.58, 0.83, 1], [0.73, 1, 0.7]];
            var colorIndex = speaker ? Number(String(speaker).replace(/\D/g, "")) + 1 : 0;
            text.fillColor = palette[isFinite(colorIndex) ? colorIndex % palette.length : 0];
            text.applyFill = true;
            text.applyStroke = false;
            text.justification = ParagraphJustification.CENTER_JUSTIFY;
            layer.property("Source Text").setValue(text);
            layer.property("Position").setValue([comp.width / 2, comp.height * 0.88]);
            layer.startTime = 0;
            layer.inPoint = start;
            layer.outPoint = Math.min(end, comp.duration);
            if (captionMode === "word" && !selectForComposer && end - start > 0.08) {
                var popEnd = Math.min(end - 0.01, start + 0.12);
                var scale = layer.property("Transform").property("Scale");
                var opacity = layer.property("Transform").property("Opacity");
                scale.setValueAtTime(start, [82, 82]);
                scale.setValueAtTime(popEnd, [100, 100]);
                opacity.setValueAtTime(start, 35);
                opacity.setValueAtTime(Math.min(end - 0.005, start + 0.08), 100);
            }
            if (selectForComposer) composerLayers.push(layer);
            count++;
        }
        if (selectForComposer) {
            var previouslySelected = comp.selectedLayers;
            for (var p = 0; p < previouslySelected.length; p++) previouslySelected[p].selected = false;
            for (var q = 0; q < composerLayers.length; q++) composerLayers[q].selected = true;
        }
    } finally { app.endUndoGroup(); }
    return count + " ta vaqtli matn qatlami yaratildi.";
}

// Strict JSON reader for older ExtendScript hosts, without evaluating file contents.
function uzAnimationRead(filePath) {
    var file = new File(filePath); file.encoding = "UTF-8";
    if (!file.exists || !file.open("r")) throw new Error("Animatsiya rejasi o‘qilmadi.");
    var text; try { text = file.read().replace(/^\uFEFF/, ""); } finally { file.close(); }
    if (typeof JSON !== "undefined" && JSON.parse) return JSON.parse(text);
    var at = 0;
    function space() { while (/\s/.test(text.charAt(at)) && at < text.length) at++; }
    function string() {
        var result = "", ch; at++;
        while (at < text.length) { ch = text.charAt(at++); if (ch === '"') return result;
            if (ch === "\\") { ch = text.charAt(at++); if (ch === "u") { var hex = text.substr(at,4); if (!/^[0-9a-fA-F]{4}$/.test(hex)) throw new Error("JSON unicode noto‘g‘ri."); result += String.fromCharCode(parseInt(hex,16)); at += 4; }
                else { var escapes = {'"':'"','\\':'\\','/':'/','b':'\b','f':'\f','n':'\n','r':'\r','t':'\t'}; if (!escapes.hasOwnProperty(ch)) throw new Error("JSON escape noto‘g‘ri."); result += escapes[ch]; } }
            else { if (ch.charCodeAt(0) < 32) throw new Error("JSON matni noto‘g‘ri."); result += ch; } }
        throw new Error("JSON matni tugamagan.");
    }
    function value(depth) {
        if (depth > 32) throw new Error("JSON juda chuqur."); space(); var ch = text.charAt(at), result, key;
        if (ch === '"') return string();
        if (ch === '[' || ch === '{') { var array = ch === '[', close = array ? ']' : '}'; result = array ? [] : {}; at++; space(); if (text.charAt(at) === close) {at++; return result;}
            while (true) { space(); if (array) result.push(value(depth+1)); else { if (text.charAt(at) !== '"') throw new Error("JSON kaliti noto‘g‘ri."); key = string(); if (key === '__proto__' || key === 'constructor') throw new Error("JSON kaliti rad etildi."); space(); if (text.charAt(at++) !== ':') throw new Error("JSON ikki nuqtasi yo‘q."); result[key] = value(depth+1); }
                space(); ch = text.charAt(at++); if (ch === close) return result; if (ch !== ',') throw new Error("JSON verguli yo‘q."); }
        }
        var rest = text.slice(at), match = /^(true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(rest);
        if (!match) throw new Error("JSON qiymati noto‘g‘ri."); at += match[0].length; return match[0] === 'true' ? true : match[0] === 'false' ? false : match[0] === 'null' ? null : Number(match[0]);
    }
    var result = value(0); space(); if (at !== text.length) throw new Error("JSON ortiqcha matn."); return result;
}
function uzAnimationComp(name, identity) {
    var comp = app.project && app.project.activeItem;
    if (!comp || !(comp instanceof CompItem) || comp.name !== name || (identity && String(comp.id) !== identity)) throw new Error("Faol kompozitsiya o‘zgargan. Avvalgi kompozitsiyani oching.");
    return comp;
}
function uzAnimationRGB(hex) {return [parseInt(hex.substr(1,2),16)/255,parseInt(hex.substr(3,2),16)/255,parseInt(hex.substr(5,2),16)/255];}
function uzAnimationHold(prop) { for (var i = 1; i <= prop.numKeys; i++) prop.setInterpolationTypeAtKey(i, KeyframeInterpolationType.HOLD, KeyframeInterpolationType.HOLD); }
function uzAnimationLinear(prop) { for (var i = 1; i <= prop.numKeys; i++) prop.setInterpolationTypeAtKey(i, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR); }
function uzAnimationLayers(comp, cue, theme, offset, expose) {
    var start = cue.start + offset, end = Math.min(cue.end + offset, comp.duration), count = 0;
    if (start >= comp.duration || end <= start) return 0;
    var preset = theme.preset, color = uzAnimationRGB(theme.color), active = uzAnimationRGB(theme.active);
    var speed = Math.min(theme.speed, (end - start)/2), pill = null;
    if (preset === 'pill') {
        pill = comp.layers.addShape(); pill.name = 'UzScribe · Highlight'; pill.inPoint = start; pill.outPoint = end;
        var group = pill.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group').property('ADBE Vectors Group');
        var rect = group.addProperty('ADBE Vector Shape - Rect'); rect.property('ADBE Vector Rect Roundness').setValue(10);
        var fill = group.addProperty('ADBE Vector Graphic - Fill'); fill.property('ADBE Vector Fill Color').setValue(active); fill.property('ADBE Vector Fill Opacity').setValue(70);
        var pos = pill.property('ADBE Transform Group').property('ADBE Position');
        for (var h = 0; h < cue.runs.length; h++) {
            var r = cue.runs[h], time = Math.max(start,r.start+offset), target = [r.x+r.width/2,r.y+r.height/2];
            if (h > 0) { var prev = cue.runs[h-1], before = Math.max(start,time-Math.min(speed,Math.max(.001,r.start-prev.start)));
                pos.setValueAtTime(before,[prev.x+prev.width/2,prev.y+prev.height/2]); rect.property('ADBE Vector Rect Size').setValueAtTime(before,[prev.width+16,prev.height+3]); }
            pos.setValueAtTime(time,target); rect.property('ADBE Vector Rect Size').setValueAtTime(time,[r.width+16,r.height+3]);
        }
        uzAnimationLinear(pos); uzAnimationLinear(rect.property('ADBE Vector Rect Size'));
    }
    for (var i = 0; i < cue.runs.length; i++) {
        var run = cue.runs[i], layer = comp.layers.addText(run.text); layer.name = 'UzScribe · '+run.text;
        var source = layer.property('ADBE Text Properties').property('ADBE Text Document'), doc = source.value;
        doc.fontSize = cue.size; try {doc.font = theme.fontPostscript || theme.fontFamily;} catch (_) {}
        doc.fillColor = preset === 'emphasis' && run.emphasis ? active : color; doc.applyFill = true; doc.applyStroke = true; doc.strokeColor = [0,0,0]; doc.strokeWidth = Math.max(1,Math.round(cue.size/32));
        doc.justification = ParagraphJustification.LEFT_JUSTIFY; source.setValue(doc);
        var bounds = layer.sourceRectAtTime(start,false), transform = layer.property('ADBE Transform Group');
        transform.property('ADBE Anchor Point').setValue([bounds.left+bounds.width/2,bounds.top+bounds.height/2]);
        var position = [run.x+run.width/2,run.y+bounds.height/2]; transform.property('ADBE Position').setValue(position);
        layer.inPoint = preset === 'reveal' ? Math.max(start,run.start+offset) : start; layer.outPoint = end;
        var on = Math.max(start,run.start+offset), off = Math.min(end,run.end+offset);
        if (preset === 'karaoke' || preset === 'pop') {
            doc = source.value; doc.fillColor = active; source.setValueAtTime(on,doc); doc = source.value; doc.fillColor = color; source.setValueAtTime(off,doc);
            if (on > start) {doc = source.value; doc.fillColor=color; source.setValueAtTime(start,doc);} uzAnimationHold(source);
        }
        if (preset === 'pop') { var scale = transform.property('ADBE Scale'), pulse = Math.min(speed,Math.max(.001,off-on)); scale.setValueAtTime(on,[100,100]); scale.setValueAtTime(on+pulse/2,[114,114]); scale.setValueAtTime(on+pulse,[100,100]); uzAnimationLinear(scale); }
        if (preset === 'slide') {
            var p = transform.property('ADBE Position'), opacity = transform.property('ADBE Opacity');
            p.setValueAtTime(start,[position[0],position[1]+24]); p.setValueAtTime(start+speed,position); uzAnimationLinear(p);
            opacity.setValueAtTime(start,0); opacity.setValueAtTime(start+speed,100); opacity.setValueAtTime(end-speed,100); opacity.setValueAtTime(end,0); uzAnimationLinear(opacity);
        }
        if (expose && source.canAddToMotionGraphicsTemplate(comp)) source.addToMotionGraphicsTemplateAs(comp,'So‘z '+(i+1));
        count++;
    }
    return count;
}
function uzImportAnimatedCaptions(planPath, offset, name, identity) {
    try {
        var comp = uzAnimationComp(name,identity), plan = uzAnimationRead(planPath), count = 0;
        if (plan.schema !== 1 || plan.width !== comp.width || plan.height !== comp.height) throw new Error("Video o‘lchami o‘zgargan. Animatsiyani qayta yarating.");
        app.beginUndoGroup('UzScribe animatsiyalari');
        try {for (var i = 0; i < plan.cues.length; i++) count += uzAnimationLayers(comp,plan.cues[i],plan.theme,Number(offset),false);}
        finally {app.endUndoGroup();}
        return count+' ta vaqtli matn qatlami yaratildi.';
    } catch (e) { return 'Animatsiya import qilinmadi: '+e.toString(); }
}
function uzExportCaptionMogrts(planPath, outputDir, name, identity) {
    try {
        uzAnimationComp(name,identity);
        if (!app.project.file) throw new Error("Avval AE loyihasini saqlang, keyin MOGRT eksportini qaytaring.");
        var plan = uzAnimationRead(planPath), folder = new Folder(outputDir); if (!folder.exists && !folder.create()) throw new Error("MOGRT papkasi yaratilmagan.");
        var clips = [], prefix = 'UzScribe-'+new Date().getTime();
        function quote(s) {return '"'+String(s).replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/\r/g,'\\r').replace(/\n/g,'\\n')+'"';}
        app.beginUndoGroup('UzScribe MOGRT eksporti');
        try {
            for (var i = 0; i < plan.cues.length; i++) {
                var cue = plan.cues[i], compName = prefix+'-'+(i+1), comp = app.project.items.addComp(compName,plan.width,plan.height,1,Math.max(1/plan.fps,cue.end-cue.start),plan.fps);
                uzAnimationLayers(comp,cue,plan.theme,-cue.start,true); comp.motionGraphicsTemplateName = compName;
                if (!comp.exportAsMotionGraphicsTemplate(true,folder.fsName)) throw new Error("MOGRT eksport qilinmadi: "+compName);
                var file = new File(folder.fsName+'/'+compName+'.mogrt'); if (!file.exists) throw new Error("Eksport qilingan MOGRT topilmadi.");
                clips.push('{"path":'+quote(file.fsName)+',"start":'+cue.start+',"end":'+cue.end+'}');
            }
        } finally {app.endUndoGroup();}
        var manifest = new File(folder.fsName+'/manifest.json'); manifest.encoding='UTF-8'; if (!manifest.open('w')) throw new Error("Manifest yozilmadi.");
        try {manifest.write('{"schema":1,"width":'+plan.width+',"height":'+plan.height+',"fps":'+plan.fps+',"clips":['+clips.join(',')+']}');} finally {manifest.close();}
        return clips.length+' ta MOGRT saqlandi.\nManifest: '+manifest.fsName;
    } catch (e) {return 'MOGRT eksport qilinmadi: '+e.toString();}
}
