/* sun-cycle-bg — a living day-cycle background for Home Assistant dashboards.
 *
 * An invisible Lovelace card that paints the view background from the real
 * position of the sun (`sun.sun` elevation) and keeps it moving all day:
 *
 *   - the sky gradient shifts continuously through night, dawn, sunrise,
 *     golden hour, noon and back — interpolated between elevation-keyed
 *     anchors, so seasons work automatically,
 *   - the sun is a warm halo that literally rises from below the frame edge,
 *     climbs to the top by noon and sets in reverse (gone at night),
 *   - animated sun rays sway gently, brightness follows the sun,
 *   - after sunset a silver moon with a soft shimmer rises on the left,
 *   - an optional star field twinkles AND drifts across the sky
 *     (rising at the right edge, setting at the left, seamless wrap).
 *
 * Performance contract: every animation is transform/opacity-only (runs on
 * the compositor), one animated layer each for rays / moon / stars, repaints
 * only when sun elevation moves >= 0.15 deg (~ every 30 s). Measured cost on
 * a wall-tablet kiosk: within noise.
 *
 * Usage — add to every view you want painted (e.g. a hidden column or a
 * shared include):
 *
 *   type: custom:sun-cycle-bg-card
 *   # all options are optional:
 *   sun_entity: sun.sun
 *   stars:                # or `stars: false` to disable the built-in field
 *     count: 90           # total stars
 *     drift: 1800         # seconds per screen-width of drift, 0 = static
 *
 * If a `#star-twinkle-layer` element from a different star card is present,
 * its opacity is driven too (fades at dawn, returns at dusk).
 */
(() => {
  // --- palette: elevation-keyed anchors -----------------------------------
  // e: sun elevation [deg]; top/mid/bot: sky gradient RGB; halo: sun RGBA;
  // ray: ray opacity; stars: star opacity; hy: sun halo Y [% of viewport,
  // >100 = below frame]; ma/my: moon alpha / moon Y.
  const STOPS = [
    { e: -18, top: [11, 16, 32], mid: [10, 14, 24], bot: [7, 10, 18], halo: [190, 205, 235, 0], ray: 0, stars: 1, hy: 118, ma: 1, my: 24 },
    { e: -9, top: [17, 24, 48], mid: [14, 19, 38], bot: [10, 13, 24], halo: [220, 160, 150, 0.22], ray: 0, stars: 0.65, hy: 108, ma: 0.85, my: 46 },
    { e: -4, top: [28, 36, 64], mid: [35, 42, 72], bot: [51, 44, 78], halo: [235, 150, 130, 0.45], ray: 0.08, stars: 0.2, hy: 96, ma: 0.45, my: 74 },
    { e: 0, top: [43, 63, 102], mid: [49, 72, 111], bot: [39, 64, 100], halo: [255, 170, 95, 0.58], ray: 0.25, stars: 0, hy: 80, ma: 0, my: 98 },
    { e: 7, top: [74, 118, 166], mid: [63, 107, 157], bot: [43, 79, 121], halo: [255, 205, 130, 0.52], ray: 0.6, stars: 0, hy: 52, ma: 0, my: 112 },
    { e: 22, top: [111, 166, 212], mid: [72, 121, 159], bot: [38, 73, 111], halo: [255, 235, 180, 0.55], ray: 0.92, stars: 0, hy: 16, ma: 0, my: 112 },
    { e: 52, top: [127, 178, 220], mid: [76, 126, 173], bot: [38, 73, 111], halo: [255, 245, 215, 0.6], ray: 1, stars: 0, hy: -10, ma: 0, my: 112 },
  ];
  const lerp = (a, b, t) => a + (b - a) * t;
  const lerpA = (a, b, t) => a.map((v, i) => lerp(v, b[i], t));
  function paletteFor(elev) {
    if (elev <= STOPS[0].e) return STOPS[0];
    if (elev >= STOPS[STOPS.length - 1].e) return STOPS[STOPS.length - 1];
    let i = 0;
    while (STOPS[i + 1].e < elev) i++;
    const a = STOPS[i], b = STOPS[i + 1], t = (elev - a.e) / (b.e - a.e);
    return {
      top: lerpA(a.top, b.top, t), mid: lerpA(a.mid, b.mid, t), bot: lerpA(a.bot, b.bot, t),
      halo: lerpA(a.halo, b.halo, t), ray: lerp(a.ray, b.ray, t),
      stars: lerp(a.stars, b.stars, t), hy: lerp(a.hy, b.hy, t),
      ma: lerp(a.ma, b.ma, t), my: lerp(a.my, b.my, t),
    };
  }
  const rgb = (c) => `rgb(${c.slice(0, 3).map(Math.round).join(',')})`;
  const rgba = (c) => `rgba(${c.slice(0, 3).map(Math.round).join(',')},${c[3].toFixed(2)})`;

  // --- static CSS (injected once per shadow root) -------------------------
  const STYLE_CLASS = 'sun-cycle-style';
  const CSS =
    '@keyframes sun-ray-sway{0%{transform:rotate(-4deg)}50%{transform:rotate(3deg)}100%{transform:rotate(-4deg)}}' +
    '.sun-cycle-clip{position:absolute;inset:0;overflow:hidden;pointer-events:none;' +
    '-webkit-mask-image:linear-gradient(200deg,black 40%,rgba(0,0,0,.55) 68%,transparent 92%);' +
    'mask-image:linear-gradient(200deg,black 40%,rgba(0,0,0,.55) 68%,transparent 92%);}' +
    '.sun-cycle-ray{position:absolute;inset:-35%;animation:sun-ray-sway 24s ease-in-out infinite;' +
    'transition:opacity 2s linear;will-change:transform,opacity;}' +
    '.sun-cycle-moon{position:absolute;left:13%;width:17%;aspect-ratio:1;transform:translate(-50%,-50%);' +
    'pointer-events:none;transition:opacity 2s linear;}' +
    '.sun-cycle-moon>i{position:absolute;inset:0;border-radius:50%;display:block;' +
    'background:radial-gradient(circle, rgba(250,252,255,1) 0%, rgba(240,246,255,.95) 7%, rgba(222,233,250,.45) 13%, rgba(198,215,242,.20) 30%, rgba(182,202,236,.08) 48%, transparent 66%);' +
    'animation:moon-shimmer 7s ease-in-out infinite;will-change:transform,opacity;}' +
    '@keyframes moon-shimmer{0%,100%{transform:scale(1);opacity:.82}50%{transform:scale(1.05);opacity:1}}' +
    '.sun-cycle-stars{position:absolute;inset:0;overflow:hidden;pointer-events:none;transition:opacity 2s linear;}' +
    '.sun-cycle-stars .scs-drift{position:absolute;top:0;left:0;width:200%;height:100%;}' +
    '.sun-cycle-stars .scs-half{position:absolute;top:0;width:50%;height:100%;}' +
    '@keyframes scs-drift{from{transform:translateX(0)}to{transform:translateX(-50%)}}';

  // --- built-in star field: 5 seed dots + box-shadow stars, twinkle via
  // group opacity, drift via one translateX loop (all compositor-side) ------
  const STAR_GROUPS = [
    { dur: 2.7, lo: 0.05, hi: 1.0 },
    { dur: 3.9, lo: 0.1, hi: 0.95 },
    { dur: 5.3, lo: 0.05, hi: 1.0 },
    { dur: 6.7, lo: 0.15, hi: 0.9 },
    { dur: 8.1, lo: 0.05, hi: 0.95 },
  ];
  function buildStars(count, driftSec) {
    const layer = document.createElement('div');
    layer.className = 'sun-cycle-stars';
    const W = window.innerWidth, H = window.innerHeight;
    const perGroup = Math.ceil(count / STAR_GROUPS.length);
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
      const shadows = [];
      for (let j = 1; j < perGroup; j++) {
        const x = (Math.random() * W - sx).toFixed(0);
        const y = (Math.random() * H - sy).toFixed(0);
        const blur = (Math.random() * 4 + 2).toFixed(1);
        const spread = (Math.random() * 1.8).toFixed(1);
        shadows.push(x + 'px ' + y + 'px ' + blur + 'px ' + spread + 'px rgba(215,235,255,1)');
      }
      seed.style.boxShadow = shadows.join(',');
      halfA.appendChild(seed);
    });
    // second identical copy at 50% => seamless wrap while the strip drifts
    const halfB = halfA.cloneNode(true);
    halfB.style.left = '50%';
    const drift = document.createElement('div');
    drift.className = 'scs-drift';
    drift.appendChild(halfA);
    drift.appendChild(halfB);
    layer.appendChild(drift);
    return layer;
  }

  class SunCycleBgCard extends HTMLElement {
    setConfig(config) {
      this._cfg = config || {};
      const s = this._cfg.stars;
      this._starCfg = s === false ? null : {
        count: (s && s.count) || 90,
        drift: s && s.drift !== undefined ? s.drift : 1800,
      };
      this._sunEntity = this._cfg.sun_entity || 'sun.sun';
    }

    set hass(h) {
      const sun = h.states && h.states[this._sunEntity];
      if (!sun) return;
      const e = Number(sun.attributes.elevation);
      if (!isFinite(e)) return;
      this._elev = e;
      // repaint only on meaningful movement (~0.15 deg) or first run
      if (this._painted === undefined || Math.abs(e - this._painted) >= 0.15) this._apply();
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

    _apply(force) {
      const c = this._container, e = this._elev;
      if (!c || !c.isConnected || e === undefined) return;
      const p = paletteFor(e);
      const hy = p.hy;

      const bg = c.querySelector('hui-view-background');
      if (bg) bg.style.background =
        `radial-gradient(44% 48% at 96% ${hy.toFixed(1)}%, ${rgba(p.halo)} 0%, ` +
        `${rgba([p.halo[0], p.halo[1], p.halo[2], p.halo[3] * 0.45])} 35%, transparent 72%),` +
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

      // sun rays (clipped so the sway never grows the page)
      let clip = c.querySelector('.sun-cycle-clip');
      if (!clip) {
        clip = document.createElement('div');
        clip.className = 'sun-cycle-clip';
        const ray = document.createElement('div');
        ray.className = 'sun-cycle-ray';
        clip.appendChild(ray);
        this._before(c, clip);
      }
      const ray = clip.firstElementChild;
      const oy = (15 + hy * 0.35).toFixed(1);
      ray.style.opacity = p.ray.toFixed(2);
      ray.style.transformOrigin = `79% ${oy}%`;
      ray.style.background =
        `conic-gradient(from 168deg at 79% ${oy}%,` +
        'transparent 0deg, rgba(255,250,222,.32) 10deg, transparent 21deg,' +
        'transparent 27deg, rgba(255,250,222,.20) 36deg, transparent 46deg,' +
        'transparent 52deg, rgba(255,250,222,.13) 61deg, transparent 71deg)';

      // moon
      let moon = c.querySelector('.sun-cycle-moon');
      if (!moon) {
        moon = document.createElement('div');
        moon.className = 'sun-cycle-moon';
        moon.appendChild(document.createElement('i'));
        this._before(c, moon);
      }
      moon.style.top = p.my.toFixed(1) + '%';
      moon.style.opacity = p.ma.toFixed(2);

      // built-in star field (optional)
      if (this._starCfg) {
        let stars = c.querySelector('.sun-cycle-stars');
        if (!stars) {
          stars = buildStars(this._starCfg.count, this._starCfg.drift);
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

      if (!force) this._painted = e;
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
    description: 'Living day-cycle view background: sky palette, rising/setting sun with rays, a shimmering moon and a drifting star field, all driven by sun.sun.',
  });
})();
