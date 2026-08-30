#!/usr/bin/env python3
"""Build the Milky Way tuning page: demo/droga-mleczna.html

Same rule as the other tuning pages: ../sun-cycle-bg.js is pasted in verbatim
and every scene is drawn by the card's own code — sky palette, star field,
planets. The one new thing, the band itself, is drawn on a canvas by the code
this page is here to judge before any of it goes into the card.

The band's geometry is baked at build time by tools/milky_way.py: a grid over
galactic latitude and longitude, each patch carrying its equatorial position
(which never changes) and its modelled brightness. The page only rotates that
grid into the sky for the chosen instant, which is a dozen lines of sidereal
time — so the brightness model has one home, in Python, and the page cannot
drift away from it.

    python3 tools/build_milkyway_poc.py
    export BW_SESSION=$(bw unlock --raw)
    python3 ~/CodeHub/hassio/ha-panel-salon-sekcje/scripts/poc_upload.py \\
        demo/droga-mleczna.html
"""
import datetime
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).parent.parent
KARTA = ROOT / "sun-cycle-bg.js"
OUT = ROOT / "demo" / "droga-mleczna.html"
LAT, LON = 53.5182, 14.4570          # Home Assistant's own coordinates
MIEJSCE = "Bartoszewem"   # forma po „nad": tak brzmi w tytule i naglowku

# The baked texture: brightness sampled on a whole-degree galactic grid. The
# page maps every pixel of the frame back onto the sky and reads this, so the
# model has one home — milky_way.py — and cannot drift into a second language.
TEKSTURA = "/local/sun-cycle/milky-way.jpg"          # panorama calego nieba
KADR = "/local/sun-cycle/milky-way-cutout.webp"      # zdjecie z przezroczystym tlem
KREDYT = "ESO/S. Brunier — CC BY 4.0"
# Gdzie na niebie lezy kadr ze zdjecia. Nie na oko: dopasowane korelacja do
# panoramy ESO (przeszukanie po srodku, obrocie i polu widzenia; najlepsze
# r = 0.64 przy zgodnym kacie pasa, jadrze i szczelinie).
KADR_L, KADR_B, KADR_ROT, KADR_FOV = -5.0, -2.0, -24.0, 62.0


STRONA = r"""<meta charset="utf-8">
<title>Droga Mleczna nad __MIEJSCE__</title>
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

  .siatka { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; }
  .wariant { display:flex; flex-direction:column; gap:7px; }
  .wariant h3 { margin:0; font-size:13.5px; font-weight:650; }
  .wariant h3 em { font-style:normal; color:var(--muted); font-weight:400; }

  table { border-collapse:collapse; width:100%; font-size:13px; }
  th, td { text-align:left; padding:5px 10px 5px 0; border-bottom:1px solid var(--line); }
  th { color:var(--muted); font-weight:600; }
  td.l { font-variant-numeric:tabular-nums; }
  .tak { color:#7fe1a8; } .nie { color:#96a0b0; }

  .przepis { margin-top:14px; background:#0b0f15; border:1px solid var(--line);
    border-radius:12px; padding:12px 14px; font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
    white-space:pre-wrap; user-select:all; color:#d7e2f2; }
  .etykieta { font-size:12px; color:var(--muted); margin:14px 0 0; }
  .note { color:var(--muted); font-size:13px; }
</style>

<main>
  <div class="lead">
    <h1>Droga Mleczna nad __MIEJSCE__</h1>
    <p>Pas Drogi Mlecznej to koło wielkie na niebie — szerokość galaktyczna zero. Jego
    miejsce w kadrze to czysta geometria: współrzędne galaktyczne → równikowe → horyzontalne
    dla <strong>__LAT__° N, __LON__° E</strong> i podanej chwili. Nic tu nie jest narysowane
    ręcznie ani skądkolwiek ściągnięte.</p>
    <p>Światło jest <strong>ze zdjęcia</strong> — do wyboru z dwóch. Domyślnie z pliku
    <code>~/Pobrane/milky-way.jpg</code>: kadr okolic centrum Galaktyki, któremu zdjęto
    czarne tło (przezroczystość liczona z jasności, więc puste niebo znika, a obłoki
    zostają). Gdzie ten kadr leży na niebie, nie zgadywałem — dopasowałem go korelacją do
    panoramy ESO: środek <strong>l = −5°, b = −2°</strong>, obrót <strong>−24°</strong>,
    pole widzenia <strong>62°</strong>, r = 0,64, i przy tych liczbach zgadza się kąt pasa,
    położenie jądra i przebieg Wielkiej Szczeliny. Suwaki niżej pozwalają to poprawić okiem.
    Drugie źródło to panorama całego nieba
    <em>The Milky Way panorama</em> (ESO/S. Brunier, GigaGalaxy Zoom, 6000×3000,
    równoprostokątna we współrzędnych galaktycznych, licencja CC BY 4.0), przeskalowana do
    2048×1024. Obłoki gwiazdowe, pas pyłu i Obłoki Magellana są takie, jakie sfotografowano —
    nic tu nie jest rysowane wzorem.</p>
    <p class="note">Niebo, gwiazdy i planety rysuje <code>sun-cycle-bg.js</code> wklejony
    w tę stronę dosłownie. Pas rysuje kod, który ta strona ma ocenić, zanim cokolwiek z niego
    trafi do karty: każdy piksel kadru wraca na niebo (wysokość i azymut → rektascensja
    i deklinacja → współrzędne galaktyczne) i czyta próbkę z panoramy. Zdjęcie:
    <strong>__KREDYT__</strong>.</p>
  </div>

  <section class="card">
    <h2>Na żywo</h2>
    <p>Kadr w proporcji panelu salonu (16:5), okno azymutu jak na panelu (50°–310°).
    Suwak godziny przesuwa noc z __DATA__ na __DATA_DO__ — widać, jak pas obraca się
    wraz z niebem: wieczorem centrum Galaktyki nisko na południu, nad ranem pas staje
    dęba na wschodzie.</p>
    <div class="scena szeroka" id="glowna"></div>
    <p class="note" style="margin-top:10px"><strong>Uwaga o kadrze:</strong> karta pokazuje
    niebo od −6° do 54° wysokości — tyle, ile potrzeba Słońcu, Księżycowi i planetom na tej
    szerokości. Droga Mleczna latem stoi w zenicie, więc w tym oknie widać tylko jej dolną
    część, a reszta wychodzi górą kadru. Przełącznik „okno wysokości" pokazuje, jak by to
    wyglądało, gdyby kadr sięgał zenitu — kosztem tego, że wszystko inne siedzi niżej, niż
    jest naprawdę.</p>
    <div class="panel">
      <label class="pole"><b>Godzina — <span id="v-godz"></span></b>
        <input type="range" id="godz" min="18" max="30" step="0.25" value="23.5"></label>
      <label class="pole"><b>Jasność pasa — <span id="v-jasn"></span></b>
        <input type="range" id="jasn" min="0" max="2.5" step="0.05" value="1.8"></label>
      <label class="pole"><b>Rozmycie — <span id="v-rozm"></span> px</b>
        <input type="range" id="rozm" min="0" max="16" step="1" value="1"></label>
      <label class="pole"><b>Noc</b>
        <select id="noc">__NOCE__</select></label>
      <label class="pole"><b>Okno wysokości</b>
        <select id="okno">
          <option value="karta">karta (−6…54°) — jak na panelu</option>
          <option value="pelne">pełne niebo (0…90°)</option>
        </select></label>
      <label class="pole"><b>Źródło światła</b>
        <select id="zrodlo">
          <option value="kadr">zdjęcie z Pobranych (kadr __KADR_FOV__°)</option>
          <option value="panorama">panorama całego nieba (ESO)</option>
        </select></label>
      <label class="pole"><b>Szczegół — <span id="v-szcz"></span></b>
        <input type="range" id="szcz" min="1" max="5" step="1" value="2"></label>
      <label class="pole"><b>Nasycenie — <span id="v-nas"></span></b>
        <input type="range" id="nas" min="0" max="1" step="0.05" value="0.45"></label>
      <label class="pole"><b>Próg czerni — <span id="v-prog"></span></b>
        <input type="range" id="prog" min="0" max="0.4" step="0.01" value="0.05"></label>
      <label class="pole"><b>Gamma — <span id="v-gam"></span></b>
        <input type="range" id="gam" min="0.4" max="2.5" step="0.1" value="0.7"></label>
      <label class="pole"><b>Wysokość Słońca — <span id="v-slonce"></span>°</b>
        <input type="range" id="slonce" min="-25" max="6" step="0.5" value="-18"></label>
    </div>
    <div class="panel" id="panel-kadr">
      <label class="pole"><b>Kadr: długość galakt. — <span id="v-kl"></span>°</b>
        <input type="range" id="kl" min="-40" max="40" step="1" value="__KADR_L__"></label>
      <label class="pole"><b>Kadr: szerokość galakt. — <span id="v-kb"></span>°</b>
        <input type="range" id="kb" min="-25" max="25" step="1" value="__KADR_B__"></label>
      <label class="pole"><b>Kadr: obrót — <span id="v-krot"></span>°</b>
        <input type="range" id="krot" min="-90" max="90" step="1" value="__KADR_ROT__"></label>
      <label class="pole"><b>Kadr: pole widzenia — <span id="v-kfov"></span>°</b>
        <input type="range" id="kfov" min="30" max="120" step="1" value="__KADR_FOV__"></label>
    </div>
    <div class="ptaszki">
      <label><input type="checkbox" id="gwiazdy" checked> pole gwiazd karty</label>
      <label><input type="checkbox" id="planety" checked> planety</label>
      <label><input type="checkbox" id="tylkopas"> sam pas, bez nieba</label>
    </div>
    <p class="etykieta">Przepis — zaznacz i wklej mi w czacie:</p>
    <div class="przepis" id="przepis"></div>
  </section>

  <section class="card">
    <h2>Noc w czterech godzinach</h2>
    <p>Ta sama noc, ustawienia z panelu wyżej. Kadr 16:9, żeby zmieściła się większa
    część nieba.</p>
    <div class="siatka" id="godziny"></div>
  </section>

  <section class="card">
    <h2>Co i kiedy widać</h2>
    <p>Wysokość centrum Galaktyki (Strzelec, <code>l = 0</code>) i najwyższego punktu pasa,
    godzina po godzinie. Z __LAT__° N centrum nigdy nie wznosi się wyżej niż ~7° — pas jest
    tu przede wszystkim letnim Łabędziem nad głową, a nie Strzelcem nad horyzontem.</p>
    <table id="tabela"></table>
    <p class="note" style="margin-top:12px"><strong>Kadr kontra panorama:</strong> zdjęcie
    z Pobranych obejmuje 62° nieba wokół centrum Galaktyki — czyli najładniejszy kawałek pasa,
    ale tylko ten jeden. Poza jego krawędzią nie ma nic i widać to, gdy pas powinien biec
    dalej przez kadr. Panorama ESO pokrywa całe niebo, kosztem tego, że jest przeciętną
    z całej sfery, a nie ostrym zdjęciem jednego rejonu. Przełącznik „źródło światła" pokazuje
    obie naraz na tej samej chwili.</p>
    <p class="note" style="margin-top:12px">Realizm: pas widać gołym okiem dopiero przy
    niebie ciemniejszym niż ok. <strong>−12°</strong> wysokości Słońca (koniec zmierzchu
    żeglarskiego) i przy Księżycu poniżej horyzontu. Na panelu to kwestia progu, nie
    astronomii — ale warto go ustawić tak, żeby pas nie świecił nad miastem o zmierzchu.</p>
  </section>

  <p class="note"><strong>Jeśli to wejdzie do karty:</strong> pas to jedna warstwa
  <code>&lt;canvas&gt;</code> pod gwiazdami, przerysowywana wtedy, kiedy karta i tak
  przelicza niebo (co ok. pół minuty), a między przerysowaniami tylko przesuwana i
  wygaszana przez kompozytor — czyli zgodnie z kontraktem wydajności. Czas rysowania
  jednej klatki mierzę na tej stronie i wypisuję w przepisie. Zdjęcie musiałoby wtedy
  leżeć w <code>/local/</code> jak <code>sun.png</code> i planety, z zachowanym
  podpisem <strong>__KREDYT__</strong>.</p>
</main>

<script>
/* ---- karta sun-cycle-bg, wklejona dosłownie z ../sun-cycle-bg.js ---- */
__KARTA__
</script>
<script>
(() => {
  const TEX_URL = '__TEKSTURA__';        // panorama calego nieba, ESO/S. Brunier
  const KADR_URL = '__KADR__';           // zdjecie z przezroczystym tlem
  const KADR0 = { l: __KADR_L__, b: __KADR_B__, rot: __KADR_ROT__, fov: __KADR_FOV__ };
  const LAT = __LAT__, LON = __LON__;
  const DATA = '__DATA_ISO__';           // lokalna polnoc nocy, ktora pokazujemy
  const AZ0 = 50, AZ1 = 310;
  const B = window.sunCycleBg;
  const D2R = Math.PI / 180, R2D = 180 / Math.PI;

  /* --- czas gwiazdowy: te same wzory co altaz() w karcie --- */
  function julian(d) {
    let y = d.getUTCFullYear(), m = d.getUTCMonth() + 1;
    if (m <= 2) { y -= 1; m += 12; }
    const a = Math.floor(y / 100), b = 2 - a + Math.floor(a / 4);
    const dzien = d.getUTCDate() + (d.getUTCHours() + d.getUTCMinutes() / 60 +
      d.getUTCSeconds() / 3600) / 24;
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

  /* Rzut karty odslania wysokosci od -6 do 54 stopni — tyle, ile potrzebuja
     Slonce, Ksiezyc i planety na tej szerokosci. Droga Mleczna latem stoi w
     zenicie, wiec w tym oknie ladauje na gornej krawedzi. Drugi rzut, „pelne
     niebo", sciska 0-90 stopni w ten sam kadr: pas miesci sie caly, ale
     wszystko inne jest nizej, niz jest naprawde. Strona rysuje oba tym samym
     kodem karty — `buildStars` i `placePlanets` przyjmuja rzut z zewnatrz. */
  const OKNA = {
    karta: { min: -6, max: 54, opis: 'karta (−6…54°)' },
    pelne: { min: 0, max: 90, opis: 'pełne niebo (0…90°)' },
  };
  function rzut(okno) {
    const o = OKNA[okno] || OKNA.karta, zakres = o.max - o.min;
    return (alt, az) => ({
      x: Math.max(-0.05, Math.min(1.05, (az - AZ0) / (AZ1 - AZ0))) * 100,
      y: 92 - Math.max(-0.1, Math.min(1, (alt - o.min) / zakres)) * 86,
    });
  }
  // ktora noc: pas obraca sie w ciagu nocy o godziny, a w ciagu roku o miesiace
  let BAZA = DATA;
  const czas = (godz) => new Date(new Date(BAZA).getTime() + godz * 3600e3);

  /* --- odwrotne przeksztalcenia: piksel kadru -> punkt nieba --------------
     Jasnosc powierzchniowa nie zalezy od rzutu: kazdy piksel ma pokazac
     jasnosc tego kawalka nieba, ktory na niego przypada. Rysowanie plamek
     „w przod" tego nie daje — przy zenicie poludniki sie zbiegaja, plamki
     naklada sie po kilkanascie i pas wychodzi oslepiajaca kolumna. Wiec
     mapujemy w tyl: dla piksela liczymy wysokosc i azymut, z nich rektascensje
     i deklinacje, z nich wspolrzedne galaktyczne, i czytamy teksture. */
  const NGP_RA = 192.85948, NGP_DEC = 27.12825, L_NCP = 122.93192;
  function altazDoEq(alt, az, J) {
    const a = alt * D2R, z = az * D2R, pr = LAT * D2R;
    const dec = Math.asin(Math.max(-1, Math.min(1,
      Math.sin(a) * Math.sin(pr) + Math.cos(a) * Math.cos(pr) * Math.cos(z))));
    const H = Math.atan2(-Math.sin(z) * Math.cos(a),
      Math.cos(pr) * Math.sin(a) - Math.sin(pr) * Math.cos(a) * Math.cos(z));
    return { ra: ((gmst(J) + LON - H * R2D) % 360 + 360) % 360, dec: dec * R2D };
  }
  function eqDoGal(ra, dec) {
    const r = ra * D2R, d = dec * D2R;
    const rp = NGP_RA * D2R, dp = NGP_DEC * D2R, ln = L_NCP * D2R;
    const b = Math.asin(Math.max(-1, Math.min(1,
      Math.sin(dp) * Math.sin(d) + Math.cos(dp) * Math.cos(d) * Math.cos(r - rp))));
    const y = Math.cos(d) * Math.sin(r - rp);
    const x = Math.cos(dp) * Math.sin(d) - Math.sin(dp) * Math.cos(d) * Math.cos(r - rp);
    return { l: (((ln - Math.atan2(y, x)) * R2D) % 360 + 360) % 360, b: b * R2D };
  }
  /* Panorama jest rownoprostokatna we wspolrzednych galaktycznych. Mapowanie
     zmierzone na samym pliku, nie zalozone: probki w znanych miejscach dajaz
     centrum Galaktyki 140, antycentrum 62, biegun 9, a oba Oblok Magellana
     wypadaja tam, gdzie maja katalogowe wspolrzedne (LMC 34,5 przy 12,9 dla
     pustego nieba obok).
         x = ((180 - l) mod 360) / 360 * W        y = (0,5 - b / 180) * H  */
  /* Dwa zrodla swiatla pasa, oba fotograficzne:
       - panorama calego nieba (rownoprostokatna, wspolrzedne galaktyczne),
       - kadr ze zdjecia z przezroczystym tlem, wklejony w to miejsce nieba,
         w ktorym naprawde zostal zrobiony (rzut gnomoniczny wokol l0, b0). */
  const OBRAZY = {};
  function wczytaj(nazwa, url, gotowe) {
    const im = new Image();
    im.crossOrigin = 'anonymous';
    im.onload = () => {
      const c = document.createElement('canvas');
      c.width = im.naturalWidth; c.height = im.naturalHeight;
      const g = c.getContext('2d', { willReadFrequently: true });
      g.drawImage(im, 0, 0);
      OBRAZY[nazwa] = { w: c.width, h: c.height,
                        dane: g.getImageData(0, 0, c.width, c.height).data };
      gotowe();
    };
    im.onerror = () => { OBRAZY[nazwa] = 'blad'; gotowe(); };
    im.src = url;
  }
  function wczytajTeksture(gotowe) {
    let zostalo = 2;
    const krok = () => { if (--zostalo === 0) gotowe(); };
    wczytaj('panorama', TEX_URL, krok);
    wczytaj('kadr', KADR_URL, krok);
  }

  /* Panorama jest rownoprostokatna we wspolrzednych galaktycznych. Mapowanie
     zmierzone na samym pliku, nie zalozone: probki w znanych miejscach dajaz
     centrum Galaktyki 140, antycentrum 62, biegun 9, a oba Obloki Magellana
     wypadaja tam, gdzie maja katalogowe wspolrzedne (LMC 34,5 przy 12,9 dla
     pustego nieba obok).
         x = ((180 - l) mod 360) / 360 * W        y = (0,5 - b / 180) * H  */
  function probkaPanoramy(T, l, b, out) {
    const x = Math.round((((180 - l) % 360 + 360) % 360) / 360 * T.w) % T.w;
    const y = Math.max(0, Math.min(T.h - 1, Math.round((0.5 - b / 180) * T.h)));
    const i = (y * T.w + x) * 4;
    out[0] = T.dane[i]; out[1] = T.dane[i + 1]; out[2] = T.dane[i + 2];
    out[3] = 255;
    return true;
  }

  /* Kadr: odwrotny rzut gnomoniczny. Punkt nieba (l, b) wraca na piksel
     zdjecia; poza kadrem — nic. Kamera patrzy w (l0, b0), obrocona o rot,
     o poziomym polu widzenia fov. */
  function probkaKadru(T, l, b, out, k) {
    const lr = l * D2R, br = b * D2R;
    const ux = Math.cos(br) * Math.cos(lr), uy = Math.cos(br) * Math.sin(lr), uz = Math.sin(br);
    const cl = Math.cos(k.l * D2R), sl = Math.sin(k.l * D2R);
    const cb = Math.cos(k.b * D2R), sb = Math.sin(k.b * D2R);
    const x1 = ux * cl + uy * sl, y1 = -ux * sl + uy * cl, z1 = uz;
    const vx = x1 * cb + z1 * sb, vz = -x1 * sb + z1 * cb, vy = y1;
    if (vx <= 0.05) return false;                 // za plecami kamery
    const Xr = vy / vx, Yr = -vz / vx;
    const c = Math.cos(k.rot * D2R), s = Math.sin(k.rot * D2R);
    const X = Xr * c + Yr * s, Y = -Xr * s + Yr * c;
    const t = Math.tan(k.fov * D2R / 2);
    const px = (X / t + 1) / 2 * T.w;
    const py = (Y / (t * T.h / T.w) + 1) / 2 * T.h;
    if (px < 0 || py < 0 || px >= T.w || py >= T.h) return false;
    const i = ((py | 0) * T.w + (px | 0)) * 4;
    out[0] = T.dane[i]; out[1] = T.dane[i + 1]; out[2] = T.dane[i + 2];
    out[3] = T.dane[i + 3];                       // przezroczyste tlo zdjecia
    return true;
  }

  /* Rysunek: maly bufor (kadr / SKALA), rozciagany przez przegladarke. Pas
     nie ma ostrych krawedzi, wiec nikt tego nie zobaczy, a praca spada
     kilkunastokrotnie. */
  const SKALA = 2;   // domyslny dzielnik rozdzielczosci bufora
  function rysujPas(cv, godz, opcje, pr, okno) {
    const r = cv.getBoundingClientRect();
    const W = Math.max(1, Math.round(r.width)), H = Math.max(1, Math.round(r.height));
    const sk = opcje.skala || SKALA;
    const w = Math.max(2, Math.round(W / sk)), h = Math.max(2, Math.round(H / sk));
    cv.width = w; cv.height = h;
    const g = cv.getContext('2d');
    const T = OBRAZY[opcje.zrodlo === 'kadr' ? 'kadr' : 'panorama'];
    if (!T || T === 'blad') return { ms: 0, pikseli: 0, brak: true };
    const kadr = opcje.zrodlo === 'kadr';
    const kam = { l: opcje.kl, b: opcje.kb, rot: opcje.krot, fov: opcje.kfov };
    const img = g.createImageData(w, h);
    const J = julian(czas(godz));
    const o = OKNA[okno], zakres = o.max - o.min;
    const start = performance.now();
    const rgb = [0, 0, 0, 255];
    let ile = 0;
    for (let py = 0; py < h; py++) {
      const yp = (py + 0.5) / h * 100;
      const alt = o.min + (92 - yp) / 86 * zakres;
      // ekstynkcja: przy horyzoncie patrzymy przez kilkanascie razy grubsza
      // warstwe powietrza, wiec pas gasnie, zanim go dotknie
      const ekst = Math.max(0, Math.min(1, (alt - 1) / 12));
      for (let px = 0; px < w; px++) {
        const i = (py * w + px) * 4;
        if (alt <= -1 || ekst <= 0) { img.data[i + 3] = 0; continue; }
        const az = AZ0 + (px + 0.5) / w * (AZ1 - AZ0);
        const eq = altazDoEq(alt, az, J);
        const gl = eqDoGal(eq.ra, eq.dec);
        const jest = kadr ? probkaKadru(T, gl.l, gl.b, rgb, kam)
                          : probkaPanoramy(T, gl.l, gl.b, rgb);
        if (!jest) { img.data[i + 3] = 0; continue; }
        // Jasnosc panoramy jest fotograficzna: rozciagnieta, zeby bylo widac
        // pyl. Na tle nieba panelu trzeba ja sciagnac krzywa gamma, inaczej
        // czarne niebo miedzy gwiazdami swieci szarym mlekiem.
        const l0 = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255;
        // Kadr ma juz zdjete tlo, wiec jego kanal alfa JEST krzywa tonalna —
        // przepuszczanie go jeszcze raz przez prog czerni dusilo obraz dwa
        // razy i pas rozpadal sie na plamy. Panorama tla nie ma, wiec prog
        // liczy sie tam z luminancji.
        const baza = kadr ? rgb[3] / 255
                          : Math.max(0, l0 - opcje.prog) / (1 - opcje.prog);
        const a = Math.pow(baza, opcje.gamma) * opcje.jasnosc * ekst;
        if (a <= 0.004) { img.data[i + 3] = 0; continue; }
        // barwa ze zdjecia, ale przyciagnieta do bieli: goly oko widzi pas
        // prawie bezbarwnie, a mocno kolorowy pas na panelu wyglada jak druk
        const s = opcje.nasycenie;
        const sr = l0 * 255;
        img.data[i] = rgb[0] * s + sr * (1 - s);
        img.data[i + 1] = rgb[1] * s + sr * (1 - s);
        img.data[i + 2] = rgb[2] * s + sr * (1 - s);
        img.data[i + 3] = Math.max(0, Math.min(255, Math.round(a * 255)));
        ile++;
      }
    }
    g.putImageData(img, 0, 0);
    cv.style.filter = opcje.rozmycie > 0 ? `blur(${opcje.rozmycie}px)` : '';
    return { ms: performance.now() - start, pikseli: ile };
  }

  /* --- scena: warstwy karty + pas --- */
  function scena(host, godz, opcje) {
    const okno = opcje.okno || 'karta';
    const pr = rzut(okno);
    let box = host.querySelector('.warstwy');
    if (!box) {
      box = document.createElement('div'); box.className = 'warstwy';
      host.appendChild(box);
    }
    const stare = box.querySelector('.sun-cycle-stars');
    if (stare && stare.scsStop) stare.scsStop();
    box.innerHTML = '';
    const r = host.getBoundingClientRect();
    const W = Math.max(1, Math.round(r.width)), H = Math.max(1, Math.round(r.height));
    const p = B.paletteFor(opcje.slonce, false);
    const rgb = (c) => 'rgb(' + c.map(Math.round).join(',') + ')';
    host.style.background = opcje.tylkoPas ? '#05070c'
      : `linear-gradient(200deg, ${rgb(p.top)} 0%, ${rgb(p.mid)} 48%, ${rgb(p.bot)} 100%)`;

    const cv = document.createElement('canvas');
    cv.className = 'mw';
    box.appendChild(cv);
    const miara = rysujPas(cv, godz, opcje, pr, okno);
    // pas jest najdalszą rzeczą na niebie — gwiazdy i planety idą na wierzch
    cv.style.opacity = (opcje.tylkoPas ? 1 : p.stars).toFixed(2);

    if (opcje.gwiazdy && !opcje.tylkoPas) {
      const gw = B.buildStars(B.readStarConfig({ count: 150, sizes: 'mixed', size: .5,
        glow: .05, twinkle: .45, drift: 0 }), W, H, pr);
      gw.style.opacity = p.stars.toFixed(2);
      box.appendChild(gw);
    }
    if (opcje.planety && !opcje.tylkoPas) {
      const cfg = B.readPlanetConfig({ images: '/local/sun-cycle/planets/',
        size: 1.2, scale: 'diameters', glow: 0.35, day: 0.35 });
      const layer = B.buildPlanets(cfg);
      box.appendChild(layer);
      B.placePlanets(layer, cfg, STANY_PLANET, pr, opcje.slonce);
    }
    return miara;
  }

  // planety: pozycje ze snapshotu Sol (ta sama chwila co strona „tło: planety")
  const STANY_PLANET = __PLANETY__;

  /* --- panel --- */
  const G = document.getElementById('glowna');
  const el = {};
  ['godz','jasn','rozm','szcz','nas','prog','gam','zrodlo','kl','kb','krot','kfov',
   'noc','okno','slonce','gwiazdy','planety','tylkopas']
    .forEach(id => el[id] = document.getElementById(id));
  const fmt = (v, n) => Number(v).toFixed(n).replace('.', ',');
  const godzTekst = (g) => {
    const h = Math.floor(g) % 24, m = Math.round((g % 1) * 60);
    return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
  };
  function opcje() {
    BAZA = el.noc.value;
    return { jasnosc: +el.jasn.value, rozmycie: +el.rozm.value,
             nasycenie: +el.nas.value, prog: +el.prog.value, gamma: +el.gam.value,
             skala: +el.szcz.value, zrodlo: el.zrodlo.value,
             kl: +el.kl.value, kb: +el.kb.value, krot: +el.krot.value, kfov: +el.kfov.value,
             okno: el.okno.value, slonce: +el.slonce.value,
             gwiazdy: el.gwiazdy.checked, planety: el.planety.checked,
             tylkoPas: el.tylkopas.checked };
  }
  let ostatni = null;
  function rysuj() {
    const o = opcje(), godz = +el.godz.value;
    ostatni = scena(G, godz, o);
    document.getElementById('v-godz').textContent = godzTekst(godz);
    document.getElementById('v-jasn').textContent = fmt(o.jasnosc, 2);
    document.getElementById('v-rozm').textContent = o.rozmycie;
    document.getElementById('v-szcz').textContent = o.skala + '× mniejszy bufor';
    document.getElementById('v-kl').textContent = o.kl;
    document.getElementById('v-kb').textContent = o.kb;
    document.getElementById('v-krot').textContent = o.krot;
    document.getElementById('v-kfov').textContent = o.kfov;
    // suwaki kadru maja sens tylko dla kadru
    document.getElementById('panel-kadr').style.display =
      o.zrodlo === 'kadr' ? '' : 'none';
    document.getElementById('v-nas').textContent = fmt(o.nasycenie, 2);
    document.getElementById('v-prog').textContent = fmt(o.prog, 2);
    document.getElementById('v-gam').textContent = fmt(o.gamma, 1);
    document.getElementById('v-slonce').textContent = fmt(o.slonce, 1);
    const pad = (s) => (s + '                ').slice(0, 16);
    document.getElementById('przepis').textContent = [
      'strona droga-mleczna',
      pad('godzina') + godzTekst(godz),
      pad('jasnosc') + fmt(o.jasnosc, 2),
      pad('rozmycie') + o.rozmycie + ' px',
      pad('zrodlo') + el.zrodlo.options[el.zrodlo.selectedIndex].text,
      pad('kadr l/b') + o.kl + ' / ' + o.kb + ' stopni',
      pad('kadr obrot') + o.krot + ' stopni, pole ' + o.kfov + ' stopni',
      pad('szczegol') + o.skala + '× mniejszy bufor',
      pad('nasycenie') + fmt(o.nasycenie, 2),
      pad('prog czerni') + fmt(o.prog, 2),
      pad('gamma') + fmt(o.gamma, 1),
      pad('noc') + el.noc.options[el.noc.selectedIndex].text,
      pad('okno') + el.okno.options[el.okno.selectedIndex].text,
      pad('slonce') + fmt(o.slonce, 1) + ' stopni',
      pad('gwiazdy') + (o.gwiazdy ? 'tak' : 'nie'),
      pad('planety') + (o.planety ? 'tak' : 'nie'),
      pad('rysowanie') + fmt(ostatni.ms, 1) + ' ms, ' + ostatni.pikseli + ' pikseli pasa',
    ].join('\n');
  }
  Object.values(el).forEach(e => e.addEventListener('input', () => { rysuj(); przerysujGodziny(); }));

  /* --- cztery godziny --- */
  const GODZINY = [20.5, 23, 25.5, 28];
  const siatka = document.getElementById('godziny');
  function przerysujGodziny() {
    siatka.querySelectorAll('.scena').forEach((host, i) =>
      scena(host, GODZINY[i], Object.assign(opcje(), { slonce: -18 })));
  }
  GODZINY.forEach((g) => {
    const w = document.createElement('div');
    w.className = 'wariant';
    w.innerHTML = '<h3>' + godzTekst(g) + ' <em>· ' + (g >= 24 ? 'nad ranem' : 'wieczorem') +
      '</em></h3><div class="scena kadr"></div>';
    siatka.appendChild(w);
    requestAnimationFrame(() => scena(w.querySelector('.scena'), g,
      Object.assign(opcje(), { slonce: -18 })));
  });

  /* --- tabela: potrzebuje jeszcze drogi „w przod", tylko dla srodka pasa --- */
  function galDoEq(l, b) {
    const lr = l * D2R, br = b * D2R;
    const rp = NGP_RA * D2R, dp = NGP_DEC * D2R, ln = L_NCP * D2R;
    const dec = Math.asin(Math.max(-1, Math.min(1,
      Math.sin(dp) * Math.sin(br) + Math.cos(dp) * Math.cos(br) * Math.cos(ln - lr))));
    const y = Math.cos(br) * Math.sin(ln - lr);
    const x = Math.cos(dp) * Math.sin(br) - Math.sin(dp) * Math.cos(br) * Math.cos(ln - lr);
    return { ra: (((Math.atan2(y, x) + rp) * R2D) % 360 + 360) % 360, dec: dec * R2D };
  }

  /* --- tabela --- */
  const t = document.getElementById('tabela');
  t.innerHTML = '<tr><th>godzina</th><th>centrum Galaktyki</th><th>najwyższy punkt pasa</th>' +
    '<th>azymut centrum</th><th>widoczne gołym okiem</th></tr>';
  for (let g = 19; g <= 29; g += 1) {
    const J = julian(czas(g));
    const c = altaz(266.42, -28.99, J);          // Strzelec A*, l = 0
    let naj = { alt: -90 };
    for (let l = 0; l < 360; l += 2) {
      // srodek pasa wystarczy: najwyzej stoi zawsze jego linia srodkowa
      const eq = galDoEq(l, 0);
      const p = altaz(eq.ra, eq.dec, J);
      if (p.alt > naj.alt) naj = p;
    }
    const ciemno = g >= 21.5 && g <= 27;         // grubo: koniec/początek zmierzchu
    const tr = document.createElement('tr');
    tr.innerHTML = '<td class="l">' + godzTekst(g) + '</td>' +
      '<td class="l">' + fmt(c.alt, 1) + '°</td>' +
      '<td class="l">' + fmt(naj.alt, 1) + '°</td>' +
      '<td class="l">' + fmt(c.az, 0) + '°</td>' +
      '<td class="' + (ciemno ? 'tak' : 'nie') + '">' + (ciemno ? 'tak' : 'za jasno') + '</td>';
    t.appendChild(tr);
  }

  addEventListener('resize', () => { clearTimeout(window._t); window._t = setTimeout(rysuj, 200); });
  wczytajTeksture(() => { rysuj(); przerysujGodziny(); });
})();
</script>
"""

META = {
    "tytul": "Tło: Droga Mleczna nad Bartoszewem",
    "grupa": "Tło (sun-cycle-bg)",
    "status": "aktualne",
    "kolejnosc": 106,
    "opis": ("Prawdziwe zdjęcie nieba (panorama ESO/S. Brunier, CC BY 4.0) rzutowane dla "
             "53,5182° N i 14,4570° E: każdy piksel kadru wraca na niebo i czyta próbkę "
             "z panoramy. Panel na żywo: godzina nocy, jasność, próg czerni, gamma, "
             "nasycenie, rozmycie, wysokość Słońca, "
             "z gwiazdami i planetami karty pod spodem. Niżej ta sama noc w czterech "
             "godzinach i tabela: wysokość centrum Galaktyki i najwyższego punktu pasa "
             "godzina po godzinie. Jasność pasa jest modelem (grubość, spadek od centrum, "
             "Wielka Szczelina), geometria — nie."),
}


def main() -> int:
    noc = datetime.datetime.now().astimezone().replace(
        hour=0, minute=0, second=0, microsecond=0)
    planety = {}
    snap = json.loads((ROOT / "demo" / "sol_snapshot.json").read_text())
    for body, w in snap["planety"].items():
        planety[f"sensor.sol_{body}_azimuth"] = {"state": w["azimuth"]}
        planety[f"sensor.sol_{body}_elevation"] = {"state": w["elevation"]}
    noce = []
    for m, etykieta in ((0, "dzisiejsza"), (3, "za 3 miesiące"),
                        (6, "za pół roku"), (9, "za 9 miesięcy")):
        d = noc + datetime.timedelta(days=30 * m)
        noce.append(f'<option value="{d.isoformat()}">{etykieta} — '
                    f'{d.strftime("%d.%m.%Y")}</option>')
    html = (STRONA
            .replace("__KARTA__", KARTA.read_text())
            .replace("__TEKSTURA__", TEKSTURA)
            .replace("__KADR_URL__", KADR)
            .replace("__KADR__", KADR)
            .replace("__KADR_L__", str(KADR_L)).replace("__KADR_B__", str(KADR_B))
            .replace("__KADR_ROT__", str(KADR_ROT)).replace("__KADR_FOV__", str(KADR_FOV))
            .replace("__KREDYT__", KREDYT)
            .replace("__PLANETY__", json.dumps(planety))
            .replace("__LAT__", str(LAT)).replace("__LON__", str(LON))
            .replace("__MIEJSCE__", MIEJSCE)

            .replace("__NOCE__", "".join(noce))
            .replace("__DATA_ISO__", noc.isoformat())
            .replace("__DATA__", noc.strftime("%d.%m"))
            .replace("__DATA_DO__", (noc + datetime.timedelta(days=1)).strftime("%d.%m")))
    OUT.write_text(html)
    OUT.with_suffix(".meta.json").write_text(json.dumps(META, ensure_ascii=False, indent=1) + "\n")
    print(f"{OUT} ({len(html) // 1024} kB), tekstura: {TEKSTURA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
