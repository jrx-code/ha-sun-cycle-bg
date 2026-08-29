/* sun-cycle-bg 1.6.1 — a living day-cycle background for Home Assistant dashboards.
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
 *     but the layer has to cover the whole swept disc — see `stars.rotate`),
 *   - on top of the field, all off by default: three star sizes instead of
 *     one, a few flare stars that flash now and then, sporadic meteors (or a
 *     shower from a radiant), and the ISS crossing the sky along its real
 *     pass when the Satellite Tracker (N2YO) integration publishes one.
 *
 * Performance contract: every animation is transform/opacity-only (runs on the
 * compositor), one animated layer each for rays / moon / stars, repaints only
 * when the sun moves >= 0.15 deg in elevation or >= 0.6 deg in azimuth
 * (~ every half minute). Meteors and the ISS add at most one short-lived
 * element each, animated with the Web Animations API on transform/opacity; a
 * JS timer only decides *when* to spawn one, it never animates. Measured with
 * this card on a 1280x400 RPi5 kiosk: 60 fps.
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
 *     sizes: flat         # mixed = three diameters, a crude magnitude ladder
 *     size: 1             # scales the star dot (0.25-2)
 *     glow: 1             # scales the blur around it (0-2); 0 = hard pixels
 *     twinkle: 1          # amplitude (0-1.4); 0 = steady
 *     flares:             # a few named stars that flash bright now and then
 *       count: 0
 *       every: 26         # seconds per cycle (each star +-25 %)
 *       strength: 1       # 0-1
 *       spikes: true      # diffraction spikes on the flash
 *     meteors:            # sporadic streaks on a Poisson interval
 *       rate: 0           # per hour; 0 = off
 *       length: 190       # px
 *       speed: 1.1        # seconds per streak
 *       angle: 24         # degrees below horizontal (random +-8)
 *       radiant: null     # [x%, y%] = a shower, every streak runs from there
 *       pair: 0           # chance (0-1) of a second streak right after
 *     iss: false          # true = real passes from sensor.iss_visual_pass_0..4
 *                         # (Satellite Tracker / N2YO), or:
 *     # iss:
 *     #   entities: sensor.iss_visual_pass_   # prefix, + 0..count-1
 *     #   count: 5
 *     #   trail: 60       # px of trail behind the station, 0 = none
 *     #   label: false    # "ISS" caption next to it
 *     #   every: 0        # s between demo passes on the fallback arc, 0 = off
 *     #   duration: 330   # fallback arc: seconds, azimuth from -> to, peak
 *     #   az: [200, 95]
 *     #   max_alt: 41
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
    // the star layer's own rules (drift, spin, twinkle, flares, meteors, ISS)
    // travel inside the layer, scoped to a per-instance class — see starCSS()
    '.sun-cycle-stars{position:absolute;inset:0;overflow:hidden;pointer-events:none;' +
    'transition:opacity 2s linear;}' +
    // the planet layer carries its own rules inside it — see PLANET_CSS
    '.sun-cycle-planets{position:absolute;inset:0;overflow:hidden;pointer-events:none;' +
    'transition:opacity 2s linear;}';

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
  // Five groups, each one seed dot plus a multi-point box-shadow painted once;
  // only the group's opacity animates, with literal keyframe values, so the
  // twinkle runs on the compositor. Flares, meteors and the ISS are the three
  // things a shared box-shadow cannot do (one opacity drives the whole group),
  // so each of them is a real element of its own — still transform/opacity
  // only, and short-lived where it can be.
  const STAR_GROUPS = [
    { dur: 2.7, lo: 0.05, hi: 1.0 },
    { dur: 3.9, lo: 0.1, hi: 0.95 },
    { dur: 5.3, lo: 0.05, hi: 1.0 },
    { dur: 6.7, lo: 0.15, hi: 0.9 },
    { dur: 8.1, lo: 0.05, hi: 0.95 },
  ];
  // [diameter px, share of the count] — "mixed" is a crude magnitude ladder.
  const STAR_SIZES = {
    flat: [[3, 1]],
    mixed: [[2, 0.58], [3, 0.30], [4, 0.12]],
  };
  const COMPASS = {                                 // compass point -> azimuth
    N: 0, NNE: 22.5, NE: 45, ENE: 67.5, E: 90, ESE: 112.5, SE: 135, SSE: 157.5,
    S: 180, SSW: 202.5, SW: 225, WSW: 247.5, W: 270, WNW: 292.5, NW: 315, NNW: 337.5,
  };
  let STAR_SEQ = 0;
  const numOr = (v, d) => (v === undefined || v === null || v === '' || isNaN(v) ? d : Number(v));

  /* `stars:` block -> full config with defaults. Everything new is off by
     default, so a config written for an older version draws what it drew. */
  function readStarConfig(c) {
    c = c || {};
    const f = c.flares || {}, m = c.meteors || {}, i = c.iss;
    return {
      count: numOr(c.count, 90),
      drift: numOr(c.drift, 1800),                  // s per screen-width, 0 = static
      rotate: !!c.rotate,
      pivot: numOr(c.pivot, 2.2),
      sizes: c.sizes === 'mixed' ? 'mixed' : 'flat',
      size: clamp(numOr(c.size, 1), 0.25, 2),       // scales every star diameter
      glow: clamp(numOr(c.glow, 1), 0, 2),          // scales the blur around it
      twinkle: clamp(numOr(c.twinkle, 1), 0, 1.4),  // amplitude, 0 = steady
      flares: {
        count: Math.round(numOr(f.count, 0)),
        every: numOr(f.every, 26),                  // s per cycle (±25 %)
        strength: clamp(numOr(f.strength, 1), 0, 1),
        spikes: f.spikes !== false,
      },
      meteors: {
        rate: numOr(m.rate, 0),                     // per hour, 0 = off
        length: numOr(m.length, 190),               // px
        speed: numOr(m.speed, 1.1),                 // s per streak
        angle: numOr(m.angle, 24),                  // deg below horizontal
        radiant: Array.isArray(m.radiant) ? m.radiant : null,   // [%x, %y] = a shower
        pair: clamp(numOr(m.pair, 0), 0, 1),        // chance of a second streak
      },
      iss: i
        ? {
            // `entities` = the Satellite Tracker (N2YO) sensors; with them the
            // pass is the real one, at its real hour. duration / az / max_alt
            // are the fallback arc for a page with no Home Assistant behind it
            // (a tuning page), or for `every` > 0.
            entities: i === true ? 'sensor.iss_visual_pass_'
                                 : (typeof i.entities === 'string' ? i.entities : null),
            count: Math.round(numOr(i === true ? 5 : i.count, 5)),
            duration: numOr(i.duration, 330),
            az: Array.isArray(i.az) ? i.az : [200, 95],
            alt: numOr(i.max_alt, 41),
            trail: numOr(i.trail, 0),
            label: !!(i === true ? false : i.label),
            every: numOr(i.every, 0),               // s between repeats, 0 = on demand
          }
        : null,
    };
  }

  /* Per-layer CSS. Every keyframe name carries the layer's own suffix, so two
     layers on one page (a tuning page mounts a dozen) cannot overwrite each
     other's twinkle. */
  function starCSS(cfg, sel) {
    const amp = cfg.twinkle;
    let css =
      sel + ' .scs{position:absolute;border-radius:50%;background:#eaf3ff;will-change:opacity;}' +
      sel + ' .scs-drift{position:absolute;top:0;left:0;width:200%;height:100%;}' +
      sel + ' .scs-half{position:absolute;top:0;width:50%;height:100%;}';
    if (cfg.drift > 0 && !cfg.rotate) {
      css += '@keyframes ' + sel.slice(1) + '-drift{from{transform:translateX(-50%)}to{transform:translateX(0)}}' +
        sel + ' .scs-drift{animation:' + sel.slice(1) + '-drift ' + cfg.drift +
        's linear infinite;will-change:transform;}';
    }
    if (cfg.rotate) {
      css += '@keyframes ' + sel.slice(1) + '-spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}' +
        sel + ' .scs-spin{position:absolute;left:50%;top:0;' +
        'animation:' + sel.slice(1) + '-spin 86164s linear infinite;will-change:transform;}';
    }
    STAR_GROUPS.forEach((g, i) => {
      // amplitude scales the swing around the bright end: twinkle 0 = steady
      const lo = clamp(g.hi - (g.hi - g.lo) * amp, 0, 1).toFixed(3);
      const nam = sel.slice(1) + '-tw' + i;
      css +=
        '@keyframes ' + nam + '{0%,100%{opacity:' + lo + '}50%{opacity:' + g.hi + '}}' +
        sel + ' .scs' + i + '{animation:' + nam + ' ' + g.dur +
        's ease-in-out infinite;animation-delay:-' + (g.dur * Math.random()).toFixed(1) + 's;}';
    });
    if (cfg.flares.count > 0) {
      const d = (4 * cfg.size).toFixed(2);
      css +=
        sel + ' .scs-flare{position:absolute;width:' + d + 'px;height:' + d + 'px;border-radius:50%;' +
        'background:#ffffff;will-change:opacity,transform;}' +
        sel + ' .scs-flare::before,' + sel + ' .scs-flare::after{content:"";position:absolute;' +
        'left:50%;top:50%;background:linear-gradient(90deg,transparent,rgba(226,240,255,.95),transparent);' +
        'height:1.5px;width:' + (34 * cfg.size).toFixed(0) + 'px;transform:translate(-50%,-50%);border-radius:2px;}' +
        sel + ' .scs-flare::after{transform:translate(-50%,-50%) rotate(90deg);}' +
        sel + ' .scs-flare.no-spikes::before,' + sel + ' .scs-flare.no-spikes::after{display:none;}';
    }
    // always defined: a meteor can also be fired on demand at rate 0
    css +=
      sel + ' .scs-meteor{position:absolute;height:2px;border-radius:2px;' +
      'transform-origin:0 50%;will-change:transform,opacity;' +
      'background:linear-gradient(90deg,rgba(200,225,255,0) 0%,rgba(206,230,255,.55) 55%,' +
      'rgba(255,255,255,.98) 100%);box-shadow:0 0 8px 1px rgba(190,220,255,.55);}' +
      sel + ' .scs-meteor b{position:absolute;right:-2px;top:-2px;width:6px;height:6px;' +
      'border-radius:50%;background:#fff;box-shadow:0 0 10px 3px rgba(210,232,255,.9);}' +
      sel + ' .scs-iss{position:absolute;left:0;top:0;width:5px;height:5px;margin:-2.5px 0 0 -2.5px;' +
      'border-radius:50%;background:#fdf6e6;box-shadow:0 0 9px 2px rgba(255,244,214,.85);' +
      'will-change:transform,opacity;}' +
      sel + ' .scs-iss i{position:absolute;right:3px;top:50%;height:2px;border-radius:2px;' +
      'transform:translateY(-50%);background:linear-gradient(90deg,rgba(255,244,214,0),rgba(255,244,214,.5));}' +
      sel + ' .scs-iss span{position:absolute;left:9px;top:-6px;font:600 10px/1 system-ui,sans-serif;' +
      'letter-spacing:.14em;color:rgba(255,246,224,.85);text-shadow:0 1px 3px rgba(0,0,0,.6);}';
    return css;
  }

  /* One group of stars: the seed dot carries every sibling as a box-shadow
     point. The dot is the star; the blur around it is what makes a 3 px dot
     read as a 9 px blob — `size` scales one, `glow` the other. */
  function starDot(cfg, i, px, n, pts) {
    const dot = document.createElement('div');
    dot.className = 'scs scs' + i;
    const d = (px * cfg.size).toFixed(2);
    dot.style.width = dot.style.height = d + 'px';
    const [sx, sy] = pts[0];
    dot.style.left = sx.toFixed(0) + 'px';
    dot.style.top = sy.toFixed(0) + 'px';
    const shadows = [];
    for (let j = 1; j < n; j++) {
      const blur = ((Math.random() * 4 + 2) * cfg.glow).toFixed(2);
      const spread = (Math.random() * 1.8 * cfg.glow * cfg.size).toFixed(2);
      shadows.push((pts[j][0] - sx).toFixed(0) + 'px ' + (pts[j][1] - sy).toFixed(0) + 'px ' +
        blur + 'px ' + spread + 'px rgba(215,235,255,1)');
    }
    // the seed has no shadow of its own — give it one to match its siblings,
    // otherwise one star per group is crisp and the rest are soft
    if (cfg.glow > 0) {
      shadows.unshift('0 0 ' + (4 * cfg.glow).toFixed(2) + 'px ' +
        (0.8 * cfg.glow * cfg.size).toFixed(2) + 'px rgba(215,235,255,1)');
    }
    if (shadows.length) dot.style.boxShadow = shadows.join(',');
    return dot;
  }

  /* Drifting field: two identical halves sliding east to west (or static). */
  function buildStarsDrift(cfg, W, H) {
    const half = document.createElement('div');
    half.className = 'scs-half';
    half.style.left = '0';
    STAR_SIZES[cfg.sizes].forEach(([px, share]) => {
      const n = Math.max(1, Math.round((cfg.count / STAR_GROUPS.length) * share));
      STAR_GROUPS.forEach((g, i) => {
        const pts = [];
        for (let j = 0; j < n; j++) pts.push([Math.random() * W, Math.random() * H]);
        half.appendChild(starDot(cfg, i, px, n, pts));
      });
    });
    return half;
  }

  /* Rotating field: stars laid out in the annulus that the frame sweeps out
     around the celestial pole, so the frame stays covered at every angle.
     That annulus is several times the frame area — hence the star count is
     scaled up to keep the on-screen density. Costs one big painted layer;
     recommended for panel-sized views, not for full 4K dashboards. */
  function buildStarsRotate(cfg, W, H) {
    const py = H * cfg.pivot;                                // pole, below the frame
    const rMin = Math.max(1, (cfg.pivot - 1) * H);
    const rMax = Math.hypot(W / 2, py);
    const annulus = Math.PI * (rMax * rMax - rMin * rMin);
    const total = Math.min(4000, Math.round(cfg.count * annulus / (W * H)));
    const spin = document.createElement('div');
    spin.className = 'scs-spin';
    spin.style.width = spin.style.height = '0';
    spin.style.top = py.toFixed(0) + 'px';                   // rotate about the pole
    STAR_SIZES[cfg.sizes].forEach(([px, share]) => {
      const n = Math.max(1, Math.round((total / STAR_GROUPS.length) * share));
      STAR_GROUPS.forEach((g, i) => {
        const pts = [];
        for (let j = 0; j < n; j++) {
          const a = Math.random() * 2 * Math.PI;
          const r = Math.sqrt(rMin * rMin + Math.random() * (rMax * rMax - rMin * rMin));
          pts.push([Math.sin(a) * r, -Math.cos(a) * r]);     // relative to the pole
        }
        spin.appendChild(starDot(cfg, i, px, n, pts));
      });
    });
    return spin;
  }

  /* Flare stars: their own element and their own keyframes, because a flash
     that lights one star cannot come out of a shared box-shadow. Each one is
     dark for most of its cycle and bright for a moment. */
  function addFlares(half, cfg, W, H, sel, style, seed0) {
    const f = cfg.flares;
    for (let k = 0; k < f.count; k++) {
      const el = document.createElement('div');
      el.className = 'scs-flare' + (f.spikes ? '' : ' no-spikes');
      el.style.left = (Math.random() * W).toFixed(0) + 'px';
      el.style.top = (Math.random() * H * 0.8).toFixed(0) + 'px';
      const nam = sel.slice(1) + '-fl' + (seed0 + k);
      const dur = f.every * (0.75 + Math.random() * 0.5);
      const dim = (0.10 + 0.10 * (1 - f.strength)).toFixed(2);
      const peak = (0.55 + 0.45 * f.strength).toFixed(2);
      const grow = (1 + 1.4 * f.strength).toFixed(2);
      // a 6 % window of the cycle carries the whole flash: rise, peak, decay
      style.textContent +=
        '@keyframes ' + nam + '{' +
        '0%,92%{opacity:' + dim + ';transform:scale(.8)}' +
        '95.5%{opacity:' + peak + ';transform:scale(' + grow + ')}' +
        '97%{opacity:' + (peak * 0.7).toFixed(2) + ';transform:scale(' + (grow * 0.85).toFixed(2) + ')}' +
        '100%{opacity:' + dim + ';transform:scale(.8)}}' +
        sel + ' .scs-flare.fl' + (seed0 + k) + '{animation:' + nam + ' ' + dur.toFixed(1) +
        's ease-in-out infinite;animation-delay:-' + (dur * Math.random()).toFixed(1) + 's;}';
      el.classList.add('fl' + (seed0 + k));
      half.appendChild(el);
    }
  }

  /* A meteor: one element, one Web Animation (transform + opacity), removed
     when it finishes. With `radiant` every streak runs away from that point,
     as a shower does; without it they fall at `angle` from anywhere. */
  function meteor(layer, cfg, W, H) {
    const m = cfg.meteors;
    const el = document.createElement('div');
    el.className = 'scs-meteor';
    const len = m.length * (0.7 + Math.random() * 0.6);
    el.style.width = len.toFixed(0) + 'px';
    el.appendChild(document.createElement('b'));
    let x, y, angle;
    if (m.radiant) {
      const rx = m.radiant[0] / 100 * W, ry = m.radiant[1] / 100 * H;
      angle = Math.atan2(Math.random() * H * 0.9 - ry, Math.random() * W - rx) * R2D;
      const near = 40 + Math.random() * 120;         // start just off the radiant
      x = rx + Math.cos(angle * D2R) * near;
      y = ry + Math.sin(angle * D2R) * near;
    } else {
      angle = m.angle + (Math.random() * 16 - 8);
      x = Math.random() * W * 0.75 - W * 0.05;
      y = Math.random() * H * 0.55;
    }
    el.style.left = x.toFixed(0) + 'px';
    el.style.top = y.toFixed(0) + 'px';
    const travel = (W + len) * (0.35 + Math.random() * 0.3);
    const base = 'rotate(' + angle.toFixed(1) + 'deg)';
    layer.appendChild(el);
    const anim = el.animate(
      [
        { transform: base + ' translateX(' + (-len).toFixed(0) + 'px) scaleX(.25)', opacity: 0 },
        { opacity: 1, offset: 0.18 },
        { opacity: 1, offset: 0.62 },
        { transform: base + ' translateX(' + travel.toFixed(0) + 'px) scaleX(1)', opacity: 0 },
      ],
      { duration: m.speed * 1000 * (0.8 + Math.random() * 0.4), easing: 'cubic-bezier(.3,.65,.45,1)' }
    );
    anim.onfinish = () => el.remove();
    if (Math.random() < m.pair) setTimeout(() => { if (layer.isConnected) meteor(layer, cfg, W, H); },
      250 + Math.random() * 600);
  }

  /* The station is not a star: it does not twinkle, it moves at a steady pace
     and fades where it flies into the Earth's shadow. `proj(alt, az)` is the
     card's own sky projection, so the pass lands where the sun and moon do. */
  function issPass(layer, cfg, W, H, proj, pass, offsetMs) {
    const i = cfg.iss;
    if (!i || layer.querySelector('.scs-iss')) return;
    // a real pass overrides the configured arc; without one the config is used
    const arc = pass || { az: i.az, alt: i.alt, ms: i.duration * 1000 };
    const el = document.createElement('div');
    el.className = 'scs-iss';
    if (i.trail > 0) {
      const t = document.createElement('i');
      t.style.width = i.trail + 'px';
      el.appendChild(t);
    }
    if (i.label) {
      const s = document.createElement('span');
      s.textContent = 'ISS';
      el.appendChild(s);
    }
    const [a0, a1] = arc.az, N = 60, frames = [];
    for (let s = 0; s <= N; s++) {
      const t = s / N;
      const p = proj(arc.alt * Math.sin(Math.PI * t), a0 + (a1 - a0) * t);
      // bright through the middle, fading in at the horizon and out into shadow
      const o = Math.pow(Math.sin(Math.PI * t), 0.45) * (t > 0.86 ? clamp((1 - t) / 0.14, 0, 1) : 1);
      frames.push({ offset: t, opacity: o.toFixed(3),
        transform: 'translate3d(' + (p.x / 100 * W).toFixed(1) + 'px,' + (p.y / 100 * H).toFixed(1) + 'px,0)' });
    }
    layer.appendChild(el);
    const anim = el.animate(frames, { duration: Math.max(1000, arc.ms), easing: 'linear' });
    // the panel is not always opened at the start of a pass — join it in flight
    if (offsetMs > 0) anim.currentTime = Math.min(offsetMs, arc.ms - 500);
    anim.onfinish = () => el.remove();
    return anim;
  }

  /* Passes as the Satellite Tracker (N2YO) integration publishes them:
     sensor.iss_visual_pass_0..4, one attribute set per pass. "Visual" already
     means a sunlit station over a dark observer, so nothing has to be gated
     by daylight — the layer's own opacity hides it by day. */
  function issPassesFromHass(h, i) {
    const out = [];
    for (let n = 0; n < i.count; n++) {
      const s = h.states && h.states[i.entities + n];
      if (!s || !s.attributes) continue;
      const a = s.attributes;
      if (!a.pass_start_unix || !a.pass_end_unix) continue;
      const az0 = COMPASS[a.start_compass], az1 = COMPASS[a.end_compass];
      if (az0 === undefined || az1 === undefined) continue;
      out.push({
        start: a.pass_start_unix * 1000,
        end: a.pass_end_unix * 1000,
        ms: (a.pass_end_unix - a.pass_start_unix) * 1000,
        alt: numOr(a.max_elevation, 25),
        // the station always travels the short way round the sky; without this
        // a SW -> E pass (225 -> 90) would be drawn crossing north
        az: [az0, az1 + (Math.abs(az1 - az0) > 180 ? (az1 > az0 ? -360 : 360) : 0)],
      });
    }
    return out.sort((a, b) => a.start - b.start);
  }

  /* One timer, re-armed whenever Home Assistant hands over new pass data: fire
     a pass that is running now (joined in flight), or wake up for the next. */
  function scheduleIss(layer, passes) {
    const now = Date.now();
    const current = passes.find((p) => now >= p.start - 1000 && now < p.end);
    const next = passes.find((p) => p.start > now);
    const target = current || next;
    if (!target || layer._issTarget === target.start) return;
    layer._issTarget = target.start;
    clearTimeout(layer._issTimer);
    const again = (ms) => {
      layer._issTimer = setTimeout(() => {
        layer._issTarget = null;
        if (layer.isConnected) scheduleIss(layer, passes);
      }, ms);
    };
    if (current) {
      layer.scsIss(current, now - current.start);
      again(current.end - now + 1000);
    } else {
      // setTimeout is not reliable over many hours; re-arm in one-hour hops
      again(Math.min(target.start - now, 3600 * 1000));
    }
  }

  // --- planets -----------------------------------------------------------
  /* The Sol integration (HACS) publishes sensor.sol_<body>_azimuth and
     _elevation for the eight planets other than Earth, updated as they move.
     The card reads those two numbers and puts the artwork on the same
     projection the sun, the moon and the ISS already use.

     Sizes are not to scale, and cannot be: Jupiter is 45 arcseconds across at
     its best, which on a 1280 px view spanning 260 degrees of azimuth is a
     twentieth of a pixel. Naked-eye planets ARE points of light. So the discs
     are drawn as small emblems instead — big enough to read as themselves,
     ranked by how bright the planet is in the sky rather than by its true
     size, which is why Venus outranks Uranus.  */
  const PLANET_BODIES = ['mercury', 'venus', 'mars', 'jupiter', 'saturn',
                         'uranus', 'neptune', 'pluto'];
  // relative to `size`; the disc measured by tools/cutout_planets.py is
  // divided out first, so these are the diameters of the balls themselves
  const PLANET_SCALE = {
    mercury: 0.58, venus: 0.88, earth: 0.8, mars: 0.7, jupiter: 1,
    saturn: 0.94, uranus: 0.6, neptune: 0.56, pluto: 0.46,
  };
  // [disc diameter / file width, cx / width, cy / height] of the shipped
  // cutouts — measured, not guessed (tools/cutout_planets.py prints them)
  const PLANET_DISCS = {
    mercury: [0.9515, 0.51, 0.4938], venus: [0.9641, 0.4908, 0.4985],
    earth: [0.9393, 0.5107, 0.5023], mars: [0.8713, 0.501, 0.4842],
    jupiter: [0.9771, 0.5026, 0.4966], saturn: [0.4316, 0.4574, 0.5229],
    uranus: [0.6519, 0.4939, 0.4965], neptune: [0.5284, 0.4589, 0.4962],
    pluto: [0.9432, 0.5079, 0.4954],
  };
  // `scale: diameters` — the true mean diameters, compressed logarithmically
  // into the same band. Pluto is 2 377 km against Jupiter's 139 820, so a
  // linear ranking would leave it a 60th of a pixel; the log keeps the order
  // and the sense of "a giant next to a rock" without losing the rock.
  const PLANET_SCALE_DIAMETERS = {
    mercury: 0.465, venus: 0.61, earth: 0.618, mars: 0.517, jupiter: 1,
    saturn: 0.971, uranus: 0.838, neptune: 0.833, pluto: 0.35,
  };
  const PLANET_SCALES = {
    brightness: PLANET_SCALE,
    diameters: PLANET_SCALE_DIAMETERS,
    equal: Object.fromEntries(Object.keys(PLANET_SCALE).map((b) => [b, 1])),
  };
  // English, like every other string the card ships; `names:` translates them
  const PLANET_NAMES = {
    mercury: 'Mercury', venus: 'Venus', earth: 'Earth', mars: 'Mars',
    jupiter: 'Jupiter', saturn: 'Saturn', uranus: 'Uranus', neptune: 'Neptune',
    pluto: 'Pluto',
  };

  function readPlanetConfig(p) {
    if (p === false || p === undefined || p === null) return null;
    const c = p === true ? {} : (p || {});
    const num = (v, def) => (isFinite(v) ? Number(v) : def);
    const bodies = Array.isArray(c.bodies) && c.bodies.length
      ? c.bodies.map((b) => String(b).toLowerCase()) : PLANET_BODIES.slice();
    return {
      entities: typeof c.entities === 'string' ? c.entities : 'sensor.sol_',
      bodies,
      images: typeof c.images === 'string' ? c.images : '/local/sun-cycle/planets/',
      files: c.files && typeof c.files === 'object' ? c.files : {},
      discs: Object.assign({}, PLANET_DISCS, c.discs || {}),
      // a name picks one of the shipped ladders; an object overrides body by
      // body on top of the default one
      scale: typeof c.scale === 'string'
        ? Object.assign({}, PLANET_SCALES[c.scale] || PLANET_SCALE)
        : Object.assign({}, PLANET_SCALE, c.scale || {}),
      names: Object.assign({}, PLANET_NAMES, c.names || {}),
      size: num(c.size, 2.4),
      glow: num(c.glow, 0.5),
      labels: c.labels === true,
      // `day` is how much of a planet survives full daylight: false/0 = none,
      // true = the default floor, or a number 0-1 of your own. A planet at
      // full opacity against a noon sky reads as a sticker, but at nothing it
      // is a feature you only ever see in the dark.
      day: c.day === true ? 0.35 : (c.day === false || c.day === undefined
        ? 0 : clamp(num(c.day, 0), 0, 1)),
      min_elevation: num(c.min_elevation, 0),
    };
  }

  /* Travels inside the layer, the way the star field's rules do: a tuning
     page builds the layer on its own and never gets the card's stylesheet. */
  const PLANET_CSS =
    '.sun-cycle-planets>div{position:absolute;pointer-events:none;transition:opacity 2s linear;}' +
    '.sun-cycle-planets img{display:block;width:100%;height:auto;}' +
    '.sun-cycle-planets b{position:absolute;transform:translateX(-50%);' +
    'font:500 9px/1 system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;' +
    'color:rgba(232,238,248,.62);text-shadow:0 1px 2px rgba(0,0,0,.75);white-space:nowrap;}';

  function planetSrc(cfg, body) {
    return cfg.files[body] || (cfg.images + body + '.png');
  }

  /* One <div><img></div> per body, built once and then only moved. */
  function buildPlanets(cfg) {
    const layer = document.createElement('div');
    layer.className = 'sun-cycle-planets';
    const style = document.createElement('style');
    style.textContent = PLANET_CSS;
    layer.appendChild(style);
    cfg.bodies.forEach((body) => {
      const el = document.createElement('div');
      el.dataset.body = body;
      el.style.opacity = '0';
      const im = document.createElement('img');
      im.src = planetSrc(cfg, body);
      im.alt = '';
      im.loading = 'lazy';
      el.appendChild(im);
      if (cfg.labels) {
        const b = document.createElement('b');
        b.textContent = cfg.names[body] || body;
        el.appendChild(b);
      }
      layer.appendChild(el);
    });
    layer.scsPlanetPrint = '';
    return layer;
  }

  /* Position and fade every planet. `states` is hass.states, `sunElev` the
     sun's elevation — planets are daylight-invisible for the same reason the
     stars are, so they ride the same curve. */
  function placePlanets(layer, cfg, states, proj, sunElev) {
    if (!states) return;
    // deep enough into the night for a planet to hold its own against the sky,
    // never below the daylight floor
    const night = lerp(cfg.day, 1, clamp((-sunElev - 1) / 8, 0, 1));
    for (const el of layer.children) {
      const body = el.dataset.body;
      if (!body) continue;                    // the layer's own <style>
      const az = Number((states[cfg.entities + body + '_azimuth'] || {}).state);
      const alt = Number((states[cfg.entities + body + '_elevation'] || {}).state);
      if (!isFinite(az) || !isFinite(alt)) { el.style.opacity = '0'; continue; }
      const pos = proj(alt, az);
      const disc = cfg.discs[body] || [1, 0.5, 0.5];
      const w = cfg.size * (cfg.scale[body] || 1) / disc[0];
      // A planet below the horizon is behind the Earth; the projection parks
      // anything down there on the bottom edge, so it has to be faded out
      // rather than left sitting on the rim all night.
      const up = clamp((alt - cfg.min_elevation) / 4, 0, 1);
      // The sky window is narrower than the sky: a planet outside it gets
      // parked on the frame edge by the projection, and half a dozen of them
      // parked there would read as a row of stickers on the rim. Fade the
      // last two percent instead.
      const inFrame = clamp(pos.x / 2, 0, 1) * clamp((100 - pos.x) / 2, 0, 1);
      const a = night * up * inFrame;
      el.style.width = w.toFixed(3) + '%';
      el.style.left = pos.x.toFixed(2) + '%';
      el.style.top = pos.y.toFixed(2) + '%';
      el.style.transform =
        `translate(${(-disc[1] * 100).toFixed(2)}%, ${(-disc[2] * 100).toFixed(2)}%)`;
      el.style.opacity = a.toFixed(3);
      // the caption belongs under the *ball*, not under the file: Saturn's
      // box is more than twice its disc, and a label hung off the box bottom
      // would float a ring-width below the planet
      const cap = el.lastElementChild;
      if (cap && cap.tagName === 'B') {
        cap.style.left = (disc[1] * 100).toFixed(1) + '%';
        cap.style.top = ((disc[2] + disc[0] / 2) * 100 + 4).toFixed(1) + '%';
      }
      // A disc pasted on the sky reads as a sticker; a hair of glow in the
      // planet's own colour is what the eye expects around a bright object.
      el.style.filter = cfg.glow > 0
        ? `drop-shadow(0 0 ${(w * 0.35 * cfg.glow).toFixed(2)}vw rgba(210,226,255,${(0.5 * cfg.glow).toFixed(2)}))`
        : '';
    }
  }

  /* The whole star layer for one frame of W x H px. `proj(alt, az)` maps a
     sky position to {x, y} in % of the frame (the ISS needs it). */
  function buildStars(cfg, W, H, proj) {
    // no projection handed in (a page without the card): the default window
    proj = proj || ((alt, az) => ({
      x: clamp((az - 50) / 260, -0.05, 1.05) * 100,
      y: 92 - clamp((alt + 6) / 60, -0.1, 1) * 86,
    }));
    const inst = 'scs-i' + (++STAR_SEQ), sel = '.' + inst;
    const layer = document.createElement('div');
    layer.className = 'sun-cycle-stars ' + inst;
    const style = document.createElement('style');
    style.textContent = starCSS(cfg, sel);
    layer.appendChild(style);
    if (cfg.rotate) {
      layer.appendChild(buildStarsRotate(cfg, W, H));
    } else {
      const halfA = buildStarsDrift(cfg, W, H);
      const halfB = halfA.cloneNode(true);      // seamless wrap for the drift
      halfB.style.left = '50%';
      // flares are added per half, after the clone, so the two halves do not
      // flash in lockstep one screen-width apart
      addFlares(halfA, cfg, W, H, sel, style, 0);
      addFlares(halfB, cfg, W, H, sel, style, cfg.flares.count);
      const drift = document.createElement('div');
      drift.className = 'scs-drift';
      drift.appendChild(halfA);
      drift.appendChild(halfB);
      layer.appendChild(drift);
    }
    // handles: on demand (a tuning page), and for the schedulers below
    layer.scsConfig = cfg;
    layer.scsMeteor = () => meteor(layer, cfg, W, H);
    layer.scsIss = (pass, offset) => issPass(layer, cfg, W, H, proj, pass, offset);
    layer.scsPasses = (h) => {
      if (!cfg.iss || !cfg.iss.entities) return 0;
      const p = issPassesFromHass(h, cfg.iss);
      if (p.length) scheduleIss(layer, p);
      return p.length;
    };
    // timers: meteors on a Poisson interval, ISS on a fixed cadence if asked.
    // A JS timer only decides *when* to spawn; nothing here animates in JS.
    // Both stop re-arming once the layer has left the document.
    const timers = [];
    layer.scsStop = () => { timers.forEach(clearTimeout); clearTimeout(layer._issTimer); };
    if (cfg.meteors.rate > 0) {
      const mean = 3600 / cfg.meteors.rate;
      const nextMeteor = () => {
        const wait = -Math.log(1 - Math.random()) * mean * 1000;
        timers.push(setTimeout(() => {
          if (!layer.isConnected && layer._scsStarted) return;
          if (layer.isConnected) { layer._scsStarted = true; meteor(layer, cfg, W, H); }
          nextMeteor();
        }, Math.min(wait, 15 * 60 * 1000)));
      };
      nextMeteor();
    }
    if (cfg.iss && cfg.iss.every > 0) {
      const nextPass = () => {
        timers.push(setTimeout(() => {
          if (!layer.isConnected && layer._scsStarted) return;
          if (layer.isConnected) { layer._scsStarted = true; layer.scsIss(); }
          nextPass();
        }, cfg.iss.every * 1000));
      };
      nextPass();
    }
    return layer;
  }

  class SunCycleBgCard extends HTMLElement {
    setConfig(config) {
      this._cfg = config || {};
      const s = this._cfg.stars;
      this._starCfg = s === false ? null : readStarConfig(s === true ? {} : s);
      this._sunEntity = this._cfg.sun_entity || 'sun.sun';
      const az = this._cfg.azimuth;
      this._az0 = Array.isArray(az) ? az[0] : 50;
      this._az1 = Array.isArray(az) ? az[1] : 310;
      const r = this._cfg.rays;
      this._rayBlur = r && r.blur !== undefined ? r.blur : 28;
      this._rayPeak = r && r.strength !== undefined ? r.strength : 0.5;
      this._showMoon = this._cfg.moon !== false;
      this._planetCfg = readPlanetConfig(this._cfg.planets);
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
      this._hass = h;
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
      if (moved) this._apply(); else { this._issSync(); this._planetSync(); }
    }

    /* `hass` arrives on every state change in the house; the ISS pass sensors
       are fingerprinted so the scheduler only runs when one of them moved. */
    _issSync() {
      const cfg = this._starCfg, h = this._hass, c = this._container;
      if (!cfg || !cfg.iss || !cfg.iss.entities || !h || !c) return;
      const layer = c.querySelector('.sun-cycle-stars');
      if (!layer || !layer.scsPasses) return;
      let print = '';
      for (let n = 0; n < cfg.iss.count; n++) {
        const s = h.states && h.states[cfg.iss.entities + n];
        print += (s && s.attributes && s.attributes.pass_start_unix) + '|';
      }
      if (print === layer._issPrint) return;
      layer._issPrint = print;
      layer.scsPasses(h);
    }

    /* The Sol sensors step by a degree at a time, far more often than the sun
       clears the repaint threshold, so the planets get their own cheap update:
       read eight pairs of states, write nothing unless one of them moved. */
    _planetSync() {
      const cfg = this._planetCfg, c = this._container;
      if (!cfg || !c || this._elev === undefined) return;
      const layer = c.querySelector('.sun-cycle-planets');
      if (!layer) return;
      const st = this._hass && this._hass.states;
      if (!st) return;
      // fingerprint first: `hass` lands on every state change in the house,
      // and eight string reads are cheaper than sixteen style writes
      let print = this._elev.toFixed(2);
      for (const b of cfg.bodies) {
        print += '|' + (st[cfg.entities + b + '_azimuth'] || {}).state +
                 ',' + (st[cfg.entities + b + '_elevation'] || {}).state;
      }
      if (print === layer._print) return;
      layer._print = print;
      placePlanets(layer, cfg, st, (alt, az) => this._project(alt, az), this._elev);
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

      // --- planets ---------------------------------------------------------
      if (this._planetCfg) {
        let pl = c.querySelector('.sun-cycle-planets');
        if (!pl) {
          pl = buildPlanets(this._planetCfg);
          // above the stars (a planet is nearer than the field behind it) and
          // below the moon, which is nearer still — the moon layer is built
          // earlier in this same pass, so it is already there to sit under
          const moon = c.querySelector('.sun-cycle-moon');
          if (moon && moon.parentNode === c) c.insertBefore(pl, moon);
          else this._before(c, pl);
        }
        this._planetSync();
      }

      // --- star field ------------------------------------------------------
      if (this._starCfg) {
        let stars = c.querySelector('.sun-cycle-stars');
        if (!stars) {
          // sized to the container, not the window: a view narrower than the
          // window would otherwise get stars laid out beyond its edge
          const r = c.getBoundingClientRect();
          const W = Math.round(r.width) || window.innerWidth;
          const H = Math.round(r.height) || window.innerHeight;
          stars = buildStars(this._starCfg, W, H, (alt, az) => this._project(alt, az));
          // right above the painted backdrop, under the sun, the rays and the
          // moon — stars are the farthest thing in the sky
          if (bg && bg.parentNode === c) c.insertBefore(stars, bg.nextSibling);
          else this._before(c, stars);
        }
        stars.style.opacity = p.stars.toFixed(2);
        this._issSync();
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

  // A tuning page builds star layers directly, with its own frames and configs.
  window.sunCycleBg = { buildStars, readStarConfig, COMPASS, paletteFor,
                       buildPlanets, readPlanetConfig, placePlanets,
                       PLANET_BODIES, PLANET_DISCS, PLANET_SCALE, PLANET_SCALES,
                       PLANET_NAMES };

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'sun-cycle-bg-card',
    name: 'Sun Cycle Background',
    description: 'Living day-cycle view background: sky palette, the sun on its real diurnal arc with crepuscular rays, a moon with its own ephemeris and phase, the planets where the Sol integration puts them, and a star field with flares, meteors and the real ISS.',
  });
})();
