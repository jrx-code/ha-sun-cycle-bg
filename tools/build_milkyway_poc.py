#!/usr/bin/env python3
"""Build the Milky Way tuning page: demo/droga-mleczna.html

Same rule as the other tuning pages: ../sun-cycle-bg.js is pasted in verbatim
and every scene is drawn by the card's own code — sky palette, star field,
planets. The one new thing, the band itself, is drawn on a canvas by the code
this page is here to judge before any of it goes into the card.

Nothing is baked at build time and no brightness is modelled: the light is two
photographs, and the page computes only where each piece of them belongs at the
chosen instant. That is a dozen lines of sidereal time plus the galactic to
equatorial rotation, the same chain tools/milky_way.py prints for a sanity
check on the command line.

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

# Dwa zdjecia: panorama calego nieba (ESO) i wlasny kadr ze zdjetym tlem.
# Zadnego modelu jasnosci tu nie ma — analityczny zostal wyrzucony, bo pas to
# rozdzielone oblok gwiazdowe i poszarpany pyl, a nie gladka funkcja l i b.
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
    <p>Zdjęcie trafia na niebo jako <em>zdjęcie</em>: siatka 32×22 czworokątów, każdy
    z własnym przekształceniem policzonym z prawdziwej geometrii nieba, próbkowanie w pełnej
    rozdzielczości źródła, składanie przez <strong>dodawanie światła</strong> — ciemny pył
    nie dokłada nic, obłok dokłada swoją jasność. Wygaszanie przy horyzoncie idzie
    gradientem po całym kadrze. Kadr w proporcji panelu salonu (16:5), okno azymutu jak
    na panelu (50°–310°).
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
        <input type="range" id="jasn" min="0" max="1" step="0.02" value="0.9"></label>
      <label class="pole"><b>Zanik przy horyzoncie od — <span id="v-hor"></span>°</b>
        <input type="range" id="hor" min="0" max="40" step="1" value="22"></label>
      <label class="pole"><b>Rozmycie — <span id="v-rozm"></span> px</b>
        <input type="range" id="rozm" min="0" max="8" step="1" value="0"></label>
      <label class="pole"><b>Noc</b>
        <select id="noc">__NOCE__</select></label>
      <label class="pole"><b>Okno wysokości</b>
        <select id="okno">
          <option value="karta">karta (−6…54°) — jak na panelu</option>
          <option value="pelne">pełne niebo (0…90°)</option>
        </select></label>
      <label class="pole"><b>Źródło światła</b>
        <select id="zrodlo">
          <option value="kadr">własne zdjęcie (kadr)</option>
          <option value="panorama">panorama całego nieba (ESO)</option>
        </select></label>
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
      <label class="pole"><b>Kadr: rozpiętość — <span id="v-kfov"></span>° nieba</b>
        <input type="range" id="kfov" min="30" max="150" step="2" value="__KADR_FOV__"></label>
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
    <p class="note" style="margin-top:12px"><strong>O rozpiętości:</strong> prawdziwe pole
    widzenia tego zdjęcia to <strong>62°</strong> — tyle wyszło z dopasowania i tyle stoi
    na suwaku. Większa liczba <em>powiększa</em> zdjęcie na niebie: w skali 1:1 zajmuje ono
    mały placek nisko nad horyzontem, więc powiększenie kupuje widoczność, bo kadr rośnie
    też do góry. To zabieg plastyczny, nie astronomia: kierunek, obrót i pora zostają
    prawdziwe, sama skala nie. Przy 110° we wrześniu nad horyzontem jest 35% kadru zamiast
    12%.</p>
    <p class="note" style="margin-top:12px"><strong>Kadr kontra panorama:</strong> zdjęcie
    obejmuje jeden rejon nieba wokół centrum Galaktyki — czyli najładniejszy kawałek pasa,
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
  /* Zdjecie trafia na niebo jako ZDJECIE, nie jako chmura probek.

     Pierwsza wersja liczyla kazdy piksel kadru osobno, w buforze dwa razy
     mniejszym, i jeszcze rozmywala wynik — z ostrej fotografii zostawala
     ziarnista breja. Teraz obraz rysuje przegladarka: siatka 24 x 16 czworokatow,
     kazdy z wlasnym przeksztalceniem afinicznym policzonym z prawdziwej
     geometrii nieba. Geometria jest wiec dokladna co do oczka siatki, a
     probkowanie robi GPU w pelnej rozdzielczosci zrodla.

     Skladanie jest dodawanie ('lighter'), bo tak dziala swiatlo: ciemny pyl na
     zdjeciu nie dokłada nic, oblok dokłada swoja jasnosc. Malowanie alfa robilo
     z tego szara mgle. */
  const OBRAZY = {};
  function wczytaj(nazwa, url, gotowe) {
    const im = new Image();
    im.crossOrigin = 'anonymous';
    im.onload = () => { OBRAZY[nazwa] = im; gotowe(); };
    im.onerror = () => { OBRAZY[nazwa] = 'blad'; gotowe(); };
    im.src = url;
  }
  function wczytajTeksture(gotowe) {
    let zostalo = 2;
    const krok = () => { if (--zostalo === 0) gotowe(); };
    wczytaj('kadr', KADR_URL, krok);
    wczytaj('panorama', TEX_URL, krok);
  }

  /* Piksel zdjecia -> punkt nieba. Kadr jest rzutem gnomonicznym wokol
     (l0, b0), obroconym o rot, o poziomym polu widzenia fov — parametry
     dopasowane korelacja do panoramy ESO, nie na oko. */
  function kadrDoGal(u, v, k) {
    const t = Math.tan(k.fov * D2R / 2);
    const X = (u * 2 - 1) * t, Y = (v * 2 - 1) * t * k.ar;
    const c = Math.cos(k.rot * D2R), s = Math.sin(k.rot * D2R);
    const Xr = X * c - Y * s, Yr = X * s + Y * c;
    let vx = 1, vy = Xr, vz = -Yr;
    const n = Math.hypot(vx, vy, vz); vx /= n; vy /= n; vz /= n;
    const cb = Math.cos(k.b * D2R), sb = Math.sin(k.b * D2R);
    const cl = Math.cos(k.l * D2R), sl = Math.sin(k.l * D2R);
    const x1 = vx * cb - vz * sb, z1 = vx * sb + vz * cb, y1 = vy;
    const x2 = x1 * cl - y1 * sl, y2 = x1 * sl + y1 * cl;
    return { l: ((Math.atan2(y2, x2) * R2D) % 360 + 360) % 360,
             b: Math.asin(Math.max(-1, Math.min(1, z1))) * R2D };
  }
  function galDoEq2(l, b) {
    const lr = l * D2R, br = b * D2R;
    const rp = NGP_RA * D2R, dp = NGP_DEC * D2R, ln = L_NCP * D2R;
    const dec = Math.asin(Math.max(-1, Math.min(1,
      Math.sin(dp) * Math.sin(br) + Math.cos(dp) * Math.cos(br) * Math.cos(ln - lr))));
    const y = Math.cos(br) * Math.sin(ln - lr);
    const x = Math.cos(dp) * Math.sin(br) - Math.sin(dp) * Math.cos(br) * Math.cos(ln - lr);
    return { ra: (((Math.atan2(y, x) + rp) * R2D) % 360 + 360) % 360, dec: dec * R2D };
  }

  const SIATKA_U = 32, SIATKA_V = 22;
  const SIATKA_WIDOCZNA = new URLSearchParams(location.search).has('siatka');
  let BUFOR = null;                      // pomocniczy kadr, zeby szwy nie sumowaly sie dwa razy
  function rysujPas(cv, godz, opcje, pr, okno) {
    const r = cv.getBoundingClientRect();
    const W = Math.max(1, Math.round(r.width)), H = Math.max(1, Math.round(r.height));
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    const g = cv.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, W, H);
    const obraz = OBRAZY[opcje.zrodlo === 'panorama' ? 'panorama' : 'kadr'];
    if (!obraz || obraz === 'blad') return { ms: 0, oczek: 0, brak: true };
    const J = julian(czas(godz));
    const start = performance.now();
    const kam = { l: opcje.kl, b: opcje.kb, rot: opcje.krot, fov: opcje.kfov,
                  ar: obraz.naturalHeight / obraz.naturalWidth };
    const panorama = opcje.zrodlo === 'panorama';

    if (!BUFOR) BUFOR = document.createElement('canvas');
    BUFOR.width = cv.width; BUFOR.height = cv.height;
    const gb = BUFOR.getContext('2d');
    gb.setTransform(dpr, 0, 0, dpr, 0, 0);
    gb.clearRect(0, 0, W, H);

    // wezly siatki: rog zrodla -> niebo -> kadr
    const N = (SIATKA_U + 1) * (SIATKA_V + 1);
    const wx = new Float64Array(N), wy = new Float64Array(N);
    const ok = new Uint8Array(N);
    for (let j = 0; j <= SIATKA_V; j++) {
      for (let i = 0; i <= SIATKA_U; i++) {
        const n = j * (SIATKA_U + 1) + i;
        const u = i / SIATKA_U, v = j / SIATKA_V;
        const gl = panorama
          ? { l: ((180 - u * 360) % 360 + 360) % 360, b: (0.5 - v) * 180 }
          : kadrDoGal(u, v, kam);
        const eq = galDoEq2(gl.l, gl.b);
        const p = altaz(eq.ra, eq.dec, J);
        const q = pr(p.alt, p.az);
        wx[n] = q.x / 100 * W; wy[n] = q.y / 100 * H;
        // Odrzucanie oczek po wysokosci rysowalo kanciasta, wielokatna
        // krawedz u dolu — to ona wygladala na „ucieta dolna czesc", nie
        // gradient. Odrzucamy dopiero gleboko pod horyzontem, gdzie gradient
        // i tak wyzerowal krycie, wiec granica nie moze byc widoczna.
        ok[n] = p.alt > -25 ? 1 : 0;
      }
    }

    // Warp idzie do bufora zwyklym rysowaniem, nie dodawaniem: przy dodawaniu
    // zakladka na szwach sumuje sie dwa razy i siatka wychodzi na wierzch
    // jasnymi kreskami. Dodawanie jest raz, na koncu, dla calego kadru.
    const sw = obraz.naturalWidth / SIATKA_U, sh = obraz.naturalHeight / SIATKA_V;
    let oczek = 0;
    for (let j = 0; j < SIATKA_V; j++) {
      for (let i = 0; i < SIATKA_U; i++) {
        const a = j * (SIATKA_U + 1) + i, b2 = a + 1, c2 = a + SIATKA_U + 1;
        if (!ok[a] || !ok[b2] || !ok[c2]) continue;
        const szer = Math.max(Math.abs(wx[b2] - wx[a]), Math.abs(wx[c2] - wx[a]));
        if (szer > W * 0.4) continue;        // oczko rozerwane przez zawijanie azymutu
        const wys = Math.max(Math.abs(wy[b2] - wy[a]), Math.abs(wy[c2] - wy[a]));
        if (wys > H * 0.6) continue;         // oczko rozciagniete przez zenit
        const m11 = (wx[b2] - wx[a]) / sw, m12 = (wy[b2] - wy[a]) / sw;
        const m21 = (wx[c2] - wx[a]) / sh, m22 = (wy[c2] - wy[a]) / sh;
        gb.save();
        gb.transform(m11, m12, m21, m22, wx[a], wy[a]);
        gb.translate(-i * sw, -j * sh);
        gb.beginPath();
        gb.rect(i * sw, j * sh, sw + 0.6, sh + 0.6);
        gb.clip();
        gb.drawImage(obraz, 0, 0);
        gb.restore();
        if (SIATKA_WIDOCZNA) {            // ?siatka=1 — obrys oczek do diagnozy
          gb.save();
          gb.strokeStyle = 'rgba(255,80,80,.9)'; gb.lineWidth = 0.6;
          gb.beginPath();
          gb.moveTo(wx[a], wy[a]); gb.lineTo(wx[b2], wy[b2]);
          gb.moveTo(wx[a], wy[a]); gb.lineTo(wx[c2], wy[c2]);
          gb.stroke(); gb.restore();
        }
        oczek++;
      }
    }

    // Ekstynkcja: pas gasnie przy horyzoncie, bo patrzymy przez kilkanascie
    // razy grubsza warstwe powietrza. Gradientem po calym kadrze, nie na
    // oczko — na oczko wychodzily schodki.
    const o = OKNA[okno], zakres = o.max - o.min;
    const yDla = (a) => (92 - (a - o.min) / zakres * 86) / 100 * H;
    // Pierwsza wersja gasla do zera dokladnie na wysokosci 0 stopni, czyli na
    // 84 % wysokosci kadru — a pod spodem zostawalo jeszcze 16 % ramki i pas
    // wygladal, jakby ktos go uciac w powietrzu. Teraz zanik konczy sie na
    // dolnej krawedzi: astronomicznie to i tak obszar pod horyzontem, ale nic
    // sie nie urywa. Suwak ustawia, jak wysoko zanik sie zaczyna.
    const grad = gb.createLinearGradient(0, yDla(opcje.horyzont), 0, H);
    grad.addColorStop(0, 'rgba(0,0,0,1)');
    grad.addColorStop(0.45, 'rgba(0,0,0,0.72)');
    grad.addColorStop(0.78, 'rgba(0,0,0,0.28)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    gb.globalCompositeOperation = 'destination-in';
    gb.fillStyle = grad;
    gb.fillRect(0, 0, W, H);
    gb.globalCompositeOperation = 'source-over';

    // jedno dodanie swiatla na kadr
    g.globalCompositeOperation = 'lighter';
    g.globalAlpha = Math.max(0, Math.min(1, opcje.jasnosc));
    g.drawImage(BUFOR, 0, 0, BUFOR.width, BUFOR.height, 0, 0, W, H);
    g.globalAlpha = 1;
    g.globalCompositeOperation = 'source-over';
    cv.style.filter = opcje.rozmycie > 0 ? `blur(${opcje.rozmycie}px)` : '';
    return { ms: performance.now() - start, oczek };
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
  ['godz','jasn','rozm','hor','zrodlo','kl','kb','krot','kfov',
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
             horyzont: +el.hor.value, zrodlo: el.zrodlo.value,
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
    document.getElementById('v-hor').textContent = o.horyzont;
    document.getElementById('v-kl').textContent = o.kl;
    document.getElementById('v-kb').textContent = o.kb;
    document.getElementById('v-krot').textContent = o.krot;
    document.getElementById('v-kfov').textContent = o.kfov;
    // suwaki kadru maja sens tylko dla kadru
    document.getElementById('panel-kadr').style.display =
      o.zrodlo === 'kadr' ? '' : 'none';
    document.getElementById('v-slonce').textContent = fmt(o.slonce, 1);
    const pad = (s) => (s + '                ').slice(0, 16);
    document.getElementById('przepis').textContent = [
      'strona droga-mleczna',
      pad('godzina') + godzTekst(godz),
      pad('jasnosc') + fmt(o.jasnosc, 2),
      pad('rozmycie') + o.rozmycie + ' px',
      pad('zanik od') + o.horyzont + ' stopni wysokosci',
      pad('zrodlo') + el.zrodlo.options[el.zrodlo.selectedIndex].text,
      pad('kadr l/b') + o.kl + ' / ' + o.kb + ' stopni',
      pad('kadr obrot') + o.krot + ' stopni, pole ' + o.kfov + ' stopni',
      pad('noc') + el.noc.options[el.noc.selectedIndex].text,
      pad('okno') + el.okno.options[el.okno.selectedIndex].text,
      pad('slonce') + fmt(o.slonce, 1) + ' stopni',
      pad('gwiazdy') + (o.gwiazdy ? 'tak' : 'nie'),
      pad('planety') + (o.planety ? 'tak' : 'nie'),
      pad('rysowanie') + fmt(ostatni.ms, 1) + ' ms, ' + ostatni.oczek + ' oczek siatki',
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
    "opis": ("Własne zdjęcie Drogi Mlecznej ze zdjętym tłem, wklejone w to miejsce nieba, "
             "w którym naprawdę zostało zrobione (dopasowane korelacją do panoramy ESO: "
             "l = −5°, b = −2°, obrót −24°). Warp siatkowy w pełnej rozdzielczości, "
             "dodawanie światła. Panel na żywo: godzina nocy, jasność, powiększenie kadru, "
             "położenie i obrót, wysokość Słońca, "
             "z gwiazdami i planetami karty pod spodem. Niżej ta sama noc w czterech "
             "godzinach i tabela: wysokość centrum Galaktyki i najwyższego punktu pasa "
             "godzina po godzinie. Światło pasa to fotografia, nie model: gładka funkcja "
             "l i b daje szarą plamę i została skasowana. Kadr stoi na zmierzonych 62°."),
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
