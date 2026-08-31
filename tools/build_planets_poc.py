#!/usr/bin/env python3
"""Build the planets tuning page: demo/tlo-planety.html

Same rule as the star page: nothing here is a mock-up. ../src/sun-cycle-bg.js is
read at build time and pasted into the page verbatim, and every scene is drawn
by that file's own window.sunCycleBg.buildPlanets() / placePlanets(), on the
sun-cycle-bg palette, with the projection the card uses for the sun and moon.

Positions are real, from demo/sol_snapshot.json (tools/sol_snapshot.py). The
page is served from /local without a token, so it cannot ask Home Assistant
itself.

    python3 tools/sol_snapshot.py             # refresh the positions
    python3 tools/build_planets_poc.py        # -> demo/tlo-planety.html
    export BW_SESSION=$(bw unlock --raw)
    python3 ~/CodeHub/hassio/ha-panel-salon-sekcje/scripts/poc_upload.py \\
        demo/tlo-planety.html
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
KARTA = ROOT / "src" / "sun-cycle-bg.js"
SNAP = ROOT / "demo" / "sol_snapshot.json"
OUT = ROOT / "demo" / "tlo-planety.html"

NAZWY = {"mercury": "Merkury", "venus": "Wenus", "earth": "Ziemia",
         "mars": "Mars", "jupiter": "Jowisz", "saturn": "Saturn",
         "uranus": "Uran", "neptune": "Neptun", "pluto": "Pluton"}

# true mean diameters [km] — only for the "prawdziwe" size preset and the table
SREDNICE = {"mercury": 4879, "venus": 12104, "earth": 12742, "mars": 6779,
            "jupiter": 139820, "saturn": 116460, "uranus": 50724,
            "neptune": 49244, "pluto": 2377}

STRONA = r"""<meta charset="utf-8">
<title>Tło: planety z integracji Sol</title>
<style>
  :root { --bg:#0d1015; --surface:#151a22; --line:rgba(255,255,255,.08);
          --text:#e8ebf1; --muted:#96a0b0; --accent:#7cb3f9; }
  body { background:var(--bg); color:var(--text); margin:0; padding:28px 20px 72px;
         font:15px/1.55 system-ui,"Segoe UI",Roboto,sans-serif; }
  main { max-width:1240px; margin:0 auto; display:flex; flex-direction:column; gap:22px; }
  h1 { font-size:24px; font-weight:750; margin:0 0 6px; letter-spacing:-.2px; }
  .lead p { color:var(--muted); margin:0 0 6px; max-width:88ch; }
  .card { background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:18px; }
  .card h2 { margin:0 0 4px; font-size:17px; }
  .card > p { margin:0 0 14px; color:var(--muted); font-size:13.5px; max-width:92ch; }
  code { background:rgba(255,255,255,.06); padding:1px 5px; border-radius:5px; font-size:.92em; }

  .scena { position:relative; border-radius:14px; overflow:hidden; border:1px solid var(--line); }
  .scena.szeroka { aspect-ratio:16/5; }
  .scena.kadr { aspect-ratio:16/9; }
  .warstwy { position:absolute; inset:0; }
  .horyzont { position:absolute; left:0; right:0; bottom:0; height:8%;
              background:linear-gradient(to top,rgba(0,0,0,.55),transparent); pointer-events:none; }

  .panel { display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr));
           gap:12px 18px; margin-top:14px; }
  .pole { display:flex; flex-direction:column; gap:4px; font-size:12.5px; color:var(--muted); }
  .pole b { color:var(--text); font-weight:600; font-size:12.5px; }
  .pole input[type=range] { width:100%; accent-color:var(--accent); }
  .pole select, .pole input[type=text] { background:#0e131a; color:var(--text);
    border:1px solid var(--line); border-radius:8px; padding:5px 7px; font:inherit; font-size:13px; }
  .ptaszki { display:flex; flex-wrap:wrap; gap:10px 16px; margin-top:12px; font-size:13px; }
  .ptaszki label { display:flex; align-items:center; gap:6px; color:var(--muted); }
  .ciala { display:flex; flex-wrap:wrap; gap:8px 14px; margin-top:10px; font-size:13px; }
  .ciala label { display:flex; align-items:center; gap:6px; color:var(--muted); }

  .siatka { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; }
  .wariant { display:flex; flex-direction:column; gap:7px; }
  .wariant h3 { margin:0; font-size:13.5px; font-weight:650; }
  .wariant h3 em { font-style:normal; color:var(--muted); font-weight:400; }

  .wycinki { display:grid; grid-template-columns:repeat(auto-fit,minmax(126px,1fr)); gap:14px; }
  .wycinek { text-align:center; font-size:11.5px; color:var(--muted); }
  .wycinek div { aspect-ratio:1; border-radius:12px; border:1px solid var(--line);
    background-color:#20283c;
    background-image:linear-gradient(45deg,rgba(255,255,255,.05) 25%,transparent 25%,transparent 75%,rgba(255,255,255,.05) 75%),
                     linear-gradient(45deg,rgba(255,255,255,.05) 25%,transparent 25%,transparent 75%,rgba(255,255,255,.05) 75%);
    background-size:18px 18px; background-position:0 0,9px 9px; display:grid; place-items:center; }
  .wycinek img { width:86%; height:86%; object-fit:contain; }
  .wycinek b { display:block; color:var(--text); font-size:12.5px; margin-top:6px; font-weight:600; }

  table { border-collapse:collapse; width:100%; font-size:13px; }
  th, td { text-align:left; padding:5px 10px 5px 0; border-bottom:1px solid var(--line); }
  th { color:var(--muted); font-weight:600; }
  td.l { font-variant-numeric:tabular-nums; }
  .nad { color:#7fe1a8; } .pod { color:#96a0b0; }

  .przepis, .yaml { margin-top:14px; background:#0b0f15; border:1px solid var(--line);
    border-radius:12px; padding:12px 14px; font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
    white-space:pre-wrap; user-select:all; color:#d7e2f2; }
  .etykieta { font-size:12px; color:var(--muted); margin:14px 0 0; }
  .note { color:var(--muted); font-size:13px; }
</style>

<main>
  <div class="lead">
    <h1>Tło: planety z integracji Sol</h1>
    <p>Karta <code>sun-cycle-bg</code> rysuje dziś Słońce, Księżyc, gwiazdy, meteory i ISS.
    Tu dochodzi <strong>osiem planet</strong> — pozycje bierze integracja Sol
    (<code>sensor.sol_&lt;ciało&gt;_azimuth</code> i <code>_elevation</code>), rysunek to wycięte
    z tła zdjęcia z katalogu <code>planety i efekty</code>, z kanałem alfa.</p>
    <p>Rozmiary <strong>nie są w skali i być nie mogą</strong>: Jowisz ma w najlepszym razie
    45 sekund kątowych, co na kadrze 1280 px obejmującym 260° azymutu wychodzi jedna
    dwudziesta piksela. Prawdziwa planeta to punkt światła. Tarcze są więc godłami —
    domyślnie uszeregowanymi według jasności na niebie (stąd Wenus większa od Urana),
    a nie według średnicy. Do wyboru są też dwa inne szeregi.</p>
    <p class="note">Pozycje z __POBRANO__. Nad horyzontem: __NAD__. Kod karty na tej stronie
    to <code>sun-cycle-bg.js</code> wklejony dosłownie — wszystko poniżej rysuje jej własny
    <code>buildPlanets()</code>.</p>
  </div>

  <section class="card">
    <h2>Na żywo</h2>
    <p>Kadr w proporcji panelu salonu (16:5). Suwaki zmieniają dokładnie te pola, które
    trafiają do YAML-a pod spodem. <em>Widoczność w dzień</em> to podłoga krycia:
    0 znaczy „w dzień ich nie ma”, 0,35 — tyle zostaje w samo południe, a między
    zmierzchem a nocą karta i tak dochodzi do pełnego krycia. Przesuń suwak Słońca
    w prawo, żeby to zobaczyć.</p>
    <div class="scena szeroka" id="glowna"><div class="horyzont"></div></div>
    <div class="panel">
      <label class="pole"><b>Wielkość (Jowisz, % szerokości) — <span id="v-size"></span></b>
        <input type="range" id="size" min="0.6" max="6" step="0.1" value="1.2"></label>
      <label class="pole"><b>Poświata — <span id="v-glow"></span></b>
        <input type="range" id="glow" min="0" max="2" step="0.05" value="0.35"></label>
      <label class="pole"><b>Widoczność w dzień — <span id="v-day"></span></b>
        <input type="range" id="day" min="0" max="1" step="0.05" value="0.35"></label>
      <label class="pole"><b>Wysokość Słońca — <span id="v-elev"></span>°</b>
        <input type="range" id="elev" min="-25" max="30" step="0.5" value="-25"></label>
      <label class="pole"><b>Znikają poniżej — <span id="v-min"></span>°</b>
        <input type="range" id="min" min="-5" max="20" step="1" value="0"></label>
      <label class="pole"><b>Szereg wielkości</b>
        <select id="szereg">
          <option value="diameters">wg prawdziwych średnic</option>
          <option value="brightness">wg jasności (domyślny karty)</option>
          <option value="equal">wszystkie równe</option>
        </select></label>
      <label class="pole"><b>Pozycje</b>
        <select id="pozycje">
          <option value="prawdziwe">prawdziwe (ze snapshotu)</option>
          <option value="rozstaw">rozstawione — wszystkie widoczne</option>
        </select></label>
    </div>
    <div class="ptaszki">
      <label><input type="checkbox" id="labels"> podpisy pod tarczami</label>
      <label><input type="checkbox" id="gwiazdy" checked> pole gwiazd pod spodem</label>
    </div>
    <div class="ciala" id="ciala"></div>
    <p class="etykieta">Przepis — zaznacz i wklej mi w czacie:</p>
    <div class="przepis" id="przepis"></div>
    <p class="etykieta">YAML do karty:</p>
    <div class="yaml" id="yaml"></div>
  </section>

  <section class="card">
    <h2>Pięć wielkości</h2>
    <p>Ta sama chwila i ten sam szereg (wg średnic), tylko <code>size</code> inne. Kadr 16:9,
    planety rozstawione, żeby w każdym wariancie było widać całą ósemkę.</p>
    <div class="siatka" id="rozmiary"></div>
  </section>

  <section class="card">
    <h2>Wycinki</h2>
    <p>Pliki <code>p_*.jpg</code> to rendery na czarnym niebie z gwiazdami. Tło jest zdejmowane
    przez <code>tools/cutout_planets.py</code>: próg jasności, największa spójna składowa (to
    zawsze planeta, nigdy gwiazda), dziury wypełnione, brzeg zmiękczony jednym pikselem.
    Wnętrze dopasowanego koła jest w pełni kryjące — inaczej nocna strona Marsa czy Merkurego
    prześwitywałaby niebem. Pierścienie Saturna, Urana i Neptuna zostają półprzezroczyste,
    bo są półprzezroczyste naprawdę.</p>
    <div class="wycinki" id="wycinki"></div>
    <p class="note" style="margin-top:12px">Kolumna <em>tarcza</em> to
    <code>[średnica, cx, cy]</code> kuli wewnątrz pliku — mierzone dopasowaniem okręgu (RANSAC),
    bo prostokąt otaczający mierzyłby pierścienie Saturna (0,95 pliku zamiast 0,43), a
    transformata odległościowa mierzyłaby oświetlony sierp Marsa. Karta skaluje
    <strong>kulę</strong>, więc Saturn nie kurczy się przez własne pierścienie.</p>
  </section>

  <section class="card">
    <h2>Skąd biorą się pozycje</h2>
    <p>Integracja Sol (HACS) publikuje dla każdego ciała azymut, wysokość, wschód, zachód,
    górowanie i dołowanie. Karta czyta dwa pierwsze i rzutuje je tak samo jak Słońce
    i Księżyc — okno azymutu __AZOKNO__ na szerokość kadru, wysokość na jego wysokość.</p>
    <table id="tabela"></table>
  </section>

  <p class="note"><strong>Wdrożenie:</strong> wybrane wartości idą do bloku
  <code>planets:</code> karty <code>custom:sun-cycle-bg-card</code>
  (<code>scripts/generate_dashboard.py</code> w panelu). Obrazki leżą w
  <code>/local/sun-cycle/planets/</code> — karta ich nie wozi, tak samo jak nie wozi
  <code>sun.png</code> i <code>moon.png</code>. Bez bloku <code>planets:</code> karta rysuje
  dokładnie to, co 1.4.</p>
</main>

<script>
/* ---- karta sun-cycle-bg, wklejona dosłownie z ../src/sun-cycle-bg.js ---- */
__KARTA__
</script>
<script>
(() => {
  const SNAP = __SNAP__;
  const SREDNICE = __SREDNICE__;
  const NAZWY = __NAZWY__;
  const AZ0 = __AZ0__, AZ1 = __AZ1__;
  const B = window.sunCycleBg;
  const CIALA = B.PLANET_BODIES;
  const OBRAZKI = '__OBRAZKI__';

  /* --- niebo: STOPS z sun-cycle-bg (paletteFor jest wystawione przez kartę) --- */
  function niebo(el, e) {
    const p = B.paletteFor(e, false);
    const rgb = (c) => 'rgb(' + c.map(Math.round).join(',') + ')';
    el.style.background = 'linear-gradient(200deg,' + rgb(p.top) + ' 0%,' +
      rgb(p.mid) + ' 48%,' + rgb(p.bot) + ' 100%)';
    return p.stars;
  }
  const proj = (alt, az) => ({
    x: Math.max(-0.05, Math.min(1.05, (az - AZ0) / (AZ1 - AZ0))) * 100,
    y: 92 - Math.max(-0.1, Math.min(1, (alt + 6) / 60)) * 86,
  });

  /* --- stany: albo prawdziwe ze snapshotu, albo rozstawione po niebie --- */
  function stany(tryb) {
    const s = {};
    CIALA.forEach((b, i) => {
      const p = SNAP.planety[b] || {};
      let az = Number(p.azimuth), alt = Number(p.elevation);
      if (tryb === 'rozstaw') {
        az = AZ0 + (AZ1 - AZ0) * (i + 0.5) / CIALA.length;
        alt = 8 + 30 * Math.sin((i + 0.5) / CIALA.length * Math.PI);
      }
      s['sensor.sol_' + b + '_azimuth'] = { state: String(az) };
      s['sensor.sol_' + b + '_elevation'] = { state: String(alt) };
    });
    return s;
  }

  // the ladders belong to the card (`scale: diameters` etc.); the page only
  // names them, so a number chosen here is the number that ships
  const SZEREGI = B.PLANET_SCALES;

  /* --- scena: prawdziwa warstwa karty --- */
  function scena(host, cfg, elev, tryb, gwiazdy) {
    let box = host.querySelector('.warstwy');
    if (!box) {
      box = document.createElement('div');
      box.className = 'warstwy';
      host.insertBefore(box, host.firstChild);
    }
    const stara = box.querySelector('.sun-cycle-stars');
    if (stara && stara.scsStop) stara.scsStop();
    box.innerHTML = '';
    const r = host.getBoundingClientRect();
    const W = Math.max(1, Math.round(r.width)), H = Math.max(1, Math.round(r.height));
    const kr = niebo(host, elev);
    if (gwiazdy) {
      const pole = B.buildStars(B.readStarConfig({ count: 150, sizes: 'mixed', size: .5,
        glow: .05, twinkle: .45, drift: 0 }), W, H, proj);
      pole.style.opacity = kr.toFixed(2);
      box.appendChild(pole);
    }
    const layer = B.buildPlanets(cfg);
    box.appendChild(layer);
    B.placePlanets(layer, cfg, stany(tryb), proj, elev);
    return layer;
  }

  /* --- panel na żywo --- */
  const G = document.getElementById('glowna');
  const el = {};
  ['size','glow','day','elev','min','szereg','pozycje','labels','gwiazdy']
    .forEach(id => el[id] = document.getElementById(id));

  const wybrane = new Set(CIALA);
  const cialaBox = document.getElementById('ciala');
  CIALA.forEach(b => {
    const lab = document.createElement('label');
    const i = document.createElement('input');
    i.type = 'checkbox'; i.checked = true; i.dataset.body = b;
    i.addEventListener('change', () => { i.checked ? wybrane.add(b) : wybrane.delete(b); rysuj(); });
    lab.appendChild(i);
    lab.appendChild(document.createTextNode(NAZWY[b] || b));
    cialaBox.appendChild(lab);
  });

  const fmt = (v, n) => Number(v).toFixed(n).replace('.', ',');
  function config() {
    return B.readPlanetConfig({
      images: OBRAZKI,
      bodies: CIALA.filter(b => wybrane.has(b)),
      size: +el.size.value,
      glow: +el.glow.value,
      min_elevation: +el.min.value,
      scale: el.szereg.value,
      names: NAZWY,             // karta podpisuje po angielsku, strona po polsku
      labels: el.labels.checked,
      day: +el.day.value,
    });
  }

  function yaml(cfg) {
    const l = ['planets:'];
    l.push('  size: ' + cfg.size);
    if (cfg.glow !== 0.5) l.push('  glow: ' + cfg.glow);
    if (cfg.min_elevation !== 0) l.push('  min_elevation: ' + cfg.min_elevation);
    if (cfg.labels) {
      l.push('  labels: true');
      l.push('  names:');
      cfg.bodies.forEach(b => l.push('    ' + b + ': ' + (NAZWY[b] || b)));
    }
    if (cfg.day > 0) l.push('  day: ' + cfg.day);
    if (cfg.bodies.length !== CIALA.length)
      l.push('  bodies: [' + cfg.bodies.join(', ') + ']');
    if (el.szereg.value !== 'brightness') l.push('  scale: ' + el.szereg.value);
    if (cfg.images !== '/local/sun-cycle/planets/') l.push('  images: ' + cfg.images);
    return l.join('\n');
  }

  function przepis(cfg) {
    const pad = (s) => (s + '                ').slice(0, 16);
    const pikseli = (b) => Math.round(1280 * cfg.size * (cfg.scale[b] || 1) / 100);
    return [
      'strona tlo-planety',
      pad('wielkosc') + fmt(cfg.size, 1) + ' % szerokosci (Jowisz ~' + pikseli('jupiter') + ' px na 1280)',
      pad('poswiata') + fmt(cfg.glow, 2),
      pad('szereg') + el.szereg.options[el.szereg.selectedIndex].text,
      pad('znikaja pod') + cfg.min_elevation + ' stopni',
      pad('podpisy') + (cfg.labels ? 'tak' : 'nie'),
      pad('w dzien') + (cfg.day > 0 ? fmt(cfg.day, 2) + ' krycia' : 'niewidoczne'),
      pad('ciala') + cfg.bodies.map(b => NAZWY[b] || b).join(', '),
      pad('slonce') + fmt(el.elev.value, 1) + ' stopni (podglad)',
      pad('pozycje') + el.pozycje.options[el.pozycje.selectedIndex].text,
      pad('najmniejszy') + (() => {
        const b = cfg.bodies.slice().sort((x, y) => (cfg.scale[x] || 1) - (cfg.scale[y] || 1))[0];
        return b ? (NAZWY[b] || b) + ' ~' + pikseli(b) + ' px' : '—';
      })(),
    ].join('\n');
  }

  function rysuj() {
    const cfg = config();
    scena(G, cfg, +el.elev.value, el.pozycje.value, el.gwiazdy.checked);
    document.getElementById('v-size').textContent = fmt(el.size.value, 1);
    document.getElementById('v-glow').textContent = fmt(el.glow.value, 2);
    document.getElementById('v-day').textContent =
      +el.day.value > 0 ? fmt(el.day.value, 2) : 'niewidoczne';
    document.getElementById('v-elev').textContent = fmt(el.elev.value, 1);
    document.getElementById('v-min').textContent = el.min.value;
    document.getElementById('yaml').textContent = yaml(cfg);
    document.getElementById('przepis').textContent = przepis(cfg);
  }
  Object.values(el).forEach(e => e.addEventListener('input', rysuj));

  /* --- pięć wielkości --- */
  const ROZMIARY = [0.9, 1.2, 1.8, 2.4, 3.6];
  const siatka = document.getElementById('rozmiary');
  ROZMIARY.forEach((s, i) => {
    const w = document.createElement('div');
    w.className = 'wariant';
    w.innerHTML = '<h3>S' + (i + 1) + ' — size: ' + String(s).replace('.', ',') +
      ' <em>· Jowisz ' + Math.round(1280 * s / 100) + ' px na 1280</em></h3>' +
      '<div class="scena kadr"><div class="horyzont"></div></div>';
    siatka.appendChild(w);
    const host = w.querySelector('.scena');
    requestAnimationFrame(() => scena(host, B.readPlanetConfig({
      images: OBRAZKI, size: s, labels: true, scale: 'diameters',
      glow: 0.35 }), -18, 'rozstaw', true));
  });

  /* --- wycinki --- */
  const wyc = document.getElementById('wycinki');
  Object.keys(B.PLANET_DISCS).forEach(b => {
    const d = B.PLANET_DISCS[b];
    const e = document.createElement('div');
    e.className = 'wycinek';
    e.innerHTML = '<div><img src="' + OBRAZKI + b + '.png" alt=""></div>' +
      '<b>' + (NAZWY[b] || b) + '</b>tarcza ' + d.map(v => String(v).replace('.', ',')).join(' · ');
    wyc.appendChild(e);
  });

  /* --- tabela pozycji --- */
  const t = document.getElementById('tabela');
  t.innerHTML = '<tr><th>ciało</th><th>azymut</th><th>wysokość</th><th>wschód</th>' +
    '<th>zachód</th><th>średnica</th><th>godło (wg średnic)</th></tr>';
  CIALA.forEach(b => {
    const p = SNAP.planety[b] || {};
    const alt = Number(p.elevation);
    const godz = (s) => s ? new Date(s).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' }) : '—';
    const tr = document.createElement('tr');
    tr.innerHTML = '<td>' + (NAZWY[b] || b) + '</td>' +
      '<td class="l">' + fmt(p.azimuth, 0) + '°</td>' +
      '<td class="l ' + (alt > 0 ? 'nad' : 'pod') + '">' + fmt(alt, 1) + '°</td>' +
      '<td class="l">' + godz(p.rise) + '</td><td class="l">' + godz(p.set) + '</td>' +
      '<td class="l">' + SREDNICE[b].toLocaleString('pl-PL') + ' km</td>' +
      '<td class="l">×' + String(B.PLANET_SCALES.diameters[b]).replace('.', ',') +
      ' <span style="color:var(--muted)">(jasność ×' +
      String(B.PLANET_SCALE[b]).replace('.', ',') + ')</span></td>';
    t.appendChild(tr);
  });

  addEventListener('resize', () => { clearTimeout(window._t); window._t = setTimeout(rysuj, 200); });
  rysuj();
})();
</script>
"""

META = {
    "tytul": "Tło: planety z integracji Sol",
    "grupa": "Tło (sun-cycle-bg)",
    "status": "aktualne",
    "kolejnosc": 105,
    "opis": ("Osiem planet na tle nieba, pozycje z integracji Sol (sensor.sol_*_azimuth "
             "i _elevation), rysunek z wyciętych zdjęć z przezroczystym tłem. Panel na żywo: "
             "wielkość tarcz, poświata, widoczność w dzień, szereg wielkości (prawdziwe średnice "
             "/ jasność / równe), próg znikania, podpisy, wybór ciał — plus gotowy YAML i przepis "
             "do skopiowania. "
             "Niżej pięć wielkości na kadrach 16:9, galeria wycinków z pomiarem tarczy i tabela "
             "pozycji ze wschodami i zachodami."),
}


def main() -> int:
    snap = json.loads(SNAP.read_text())
    nad = [NAZWY[b] for b, w in snap["planety"].items()
           if float(w.get("elevation", -99)) > 0]
    html = (STRONA
            .replace("__KARTA__", KARTA.read_text())
            .replace("__SNAP__", json.dumps(snap, ensure_ascii=False))
            .replace("__SREDNICE__", json.dumps(SREDNICE))
            .replace("__NAZWY__", json.dumps(NAZWY, ensure_ascii=False))
            .replace("__AZ0__", "50").replace("__AZ1__", "310")
            .replace("__AZOKNO__", "50°–310°")
            .replace("__OBRAZKI__", "/local/sun-cycle/planets/")
            .replace("__POBRANO__", snap["pobrano"][:16].replace("T", " "))
            .replace("__NAD__", ", ".join(nad) if nad else "żadna"))
    OUT.write_text(html)
    OUT.with_suffix(".meta.json").write_text(json.dumps(META, ensure_ascii=False, indent=1) + "\n")
    print(f"{OUT} ({len(html) // 1024} kB) + {OUT.with_suffix('.meta.json').name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
