// Header banner: an abstract sky. Black at the top through teal to a peach glow,
// a halftone dot band near the bottom, and a scatter of stars.
(function () {
    const svg = document.getElementById('scene');
    if (!svg) return;
    const NS = 'http://www.w3.org/2000/svg';
    const W = 1200, H = 200;
    const C = { peach: '#F7C4A0', paper: '#F3E7D3' };

    let seed = 11;
    const rnd = () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const f = n => Math.round(n * 10) / 10;

    function el(tag, attrs = {}, parent = svg) {
        const e = document.createElementNS(NS, tag);
        for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
        parent.appendChild(e);
        return e;
    }

    const defs = el('defs');
    const grad = (id, stops) => {
        const g = el('linearGradient', { id, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
        stops.forEach(([o, c, op = 1]) => el('stop', { offset: o, 'stop-color': c, 'stop-opacity': op }, g));
    };
    grad('sky', [[0, '#000000'], [0.3, '#07202a'], [0.55, '#0C3440'], [0.75, '#1F7A80'], [0.92, '#E9B99A'], [1, '#F4A68A']]);
    grad('fade', [[0, '#fff', 0], [0.5, '#fff', 0], [1, '#fff', 0.45]]);
    const dots = el('pattern', { id: 'halftone', width: 7, height: 7, patternUnits: 'userSpaceOnUse' }, defs);
    el('circle', { cx: 3.5, cy: 3.5, r: 1.2, fill: C.peach }, dots);
    const mask = el('mask', { id: 'halftone-mask' }, defs);
    el('rect', { width: W, height: H, fill: 'url(#fade)' }, mask);

    el('rect', { width: W, height: H, fill: 'url(#sky)' });
    el('rect', { width: W, height: H, fill: 'url(#halftone)', mask: 'url(#halftone-mask)' });
    for (let i = 0; i < 55; i++) {
        el('circle', { cx: f(rnd() * W), cy: f(rnd() * rnd() * 125), r: f(0.6 + rnd()), fill: C.paper, opacity: f(0.45 + rnd() * 0.5) });
    }
})();
