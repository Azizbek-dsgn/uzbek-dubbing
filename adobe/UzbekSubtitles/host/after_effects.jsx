function importUzbekSrt(srtPath, offsetSeconds) {
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
            text.fillColor = [1, 1, 1];
            text.applyFill = true;
            text.applyStroke = false;
            text.justification = ParagraphJustification.CENTER_JUSTIFY;
            layer.property("Source Text").setValue(text);
            layer.property("Position").setValue([comp.width / 2, comp.height * 0.88]);
            layer.startTime = 0;
            layer.inPoint = start;
            layer.outPoint = Math.min(end, comp.duration);
            count++;
        }
    } finally { app.endUndoGroup(); }
    return count + " ta vaqtli matn qatlami yaratildi.";
}
