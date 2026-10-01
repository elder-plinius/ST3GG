/* ST3GG's reversible cellular-automaton instrument. No network or storage. */
(function () {
    'use strict';
    const E = window.CellularFieldEngine;
    const $ = id => document.getElementById('cf-' + id);
    const panel = document.getElementById('cellular-panel');
    if (!panel || !E) return;
    const SIZE = 192, LIMIT = 8192;
    const canvases = [$('control'), $('twin')];
    let worlds, originDigest, target = null, frame = 0, revision = 0, brush = null;
    let cursor = { x: SIZE / 2, y: SIZE / 2 }, perturbed = false;
    const proofs = [$('proof-control'), $('proof-twin')];

    function message(text) { $('message').textContent = text; }
    function clearError() { $('error').textContent = ''; }
    function fail(error) { $('error').textContent = error.message || String(error); }
    function stop() {
        target = null;
        cancelAnimationFrame(frame);
        frame = 0;
    }
    function invalidate() { revision++; proofs.forEach(p => { p.textContent = 'Current cells only'; }); }
    function paint() {
        worlds.forEach((world, j) => {
            const canvas = canvases[j];
            if (canvas.width !== world.width || canvas.height !== world.height) {
                canvas.width = world.width; canvas.height = world.height;
            }
            const ctx = canvas.getContext('2d');
            const img = ctx.createImageData(world.width, world.height);
            for (let i = 0; i < world.cells.length; i++) {
                const different = j === 1 && world.cells[i] !== worlds[0].cells[i];
                const live = E.displayCell(world, i), p = i * 4;
                img.data[p] = different ? 255 : live ? 0 : 7;
                img.data[p + 1] = different ? 196 : live ? 255 : 17;
                img.data[p + 2] = different ? 64 : live ? 100 : 12;
                img.data[p + 3] = 255;
            }
            ctx.putImageData(img, 0, 0);
            if (document.activeElement === canvas && j === 0 && world.step === 0) {
                ctx.strokeStyle = '#00d4ff';
                ctx.strokeRect(cursor.x - 2.5, cursor.y - 2.5, 6, 6);
            }
        });
        $('time').textContent = worlds[0].step.toLocaleString();
        $('difference').textContent = E.hammingDistance(worlds[0].cells, worlds[1].cells).toLocaleString();
        $('dimensions').textContent = worlds[0].width + ' × ' + worlds[0].height;
        const busy = target !== null;
        $('stop').disabled = !busy;
        $('return').disabled = worlds[0].step === 0 && !busy;
        $('step-back').disabled = busy || worlds[0].step === 0;
        $('step-forward').disabled = busy || worlds[0].step >= LIMIT;
        $('evolve').disabled = busy || worlds[0].step >= LIMIT;
        $('perturb').disabled = busy || perturbed;
        $('rejoin').disabled = busy;
        canvases[0].setAttribute('aria-label', 'Control field. At time zero, draw with pointer or move with arrow keys and press Space to toggle a cell. Cursor ' + cursor.x + ', ' + cursor.y + '.');
    }
    async function digest(cells) {
        if (!globalThis.crypto?.subtle) return undefined;
        const hash = await crypto.subtle.digest('SHA-256', cells.slice());
        return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
    }
    async function rememberOrigin() {
        const version = ++revision;
        originDigest = undefined;
        proofs.forEach(p => { p.textContent = 'Recording reference digest…'; });
        try {
            const hash = await digest(worlds[0].cells);
            if (version !== revision) return;
            originDigest = hash;
            proofs.forEach(p => { p.textContent = hash ? 'Origin digest recorded' : 'Digest unavailable; inverse still works'; });
        } catch (error) { if (version === revision) proofs.forEach(p => { p.textContent = 'Digest unavailable; inverse still works'; }); }
    }
    async function verifyReturn() {
        const version = ++revision;
        const reference = originDigest;
        if (!reference) { proofs.forEach(p => { p.textContent = 'At zero · no reference digest'; }); return; }
        try {
            const hashes = await Promise.all(worlds.map(w => digest(w.cells)));
            if (version !== revision || worlds[0].step !== 0) return;
            proofs.forEach((p, i) => { p.textContent = !hashes[i] ? 'Digest unavailable' : hashes[i] === reference ? 'SHA-256 matches origin' : 'Differs from origin'; });
        } catch (error) { if (version === revision) proofs.forEach(p => { p.textContent = 'Digest unavailable'; }); }
    }
    function textCells(text) {
        const canvas = document.createElement('canvas'); canvas.width = canvas.height = SIZE;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#000'; ctx.fillRect(0, 0, SIZE, SIZE);
        ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        const clean = text.trim().replace(/\s+/g, ' ');
        let lines = [clean];
        if (clean.length > 8) {
            const middle = Math.floor(clean.length / 2);
            const spaces = [...clean.matchAll(/ /g)].map(m => m.index);
            const split = spaces.length ? spaces.reduce((a, b) => Math.abs(a - middle) < Math.abs(b - middle) ? a : b) : middle;
            lines = [clean.slice(0, split), clean.slice(split).trim()];
        }
        ctx.font = 'bold ' + Math.min(44, 260 / Math.max(...lines.map(s => s.length), 1)) + 'px monospace';
        lines.forEach((line, i) => ctx.fillText(line, 96, 96 + (i - (lines.length - 1) / 2) * 46));
        const pixels = ctx.getImageData(0, 0, SIZE, SIZE).data;
        return Uint8Array.from({ length: SIZE * SIZE }, (_, i) => +(pixels[i * 4] > 127));
    }
    function seed(blank = false) {
        clearError();
        if (!blank && !$('seed').value.trim()) { fail(new Error('Enter a mark, or choose Blank field to draw.')); return; }
        stop(); invalidate();
        const cells = blank ? new Uint8Array(SIZE * SIZE) : textCells($('seed').value);
        worlds = [E.createWorld(SIZE, SIZE, cells), E.createWorld(SIZE, SIZE, cells)];
        perturbed = false; brush = null; cursor = { x: SIZE / 2, y: SIZE / 2 };
        paint(); void rememberOrigin();
        message(blank ? 'Draw on Control. Both fields receive the same mark.' : 'Evolve the mark, flip one twin cell, then return both fields to zero.');
    }
    function finishMotion() {
        stop(); paint();
        if (worlds[0].step === 0) { message('Returned using the inverse rule, without a saved image or frame history.'); void verifyReturn(); }
    }
    function tick() {
        if (target === null) return;
        const delta = target - worlds[0].step;
        const count = Math.min(8, Math.abs(delta));
        worlds.forEach(w => delta > 0 ? E.forward(w, count) : E.backward(w, count));
        if (worlds[0].step === target) { finishMotion(); return; }
        paint(); frame = requestAnimationFrame(tick);
    }
    function run(to) {
        stop(); clearError(); invalidate(); brush = null;
        target = Math.max(0, Math.min(LIMIT, to));
        message(target === 0 ? 'Applying the inverse rule…' : 'Evolving the current cells…');
        paint(); frame = requestAnimationFrame(tick);
    }
    function step(direction) {
        stop(); clearError(); invalidate();
        if (worlds[0].step + direction < 0 || worlds[0].step + direction > LIMIT) return;
        worlds.forEach(w => direction > 0 ? E.forward(w) : E.backward(w));
        paint(); if (worlds[0].step === 0) void verifyReturn();
        message('Applied one ' + (direction > 0 ? 'forward' : 'inverse') + ' step.');
    }
    function perturb(index) {
        if (target !== null || perturbed) return;
        invalidate(); clearError();
        const w = worlds[1];
        if (index === undefined) index = Math.floor(w.height / 2) * w.width + Math.floor(w.width / 2);
        E.flip(w, index); perturbed = true; paint();
        message('Flipped exactly one twin cell at (' + index % w.width + ', ' + Math.floor(index / w.width) + '), time ' + w.step + '. Return to zero to compare.');
        if (w.step === 0) void verifyReturn();
    }
    function download(which) {
        stop(); paint();
        const world = worlds[which];
        const url = URL.createObjectURL(new Blob([JSON.stringify(E.exportState(world, originDigest), null, 2)], { type: 'application/json' }));
        const link = document.createElement('a'); link.href = url;
        link.download = 'cellular-field-' + (which ? 'twin' : 'control') + '-t' + world.step + '.json'; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1500);
        message('Saved current cells, dimensions, time, and optional reference digest. No original bitmap.');
    }
    async function load(file) {
        if (!file) return;
        stop(); invalidate(); paint(); clearError();
        const version = revision;
        try {
            if (file.size > 265000) throw new Error('State file exceeds the 265 KB limit.');
            const w = E.importState(await file.text());
            if (version !== revision) return;
            if (w.width > 256 || w.height > 256) throw new Error('This viewer supports fields up to 256 × 256.');
            if (w.step < 0 || w.step > LIMIT) throw new Error('This viewer supports time 0–8192.');
            originDigest = w.originDigest;
            delete w.originDigest; // Keep reference metadata outside the mutable engine worlds.
            worlds = [w, { ...w, cells: w.cells.slice() }]; perturbed = false; brush = null;
            cursor = { x: Math.floor(w.width / 2), y: Math.floor(w.height / 2) };
            $('seed').value = ''; paint();
            message('Loaded only the current field. Return to zero to recover its predecessor.');
            if (w.step === 0) void verifyReturn();
        } catch (error) { if (version === revision) fail(error); }
        finally { $('file').value = ''; }
    }
    function point(event) {
        const rect = event.currentTarget.getBoundingClientRect(), w = worlds[0];
        return { x: Math.max(0, Math.min(w.width - 1, Math.floor((event.clientX - rect.left) / rect.width * w.width))), y: Math.max(0, Math.min(w.height - 1, Math.floor((event.clientY - rect.top) / rect.height * w.height))) };
    }
    function draw(event, start) {
        if (target !== null || worlds[0].step !== 0 || perturbed || (!start && !brush)) return;
        const pos = point(event), previous = brush || { ...pos, bit: event.altKey ? 0 : 1 };
        if (start) event.currentTarget.setPointerCapture(event.pointerId);
        const distance = Math.max(1, Math.abs(pos.x - previous.x), Math.abs(pos.y - previous.y));
        for (let s = 0; s <= distance; s++) {
            const x = Math.round(previous.x + (pos.x - previous.x) * s / distance), y = Math.round(previous.y + (pos.y - previous.y) * s / distance);
            worlds.forEach(w => {
                for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
                    const px = x + dx, py = y + dy;
                    if (dx * dx + dy * dy <= 5 && px >= 0 && py >= 0 && px < w.width && py < w.height) w.cells[py * w.width + px] = previous.bit;
                }
            });
        }
        brush = { ...pos, bit: previous.bit }; cursor = pos; originDigest = undefined; invalidate(); paint();
    }
    function endDraw() { if (brush) { brush = null; void rememberOrigin(); message('Mark recorded in both fields. Ready to evolve.'); } }
    $('new').addEventListener('click', () => seed());
    $('blank').addEventListener('click', () => { seed(true); canvases[0].focus(); });
    $('evolve').addEventListener('click', () => run(worlds[0].step + Number($('steps').value)));
    $('return').addEventListener('click', () => run(0));
    $('stop').addEventListener('click', () => { stop(); paint(); message('Paused at the current state.'); });
    $('step-forward').addEventListener('click', () => step(1));
    $('step-back').addEventListener('click', () => step(-1));
    $('perturb').addEventListener('click', () => perturb());
    $('rejoin').addEventListener('click', () => {
        invalidate(); worlds[1] = { ...worlds[0], cells: worlds[0].cells.slice() }; perturbed = false;
        paint(); if (worlds[0].step === 0) void verifyReturn(); message('Twin copied from Control at the current time.');
    });
    $('save-control').addEventListener('click', () => download(0));
    $('save-twin').addEventListener('click', () => download(1));
    $('load').addEventListener('click', () => $('file').click());
    $('file').addEventListener('change', () => void load($('file').files[0]));
    $('seed').addEventListener('keydown', e => { if (e.key === 'Enter') seed(); });
    canvases[0].addEventListener('pointerdown', e => draw(e, true));
    canvases[0].addEventListener('pointermove', e => draw(e, false));
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(type => canvases[0].addEventListener(type, endDraw));
    canvases[0].addEventListener('keydown', event => {
        if (target !== null || worlds[0].step !== 0 || perturbed) return;
        const moves = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
        if (moves[event.key]) {
            event.preventDefault(); const [dx, dy] = moves[event.key];
            cursor.x = Math.max(0, Math.min(worlds[0].width - 1, cursor.x + dx));
            cursor.y = Math.max(0, Math.min(worlds[0].height - 1, cursor.y + dy)); paint();
        } else if (event.key === ' ') {
            event.preventDefault(); worlds.forEach(w => E.flip(w, cursor.y * w.width + cursor.x));
            invalidate(); paint(); void rememberOrigin();
        }
    });
    canvases[0].addEventListener('focus', paint); canvases[0].addEventListener('blur', paint);
    canvases[1].addEventListener('pointerdown', event => { const pos = point(event); perturb(pos.y * worlds[1].width + pos.x); });
    function pauseHidden() {
        if (target !== null && (document.hidden || !panel.classList.contains('active'))) {
            stop(); paint(); message('Paused while the field is out of view.');
        }
    }
    document.addEventListener('visibilitychange', pauseHidden);
    new MutationObserver(pauseHidden).observe(panel, { attributes: true, attributeFilter: ['class'] });
    seed();
})();
