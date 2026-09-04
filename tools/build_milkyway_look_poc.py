#!/usr/bin/env python3
"""Build the Milky Way *look* page: demo/droga-mleczna-widok.html

The sibling page, tools/build_milkyway_poc.py, answers one question: where does
the band really stand over this house at this hour. This one answers the other:
what should the panel show so that it looks good. The two are not the same
question and, at 53.5 deg N, they pull apart badly - the sharpest photograph on
hand looks at the galactic centre, and half of that region never rises here at
all (median culmination -0.9 deg, only 15 % of it ever clears the 22 deg where
the card's horizon fade begins).

So this page drops the constraint. It offers the same band drawn four ways and
lets the choice be made by eye:

  panorama   the all-sky ESO panorama, 4096x2048. True everywhere, and soft:
             4096/360 = 11.4 px/deg against the ~15 px/deg the panel asks for
             down the frame.
  kadr 4k    the sharp frame, 3920 px across, placed wherever it looks best.
             The card already takes this: `projection: frame` plus l/b/rot/fov.
             The geometry stays honest - the picture still turns with the sky -
             only the claim about which piece of sky it is gets dropped.
  kadr       the frame that ships with the card, 1168 px. Same thing, softer.
  przypiety  the frame pinned to the panel: no sidereal rotation at all, the
             band simply sits where it is put. The steadiest composition and
             the only one the card cannot do today - it would need a third
             `projection` value.

Every scene is drawn by the card's own code (../src/sun-cycle-bg.js pasted in
verbatim): sky palette, star field, and the same mesh warp the card runs.

    python3 tools/build_milkyway_look_poc.py
    python3 ~/CodeHub/hassio/ha-panel-salon-sekcje/scripts/poc_upload.py \
        demo/droga-mleczna-widok.html
"""
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
KARTA = ROOT / "src" / "sun-cycle-bg.js"
OUT = ROOT / "demo" / "droga-mleczna-widok.html"
LAT, LON = 52.2297, 21.0122
AZ0, AZ1 = 50, 310

PANORAMA = "/local/sun-cycle/milky-way.jpg?v=2"      # ESO/S. Brunier, 4096x2048
KADR4K = "/local/sun-cycle/milky-way-4k.webp"        # 3920x1960, tlo zdjete
KADR = "/local/sun-cycle/milky-way-cutout.webp"      # 1168x784, tlo zdjete

# Ustawienia do porownania. Kazde to jeden kompletny stan panelu na zywo -
# klikniecie "wez ten" przepisuje je na suwaki.
WARIANTY = [
    {"id": "panorama", "nazwa": "Panorama ESO 4096",
     "opis": "To, co panel pokazuje dzisiaj, po podbiciu tekstury z 2048 na 4096 px. "
             "Prawdziwe niebo, cały pas, obraz najbliższy temu, co karta umie bez zmian.",
     "s": {"zrodlo": "panorama", "jasnosc": 0.9, "horyzont": 22}},
    {"id": "kadr-prawa", "nazwa": "Ostry kadr, ukośnie po prawej",
     "opis": "Najlepsze z 16 położeń przejrzanych na tej stronie o 23:30. Zdjęcie jest "
             "ostre, ale gnomoniczny kadr o rozpiętości 110° siedzi w oknie szerokim na "
             "260° — więcej niż pół panelu nie zajmie, choćby go przesuwać dowolnie.",
     "s": {"zrodlo": "kadr4k", "kl": 30, "kb": 0, "krot": 30, "kfov": 110,
           "jasnosc": 0.9, "horyzont": 16}},
    {"id": "kadr-gora", "nazwa": "Ostry kadr, szeroko pod górną krawędzią",
     "opis": "To samo zdjęcie położone płasko: pas idzie wtedy przez górę kadru, a dół "
             "panelu zostaje pusty na kafle.",
     "s": {"zrodlo": "kadr4k", "kl": 60, "kb": -15, "krot": 60, "kfov": 110,
           "jasnosc": 0.9, "horyzont": 16}},
    {"id": "kadr-karty", "nazwa": "Kadr karty (1168 px), to samo miejsce",
     "opis": "Dla porównania ostrości: zdjęcie, które karta wysyła dzisiaj, w tym samym "
             "położeniu co wariant wyżej.",
     "s": {"zrodlo": "kadr", "kl": 30, "kb": 0, "krot": 30, "kfov": 110,
           "jasnosc": 0.9, "horyzont": 16}},
    {"id": "przypiety", "nazwa": "Przypięty do panelu",
     "opis": "Bez obrotu nieba: zdjęcie ląduje wprost w kadrze. Jako jedyny wariant "
             "wypełnia panel całą szerokością i trzyma tę samą kompozycję o każdej porze "
             "roku i doby. Wymaga nowej wartości `projection` w karcie.",
     "s": {"zrodlo": "przypiety", "pskala": 1.35, "px": 50, "py": 46, "prot": -16,
           "jasnosc": 0.85, "horyzont": 16}},
    {"id": "przypiety-mocny", "nazwa": "Przypięty, bliżej i jaśniej",
     "opis": "To samo powiększone: pas robi się głównym motywem tła zamiast tłem tła.",
     "s": {"zrodlo": "przypiety", "pskala": 1.9, "px": 56, "py": 40, "prot": -22,
           "jasnosc": 1.0, "horyzont": 12}},
]

STRONA = r"""<meta charset="utf-8">
<title>Droga Mleczna: jak ma wyglądać</title>
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
  strong { color:var(--text); }

  .scena { position:relative; border-radius:14px; overflow:hidden; border:1px solid var(--line); }
  .scena.szeroka { aspect-ratio:16/5; }
  .warstwy { position:absolute; inset:0; }
  canvas.mw { position:absolute; inset:0; width:100%; height:100%; }

  .panel { display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr));
           gap:12px 18px; margin-top:14px; }
  .pole { display:flex; flex-direction:column; gap:4px; font-size:12.5px; color:var(--muted); }
  .pole b { color:var(--text); font-weight:600; font-size:12.5px; }
  .pole input[type=range] { width:100%; accent-color:var(--accent); }
  .pole select { background:#0e131a; color:var(--text); border:1px solid var(--line);
    border-radius:8px; padding:5px 7px; font:inherit; font-size:13px; }
  .ptaszki { display:flex; flex-wrap:wrap; gap:10px 16px; margin-top:12px; font-size:13px; }
  .ptaszki label { display:flex; align-items:center; gap:6px; color:var(--muted); }

  .warianty { display:flex; flex-direction:column; gap:18px; }
  .wariant h3 { margin:0 0 2px; font-size:14.5px; font-weight:650; }
  .wariant p { margin:0 0 8px; color:var(--muted); font-size:13px; max-width:92ch; }
  .wariant .naglowek { display:flex; align-items:baseline; gap:12px; justify-content:space-between; }
  button.wez { background:#1d2836; color:var(--accent); border:1px solid var(--line);
    border-radius:9px; padding:5px 12px; font:inherit; font-size:12.5px; cursor:pointer;
    white-space:nowrap; }
  button.wez:hover { background:#243248; }

  .przepis { margin-top:14px; background:#0b0f15; border:1px solid var(--line);
    border-radius:12px; padding:12px 14px; font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
    white-space:pre-wrap; user-select:all; color:#d7e2f2; }
  .etykieta { font-size:12px; color:var(--muted); margin:14px 0 0; }
  .note { color:var(--muted); font-size:13px; }
</style>

<main>
  <div class="lead">
    <h1>Droga Mleczna: jak ma wyglądać</h1>
    <p>Siostrzana strona <em>Droga Mleczna nad Bartoszewem</em> odpowiada na pytanie, gdzie
    pas naprawdę stoi o danej godzinie. Ta odpowiada na drugie: co ma pokazać panel, żeby
    to dobrze wyglądało. Na 53,5&deg; N te dwa pytania się rozjeżdżają &mdash; najostrzejsze
    zdjęcie, jakie mamy, patrzy na centrum Galaktyki, a połowa tego rejonu nigdy tu nie
    wschodzi (mediana górowania &minus;0,9&deg;, tylko 15&nbsp;% powierzchni kiedykolwiek
    przekracza 22&deg;, od których karta zaczyna wygaszać pas przy horyzoncie).</p>
    <p>Więc ta strona zdejmuje ten warunek. Cztery źródła, jedno okno panelu (16:5, azymut
    50&deg;&ndash;310&deg; jak na salonie), wybór okiem:</p>
    <p><strong>panorama</strong> &mdash; panorama całego nieba ESO, teraz 4096&times;2048
    zamiast 2048&times;1024. Prawdziwa wszędzie i najmiększa: 4096/360 = 11,4&nbsp;px na
    stopień wobec ~15&nbsp;px/stopień, których panel potrzebuje w pionie.<br>
    <strong>kadr 4k</strong> &mdash; ostre zdjęcie 3920&nbsp;px, wstawione tam, gdzie
    wygląda najlepiej. Karta już to potrafi: <code>projection: frame</code> plus
    <code>l/b/rot/fov</code>. Geometria zostaje uczciwa (obraz dalej obraca się z niebem),
    znika tylko twierdzenie, że to akurat ten kawałek nieba.<br>
    <strong>kadr</strong> &mdash; kadr, który wysyła karta, 1168&nbsp;px. To samo, tylko miększe.<br>
    <strong>przypiety</strong> &mdash; kadr przypięty do panelu, bez obrotu nieba. Kompozycja
    stoi w miejscu o każdej porze. Jedyny wariant, którego karta dziś nie umie: wymagałby
    trzeciej wartości <code>projection</code>.</p>
    <p class="note">Niebo, gwiazdy i sam warp rysuje <code>sun-cycle-bg.js</code> wklejony
    w tę stronę dosłownie. Panorama: <strong>__KREDYT__</strong>. Ostry kadr pochodzi z pliku
    wrzuconego do <code>~/Pobrane</code> 31.08 &mdash; przed publikacją gdziekolwiek poza
    domowym HA trzeba sprawdzić jego licencję, bo to nie jest własne zdjęcie.</p>
  </div>

  <section class="card">
    <h2>Na żywo</h2>
    <p>Suwak godziny przesuwa noc: warianty związane z niebem będą płynąć, przypięty stoi.
    Wysokość Słońca ustawia paletę karty, żeby było widać, jak pas gaśnie o zmierzchu.</p>
    <div class="scena szeroka" id="glowna"></div>
    <div class="panel">
      <label class="pole"><b>Źródło</b>
        <select id="zrodlo">
          <option value="kadr4k">kadr 4k (3920 px, ostry)</option>
          <option value="panorama">panorama ESO 4096 (całe niebo)</option>
          <option value="kadr">kadr karty (1168 px)</option>
          <option value="przypiety">przypięty do panelu (bez obrotu nieba)</option>
        </select></label>
      <label class="pole"><b>Godzina &mdash; <span id="v-godz"></span></b>
        <input type="range" id="godz" min="18" max="30" step="0.25" value="23.5"></label>
      <label class="pole"><b>Jasność pasa &mdash; <span id="v-jasn"></span></b>
        <input type="range" id="jasn" min="0" max="1" step="0.02" value="0.85"></label>
      <label class="pole"><b>Zanik przy horyzoncie od &mdash; <span id="v-hor"></span>&deg;</b>
        <input type="range" id="hor" min="0" max="40" step="1" value="18"></label>
      <label class="pole"><b>Wysokość Słońca &mdash; <span id="v-slonce"></span>&deg;</b>
        <input type="range" id="slonce" min="-25" max="6" step="0.5" value="-18"></label>
    </div>
    <div class="panel" id="panel-kadr">
      <label class="pole"><b>Kadr: długość galakt. &mdash; <span id="v-kl"></span>&deg;</b>
        <input type="range" id="kl" min="0" max="359" step="1" value="30"></label>
      <label class="pole"><b>Kadr: szerokość galakt. &mdash; <span id="v-kb"></span>&deg;</b>
        <input type="range" id="kb" min="-40" max="40" step="1" value="0"></label>
      <label class="pole"><b>Kadr: obrót &mdash; <span id="v-krot"></span>&deg;</b>
        <input type="range" id="krot" min="-90" max="90" step="1" value="30"></label>
      <label class="pole"><b>Kadr: rozpiętość &mdash; <span id="v-kfov"></span>&deg; nieba</b>
        <input type="range" id="kfov" min="30" max="150" step="2" value="110"></label>
    </div>
    <div class="panel" id="panel-przypiety">
      <label class="pole"><b>Przypięty: skala &mdash; <span id="v-pskala"></span>&times;</b>
        <input type="range" id="pskala" min="0.6" max="3" step="0.05" value="1.35"></label>
      <label class="pole"><b>Przypięty: środek w poziomie &mdash; <span id="v-px"></span>&nbsp;%</b>
        <input type="range" id="px" min="0" max="100" step="1" value="50"></label>
      <label class="pole"><b>Przypięty: środek w pionie &mdash; <span id="v-py"></span>&nbsp;%</b>
        <input type="range" id="py" min="0" max="100" step="1" value="46"></label>
      <label class="pole"><b>Przypięty: obrót &mdash; <span id="v-prot"></span>&deg;</b>
        <input type="range" id="prot" min="-45" max="45" step="1" value="-16"></label>
    </div>
    <div class="ptaszki">
      <label><input type="checkbox" id="gwiazdy" checked> pole gwiazd karty</label>
      <label><input type="checkbox" id="tylkopas"> sam pas, bez nieba</label>
    </div>
    <p class="etykieta">Przepis &mdash; zaznacz i wklej mi w czacie:</p>
    <div class="przepis" id="przepis"></div>
  </section>

  <section class="card">
    <h2>Warianty</h2>
    <p>Ta sama godzina i to samo Słońce dla wszystkich. &bdquo;Weź ten&rdquo; przepisuje
    ustawienia na panel wyżej, gdzie można je dociągnąć suwakami.</p>
    <div class="warianty" id="warianty"></div>
  </section>

  <p class="note"><strong>Co to znaczy dla karty:</strong> cztery pierwsze warianty nie
  wymagają w niej ani jednej linii &mdash; to sam config (<code>milky_way.image</code>,
  <code>projection</code>, <code>l/b/rot/fov</code>, <code>strength</code>,
  <code>horizon</code>). Dwa ostatnie wymagają nowej wartości <code>projection</code>, która
  pomija całą geometrię nieba i stawia zdjęcie wprost w kadrze &mdash; kilkanaście linii
  w <code>drawMilky</code>.</p>
</main>

<script>
/* ---- karta sun-cycle-bg, wklejona doslownie z ../src/sun-cycle-bg.js ---- */
__KARTA__
</script>
<script>
(() => {
  const ZRODLA = {
    panorama: { url: '__PANORAMA__', typ: 'equirect' },
    kadr4k:   { url: '__KADR4K__',   typ: 'frame' },
    kadr:     { url: '__KADR__',     typ: 'frame' },
    przypiety:{ url: '__KADR4K__',   typ: 'pin' },
  };
  const WARIANTY = __WARIANTY__;
  const LAT = __LAT__, LON = __LON__, AZ0 = __AZ0__, AZ1 = __AZ1__;
  const DATA = '__DATA_ISO__';
  const B = window.sunCycleBg;
  const D2R = Math.PI / 180, R2D = 180 / Math.PI;
  const OKNO = { min: -6, max: 54, az0: __AZ0__, az1: __AZ1__ };  // drawMilkyPanorama czyta az0/az1

  function julian(d) {
    let y = d.getUTCFullYear(), m = d.getUTCMonth() + 1;
    if (m <= 2) { y -= 1; m += 12; }
    const a = Math.floor(y / 100), b = 2 - a + Math.floor(a / 4);
    const dzien = d.getUTCDate() + (d.getUTCHours() + d.getUTCMinutes() / 60) / 24;
    return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + dzien + b - 1524.5;
  }
  const gmst = (J) => (280.46061837 + 360.98564736629 * (J - 2451545)) % 360;
  function altaz(ra, dec, J) {
    const H = ((gmst(J) + LON - ra) % 360) * D2R, dr = dec * D2R, pr = LAT * D2R;
    const alt = Math.asin(Math.sin(dr) * Math.sin(pr) + Math.cos(dr) * Math.cos(pr) * Math.cos(H));
    const az = Math.atan2(-Math.sin(H) * Math.cos(dr),
      Math.cos(pr) * Math.sin(dr) - Math.sin(pr) * Math.cos(dr) * Math.cos(H));
    return { alt: alt * R2D, az: ((az * R2D) % 360 + 360) % 360 };
  }
  const rzut = (alt, az) => ({
    x: Math.max(-0.05, Math.min(1.05, (az - AZ0) / (AZ1 - AZ0))) * 100,
    y: 92 - Math.max(-0.1, Math.min(1, (alt - OKNO.min) / (OKNO.max - OKNO.min))) * 86,
  });
  const czas = (godz) => new Date(new Date(DATA).getTime() + godz * 3600e3);

  const OBRAZY = {};
  function wczytajWszystko(gotowe) {
    const nazwy = Object.keys(ZRODLA);
    let zostalo = nazwy.length;
    nazwy.forEach((n) => {
      const im = new Image();
      im.crossOrigin = 'anonymous';
      const krok = () => { if (--zostalo === 0) gotowe(); };
      im.onload = () => { OBRAZY[n] = im; krok(); };
      im.onerror = () => { OBRAZY[n] = 'blad'; krok(); };
      im.src = ZRODLA[n].url;
    });
  }

  /* gradient ekstynkcji - identyczny z milkyHorizon() w karcie */
  function wygasHoryzont(gb, horyzont, W, H) {
    const yDla = (a) => (92 - (a - OKNO.min) / (OKNO.max - OKNO.min) * 86) / 100 * H;
    const grad = gb.createLinearGradient(0, yDla(horyzont), 0, H);
    grad.addColorStop(0, 'rgba(0,0,0,1)');
    grad.addColorStop(0.45, 'rgba(0,0,0,0.72)');
    grad.addColorStop(0.78, 'rgba(0,0,0,0.28)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    gb.globalCompositeOperation = 'destination-in';
    gb.fillStyle = grad;
    gb.fillRect(0, 0, W, H);
    gb.globalCompositeOperation = 'source-over';
  }

  let BUFOR = null;
  /* Warianty zwiazane z niebem rysuje sama karta: B.drawMilky() to ten sam kod,
     ktory chodzi na panelu, wiec strona nie moze pokazac czegos, czego karta nie
     narysuje. Pierwsza wersja tej strony miala wlasna kopie warpu i dla panoramy
     rysowala siatke po pikselach obrazu zamiast po niebie - z bieguna galaktycznego
     robil sie wachlarz slivkow i ciemne krawedzie, ktorych na panelu nie ma.
     Wlasnego kodu zostal tu tylko wariant przypiety, bo jego karta nie umie. */
  function rysujPas(cv, godz, o) {
    const r = cv.getBoundingClientRect();
    const W = Math.max(1, Math.round(r.width)), H = Math.max(1, Math.round(r.height));
    const obraz = OBRAZY[o.zrodlo];
    if (!obraz || obraz === 'blad') return { ms: 0, oczek: 0 };
    const typ = ZRODLA[o.zrodlo].typ;
    const start = performance.now();

    if (typ !== 'pin') {
      cv._img = obraz;
      const cfg = B.readMilkyConfig({
        image: ZRODLA[o.zrodlo].url,
        projection: typ === 'equirect' ? 'equirect' : 'frame',
        l: o.kl, b: o.kb, rot: o.krot, fov: o.kfov,
        strength: 1, horizon: o.horyzont,
      }, '');
      const oczek = B.drawMilky(cv, cfg, rzut, julian(czas(godz)), LAT, LON,
                               Math.max(0, Math.min(1, o.jasnosc)), OKNO);
      return { ms: performance.now() - start, oczek };
    }

    /* przypiety: zadnej geometrii nieba, zdjecie ladauje wprost w kadrze */
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    const g = cv.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, W, H);
    if (!BUFOR) BUFOR = document.createElement('canvas');
    BUFOR.width = cv.width; BUFOR.height = cv.height;
    const gb = BUFOR.getContext('2d');
    gb.setTransform(dpr, 0, 0, dpr, 0, 0);
    gb.clearRect(0, 0, W, H);
    const skala = o.pskala * W / obraz.naturalWidth;
    gb.save();
    gb.translate(o.px / 100 * W, o.py / 100 * H);
    gb.rotate(o.prot * D2R);
    gb.scale(skala, skala);
    gb.drawImage(obraz, -obraz.naturalWidth / 2, -obraz.naturalHeight / 2);
    gb.restore();
    wygasHoryzont(gb, o.horyzont, W, H);
    g.globalCompositeOperation = 'lighter';
    g.globalAlpha = Math.max(0, Math.min(1, o.jasnosc));
    g.drawImage(BUFOR, 0, 0, BUFOR.width, BUFOR.height, 0, 0, W, H);
    g.globalAlpha = 1;
    g.globalCompositeOperation = 'source-over';
    return { ms: performance.now() - start, oczek: 1 };
  }

  function scena(host, godz, o) {
    let box = host.querySelector('.warstwy');
    if (!box) { box = document.createElement('div'); box.className = 'warstwy'; host.appendChild(box); }
    const stare = box.querySelector('.sun-cycle-stars');
    if (stare && stare.scsStop) stare.scsStop();
    box.innerHTML = '';
    const r = host.getBoundingClientRect();
    const W = Math.max(1, Math.round(r.width)), H = Math.max(1, Math.round(r.height));
    const p = B.paletteFor(o.slonce, false);
    const rgb = (c) => 'rgb(' + c.map(Math.round).join(',') + ')';
    host.style.background = o.tylkoPas ? '#05070c'
      : 'linear-gradient(200deg, ' + rgb(p.top) + ' 0%, ' + rgb(p.mid) + ' 48%, ' + rgb(p.bot) + ' 100%)';
    const cv = document.createElement('canvas');
    cv.className = 'mw';
    box.appendChild(cv);
    const miara = rysujPas(cv, godz, o);
    cv.style.opacity = (o.tylkoPas ? 1 : p.stars).toFixed(2);
    if (o.gwiazdy && !o.tylkoPas) {
      const gw = B.buildStars(B.readStarConfig({ count: 150, sizes: 'mixed', size: .5,
        glow: .05, twinkle: .45, drift: 0 }), W, H, rzut);
      gw.style.opacity = p.stars.toFixed(2);
      box.appendChild(gw);
    }
    return miara;
  }

  const G = document.getElementById('glowna');
  const el = {};
  ['zrodlo','godz','jasn','hor','slonce','kl','kb','krot','kfov',
   'pskala','px','py','prot','gwiazdy','tylkopas'].forEach(id => el[id] = document.getElementById(id));
  const fmt = (v, n) => Number(v).toFixed(n).replace('.', ',');
  const godzTekst = (g) => {
    const h = Math.floor(g) % 24, m = Math.round((g % 1) * 60);
    return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
  };
  function opcje() {
    return { zrodlo: el.zrodlo.value, jasnosc: +el.jasn.value, horyzont: +el.hor.value,
             kl: +el.kl.value, kb: +el.kb.value, krot: +el.krot.value, kfov: +el.kfov.value,
             pskala: +el.pskala.value, px: +el.px.value, py: +el.py.value, prot: +el.prot.value,
             slonce: +el.slonce.value, gwiazdy: el.gwiazdy.checked, tylkoPas: el.tylkopas.checked };
  }
  function przepis(o, miara) {
    const pad = (s) => (s + '                ').slice(0, 16);
    const w = ['strona droga-mleczna-widok', pad('zrodlo') +
               el.zrodlo.options[el.zrodlo.selectedIndex].text,
      pad('godzina') + godzTekst(+el.godz.value),
      pad('jasnosc') + fmt(o.jasnosc, 2),
      pad('zanik od') + o.horyzont + ' stopni',
      pad('slonce') + fmt(o.slonce, 1) + ' stopni'];
    if (ZRODLA[o.zrodlo].typ === 'pin') {
      w.push(pad('skala') + fmt(o.pskala, 2) + ' x szerokosci panelu',
             pad('srodek') + o.px + ' % / ' + o.py + ' %',
             pad('obrot') + o.prot + ' stopni');
    } else if (ZRODLA[o.zrodlo].typ === 'frame') {
      w.push(pad('l / b') + o.kl + ' / ' + o.kb + ' stopni',
             pad('obrot') + o.krot + ' stopni',
             pad('rozpietosc') + o.kfov + ' stopni nieba');
    }
    w.push(pad('rysowanie') + fmt(miara.ms, 1) + ' ms, ' + miara.oczek + ' oczek');
    return w.join('\n');
  }
  function rysuj() {
    const o = opcje(), godz = +el.godz.value;
    const miara = scena(G, godz, o);
    document.getElementById('v-godz').textContent = godzTekst(godz);
    document.getElementById('v-jasn').textContent = fmt(o.jasnosc, 2);
    document.getElementById('v-hor').textContent = o.horyzont;
    document.getElementById('v-slonce').textContent = fmt(o.slonce, 1);
    ['kl','kb','krot','kfov','px','py','prot'].forEach(k =>
      document.getElementById('v-' + k).textContent = o[k === 'kl' ? 'kl' : k]);
    document.getElementById('v-pskala').textContent = fmt(o.pskala, 2);
    const typ = ZRODLA[o.zrodlo].typ;
    document.getElementById('panel-kadr').style.display = typ === 'frame' ? '' : 'none';
    document.getElementById('panel-przypiety').style.display = typ === 'pin' ? '' : 'none';
    document.getElementById('przepis').textContent = przepis(o, miara);
  }
  Object.values(el).forEach(e => e.addEventListener('input', rysuj));

  /* --- warianty --- */
  const kosz = document.getElementById('warianty');
  WARIANTY.forEach((w) => {
    const div = document.createElement('div');
    div.className = 'wariant';
    div.innerHTML = '<div class="naglowek"><h3>' + w.nazwa + '</h3>' +
      '<button class="wez" type="button">weź ten</button></div>' +
      '<p>' + w.opis + '</p><div class="scena szeroka"></div>';
    kosz.appendChild(div);
    const stan = Object.assign(opcje(), w.s, { slonce: -18, gwiazdy: true, tylkoPas: false });
    requestAnimationFrame(() => scena(div.querySelector('.scena'), 23.5, stan));
    div.querySelector('button').addEventListener('click', () => {
      Object.entries(w.s).forEach(([k, v]) => {
        const map = { zrodlo: 'zrodlo', jasnosc: 'jasn', horyzont: 'hor' };
        const id = map[k] || k;
        if (el[id]) el[id].value = v;
      });
      rysuj();
      G.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });

  addEventListener('resize', () => { clearTimeout(window._t); window._t = setTimeout(rysuj, 200); });
  wczytajWszystko(() => {
    rysuj();
    kosz.querySelectorAll('.wariant').forEach((div, i) => {
      const stan = Object.assign(opcje(), WARIANTY[i].s,
        { slonce: -18, gwiazdy: true, tylkoPas: false });
      scena(div.querySelector('.scena'), 23.5, stan);
    });
  });
})();
</script>
"""

META = {
    "tytul": "Tło: Droga Mleczna — jak ma wyglądać",
    "grupa": "Tło (sun-cycle-bg)",
    "status": "aktualne",
    "kolejnosc": 107,
    "opis": ("Wybór wyglądu pasa, bez trzymania się prawdziwego nieba nad domem. Cztery "
             "źródła w oknie panelu 16:5: panorama ESO 4096×2048, ostry kadr 3920 px "
             "wstawiony tam, gdzie wygląda najlepiej (położenie wybrane z przeglądu 16 "
             "ustawień na tej stronie), "
             "kadr karty 1168 px oraz kadr przypięty do panelu bez obrotu nieba. Sześć "
             "gotowych wariantów z przyciskiem „weź ten”, panel na żywo (godzina, jasność, "
             "zanik przy horyzoncie, wysokość Słońca, położenie i rozpiętość kadru) "
             "i pole Przepis."),
}


def main() -> int:
    noc = datetime.datetime.now().astimezone().replace(
        hour=0, minute=0, second=0, microsecond=0)
    html = (STRONA
            .replace("__KARTA__", KARTA.read_text())
            .replace("__PANORAMA__", PANORAMA)
            .replace("__KADR4K__", KADR4K)
            .replace("__KADR__", KADR)
            .replace("__WARIANTY__", json.dumps(WARIANTY, ensure_ascii=False))
            .replace("__KREDYT__", "ESO/S. Brunier - CC BY 4.0")
            .replace("__LAT__", str(LAT)).replace("__LON__", str(LON))
            .replace("__AZ0__", str(AZ0)).replace("__AZ1__", str(AZ1))
            .replace("__DATA_ISO__", noc.isoformat()))
    OUT.write_text(html)
    OUT.with_suffix(".meta.json").write_text(json.dumps(META, ensure_ascii=False, indent=1) + "\n")
    print(f"{OUT} ({len(html) // 1024} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
