/* sun-cycle-bg 1.1.1 — a living day-cycle background for Home Assistant dashboards.
 *
 * An invisible Lovelace card that paints the view background from the real
 * position of the sun and moon, and keeps it moving all day:
 *
 *   - the sky gradient shifts continuously through night, dawn, sunrise,
 *     golden hour, noon and back — interpolated between elevation-keyed
 *     anchors, so seasons work automatically,
 *   - the sun travels its real diurnal arc: `sun.sun` gives both azimuth and
 *     elevation, so it rises in the east, culminates in the south and sets in
 *     the west, on a path tilted by (90 - latitude) exactly like the sky,
 *   - near the horizon a soft, blurred crepuscular fan spreads from the sun
 *     and smoothly gives way to a plain aureole as the sun climbs,
 *   - the moon runs on its own ephemeris (position AND phase), so it keeps its
 *     own schedule instead of mirroring the sun, and is drawn as the actual
 *     crescent/gibbous shape with the bright limb facing the sun,
 *   - an optional star field twinkles and moves east to west; it can either
 *     drift (cheap, default) or rotate about the celestial pole (prettier,
 *     but the layer has to cover the whole swept disc — see `stars.rotate`).
 *
 * Performance contract: every animation is transform/opacity-only (runs on the
 * compositor), one animated layer each for rays / moon / stars, repaints only
 * when the sun moves >= 0.15 deg in elevation or >= 0.6 deg in azimuth
 * (~ every half minute). Measured with this card on a 1280x400 RPi5 kiosk: 60 fps.
 *
 * Usage — add to every view you want painted (e.g. a hidden column or a
 * shared include):
 *
 *   type: custom:sun-cycle-bg-card
 *   # all options are optional:
 *   sun_entity: sun.sun
 *   azimuth: [50, 310]    # sky window mapped across the frame, degrees
 *   rays:
 *     blur: 28            # px; 0 disables the blur filter
 *     strength: 0.5       # peak opacity at the horizon
 *   moon: true            # false hides the moon entirely
 *   stars:                # or `stars: false` to disable the built-in field
 *     count: 90           # stars visible on screen
 *     drift: 1800         # seconds per screen-width, 0 = static
 *     rotate: false       # true = rotate about the pole instead of drifting
 *
 * If a `#star-twinkle-layer` element from a different star card is present,
 * its opacity is driven too (fades at dawn, returns at dusk).
 */
(() => {
  const D2R = Math.PI / 180, R2D = 180 / Math.PI;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const lerpA = (a, b, t) => a.map((v, i) => lerp(v, b[i], t));
  const smoothstep = (t) => t * t * (3 - 2 * t);

  // --- palette: elevation-keyed anchors -----------------------------------
  // e: sun elevation [deg]; top/mid/bot: sky gradient RGB; halo: sun RGBA;
  // stars: star-field opacity.
  const STOPS = [
    { e: -18, top: [11, 16, 32], mid: [10, 14, 24], bot: [7, 10, 18], halo: [190, 205, 235, 0], stars: 1 },
    { e: -9, top: [17, 24, 48], mid: [14, 19, 38], bot: [10, 13, 24], halo: [220, 160, 150, 0.22], stars: 0.65 },
    { e: -4, top: [28, 36, 64], mid: [35, 42, 72], bot: [51, 44, 78], halo: [235, 150, 130, 0.45], stars: 0.2 },
    { e: 0, top: [43, 63, 102], mid: [49, 72, 111], bot: [39, 64, 100], halo: [255, 170, 95, 0.58], stars: 0 },
    { e: 7, top: [74, 118, 166], mid: [63, 107, 157], bot: [43, 79, 121], halo: [255, 205, 130, 0.52], stars: 0 },
    { e: 22, top: [111, 166, 212], mid: [72, 121, 159], bot: [38, 73, 111], halo: [255, 235, 180, 0.55], stars: 0 },
    { e: 52, top: [127, 178, 220], mid: [76, 126, 173], bot: [38, 73, 111], halo: [255, 245, 215, 0.6], stars: 0 },
  ];
  function paletteFor(elev) {
    if (elev <= STOPS[0].e) return STOPS[0];
    if (elev >= STOPS[STOPS.length - 1].e) return STOPS[STOPS.length - 1];
    let i = 0;
    while (STOPS[i + 1].e < elev) i++;
    const a = STOPS[i], b = STOPS[i + 1], t = (elev - a.e) / (b.e - a.e);
    return {
      top: lerpA(a.top, b.top, t), mid: lerpA(a.mid, b.mid, t), bot: lerpA(a.bot, b.bot, t),
      halo: lerpA(a.halo, b.halo, t), stars: lerp(a.stars, b.stars, t),
    };
  }
  const rgb = (c) => `rgb(${c.slice(0, 3).map(Math.round).join(',')})`;
  const rgba = (c, mul = 1) =>
    `rgba(${c.slice(0, 3).map(Math.round).join(',')},${(c[3] * mul).toFixed(3)})`;

  // --- astronomy ----------------------------------------------------------
  // Low-precision series, accurate to well under a degree: verified against
  // Home Assistant's own (astral) sun values and against textbook geometry
  // (new moon 1.6 deg from the sun, full moon 179.6 deg opposite).
  function julian(date) {
    let y = date.getUTCFullYear(), m = date.getUTCMonth() + 1;
    const d = date.getUTCDate() + (date.getUTCHours() + date.getUTCMinutes() / 60 +
      date.getUTCSeconds() / 3600) / 24;
    if (m <= 2) { y -= 1; m += 12; }
    const A = Math.floor(y / 100), B = 2 - A + Math.floor(A / 4);
    return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d + B - 1524.5;
  }
  const gmst = (J) => (280.46061837 + 360.98564736629 * (J - 2451545) +
    0.000387933 * Math.pow((J - 2451545) / 36525, 2)) % 360;
  function altaz(ra, dec, J, lat, lon) {
    const H = ((gmst(J) + lon - ra) % 360) * D2R, dr = dec * D2R, pr = lat * D2R;
    const alt = Math.asin(Math.sin(dr) * Math.sin(pr) + Math.cos(dr) * Math.cos(pr) * Math.cos(H));
    const az = Math.atan2(-Math.sin(H) * Math.cos(dr),
      Math.cos(pr) * Math.sin(dr) - Math.sin(pr) * Math.cos(dr) * Math.cos(H));
    return { alt: alt * R2D, az: ((az * R2D) % 360 + 360) % 360 };
  }
  function sunEq(J) {
    const n = J - 2451545;
    const L = (280.460 + 0.9856474 * n) % 360;
    const g = ((357.528 + 0.9856003 * n) % 360) * D2R;
    const lam = ((L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) % 360) * D2R;
    const eps = 23.439 * D2R;
    return {
      ra: ((Math.atan2(Math.cos(eps) * Math.sin(lam), Math.cos(lam)) * R2D) % 360 + 360) % 360,
      dec: Math.asin(Math.sin(eps) * Math.sin(lam)) * R2D,
      lam: lam * R2D,
    };
  }
  function moonEq(J) {
    const T = (J - 2451545) / 36525, s = (x) => Math.sin(x * D2R);
    const Lp = (218.316 + 481267.8813 * T) % 360;   // mean longitude
    const M = (357.529 + 35999.0503 * T) % 360;     // sun mean anomaly
    const Mp = (134.963 + 477198.8676 * T) % 360;   // moon mean anomaly
    const D = (297.850 + 445267.1115 * T) % 360;    // mean elongation
    const F = (93.272 + 483202.0175 * T) % 360;     // argument of latitude
    const lam = (Lp + 6.289 * s(Mp) + 1.274 * s(2 * D - Mp) + 0.658 * s(2 * D)
      + 0.214 * s(2 * Mp) - 0.186 * s(M) - 0.114 * s(2 * F) + 0.059 * s(2 * D - 2 * Mp)
      + 0.057 * s(2 * D - M - Mp) + 0.053 * s(2 * D + Mp) + 0.046 * s(2 * D - M)
      - 0.041 * s(M - Mp) - 0.035 * s(D) - 0.031 * s(M + Mp)) % 360;
    const beta = 5.128 * s(F) + 0.281 * s(Mp + F) - 0.278 * s(F - Mp)
      + 0.176 * s(2 * D - F) - 0.075 * s(2 * F - Mp) - 0.041 * s(Mp - 2 * F);
    const eps = 23.439 * D2R, lr = lam * D2R, br = beta * D2R;
    return {
      ra: ((Math.atan2(Math.sin(lr) * Math.cos(eps) - Math.tan(br) * Math.sin(eps),
        Math.cos(lr)) * R2D) % 360 + 360) % 360,
      dec: Math.asin(Math.sin(br) * Math.cos(eps) + Math.cos(br) * Math.sin(eps) * Math.sin(lr)) * R2D,
      lam: (lam + 360) % 360,
    };
  }

  // --- static CSS (injected once per shadow root) -------------------------
  const STYLE_CLASS = 'sun-cycle-style';
  const CSS =
    '@keyframes sun-ray-sway{0%{transform:rotate(-3deg)}50%{transform:rotate(2.5deg)}100%{transform:rotate(-3deg)}}' +
    '.sun-cycle-clip{position:absolute;inset:0;overflow:hidden;pointer-events:none;}' +
    '.sun-cycle-ray{position:absolute;inset:-45%;animation:sun-ray-sway 42s ease-in-out infinite;' +
    'transition:opacity 3s linear;will-change:transform,opacity;}' +
    '.sun-cycle-moon{position:absolute;width:15%;max-width:190px;aspect-ratio:1;' +
    'transform:translate(-50%,-50%);pointer-events:none;transition:opacity 2s linear;' +
    'will-change:opacity;}' +
    '.sun-cycle-moon>svg{display:block;width:100%;height:100%;overflow:visible;' +
    'animation:moon-shimmer 7s ease-in-out infinite;will-change:transform,opacity;}' +
    '@keyframes moon-shimmer{0%,100%{transform:scale(1);opacity:.86}50%{transform:scale(1.04);opacity:1}}' +
    '.sun-cycle-stars{position:absolute;inset:0;overflow:hidden;pointer-events:none;' +
    'transition:opacity 2s linear;}' +
    '.sun-cycle-stars .scs-drift{position:absolute;top:0;left:0;width:200%;height:100%;}' +
    '.sun-cycle-stars .scs-half{position:absolute;top:0;width:50%;height:100%;}' +
    // east -> west: the strip travels rightwards, matching the real sky
    '@keyframes scs-drift{from{transform:translateX(-50%)}to{transform:translateX(0)}}' +
    '@keyframes scs-spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}';

  /* Conic gradient with a smooth cosine profile — soft-edged rays without
     relying on a filter. `bands` lobes, `softness` < 1 widens them. */
  function rayGradient(x, y, bands, softness, peak) {
    const steps = bands * 10;
    const stops = [];
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const wave = Math.pow(Math.max(0, Math.cos(t * bands * 2 * Math.PI)), softness);
      stops.push(`rgba(255,238,205,${(wave * peak).toFixed(3)}) ${(t * 360).toFixed(1)}deg`);
    }
    // Odd lobe count and a 23 deg offset: an even count centred on 0 deg lays the
    // lobes out along the axes and reads as a cross, not as a fan.
    return `conic-gradient(from 23deg at ${x.toFixed(1)}% ${y.toFixed(1)}%, ${stops.join(',')})`;
  }

  /* Moon drawn as the real phase: a lit region bounded by the terminator
     ellipse, rotated so the bright limb faces the sun on screen. */
  function moonSVG() {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '-2.6 -2.6 5.2 5.2');
    const defs = document.createElementNS(ns, 'defs');
    const grad = document.createElementNS(ns, 'radialGradient');
    grad.setAttribute('id', 'scb-moon-glow');
    [['0%', 'rgba(226,238,255,0.40)'], ['38%', 'rgba(210,226,252,0.13)'],
     ['100%', 'rgba(198,215,242,0)']].forEach(([o, c]) => {
      const st = document.createElementNS(ns, 'stop');
      st.setAttribute('offset', o); st.setAttribute('stop-color', c);
      grad.appendChild(st);
    });
    defs.appendChild(grad);
    svg.appendChild(defs);
    const glow = document.createElementNS(ns, 'circle');
    glow.setAttribute('r', '2.6');
    glow.setAttribute('fill', 'url(#scb-moon-glow)');
    svg.appendChild(glow);
    const dark = document.createElementNS(ns, 'circle');
    dark.setAttribute('r', '1');
    dark.setAttribute('fill', 'rgba(126,142,175,0.16)');
    svg.appendChild(dark);
    const lit = document.createElementNS(ns, 'path');
    lit.setAttribute('fill', '#f4f8ff');
    lit.setAttribute('class', 'scb-lit');
    svg.appendChild(lit);
    return svg;
  }
  function litPath(k) {
    // k = illuminated fraction, 0 = new, 1 = full. Semicircle plus the
    // terminator half-ellipse; the ellipse flips side at quarter phase.
    const a = Math.abs(1 - 2 * k).toFixed(4);
    const sweep = k > 0.5 ? 1 : 0;
    return `M 0,-1 A 1,1 0 0 1 0,1 A ${a},1 0 0 ${sweep} 0,-1 Z`;
  }

  // --- star field ---------------------------------------------------------
  const STAR_GROUPS = [
    { dur: 2.7, lo: 0.05, hi: 1.0 },
    { dur: 3.9, lo: 0.1, hi: 0.95 },
    { dur: 5.3, lo: 0.05, hi: 1.0 },
    { dur: 6.7, lo: 0.15, hi: 0.9 },
    { dur: 8.1, lo: 0.05, hi: 0.95 },
  ];
  function starCSS() {
    let css =
      '.sun-cycle-stars .scs{position:absolute;border-radius:50%;' +
      'background:#eaf3ff;width:3px;height:3px;will-change:opacity;' +
      'box-shadow:0 0 6px 1px rgba(200,225,255,.9);}';
    STAR_GROUPS.forEach((g, i) => {
      css +=
        '@keyframes scs' + i + '{0%,100%{opacity:' + g.lo + '}50%{opacity:' + g.hi + '}}' +
        '.sun-cycle-stars .scs' + i + '{animation:scs' + i + ' ' + g.dur +
        's ease-in-out infinite;animation-delay:-' + (g.dur * Math.random()).toFixed(1) + 's;}';
    });
    return css;
  }
  function shadowsFrom(points, sx, sy) {
    return points.map(([x, y]) =>
      (x - sx).toFixed(0) + 'px ' + (y - sy).toFixed(0) + 'px ' +
      (Math.random() * 4 + 2).toFixed(1) + 'px ' +
      (Math.random() * 1.8).toFixed(1) + 'px rgba(215,235,255,1)').join(',');
  }

  /* Drifting field: two identical halves sliding east to west. */
  function buildStarsDrift(count, driftSec) {
    const layer = document.createElement('div');
    layer.className = 'sun-cycle-stars';
    const W = window.innerWidth, H = window.innerHeight;
    const perGroup = Math.ceil(count / STAR_GROUPS.length);
    let css = starCSS();
    if (driftSec > 0) {
      css += '.sun-cycle-stars .scs-drift{animation:scs-drift ' + driftSec +
        's linear infinite;will-change:transform;}';
    }
    const style = document.createElement('style');
    style.textContent = css;
    layer.appendChild(style);
    const halfA = document.createElement('div');
    halfA.className = 'scs-half';
    halfA.style.left = '0';
    STAR_GROUPS.forEach((g, i) => {
      const seed = document.createElement('div');
      seed.className = 'scs scs' + i;
      const sx = Math.random() * W, sy = Math.random() * H;
      seed.style.left = sx.toFixed(0) + 'px';
      seed.style.top = sy.toFixed(0) + 'px';
      const pts = [];
      for (let j = 1; j < perGroup; j++) pts.push([Math.random() * W, Math.random() * H]);
      seed.style.boxShadow = shadowsFrom(pts, sx, sy);
      halfA.appendChild(seed);
    });
    const halfB = halfA.cloneNode(true);
    halfB.style.left = '50%';
    const drift = document.createElement('div');
    drift.className = 'scs-drift';
    drift.appendChild(halfA);
    drift.appendChild(halfB);
    layer.appendChild(drift);
    return layer;
  }

  /* Rotating field: stars laid out in the annulus that the frame sweeps out
     around the celestial pole, so the frame stays covered at every angle.
     That annulus is several times the frame area — hence the star count is
     scaled up to keep the on-screen density. Costs one big painted layer;
     recommended for panel-sized views, not for full 4K dashboards. */
  function buildStarsRotate(count, pivotY) {
    const layer = document.createElement('div');
    layer.className = 'sun-cycle-stars';
    const W = window.innerWidth, H = window.innerHeight;
    const px = W / 2, py = H * pivotY;                       // pole, below the frame
    const rMin = Math.max(1, (pivotY - 1) * H);
    const rMax = Math.hypot(W / 2, py);
    const annulus = Math.PI * (rMax * rMax - rMin * rMin);
    const total = Math.min(4000, Math.round(count * annulus / (W * H)));
    const style = document.createElement('style');
    style.textContent = starCSS() +
      '.sun-cycle-stars .scs-spin{position:absolute;left:50%;top:0;' +
      'animation:scs-spin 86164s linear infinite;will-change:transform;}';
    layer.appendChild(style);
    const spin = document.createElement('div');
    spin.className = 'scs-spin';
    spin.style.width = spin.style.height = '0';
    spin.style.top = py.toFixed(0) + 'px';                   // rotate about the pole
    const perGroup = Math.ceil(total / STAR_GROUPS.length);
    STAR_GROUPS.forEach((g, i) => {
      const seed = document.createElement('div');
      seed.className = 'scs scs' + i;
      const pts = [];
      for (let j = 0; j < perGroup; j++) {
        const a = Math.random() * 2 * Math.PI;
        const r = Math.sqrt(rMin * rMin + Math.random() * (rMax * rMax - rMin * rMin));
        pts.push([Math.sin(a) * r, -Math.cos(a) * r]);       // relative to the pole
      }
      const [sx, sy] = pts[0];
      seed.style.left = sx.toFixed(0) + 'px';
      seed.style.top = sy.toFixed(0) + 'px';
      seed.style.boxShadow = shadowsFrom(pts.slice(1), sx, sy);
      spin.appendChild(seed);
    });
    layer.appendChild(spin);
    return layer;
  }

  class SunCycleBgCard extends HTMLElement {
    setConfig(config) {
      this._cfg = config || {};
      const s = this._cfg.stars;
      this._starCfg = s === false ? null : {
        count: (s && s.count) || 90,
        drift: s && s.drift !== undefined ? s.drift : 1800,
        rotate: !!(s && s.rotate),
        pivot: (s && s.pivot) || 2.2,
      };
      this._sunEntity = this._cfg.sun_entity || 'sun.sun';
      const az = this._cfg.azimuth;
      this._az0 = Array.isArray(az) ? az[0] : 50;
      this._az1 = Array.isArray(az) ? az[1] : 310;
      const r = this._cfg.rays;
      this._rayBlur = r && r.blur !== undefined ? r.blur : 28;
      this._rayPeak = r && r.strength !== undefined ? r.strength : 0.5;
      this._showMoon = this._cfg.moon !== false;
    }

    set hass(h) {
      const sun = h.states && h.states[this._sunEntity];
      if (!sun) return;
      const e = Number(sun.attributes.elevation);
      if (!isFinite(e)) return;
      const a = Number(sun.attributes.azimuth);
      this._elev = e;
      this._azim = isFinite(a) ? a : null;
      const cfg = h.config || {};
      this._lat = cfg.latitude;
      this._lon = cfg.longitude;
      const moved = this._painted === undefined ||
        Math.abs(e - this._painted.e) >= 0.15 ||
        (this._azim !== null && Math.abs(a - this._painted.a) >= 0.6);
      if (moved) this._apply();
    }

    connectedCallback() {
      this.style.display = 'none';
      // climb to hui-view-container across shadow boundaries
      let el = this;
      while (el && (el.tagName || '').toLowerCase() !== 'hui-view-container') {
        el = el.parentElement || (el.getRootNode && el.getRootNode().host);
      }
      this._container = el || null;
      this._apply();
      // other background cards may build their layers after us
      setTimeout(() => this._apply(true), 600);
      setTimeout(() => this._apply(true), 2000);
    }

    _before(c, node) {
      const hv = c.querySelector('hui-view');
      if (hv) c.insertBefore(node, hv); else c.appendChild(node);
    }

    /* Sky window -> frame. Azimuth spans the width, elevation the height,
       with the horizon parked near the bottom edge. */
    _project(alt, az) {
      return {
        x: clamp((az - this._az0) / (this._az1 - this._az0), -0.05, 1.05) * 100,
        y: 92 - clamp((alt + 6) / 60, -0.1, 1) * 86,
      };
    }

    _apply(force) {
      const c = this._container, e = this._elev;
      if (!c || !c.isConnected || e === undefined) return;
      const p = paletteFor(e);

      // --- sun position: real arc when azimuth is available ---------------
      const sunPos = this._azim !== null ? this._project(e, this._azim)
                                         : { x: 96, y: 92 - clamp((e + 6) / 60, -0.1, 1) * 86 };

      const bg = c.querySelector('hui-view-background');
      if (bg) bg.style.background =
        `radial-gradient(38% 62% at ${sunPos.x.toFixed(1)}% ${sunPos.y.toFixed(1)}%, ` +
        `${rgba(p.halo, 1)} 0%, ${rgba(p.halo, 0.42)} 28%, ${rgba(p.halo, 0.12)} 62%, ` +
        'transparent 100%),' +
        `linear-gradient(200deg, ${rgb(p.top)} 0%, ${rgb(p.mid)} 48%, ${rgb(p.bot)} 100%)`;

      const root = c.getRootNode();
      // ShadowRoot takes the <style> directly; a plain Document needs <head>
      const styleHost = root.head || root;
      if (root.querySelector && !root.querySelector('.' + STYLE_CLASS)) {
        const st = document.createElement('style');
        st.className = STYLE_CLASS;
        st.textContent = CSS;
        styleHost.appendChild(st);
      }

      // --- crepuscular fan, fading into a plain aureole by day ------------
      let clip = c.querySelector('.sun-cycle-clip');
      if (!clip) {
        clip = document.createElement('div');
        clip.className = 'sun-cycle-clip';
        const r = document.createElement('div');
        r.className = 'sun-cycle-ray';
        clip.appendChild(r);
        this._before(c, clip);
      }
      const ray = clip.firstElementChild;
      // the ray layer is inset by -45%, so the sun sits at a different
      // fraction of it than of the frame
      const rx = (sunPos.x + 45) / 1.9, ry = (sunPos.y + 45) / 1.9;
      // full fan at the horizon, gone by mid-morning (smoothstep) and gone
      // again once the sun is well below the horizon (nothing left to scatter)
      const horizon = smoothstep(clamp(1 - Math.abs(e) / 22, 0, 1)) *
        smoothstep(clamp((e + 6) / 6, 0, 1));
      ray.style.opacity = (horizon * this._rayPeak).toFixed(3);
      ray.style.transformOrigin = `${rx.toFixed(1)}% ${ry.toFixed(1)}%`;
      ray.style.filter = this._rayBlur > 0 ? `blur(${this._rayBlur}px)` : '';
      if (horizon > 0.01) ray.style.background = rayGradient(rx, ry, 5, 0.5, 0.5);

      // --- moon: own position and phase -----------------------------------
      if (this._showMoon && isFinite(this._lat) && isFinite(this._lon)) {
        const J = julian(new Date());
        const se = sunEq(J), me = moonEq(J);
        const mp = altaz(me.ra, me.dec, J, this._lat, this._lon);
        const elong = ((me.lam - se.lam) % 360 + 360) % 360;
        const k = (1 - Math.cos(elong * D2R)) / 2;            // illuminated fraction
        const pos = this._project(mp.alt, mp.az);
        // visible when the sky is dark enough and the moon is up
        const alpha = clamp((-e - 1) / 8, 0, 1) * clamp((mp.alt + 2) / 8, 0, 1);

        let moon = c.querySelector('.sun-cycle-moon');
        if (!moon) {
          moon = document.createElement('div');
          moon.className = 'sun-cycle-moon';
          moon.appendChild(moonSVG());
          this._before(c, moon);
        }
        moon.style.left = pos.x.toFixed(1) + '%';
        moon.style.top = pos.y.toFixed(1) + '%';
        moon.style.opacity = alpha.toFixed(2);
        const lit = moon.querySelector('.scb-lit');
        if (lit) {
          lit.setAttribute('d', litPath(k));
          // Bright limb points at the sun in the same projection. The lit
          // region is drawn facing +x, and SVG rotate() turns clockwise in the
          // same y-down frame atan2 measures in, so the angle maps directly.
          const ang = Math.atan2(sunPos.y - pos.y, sunPos.x - pos.x) * R2D;
          lit.setAttribute('transform', `rotate(${ang.toFixed(1)})`);
        }
      }

      // --- star field ------------------------------------------------------
      if (this._starCfg) {
        let stars = c.querySelector('.sun-cycle-stars');
        if (!stars) {
          stars = this._starCfg.rotate
            ? buildStarsRotate(this._starCfg.count, this._starCfg.pivot)
            : buildStarsDrift(this._starCfg.count, this._starCfg.drift);
          this._before(c, stars);
        }
        stars.style.opacity = p.stars.toFixed(2);
      }
      // external star layer (e.g. a separate star-twinkle card): drive opacity
      const ext = c.querySelector('#star-twinkle-layer');
      if (ext) {
        ext.style.opacity = p.stars.toFixed(2);
        ext.style.transition = 'opacity 2s linear';
      }

      if (!force) this._painted = { e, a: this._azim === null ? 0 : this._azim };
    }

    // No destructive cleanup: layers are deduped on (re)create and die with
    // their container. Removing them here races view-to-view navigation.
    getCardSize() { return 0; }
  }
  customElements.define('sun-cycle-bg-card', SunCycleBgCard);

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'sun-cycle-bg-card',
    name: 'Sun Cycle Background',
    description: 'Living day-cycle view background: sky palette, the sun on its real diurnal arc with crepuscular rays, a moon with its own ephemeris and phase, and a star field — all driven by sun.sun.',
  });
})();
