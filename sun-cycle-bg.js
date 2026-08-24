/* sun-cycle-bg 1.3.0 — a living day-cycle background for Home Assistant dashboards.
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
 *   - the twilight glow stays where it belongs: a wide, flat band along the
 *     horizon centred on the sun's azimuth, instead of an oval riding along
 *     with the disc and sliding off the bottom edge after sunset,
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
 *   twilight_palette: false   # true = warmer amber dusk anchors instead of mauve
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
 *   # Optional: draw the discs from your own artwork instead of the render.
 *   # Both are independent; whatever is left out keeps the drawn version. The
 *   # images are NOT shipped with the card — point these at your own files
 *   # (e.g. /local/...), so the card carries no third-party artwork.
 *   sun_image: /local/sun-cycle/sun.png
 *   sun_image_width: 10.5   # disc diameter, % of the view width
 *   sun_image_blur: 11.5    # % of that diameter; 0 = none. A sharp disc reads
 *                           # as a sticker pasted on the sky.
 *   sun_image_disc: [0.789, 0.508, 0.485]   # see below
 *   moon_image: /local/sun-cycle/moon.png
 *   moon_image_width: 13
 *   moon_image_disc: [0.429, 0.5, 0.5]
 *
 * `*_image_disc` is [diameter / image width, cx / image width, cy / image
 * height] — where the disc actually sits inside the file. It matters because
 * artwork rarely fills its frame: a sun render carries rays sticking out on one
 * side, a moon render carries a baked glow, and placing such a file by its own
 * centre puts the disc beside its aureole. Measure it from the alpha channel.
 * Default [1, 0.5, 0.5] = the disc fills a square image.
 *
 * The sun disc has no drawn counterpart — without `sun_image` the sun is the
 * aureole and the ray fan, as before. It fades out below -3 deg elevation:
 * the projection parks anything under the horizon on the bottom edge rather
 * than pushing it out of frame, so an un-faded disc would sit there all night.
 * The moon image is clipped by the terminator, so the phase still shows and the
 * artwork serves as the texture of the lit part. Both discs are graded to the
 * sky palette (the sun reddens and dims towards the horizon, the moon pales at
 * dusk) so they do not read as pasted on.
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
  // Opt-in warmer dusk: the default anchors drift into mauve around -4 deg,
  // which reads grey once the glow spreads along the horizon.
  const WARM_DUSK = { '-9': [235, 120, 86, 0.26], '-4': [252, 138, 84, 0.50], '0': [255, 168, 88, 0.60] };
  function paletteFor(elev, warmDusk) {
    const TABLE = warmDusk
      ? STOPS.map((s) => (WARM_DUSK[String(s.e)] ? { ...s, halo: WARM_DUSK[String(s.e)] } : s))
      : STOPS;
    return paletteFrom(TABLE, elev);
  }
  function paletteFrom(STOPS, elev) {
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
    // The sun disc exists only when `sun_image` is set; it carries a blur
    // filter, so no transform animation rides on it (re-filtering every frame
    // is exactly what the performance contract is there to avoid).
    '.sun-cycle-sun{position:absolute;pointer-events:none;transition:opacity 2s linear;' +
    'will-change:opacity;}' +
    '.sun-cycle-sun>img{display:block;width:100%;height:auto;}' +
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

  /* Where the disc actually sits inside a supplied image, as fractions:
     [diameter / width, cx / width, cy / height]. Artwork rarely fills its
     frame — a sun render has rays sticking out on one side, a moon render has
     a baked glow — and placing such a file by its own centre puts the disc
     beside its aureole. */
  function discSpec(v) {
    const a = Array.isArray(v) ? v : [];
    const n = (x, def) => (isFinite(x) && Number(x) > 0 ? Number(x) : def);
    return { dia: n(a[0], 1), cx: isFinite(a[1]) ? Number(a[1]) : 0.5,
             cy: isFinite(a[2]) ? Number(a[2]) : 0.5 };
  }

  /* Moon drawn as the real phase: a lit region bounded by the terminator
     ellipse, rotated so the bright limb faces the sun on screen. With `img`
     the same terminator becomes a clip path and the artwork is the lit
     texture — the mask turns towards the sun while the image counter-rotates,
     so the maria stay upright. `ar` is the image's height/width. */
  function moonSVG(img, disc, ar) {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '-2.6 -2.6 5.2 5.2');
    svg.dataset.mode = img ? 'image' : 'drawn';
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
    lit.setAttribute('class', 'scb-lit');
    if (!img) {
      lit.setAttribute('fill', '#f4f8ff');
      svg.appendChild(lit);
      return svg;
    }
    // The terminator becomes a clip path instead of a filled shape.
    const clip = document.createElementNS(ns, 'clipPath');
    clip.setAttribute('id', 'scb-moon-clip');
    clip.appendChild(lit);
    defs.appendChild(clip);
    // Map the file onto the unit circle: the disc, not the frame, has to land
    // on r = 1, and the disc is generally off-centre in the file.
    const w = 2 / disc.dia, h = w * ar;
    const im = document.createElementNS(ns, 'image');
    im.setAttribute('href', img);
    im.setAttribute('x', (-w * disc.cx).toFixed(4));
    im.setAttribute('y', (-h * disc.cy).toFixed(4));
    im.setAttribute('width', w.toFixed(4));
    im.setAttribute('height', h.toFixed(4));
    const spin = document.createElementNS(ns, 'g');   // turns towards the sun
    spin.setAttribute('class', 'scb-spin');
    const hold = document.createElementNS(ns, 'g');   // keeps the maria upright
    hold.setAttribute('class', 'scb-hold');
    hold.appendChild(im);
    const clipped = document.createElementNS(ns, 'g');
    clipped.setAttribute('clip-path', 'url(#scb-moon-clip)');
    clipped.appendChild(hold);
    spin.appendChild(clipped);
    svg.appendChild(spin);
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
      this._warmDusk = this._cfg.twilight_palette === true;

      // --- optional artwork for the two discs ----------------------------
      const num = (v, def) => (isFinite(v) ? Number(v) : def);
      this._sunImg = typeof this._cfg.sun_image === 'string' ? this._cfg.sun_image : null;
      this._sunImgW = num(this._cfg.sun_image_width, 10.5);
      this._sunImgBlur = num(this._cfg.sun_image_blur, 11.5);
      this._sunDisc = discSpec(this._cfg.sun_image_disc);
      this._moonImg = typeof this._cfg.moon_image === 'string' ? this._cfg.moon_image : null;
      this._moonImgW = num(this._cfg.moon_image_width, 0);
      this._moonDisc = discSpec(this._cfg.moon_image_disc);
      // The moon SVG needs the file's aspect ratio to place the <image>, and
      // that is only known once the file is decoded. Until then the drawn moon
      // stays up; the repaint on load swaps it in.
      this._moonAR = null;
      if (this._moonImg) {
        const probe = new Image();
        probe.onload = () => {
          if (probe.naturalWidth > 0) {
            this._moonAR = probe.naturalHeight / probe.naturalWidth;
            this._apply(true);
          }
        };
        probe.src = this._moonImg;
      }
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

    // --- ink polarity -----------------------------------------------------
    // The card already owns the only number that says how bright the view is
    // about to be, so it also publishes the ink colour the cards should use.
    // Custom properties inherit through shadow DOM, so one setter on the root
    // reaches every button-card on every view without touching their code.
    //
    // Threshold measured, not chosen: interpolating the STOPS table above and
    // scoring WCAG 2.1 against the brightest stop, the light second plane
    // (#9A9384) crosses 4.5 at about +5 deg of elevation. Hysteresis of one
    // degree either side keeps it from flapping while the sun sits on the
    // boundary.
    _inkVars(e) {
      const byl = this._inkDark === true;
      const teraz = byl ? e > 4 : e >= 6;
      const root = document.documentElement;
      if (this._inkDark === teraz) return;
      this._inkDark = teraz;
      // Dzien NIE odwraca pisma na ciemne: uzytkownik chce jasnego. Biel to
      // zmierzony sufit jasnego tuszu na tym tle (2.81 na najjasniejszym
      // punkcie pod kolumnami, wobec 2.29 dla kinari), wiec samo rozjasnienie
      // nie wystarcza — dochodzi cien pod literami. Cien nie jest podkladka
      // pod kafel: nie zmienia tla karty, tylko rysunek glifu. WCAG cieni nie
      // punktuje, wiec liczba kontrastu zostaje niska mimo realnej poprawy
      // czytelnosci — to jest zapisane wprost, zeby nikt nie czytal 2.81 jako
      // 'zdaje'.
      const zestaw = teraz
        ? { tusz: '#FFFFFF', tuszRgb: '255,255,255',
            tusz2: '#E9EDF1', tusz2Rgb: '233,237,241',
            akcent: '#FF9A78', akcentRgb: '255,154,120',
            bursztyn: '#FFD166', zielen: '#86EFAC',
            cien: '0 1px 2px rgba(6,12,22,.9), 0 0 10px rgba(6,12,22,.6)' }
        : { tusz: '#EFE7D9', tuszRgb: '239,231,217',
            tusz2: '#9A9384', tusz2Rgb: '154,147,132',
            akcent: '#B14A30', akcentRgb: '177,74,48',
            bursztyn: '#fbbf24', zielen: '#4ade80',
            cien: 'none' };
      root.style.setProperty('--jrx-tusz', zestaw.tusz);
      root.style.setProperty('--jrx-tusz-rgb', zestaw.tuszRgb);
      root.style.setProperty('--jrx-tusz2', zestaw.tusz2);
      root.style.setProperty('--jrx-tusz2-rgb', zestaw.tusz2Rgb);
      root.style.setProperty('--jrx-akcent', zestaw.akcent);
      root.style.setProperty('--jrx-akcent-rgb', zestaw.akcentRgb);
      root.style.setProperty('--jrx-bursztyn', zestaw.bursztyn);
      root.style.setProperty('--jrx-zielen', zestaw.zielen);
      root.style.setProperty('--jrx-cien', zestaw.cien);
      root.setAttribute('data-jrx-pismo', teraz ? 'dzien' : 'noc');
    }

    _apply(force) {
      const c = this._container, e = this._elev;
      if (!c || !c.isConnected || e === undefined) return;
      const p = paletteFor(e, this._warmDusk);
      this._inkVars(e);

      // --- sun position: real arc when azimuth is available ---------------
      const sunPos = this._azim !== null ? this._project(e, this._azim)
                                         : { x: 96, y: 92 - clamp((e + 6) / 60, -0.1, 1) * 86 };

      // --- twilight glow ---------------------------------------------------
      // The scattered light of dusk belongs to the horizon, not to the disc:
      // a wide, flat band centred on the sun's azimuth at the bottom edge. It
      // widens as the sun sinks (light scatters along the whole horizon) and
      // fades out by roughly -15 deg, before its centre can drift off-frame.
      // The disc keeps its own aureole, which grows back to the full daytime
      // 38% x 62% above ~14 deg — so full daylight looks exactly as before.
      const u = clamp(1 - (e + 8) / 20, 0, 1);
      const bandW = 70 + 120 * u, bandH = 26 + 16 * u;
      const bandA = smoothstep(clamp(1 - Math.abs(e + 1) / 14, 0, 1));
      const discA = smoothstep(clamp((e + 2) / 8, 0, 1));
      const day = smoothstep(clamp((e - 2) / 12, 0, 1));
      const dw = lerp(26, 38, day), dh = lerp(46, 62, day);
      const sx = sunPos.x.toFixed(1), sy = sunPos.y.toFixed(1);

      const bg = c.querySelector('hui-view-background');
      if (bg) bg.style.background =
        `radial-gradient(${bandW.toFixed(0)}% ${bandH.toFixed(0)}% at ${sx}% 100%, ` +
        `${rgba(p.halo, 0.85 * bandA)} 0%, ${rgba(p.halo, 0.32 * bandA)} 38%, ` +
        `${rgba(p.halo, 0.07 * bandA)} 70%, transparent 100%),` +
        `radial-gradient(${dw.toFixed(0)}% ${dh.toFixed(0)}% at ${sx}% ${sy}%, ` +
        `${rgba(p.halo, discA)} 0%, ` +
        `${rgba(p.halo, lerp(0.35, 0.42, day) * discA)} ${(28 * lerp(0.74, 1, day)).toFixed(0)}%, ` +
        `${rgba(p.halo, 0.12 * discA * day)} 62%, transparent 100%),` +
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
      // A fan faded to nothing is not free: the element keeps its sway
      // animation, `will-change: transform` and a blur filter, so the
      // compositor holds a full-viewport layer for it all night — and promotes
      // everything painted above it to its own layer for overlap. Measured at
      // night on a 1920x1080 panel: 44 MB for the invisible fan alone. Take it
      // out of the tree instead.
      const rayVisible = horizon > 0.01;
      ray.style.display = rayVisible ? '' : 'none';
      if (!rayVisible) {
        ray.style.filter = '';
      } else {
        ray.style.opacity = (horizon * this._rayPeak).toFixed(3);
        ray.style.transformOrigin = `${rx.toFixed(1)}% ${ry.toFixed(1)}%`;
        ray.style.filter = this._rayBlur > 0 ? `blur(${this._rayBlur}px)` : '';
        ray.style.background = rayGradient(rx, ry, 5, 0.5, 0.5);
      }

      // --- sun disc, when artwork is supplied ------------------------------
      if (this._sunImg) {
        let disc = c.querySelector('.sun-cycle-sun');
        if (!disc) {
          disc = document.createElement('div');
          disc.className = 'sun-cycle-sun';
          const im = document.createElement('img');
          im.src = this._sunImg;
          im.alt = '';
          disc.appendChild(im);
          this._before(c, disc);
        }
        const d = this._sunDisc;
        // The element is sized by the *disc*, so the whole file is wider by
        // 1 / dia; the offsets put the disc centre, not the file centre, on
        // the projected position.
        disc.style.width = (this._sunImgW / d.dia).toFixed(3) + '%';
        disc.style.left = sunPos.x.toFixed(1) + '%';
        disc.style.top = sunPos.y.toFixed(1) + '%';
        disc.style.transform =
          `translate(${(-d.cx * 100).toFixed(3)}%, ${(-d.cy * 100).toFixed(3)}%)`;
        // Below -3 deg the projection has nowhere left to put the sun, so it
        // would sit on the bottom edge glowing all night. Fade it instead.
        disc.style.opacity = smoothstep(clamp((e + 3) / 6, 0, 1)).toFixed(3);
        // Blur is a share of the disc diameter, never a pixel figure: the same
        // card runs on a 430 px card and a 1920 px kiosk view.
        const px = (c.clientWidth || 0) * this._sunImgW / 100 * this._sunImgBlur / 100;
        disc.style.filter =
          (px > 0.05 ? `blur(${px.toFixed(2)}px) ` : '') +
          `brightness(${lerp(0.86, 1.06, day).toFixed(3)}) ` +
          `saturate(${lerp(1.3, 0.95, day).toFixed(3)}) ` +
          `hue-rotate(${lerp(-13, 0, day).toFixed(1)}deg)`;
      }

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

        // Artwork can only be used once its aspect ratio is known; until the
        // probe resolves, and forever if it fails, the drawn moon stands in.
        const useImg = !!(this._moonImg && this._moonAR);
        const tryb = useImg ? 'image' : 'drawn';
        let moon = c.querySelector('.sun-cycle-moon');
        if (!moon) {
          moon = document.createElement('div');
          moon.className = 'sun-cycle-moon';
          this._before(c, moon);
        }
        const svg = moon.firstElementChild;
        if (!svg || svg.dataset.mode !== tryb) {
          moon.textContent = '';
          moon.appendChild(moonSVG(useImg ? this._moonImg : null, this._moonDisc, this._moonAR));
        }
        if (this._moonImgW > 0) {
          moon.style.width = this._moonImgW + '%';
          moon.style.maxWidth = 'none';       // the 190 px cap is for the drawn disc
        }
        moon.style.left = pos.x.toFixed(1) + '%';
        moon.style.top = pos.y.toFixed(1) + '%';
        moon.style.opacity = alpha.toFixed(2);
        // Bright limb points at the sun in the same projection. The lit region
        // is drawn facing +x, and SVG rotate() turns clockwise in the same
        // y-down frame atan2 measures in, so the angle maps directly.
        const ang = Math.atan2(sunPos.y - pos.y, sunPos.x - pos.x) * R2D;
        const lit = moon.querySelector('.scb-lit');
        if (lit) lit.setAttribute('d', litPath(k));
        if (useImg) {
          const spin = moon.querySelector('.scb-spin');
          const hold = moon.querySelector('.scb-hold');
          if (spin) spin.setAttribute('transform', `rotate(${ang.toFixed(1)})`);
          if (hold) hold.setAttribute('transform', `rotate(${(-ang).toFixed(1)})`);
          // Pale at dusk, full brightness deep in the night — otherwise a photo
          // of a full moon reads as a lamp glued to a still-blue sky.
          const noc = clamp((-e - 2) / 10, 0, 1);
          moon.style.filter = `brightness(${lerp(0.82, 1.04, noc).toFixed(3)}) ` +
            `saturate(${lerp(0.7, 1, noc).toFixed(3)})`;
        } else if (lit) {
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
