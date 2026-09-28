(() => {
    const key = 'servitech-confirmacion';
    let panel, canvas, fallback, video, context, timer, frame, generation = 0;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    function close() {
        generation++;
        clearTimeout(timer); cancelAnimationFrame(frame);
        if (video) video.pause();
        if (panel) panel.hidden = true;
    }
    function create() {
        if (panel) return;
        panel = document.createElement('div');
        panel.className = 'servi-confirm'; panel.hidden = true;
        panel.innerHTML = '<div class="servi-confirm-art" aria-hidden="true"><canvas width="480" height="270"></canvas><span class="servi-confirm-fallback">✓</span></div><p role="status" aria-live="polite" aria-atomic="true"></p><button type="button" aria-label="Cerrar confirmación">×</button>';
        document.body.append(panel);
        canvas = panel.querySelector('canvas'); fallback = panel.querySelector('span');
        context = canvas.getContext('2d', {willReadFrequently: true});
        panel.querySelector('button').onclick = close;
        video = document.createElement('video');
        video.src = '/static/media/confirmacion.mp4'; video.muted = true;
        video.playsInline = true; video.preload = 'auto';
    }
    function show(message) {
        try {
            create(); close(); const current = generation;
            (document.querySelector('dialog[open]') || document.body).append(panel);
            panel.querySelector('p').textContent = String(message);
            panel.style.animation = 'none'; panel.hidden = false; void panel.offsetWidth; panel.style.animation = ''; canvas.hidden = true; fallback.hidden = false;
            timer = setTimeout(close, 5000);
            if (reduced.matches || !context) return;
            video.currentTime = 0;
            const draw = () => {
                if (generation !== current || panel.hidden) return;
                if (video.readyState >= 2) {
                    context.clearRect(0, 0, 480, 270);
                    context.drawImage(video, 0, 0, 480, 270);
                    const pixels = context.getImageData(0, 0, 480, 270);
                    // El MP4 no admite transparencia: convertir el negro en alfa al dibujar.
                    for (let i = 0; i < pixels.data.length; i += 4) {
                        const level = Math.max(pixels.data[i], pixels.data[i+1], pixels.data[i+2]);
                        const alpha = Math.min(1, Math.max(0, (level - 65) / 40));
                        pixels.data[i+3] = Math.round(alpha * 255);
                    }
                    context.putImageData(pixels, 0, 0);
                    canvas.hidden = false; fallback.hidden = true;
                }
                if (!video.ended) frame = requestAnimationFrame(draw);
                else { canvas.hidden = true; fallback.hidden = false; }
            };
            video.play().then(() => { if (generation === current) draw(); }).catch(() => {});
        } catch (_) { /* La confirmación visual nunca debe interrumpir un guardado. */ }
    }
    function next(message, destination = location.href) {
        try { sessionStorage.setItem(key, JSON.stringify({message, path: new URL(destination, location.href).pathname, at: Date.now()})); } catch (_) {}
    }
    window.ServiConfirm = {show, next};
    document.addEventListener('DOMContentLoaded', () => {
        let message;
        try {
            const saved = JSON.parse(sessionStorage.getItem(key) || 'null');
            sessionStorage.removeItem(key);
            if (saved && saved.path === location.pathname && Date.now() - saved.at < 60000) message = saved.message;
            const cookie = document.cookie.split('; ').find(x => x.startsWith('servitech_exito='));
            if (cookie) {
                document.cookie = 'servitech_exito=; Max-Age=0; Path=/; SameSite=Lax';
                message = decodeURIComponent(cookie.slice('servitech_exito='.length));
            }
        } catch (_) {}
        if (message) show(message);
    });
    window.addEventListener('pagehide', close);
})();


