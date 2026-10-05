// After Effects adapter: composition/work area and native Render Queue audio.
function uzAeJson(s) {return String(s).replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/\r/g,'\\r').replace(/\n/g,'\\n');}
function uzAeLayerToken(layer) {
    var id = ''; try {if (layer.id !== undefined) id = String(layer.id);} catch (_) {}
    var token = [id,layer.index,layer.name,layer.source.id,layer.inPoint,layer.outPoint,layer.startTime,layer.stretch,layer.timeRemapEnabled].join('|');
    if (layer.timeRemapEnabled) {
        var remap = layer.property('ADBE Time Remapping');
        token += '|' + remap.expressionEnabled + '|' + remap.expression;
        for (var k=1;k<=remap.numKeys;k++) token += '|' + remap.keyTime(k) + ':' + remap.keyValue(k);
    }
    return token;
}
function uzAeRange(mode) {
    var comp=app.project && app.project.activeItem;
    if(!comp || !(comp instanceof CompItem))throw new Error("Avval video bor kompozitsiyani oching.");
    var selected=comp.selectedLayers;
    if(!selected || selected.length!==1)throw new Error("Timeline’da subtitr qilinadigan bitta video layerni tanlang.");
    var layer=selected[0];
    if(!layer.source || !layer.source.hasVideo || !layer.hasAudio)throw new Error("Tanlangan layerda video va audio bo‘lishi kerak. Ovozli video layerni tanlang.");
    var start=Math.max(0,Number(layer.inPoint)),end=Math.min(Number(comp.duration),Number(layer.outPoint));
    var ws=Number(comp.workAreaStart),wd=Number(comp.workAreaDuration);
    if(mode==='inout') {start=Math.max(start,ws);end=Math.min(end,ws+wd);}
    if(!isFinite(start+end) || !(end>start))throw new Error("Tanlangan video layer bu oraliqda yo‘q. Layer yoki Work Area vaqtini tekshiring.");
    return {comp:comp,layer:layer,layerToken:uzAeLayerToken(layer),start:start,duration:end-start,marked:mode==='inout'};
}
function uzAeTimelineInfo(mode) {
    try {
        var r=uzAeRange(mode),comp=r.comp;
        return '{"host":"AEFT","start":'+r.start+',"duration":'+r.duration+',"marked":'+r.marked+',"fps":'+Number(comp.frameRate)+',"width":'+Number(comp.width)+',"height":'+Number(comp.height)+',"layer_name":"'+uzAeJson(r.layer.name)+'","layer_token":"'+uzAeJson(r.layerToken)+'","layer_index":'+r.layer.index+',"trackCount":0,"videoCount":0,"name":"'+uzAeJson(comp.name)+'","identity":"'+uzAeJson(comp.id)+'"}';
    }catch(e){return '{"error":"'+uzAeJson(e.toString())+'"}';}
}
function uzAeExportAudio(mode,outputPath,expectedName,expectedIdentity,expectedLayerToken,expectedStart,expectedDuration) {
    var item=null,temporaryComp=null,disabled=[];
    try {
        var r=uzAeRange(mode),comp=r.comp,queue=app.project.renderQueue;
        if(comp.name!==expectedName || (expectedIdentity && String(comp.id)!==expectedIdentity))throw new Error("Faol kompozitsiya o‘zgargan. Avvalgi kompozitsiyani oching.");
        if(queue.rendering)throw new Error("AE Render Queue hozir ishlayapti. Tugashini kuting.");
        if(expectedLayerToken && r.layerToken!==expectedLayerToken)throw new Error("Tanlangan video layer o‘zgargan. Layerni tanlab qayta boshlang.");
        if(expectedStart!==undefined && (Math.abs(r.start-Number(expectedStart))>.0001 || Math.abs(r.duration-Number(expectedDuration))>.0001))throw new Error("Layer/Work Area vaqti o‘zgargan. Qayta boshlang.");
        // Render a disposable duplicate: preserve layer timing, stretch, remap and audio effects.
        // All isolation toggles belong to the duplicate, never to the user's composition.
        temporaryComp=comp.duplicate(); temporaryComp.name='UzScribe audio · '+new Date().getTime();
        for(var l=1;l<=temporaryComp.numLayers;l++) {
            var isolated=temporaryComp.layer(l); isolated.locked=false; isolated.solo=false;
            if(isolated.hasAudio) isolated.audioEnabled=l===r.layer.index;
        }
        var chosenLayer=temporaryComp.layer(r.layer.index); chosenLayer.guideLayer=false; chosenLayer.audioEnabled=true;

        // Save only render flags we change; do not touch DONE/error queue entries.
        for(var i=1;i<=queue.numItems;i++){var other=queue.item(i);if(other.render){disabled.push(other);other.render=false;}}
        item=queue.items.add(temporaryComp);item.timeSpanStart=r.start;item.timeSpanDuration=r.duration;
        var module=item.outputModule(1),templates=module.templates,format='',chosen='';
        for(var t=0;t<templates.length;t++) {
            try {
                module=item.outputModule(1);module.applyTemplate(templates[t]);module=item.outputModule(1);
                var actual=String(module.getSettings(GetSettingsFormat.STRING).Format);
                if(/wave|wav|aiff/i.test(actual)){format=actual;chosen=templates[t];if(/wave|wav/i.test(actual))break;}
            }catch(templateError){}
        }
        if(!chosen)throw new Error("AE audio Output Module topilmadi. Render Queue’da WAV yoki AIFF formatini tanlab UzScribe Audio nomi bilan shablon saqlang; keyin qaytaring.");
        module=item.outputModule(1);module.applyTemplate(chosen);module=item.outputModule(1);
        // AIFF templates work too; the panel converts the native export to 16 kHz WAV.
        var nativePath=String(outputPath).replace(/\.wav$/i,/aiff/i.test(format)?'.aif':'.wav'),file=new File(nativePath);
        if(file.exists)file.remove();
        try {module.setSetting('Audio Output','On');}catch(audioSettingError){}
        module=item.outputModule(1);module.file=file;item.render=true;
        queue.render();
        // Output Module can adjust the extension: use its actual resulting path.
        var exported=item.outputModule(1).file;
        if(!exported || !exported.exists || exported.length<1000)throw new Error("AE kompozitsiya audiosi eksport qilinmadi. Audio yoqilganini va Render Queue xatosini tekshiring.");
        return '{"path":"'+uzAeJson(exported.fsName)+'","name":"'+uzAeJson(comp.name)+'","identity":"'+uzAeJson(comp.id)+'","layer_token":"'+uzAeJson(r.layerToken)+'","template":"'+uzAeJson(chosen)+'"}';
    }catch(e){return '{"error":"'+uzAeJson(e.toString())+'"}';}
    finally {
        if(item){try{item.remove();}catch(removeError){}}
        if(temporaryComp){try{temporaryComp.remove();}catch(removeCompError){}}
        for(var j=0;j<disabled.length;j++){try{disabled[j].render=true;}catch(restoreError){}}
    }
}

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
    var count = 0, createdLayers = [];
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
            if (start === null || end === null || end <= start) { continue; }
            start += Number(offsetSeconds) || 0;
            end += Number(offsetSeconds) || 0;
            start = Math.max(0, start); end = Math.min(end, comp.duration);
            if (end <= start) { continue; }
            var layer = comp.layers.addText(lines.slice(2).join("\r"));
            createdLayers.push(layer);
            layer.name = uzCaptionLayerName(count + 1, lines.slice(2).join(" "));
            var text = layer.property("ADBE Text Properties").property("ADBE Text Document").value;
            text.fontSize = Math.max(28, Math.round(comp.width / 32));
            var speaker = speakerLabels && speakerLabels[i];
            var palette = [[1, 1, 1], [1, 0.77, 0.37], [0.58, 0.83, 1], [0.73, 1, 0.7]];
            var colorIndex = speaker ? Number(String(speaker).replace(/\D/g, "")) + 1 : 0;
            text.fillColor = palette[isFinite(colorIndex) ? colorIndex % palette.length : 0];
            text.applyFill = true;
            text.applyStroke = false;
            text.justification = ParagraphJustification.CENTER_JUSTIFY;
            layer.property("ADBE Text Properties").property("ADBE Text Document").setValue(text);
            layer.property("ADBE Transform Group").property("ADBE Position").setValue([comp.width / 2, comp.height * 0.88]);
            layer.startTime = start;
            layer.inPoint = start;
            layer.outPoint = Math.min(end, comp.duration);
            if (captionMode === "word" && !selectForComposer && end - start > 0.08) {
                var popEnd = Math.min(end - 0.01, start + 0.12);
                var scale = layer.property("ADBE Transform Group").property("ADBE Scale");
                var opacity = layer.property("ADBE Transform Group").property("ADBE Opacity");
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
    } catch (error) {
        for (var failed = createdLayers.length - 1; failed >= 0; failed--) { try { createdLayers[failed].remove(); } catch (_) {} }
        return "Subtitr import qilinmadi: " + error.toString();
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
            if (h > 0) {
                var prev = cue.runs[h-1], moveEnd = Math.min(end,time+Math.min(speed,Math.max(.001,r.end-r.start)));
                pos.setValueAtTime(time,[prev.x+prev.width/2,prev.y+prev.height/2]); rect.property('ADBE Vector Rect Size').setValueAtTime(time,[prev.width+16,prev.height+3]);
                pos.setValueAtTime(moveEnd,target); rect.property('ADBE Vector Rect Size').setValueAtTime(moveEnd,[r.width+16,r.height+3]);
            } else {pos.setValueAtTime(time,target);rect.property('ADBE Vector Rect Size').setValueAtTime(time,[r.width+16,r.height+3]);}
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
// One cue = one editable text layer. Per-word animation lives in text animators.
function uzCaptionLayerName(index, text) {
    var number = String(index); while (number.length < 3) number = '0' + number;
    return 'UzScribe ' + number + ' · ' + String(text).replace(/\s+/g, ' ').substr(0, 70);
}
function uzCaptionLayout(cue) {
    var text = '', ranges = [], chars = 0, lastY = null;
    for (var i = 0; i < cue.runs.length; i++) {
        var run = cue.runs[i];
        if (i) { if (run.y !== lastY) text += '\r'; else {text += ' '; chars++;} }
        // AE index selectors count characters and spaces, but exclude paragraph breaks.
        var word = String(run.text); ranges.push({start:chars,end:chars+word.length,run:run});
        text += word; chars += word.length; lastY = run.y;
    }
    return {text:text,ranges:ranges};
}
function uzCaptionAnimator(layer, range, propertyName, value, label) {
    var animators = layer.property('ADBE Text Properties').property('ADBE Text Animators');
    var animator = animators.addProperty('ADBE Text Animator'); animator.name = label;
    var index = animator.propertyIndex;
    animator.property('ADBE Text Animator Properties').addProperty(propertyName).setValue(value);
    // Adding to an indexed group invalidates old native references: reacquire them.
    animator = animators.property(index);
    var selector = animator.property('ADBE Text Selectors').addProperty('ADBE Text Selector');
    var advanced = selector.property('ADBE Text Range Advanced');
    advanced.property('ADBE Text Range Units').setValue(2);
    advanced.property('ADBE Text Selector Smoothness').setValue(0);
    selector.property('ADBE Text Index Start').setValue(range.start);
    selector.property('ADBE Text Index End').setValue(range.end);
    return advanced.property('ADBE Text Selector Max Amount');
}
function uzCaptionCueLayer(comp, cue, theme, offset, index) {
    var start = Math.max(0, cue.start + offset), end = Math.min(cue.end + offset, comp.duration);
    if (!isFinite(start + end) || end <= start || !cue.runs || !cue.runs.length) return 0;
    var layout = uzCaptionLayout(cue), layer = comp.layers.addText(layout.text);
    layer.name = uzCaptionLayerName(index, layout.text);
    layer.startTime = start; layer.inPoint = start; layer.outPoint = end;
    var source = layer.property('ADBE Text Properties').property('ADBE Text Document'), doc = source.value;
    doc.fontSize = cue.size; try {doc.font = theme.fontPostscript || theme.fontFamily;} catch (_) {}
    doc.fillColor = uzAnimationRGB(theme.color); doc.applyFill = true; doc.applyStroke = true;
    doc.strokeColor = [0,0,0]; doc.strokeWidth = Math.max(1,Math.round(cue.size/32));
    doc.justification = ParagraphJustification.CENTER_JUSTIFY; doc.autoLeading = false; doc.leading = Math.round(cue.size*1.35);
    source.setValue(doc);
    var bounds = layer.sourceRectAtTime(start,false), transform = layer.property('ADBE Transform Group');
    transform.property('ADBE Anchor Point').setValue([bounds.left+bounds.width/2,bounds.top+bounds.height/2]);
    var position = [comp.width/2,cue.runs[0].y+bounds.height/2];
    transform.property('ADBE Position').setValue(position);
    var speed = Math.min(theme.speed,(end-start)/2), active = uzAnimationRGB(theme.active), preset = theme.preset;
    if (preset === 'slide') {
        var pos = transform.property('ADBE Position'), opacity = transform.property('ADBE Opacity');
        pos.setValueAtTime(start,[position[0],position[1]+24]); pos.setValueAtTime(start+speed,position); uzAnimationLinear(pos);
        opacity.setValueAtTime(start,0); opacity.setValueAtTime(start+speed,100);
        opacity.setValueAtTime(end-speed,100); opacity.setValueAtTime(end,0); uzAnimationLinear(opacity);
    }
    for (var w = 0; w < layout.ranges.length; w++) {
        var r = layout.ranges[w], on = Math.max(start,r.run.start+offset), off = Math.min(end,r.run.end+offset), amount;
        if (off <= on) continue;
        if (preset === 'karaoke' || preset === 'pop' || preset === 'pill') {
            amount = uzCaptionAnimator(layer,r,'ADBE Text Fill Color',active,'UzScribe · So‘z '+(w+1));
            if (on > start) amount.setValueAtTime(start,0);
            amount.setValueAtTime(on,100); amount.setValueAtTime(off,0); uzAnimationHold(amount);
        }
        if (preset === 'pop') {
            amount = uzCaptionAnimator(layer,r,'ADBE Text Scale 3D',[114,114,100],'UzScribe · Pop '+(w+1));
            var pulse = Math.min(speed,off-on); amount.setValueAtTime(start,0);
            amount.setValueAtTime(on,0); amount.setValueAtTime(on+pulse/2,100); amount.setValueAtTime(on+pulse,0); uzAnimationLinear(amount);
        }
        if (preset === 'reveal') {
            amount = uzCaptionAnimator(layer,r,'ADBE Text Opacity',0,'UzScribe · Ochilish '+(w+1));
            if (on > start) amount.setValueAtTime(start,100);
            amount.setValueAtTime(on,0); uzAnimationHold(amount);
        }
        if (preset === 'emphasis' && r.run.emphasis) uzCaptionAnimator(layer,r,'ADBE Text Fill Color',active,'UzScribe · Urg‘u '+(w+1));
    }
    if (preset === 'pill') {
        var pill = comp.layers.addShape(); pill.name = 'UzScribe ' + index + ' · Highlight';
        pill.startTime = start; pill.inPoint = start; pill.outPoint = end;
        pill.parent = layer; pill.moveAfter(layer); // Keep text above the helper, which follows layer moves.
        var group = pill.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group').property('ADBE Vectors Group');
        var fill = group.addProperty('ADBE Vector Graphic - Fill'); fill.property('ADBE Vector Fill Color').setValue(active); fill.property('ADBE Vector Fill Opacity').setValue(70);
        var rect = group.addProperty('ADBE Vector Shape - Rect'); rect.property('ADBE Vector Rect Roundness').setValue(10);
        var pp = pill.property('ADBE Transform Group').property('ADBE Position');
        for (var h = 0; h < cue.runs.length; h++) {
            var run = cue.runs[h], at = Math.max(start,run.start+offset);
            if (at >= end) continue;
            // Parent space: compensate for centered anchor; plan geometry remains the highlight guide.
            pp.setValueAtTime(at,[bounds.left+bounds.width/2+run.x+run.width/2-position[0],bounds.top+bounds.height/2+run.y+run.height/2-position[1]]);
            rect.property('ADBE Vector Rect Size').setValueAtTime(at,[run.width+16,run.height+3]);
        }
        uzAnimationHold(pp); uzAnimationHold(rect.property('ADBE Vector Rect Size'));
    }
    return 1;
}
function uzImportAnimatedCaptions(planPath, offset, name, identity) {
    try {
        var comp = uzAnimationComp(name,identity), plan = uzAnimationRead(planPath), count = 0, before = comp.numLayers;
        if (plan.schema !== 1 || plan.width !== comp.width || plan.height !== comp.height) throw new Error("Video o‘lchami o‘zgargan. Animatsiyani qayta yarating.");
        app.beginUndoGroup('UzScribe animatsiyalari');
        try {for (var i = 0; i < plan.cues.length; i++) count += uzCaptionCueLayer(comp,plan.cues[i],plan.theme,Number(offset)||0,i+1);}
        catch (error) {while (comp.numLayers > before) comp.layer(1).remove();throw error;}
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
                clips.push('{"path":'+quote(compName+'.mogrt')+',"start":'+cue.start+',"end":'+cue.end+'}');
            }
        } finally {app.endUndoGroup();}
        var manifest = new File(folder.fsName+'/manifest.json'); manifest.encoding='UTF-8'; if (!manifest.open('w')) throw new Error("Manifest yozilmadi.");
        try {manifest.write('{"schema":1,"width":'+plan.width+',"height":'+plan.height+',"fps":'+plan.fps+',"clips":['+clips.join(',')+']}');} finally {manifest.close();}
        return clips.length+' ta MOGRT saqlandi.\nManifest: '+manifest.fsName;
    } catch (e) {return 'MOGRT eksport qilinmadi: '+e.toString();}
}
