function uzJson(s) {
    return String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r/g, "").replace(/\n/g, "\\n");
}
function uzIsAE() {
    try { return app.name.indexOf("After Effects") !== -1; } catch (e) { return false; }
}
function uzRange(mode) {
    var start = 0, duration = 0, total = 0, marked = false, fps = 25, name = "", identity = "", trackCount = 0, videoCount = 0;
    if (uzIsAE()) {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) throw new Error("Faol kompozitsiyani oching.");
        name = comp.name; identity = String(comp.id); total = Number(comp.duration); fps = Number(comp.frameRate);
        var ws = Number(comp.workAreaStart), wd = Number(comp.workAreaDuration);
        marked = wd > 0.05 && (ws > 0.05 || wd < total - 0.05);
        if (mode === "inout" && !marked) throw new Error("Work Area belgilanmagan.");
        if (mode !== "full" && marked) { start = ws; duration = wd; }
        else duration = total;
    } else {
        var seq = app.project.activeSequence;
        if (!seq) throw new Error("Faol sequence’ni oching.");
        name = seq.name;
        try { trackCount = Number(seq.audioTracks.numTracks); videoCount = Number(seq.videoTracks.numTracks); } catch (e) {}
        try { identity = seq.sequenceID ? String(seq.sequenceID) : ""; } catch (e) {}
        total = (Number(seq.end) - Number(seq.zeroPoint)) / 254016000000;
        try { fps = 254016000000 / Number(seq.timebase); } catch (e) {}
        var inside = -1, outside = -1;
        try { inside = Number(seq.getInPointAsTime().seconds); outside = Number(seq.getOutPointAsTime().seconds); } catch (e) {}
        marked = isFinite(inside) && isFinite(outside) && inside >= 0 &&
            outside > inside + 0.05 && outside <= total + 0.05 &&
            (inside > 0.05 || outside < total - 0.05);
        if (mode === "inout" && !marked) throw new Error("In va Out nuqtalarini belgilang (I va O).");
        if (mode !== "full" && marked) { start = inside; duration = outside - inside; }
        else duration = total;
    }
    if (!(duration > 0)) throw new Error("Timeline’da audio uzunligi topilmadi.");
    if (!(fps > 0) || !isFinite(fps)) fps = 25;
    return {start:start, duration:duration, total:total, marked:marked && mode !== "full", fps:fps, name:name, identity:identity, trackCount:trackCount, videoCount:videoCount};
}
function uzTimelineInfo(mode) {
    try {
        var r = uzRange(mode);
        return '{"start":' + r.start + ',"duration":' + r.duration + ',"marked":' + r.marked +
            ',"fps":' + r.fps + ',"trackCount":' + r.trackCount + ',"videoCount":' + r.videoCount + ',"name":"' + uzJson(r.name) + '","identity":"' + uzJson(r.identity) +
            '","host":"' + (uzIsAE() ? "AEFT" : "PPRO") + '"}';
    } catch (e) { return '{"error":"' + uzJson(e.toString()) + '"}'; }
}
function uzExportAudio(mode, outputPath, presetPath, selectedTrack) {
    try {
        var r = uzRange(mode), out = new File(outputPath);
        if (out.exists) out.remove();
        if (uzIsAE()) {
            var comp = app.project.activeItem, queue = app.project.renderQueue;
            var item = queue.items.add(comp), module = item.outputModule(1), applied = false;
            for (var t = 0; t < 3; t++) {
                try { module.applyTemplate(["WAV", "Audio Only", "AIFF"][t]); applied = true; break; } catch (e) {}
            }
            if (!applied) { item.remove(); throw new Error("AE audio Output Module shabloni topilmadi."); }
            module.file = out;
            item.timeSpanStart = r.start;
            item.timeSpanDuration = r.duration;
            var disabled = [], currentIndex = queue.numItems;
            for (var i = 1; i <= queue.numItems; i++) {
                var other = queue.item(i);
                if (i !== currentIndex) { disabled.push([other, other.render]); other.render = false; }
            }
            try { queue.render(); }
            finally {
                for (var j = 0; j < disabled.length; j++) disabled[j][0].render = disabled[j][1];
                item.remove();
            }
        } else {
            var seq = app.project.activeSequence, preset = new File(presetPath);
            if (!preset.exists) throw new Error("Premiere WAV eksport preset’i topilmadi.");
            var trackIndex = Number(selectedTrack), states = [];
            if (selectedTrack !== "all") {
                if (!isFinite(trackIndex) || trackIndex < 0 || trackIndex >= seq.audioTracks.numTracks)
                    throw new Error("Tanlangan audio trek topilmadi.");
                try {
                    for (var a = 0; a < seq.audioTracks.numTracks; a++) {
                        var track = seq.audioTracks[a];
                        states.push([track, track.isMuted()]);
                        track.setMute(a === trackIndex ? 0 : 1);
                    }
                    seq.exportAsMediaDirect(out.fsName, preset.fsName, r.marked ? 1 : 0);
                } finally {
                    for (var b = 0; b < states.length; b++) {
                        states[b][0].setMute(states[b][1] ? 1 : 0);
                    }
                }
            } else seq.exportAsMediaDirect(out.fsName, preset.fsName, r.marked ? 1 : 0);
        }
        if (!out.exists || out.length < 1000) throw new Error("Timeline audiosi eksport qilinmadi.");
        return '{"path":"' + uzJson(out.fsName) + '","name":"' + uzJson(r.name) +
            '","identity":"' + uzJson(r.identity) + '"}';
    } catch (e) { return '{"error":"' + uzJson(e.toString()) + '"}'; }
}
function uzFindSrt(item, nativePath) {
    if (!item) return null;
    try { if (item.getMediaPath && item.getMediaPath() === nativePath) return item; } catch (e) {}
    try {
        for (var i = 0; i < item.children.numItems; i++) {
            var found = uzFindSrt(item.children[i], nativePath);
            if (found) return found;
        }
    } catch (e) {}
    return null;
}
function uzImportCaptions(srtPath, offset, expectedName, expectedIdentity) {
    try {
        var seq = app.project.activeSequence, file = new File(srtPath);
        if (!seq || !file.exists) throw new Error("Sequence yoki SRT topilmadi.");
        if (seq.name !== expectedName) throw new Error("Faol sequence o'zgargan. Avvalgi sequence'ni oching.");
        if (expectedIdentity && String(seq.sequenceID) !== expectedIdentity)
            throw new Error("Faol sequence o'zgargan. Avvalgi sequence'ni oching.");
        var item = uzFindSrt(app.project.rootItem, file.fsName);
        if (!item) {
            if (!app.project.importFiles([file.fsName], true, app.project.rootItem, false))
                throw new Error("SRT import qilinmadi.");
            item = uzFindSrt(app.project.rootItem, file.fsName);
        }
        if (!item) throw new Error("Import qilingan SRT topilmadi.");
        if (!seq.createCaptionTrack(item, Number(offset)))
            throw new Error("Caption track yaratilmagan.");
        return '{"success":true}';
    } catch (e) { return '{"error":"' + uzJson(e.toString()) + '"}'; }
}

function uzPodcastExport(outputPath, expectedName, expectedIdentity) {
    try {
        if (uzIsAE()) throw new Error("Podcast montaji Premiere Pro uchun.");
        var seq = app.project.activeSequence, file = new File(outputPath);
        if (!seq || seq.name !== expectedName || (expectedIdentity && String(seq.sequenceID) !== expectedIdentity))
            throw new Error("Faol sequence o‘zgargan. Avvalgi sequence’ni oching.");
        if (file.exists) file.remove();
        if (!seq.exportAsFinalCutProXML(file.fsName) || !file.exists || file.length < 100)
            throw new Error("Timeline XML eksport qilinmadi.");
        return '{"success":true}';
    } catch (e) { return '{"error":"' + uzJson(e.toString()) + '"}'; }
}
function uzPodcastImport(xmlPath, expectedName, expectedIdentity) {
    try {
        if (uzIsAE()) throw new Error("Podcast montaji Premiere Pro uchun.");
        var seq = app.project.activeSequence, file = new File(xmlPath);
        if (!seq || seq.name !== expectedName || (expectedIdentity && String(seq.sequenceID) !== expectedIdentity))
            throw new Error("Faol sequence o‘zgargan. Avvalgi sequence’ni oching.");
        if (!file.exists || file.length < 100) throw new Error("Montaj XML topilmadi.");
        if (!app.project.importFiles([file.fsName], true, app.project.rootItem, false))
            throw new Error("Yangi sequence import qilinmadi. XML faylni File > Import orqali tekshiring.");
        return '{"success":true}';
    } catch (e) { return '{"error":"' + uzJson(e.toString()) + '"}'; }
}
