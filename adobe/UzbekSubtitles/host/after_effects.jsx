function importUzbekSrt(srtPath, offsetSeconds, expectedName, expectedIdentity, captionMode, speakerLabels) {
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
            if (captionMode === "word" && end - start > 0.08) {
                var popEnd = Math.min(end - 0.01, start + 0.12);
                var scale = layer.property("Transform").property("Scale");
                var opacity = layer.property("Transform").property("Opacity");
                scale.setValueAtTime(start, [82, 82]);
                scale.setValueAtTime(popEnd, [100, 100]);
                opacity.setValueAtTime(start, 35);
                opacity.setValueAtTime(Math.min(end - 0.005, start + 0.08), 100);
            }
            count++;
        }
    } finally { app.endUndoGroup(); }
    return count + " ta vaqtli matn qatlami yaratildi.";
}
