#!/usr/bin/env python3
"""Build the configurator page: demo/konfigurator.html

Every option the card has, as a control, over a live preview drawn by the card
itself, with the YAML fragment underneath — only the keys that differ from the
defaults, ready to paste into a dashboard.

Why generated and not committed: ../sun-cycle-bg.js is pasted in verbatim at
build time, so the page can never be tuning a different card than the one in
the repository. demo/config-poc.html, the page this replaces, was committed
with the card inlined by hand and still carried 1.3.0 eight releases later.

The defaults are not written down twice either. The page calls the card's own
readStarConfig({}), readPlanetConfig(true) and readMilkyConfig({}) and checks
its control table against them on load; a mismatch paints a red banner instead
of quietly emitting a wrong fragment.

    python3 tools/build_config_poc.py
    export BW_SESSION=$(bw unlock --raw)
    python3 ~/CodeHub/hassio/ha-panel-salon-sekcje/scripts/poc_upload.py \\
        demo/konfigurator.html
"""
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
KARTA = ROOT / "sun-cycle-bg.js"
OUT = ROOT / "demo" / "konfigurator.html"
LAT, LON = 53.5182, 14.4570
# obrazki na HA; na dysku repo ta sama para lezy w demo/assets
ZASOBY = "/local/sun-cycle/"

META = {
    "tytul": "Tło: konfigurator karty",
    "grupa": "Tło (sun-cycle-bg)",
    "status": "aktualne",
    "kolejnosc": 100,
    "opis": ("Wszystkie opcje karty sun-cycle-bg jako suwaki i przełączniki, nad żywym "
             "podglądem rysowanym przez samą kartę, a pod spodem gotowy fragment YAML do "
             "wklejenia w dashboard — tylko te klucze, które różnią się od domyślnych. "
             "Słońce symulowane (godzina, dzień roku, szerokość geograficzna), planety "
             "przeliczane z migawki Sol na wybraną chwilę, więc jadą razem z niebem. "
             "Strona jest generowana: karta wkleja się do niej przy budowaniu, więc nie "
             "może stroić innej wersji niż ta w repo."),
}

STRONA = r"""<meta charset="utf-8">
<title>Sun Cycle — konfigurator</title>
<style>
  :root { --bg:#0d1015; --surface:#151a22; --line:rgba(255,255,255,.08);
          --text:#e8ebf1; --muted:#96a0b0; --accent:#7cb3f9; --zle:#e0574a; }
  * { box-sizing: border-box; }
  body { background:var(--bg); color:var(--text); margin:0; padding:26px 18px 72px;
         font:15px/1.55 system-ui,"Segoe UI",Roboto,sans-serif; }
  main { max-width:1320px; margin:0 auto; display:flex; flex-direction:column; gap:20px; }
  h1 { font-size:23px; font-weight:750; margin:0 0 6px; letter-spacing:-.2px; }
  .lead p { color:var(--muted); margin:0 0 4px; max-width:88ch; }
  .card { background:var(--surface); border:1px solid var(--line);
          border-radius:16px; padding:16px 18px; }
  .card h2 { margin:0 0 10px; font-size:16px; }
  code { background:rgba(255,255,255,.06); border-radius:4px; padding:1px 5px; font-size:.92em; }

  .layout { display:grid; grid-template-columns:minmax(0,1fr) 420px; gap:18px; align-items:start; }
  @media (max-width:1080px) { .layout { grid-template-columns:1fr; } }

  hui-view-container#scena { position:relative; display:block; aspect-ratio:16/7;
    border-radius:12px; overflow:hidden; border:1px solid var(--line); background:#000; }
  hui-view-background { position:absolute; inset:0; display:block; z-index:0; }
  hui-view { position:absolute; inset:0; display:block; pointer-events:none; }
  .odczyt { display:flex; gap:16px; flex-wrap:wrap; color:var(--muted); font-size:13px;
            margin-top:8px; font-variant-numeric:tabular-nums; }
  .odczyt b { color:var(--text); font-weight:650; }

  fieldset { border:1px solid var(--line); border-radius:12px; margin:0 0 12px; padding:10px 12px 12px; }
  legend { padding:0 6px; font-size:13px; font-weight:650; color:var(--accent); letter-spacing:.02em; }
  .row { display:grid; grid-template-columns:150px minmax(0,1fr) 54px; gap:8px;
         align-items:center; margin:5px 0; font-size:13.5px; }
  .row.check { grid-template-columns:auto 1fr; }
  .row label { color:var(--muted); }
  .row .n { text-align:right; font-variant-numeric:tabular-nums; color:var(--text); }
  .row input[type=range] { width:100%; }
  .row input[type=text] { width:100%; background:#0a0c10; color:var(--text);
    border:1px solid var(--line); border-radius:7px; padding:5px 8px; font:inherit; font-size:13px; }
  .row select { background:#0a0c10; color:var(--text); border:1px solid var(--line);
    border-radius:7px; padding:4px 8px; font:inherit; font-size:13px; }
  fieldset[data-wylaczone] .row:not(.glowna) { opacity:.38; pointer-events:none; }

  .yamlglowa { display:flex; align-items:center; justify-content:space-between; gap:10px; }
  pre.yaml { margin:10px 0 0; background:#0a0c10; border:1px solid var(--line);
    border-radius:10px; padding:12px 14px; overflow:auto; font:13px/1.5 ui-monospace,
    "SF Mono","Roboto Mono",monospace; color:#cfe0ff; white-space:pre; }
  button { background:#1d2836; color:var(--text); border:1px solid var(--line);
    border-radius:8px; padding:6px 12px; font:inherit; font-size:13px; cursor:pointer; }
  button:hover { border-color:var(--accent); }
  .skopiowane { color:#6fbf8b; font-size:13px; opacity:0; transition:opacity .2s; }
  .skopiowane.jest { opacity:1; }
  .banner { display:none; background:rgba(224,87,74,.14); border:1px solid var(--zle);
    color:#ffd9d4; border-radius:10px; padding:10px 14px; font-size:13.5px; }
  .banner.jest { display:block; }
  .note { color:var(--muted); font-size:13px; margin:10px 0 0; }
</style>

<main>
  <div class="lead">
    <h1>Sun Cycle — konfigurator</h1>
    <p>Każda opcja karty jako suwak albo przełącznik. Podgląd rysuje <b>ta sama karta</b>,
    która pójdzie na dashboard — wklejona tu przy budowaniu strony, wersja
    <b id="wersja">—</b>. Pod spodem fragment YAML: tylko to, co różni się od domyślnych,
    więc wklejasz trzy linijki, a nie czterdzieści.</p>
  </div>

  <div id="banner" class="banner"></div>

  <div class="layout">
    <div>
      <div class="card">
        <h2>Podgląd</h2>
        <hui-view-container id="scena">
          <hui-view-background></hui-view-background>
          <sun-cycle-bg-card id="karta"></sun-cycle-bg-card>
          <hui-view></hui-view>
        </hui-view-container>
        <div class="odczyt">
          <span>słońce <b id="o-elev">—</b>° / <b id="o-az">—</b>°</span>
          <span>planet nad horyzontem: <b id="o-planet">—</b></span>
          <span>pas: <b id="o-pas">—</b></span>
        </div>
      </div>

      <div class="card" style="margin-top:16px">
        <h2>Symulowana chwila</h2>
        <div class="row"><label for="t">godzina</label>
          <input type="range" id="t" min="0" max="1439" step="1" value="1320">
          <span class="n" id="t-n"></span></div>
        <div class="row"><label for="d">dzień roku</label>
          <input type="range" id="d" min="0" max="364" step="1" value="241">
          <span class="n" id="d-n"></span></div>
        <div class="row"><label for="lat">szerokość</label>
          <input type="range" id="lat" min="0" max="66" step="0.5" value="__LAT__">
          <span class="n" id="lat-n"></span></div>
        <div class="row check"><button id="graj">▶ doba w 60 s</button>
          <span class="n" style="text-align:left;color:var(--muted)">podgląd, nie konfiguracja</span></div>
        <p class="note">Planety nie stoją w miejscu przy przesuwaniu czasu: pozycje z migawki
        <code>sensor.sol_*</code> (<span id="o-migawka">—</span>) są przeliczane na
        równikowe i rzutowane z powrotem na wybraną chwilę, więc jadą razem z niebem.</p>
      </div>

      <div class="card" style="margin-top:16px">
        <div class="yamlglowa">
          <h2 style="margin:0">YAML do wklejenia</h2>
          <span style="display:flex;gap:10px;align-items:center">
            <span class="skopiowane" id="skopiowane">skopiowane ✓</span>
            <button id="kopiuj">Kopiuj</button>
            <button id="zeruj">Domyślne</button>
          </span>
        </div>
        <pre class="yaml" id="yaml">—</pre>
        <p class="note" id="ile"></p>
        <p class="note">Wklej to jako kartę w każdym widoku, który ma być pomalowany —
        karta jest niewidoczna, maluje tło widoku, w którym stoi. W trybie YAML dashboardu
        albo przez <b>Dodaj kartę → Ręcznie</b>.</p>
      </div>
    </div>

    <div class="card" id="panel"><h2>Opcje</h2><div id="kontrolki"></div></div>
  </div>
</main>

<script>
/* ---- sun-cycle-bg.js, wklejone przy budowaniu strony ---- */
__KARTA__
</script>

<script>
(() => {
  const D2R = Math.PI / 180, R2D = 180 / Math.PI;
  const MIGAWKA = __MIGAWKA__;
  // ?assets=/demo/assets/ — żeby stronę dało się otworzyć wprost z repo,
  // gdzie /local/ nie istnieje
  const ZASOBY = new URLSearchParams(location.search).get("assets") || "__ZASOBY__";
  const $ = (id) => document.getElementById(id);

  /* ---------- astronomia strony: tyle, ile trzeba do symulacji ---------- */
  function julian(dt) {
    let y = dt.getUTCFullYear(), m = dt.getUTCMonth() + 1;
    const d = dt.getUTCDate() + (dt.getUTCHours() + dt.getUTCMinutes() / 60) / 24;
    if (m <= 2) { y -= 1; m += 12; }
    const A = Math.floor(y / 100), B = 2 - A + Math.floor(A / 4);
    return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d + B - 1524.5;
  }
  const gmst = (J) => (280.46061837 + 360.98564736629 * (J - 2451545)) % 360;
  function altaz(ra, dec, J, lat, lon) {
    const H = ((gmst(J) + lon - ra) % 360) * D2R, dr = dec * D2R, pr = lat * D2R;
    const alt = Math.asin(Math.sin(dr) * Math.sin(pr) + Math.cos(dr) * Math.cos(pr) * Math.cos(H));
    const az = Math.atan2(-Math.sin(H) * Math.cos(dr),
      Math.cos(pr) * Math.sin(dr) - Math.sin(pr) * Math.cos(dr) * Math.cos(H));
    return { alt: alt * R2D, az: ((az * R2D) % 360 + 360) % 360 };
  }
  // odwrotnosc powyzszego: z tego, gdzie cialo stalo w chwili migawki, wyjmij
  // wspolrzedne rownikowe, ktore sie nie zmieniaja przez kilka dni
  function altazDoEq(alt, az, J, lat, lon) {
    const a = alt * D2R, A = az * D2R, pr = lat * D2R;
    const dec = Math.asin(Math.sin(a) * Math.sin(pr) + Math.cos(a) * Math.cos(pr) * Math.cos(A));
    const H = Math.atan2(-Math.sin(A) * Math.cos(a),
      Math.cos(pr) * Math.sin(a) - Math.sin(pr) * Math.cos(a) * Math.cos(A));
    const ra = ((gmst(J) + lon - H * R2D) % 360 + 360) % 360;
    return { ra, dec: dec * R2D };
  }
  function sunEq(J) {
    const n = J - 2451545, L = (280.460 + 0.9856474 * n) % 360;
    const g = ((357.528 + 0.9856003 * n) % 360) * D2R;
    const lam = ((L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) % 360) * D2R;
    const eps = 23.439 * D2R;
    return {
      ra: ((Math.atan2(Math.cos(eps) * Math.sin(lam), Math.cos(lam)) * R2D) % 360 + 360) % 360,
      dec: Math.asin(Math.sin(eps) * Math.sin(lam)) * R2D,
    };
  }
  // rownikowe kazdej planety, policzone raz z migawki
  const J_MIGAWKA = julian(new Date(MIGAWKA.pobrano));
  const PLANETY_EQ = {};
  for (const [b, w] of Object.entries(MIGAWKA.planety)) {
    PLANETY_EQ[b] = altazDoEq(Number(w.elevation), Number(w.azimuth),
                              J_MIGAWKA, __LAT__, __LON__);
  }

  /* ---------- tabela kontrolek ----------
     klucz: sciezka w configu, dom: wartosc domyslna karty, spr: skad ja
     wziac z samej karty (do kontroli spojnosci) */
  const GRUPY = __GRUPY__;

  /* ---------- kontrola spojnosci z kartą ---------- */
  function sprawdzDomyslne() {
    const scb = window.sunCycleBg;
    if (!scb) return ["Karta nie wystawiła window.sunCycleBg — strona zbudowana ze złego pliku?"];
    const zrodla = {
      stars: scb.readStarConfig({}),
      planets: scb.readPlanetConfig(true),
      milky_way: scb.readMilkyConfig({}),
    };
    const bledy = [];
    for (const g of GRUPY) for (const p of g.pola) {
      if (!p.spr) continue;
      const [blok, ...reszta] = p.spr.split(".");
      let v = zrodla[blok];
      for (const k of reszta) v = v && v[k];
      const oczek = p.dom;
      const rowne = Array.isArray(oczek) ? JSON.stringify(v) === JSON.stringify(oczek)
                  : (typeof v === "number" ? Math.abs(v - oczek) < 1e-9 : v === oczek);
      if (!rowne) bledy.push(`${p.klucz}: strona mówi ${JSON.stringify(oczek)}, ` +
                             `karta ${JSON.stringify(v)}`);
    }
    return bledy;
  }

  /* ---------- budowa panelu ---------- */
  const POLA = {};
  function zbudujPanel() {
    const host = $("kontrolki");
    for (const g of GRUPY) {
      const fs = document.createElement("fieldset");
      fs.innerHTML = `<legend>${g.tytul}</legend>`;
      if (g.opis) {
        const p = document.createElement("p");
        p.className = "note"; p.style.margin = "0 0 6px"; p.textContent = g.opis;
        fs.appendChild(p);
      }
      for (const p of g.pola) {
        const id = "f_" + p.klucz.replace(/[^a-z0-9]/gi, "_");
        const row = document.createElement("div");
        row.className = "row" + (p.typ === "bool" ? " check" : "") + (p.glowna ? " glowna" : "");
        if (p.typ === "bool") {
          row.innerHTML = `<input type="checkbox" id="${id}"><label for="${id}">${p.etykieta}</label>`;
        } else if (p.typ === "tekst") {
          row.innerHTML = `<label for="${id}">${p.etykieta}</label>` +
                          `<input type="text" id="${id}" placeholder="${p.hint || ""}">` +
                          `<span class="n"></span>`;
        } else if (p.typ === "wybor") {
          row.innerHTML = `<label for="${id}">${p.etykieta}</label><select id="${id}">` +
            p.opcje.map((o) => `<option value="${o}">${o}</option>`).join("") +
            `</select><span class="n"></span>`;
        } else {
          row.innerHTML = `<label for="${id}">${p.etykieta}</label>` +
            `<input type="range" id="${id}" min="${p.min}" max="${p.max}" step="${p.krok}">` +
            `<span class="n" id="${id}_n"></span>`;
        }
        fs.appendChild(row);
        POLA[p.klucz] = { def: p, el: null, id, fs };
      }
      host.appendChild(fs);
      g._fs = fs;
    }
    for (const k of Object.keys(POLA)) POLA[k].el = $(POLA[k].id);
    zeruj();
  }

  function ustaw(k, v) {
    const { def, el } = POLA[k];
    if (def.typ === "bool") el.checked = !!v;
    else if (def.typ === "tekst") el.value = v == null ? "" : String(v);
    else if (def.typ === "wybor") el.value = String(v);
    else el.value = String(v);
  }
  function czytaj(k) {
    const { def, el } = POLA[k];
    if (def.typ === "bool") return el.checked;
    if (def.typ === "tekst") return el.value.trim();
    if (def.typ === "wybor") return el.value;
    return Number(el.value);
  }
  function zeruj() {
    for (const g of GRUPY) for (const p of g.pola) ustaw(p.klucz, p.start !== undefined ? p.start : p.dom);
    zastosuj();
  }

  /* ---------- config z kontrolek ----------
     Dwa przebiegi po tej samej tabeli. `pelnyConfig` daje kartę do podglądu:
     każda wartość, jaka stoi na suwakach. `yamlConfig` daje fragment do
     wklejenia: tylko to, co różni się od domyślnych karty, plus skrót na blok,
     który jest domyślnie wyłączony (`planets: true`, `milky_way: {}`) albo
     domyślnie włączony i właśnie go gasimy (`stars: false`). */
  function wstaw(cel, sciezka, wartosc) {
    const czesci = sciezka.split(".");
    let o = cel;
    for (let i = 0; i < czesci.length - 1; i++) {
      if (typeof o[czesci[i]] !== "object" || o[czesci[i]] === null) o[czesci[i]] = {};
      o = o[czesci[i]];
    }
    o[czesci[czesci.length - 1]] = wartosc;
  }
  function rowneDomyslnej(v, d) {
    if (Array.isArray(d)) return JSON.stringify(v) === JSON.stringify(d);
    if (typeof d === "number" && typeof v === "number") return Math.abs(v - d) < 1e-9;
    return v === d;
  }
  const wlaczona = (g) => !g.wlacznik || czytaj(g.wlacznik);
  // Blok w zgaszonym rodzicu nie istnieje: `stars: false` i `stars.iss` naraz
  // to nie jest config, tylko nadpisanie fałszu obiektem.
  const rodzicZgaszony = (g) => {
    if (!g.zalezyOd) return false;
    const r = GRUPY.find((x) => x.wlacznik === g.zalezyOd);
    return !!r && !czytaj(r.wlacznik);
  };

  function pelnyConfig() {
    const cfg = {};
    for (const g of GRUPY) {
      if (rodzicZgaszony(g)) continue;
      if (g.wlacznik && !czytaj(g.wlacznik)) { wstaw(cfg, g.wlacznik, false); continue; }
      for (const p of g.pola) {
        if (p.klucz === g.wlacznik) continue;
        const v = czytaj(p.klucz);
        if (p.typ === "tekst" && v === "") continue;
        wstaw(cfg, p.klucz, v);
      }
    }
    cfg.azimuth = [czytaj("__az0"), czytaj("__az1")];
    delete cfg.__az0; delete cfg.__az1;
    return cfg;
  }

  function yamlConfig() {
    const cfg = {};
    for (const g of GRUPY) {
      if (rodzicZgaszony(g)) continue;
      const wl = wlaczona(g);
      if (g.wlacznik && !wl) {
        // wyłączony blok trzeba napisać tylko wtedy, gdy domyślnie jest włączony
        if (g.domWl) wstaw(cfg, g.wlacznik, false);
        continue;
      }
      let zmian = 0;
      for (const p of g.pola) {
        if (p.klucz === g.wlacznik) continue;
        const v = czytaj(p.klucz);
        if (p.typ === "tekst" && v === "") continue;
        if (rowneDomyslnej(v, p.dom)) continue;
        wstaw(cfg, p.klucz, v);
        zmian++;
      }
      // blok domyślnie wyłączony, a nic w nim nie ruszone: sam skrót
      if (g.wlacznik && wl && !g.domWl && !zmian) wstaw(cfg, g.wlacznik, g.skrotWl);
    }
    const a0 = czytaj("__az0"), a1 = czytaj("__az1");
    delete cfg.__az0; delete cfg.__az1;
    if (a0 !== 50 || a1 !== 310) cfg.azimuth = [a0, a1];
    return cfg;
  }

  /* ---------- YAML ---------- */
  function yaml(cfg) {
    const linie = ["type: custom:sun-cycle-bg-card"];
    const skalar = (v) => typeof v === "string"
      ? (/^[\w./:-]+$/.test(v) ? v : JSON.stringify(v)) : String(v);
    const dump = (o, wciecie) => {
      for (const [k, v] of Object.entries(o)) {
        if (Array.isArray(v)) linie.push(`${wciecie}${k}: [${v.map(skalar).join(", ")}]`);
        else if (v && typeof v === "object") {
          if (!Object.keys(v).length) linie.push(`${wciecie}${k}: {}`);
          else { linie.push(`${wciecie}${k}:`); dump(v, wciecie + "  "); }
        } else linie.push(`${wciecie}${k}: ${skalar(v)}`);
      }
    };
    dump(cfg, "");
    return linie.join("\n");
  }

  /* ---------- podglad ---------- */
  const karta = $("karta");
  let graTimer = null;

  function zastosuj() {
    for (const g of GRUPY) {
      if (g.wlacznik) g._fs.toggleAttribute("data-wylaczone", !czytaj(g.wlacznik));
    }
    for (const k of Object.keys(POLA)) {
      const n = $(POLA[k].id + "_n");
      if (n) n.textContent = POLA[k].def.fmt ? POLA[k].def.fmt(czytaj(k)) : czytaj(k);
    }
    const pelny = pelnyConfig();
    pelny.assets = ZASOBY;
    karta.setConfig(pelny);

    const t = Number($("t").value), d = Number($("d").value), lat = Number($("lat").value);
    $("t-n").textContent = String(Math.floor(t / 60)).padStart(2, "0") + ":" +
                           String(t % 60).padStart(2, "0");
    const data = new Date(Date.UTC(2026, 0, 1) + d * 86400000 + t * 60000);
    $("d-n").textContent = String(data.getUTCDate()).padStart(2, "0") + "." +
                           String(data.getUTCMonth() + 1).padStart(2, "0");
    $("lat-n").textContent = lat + "°";
    const J = julian(data);
    const se = sunEq(J), sp = altaz(se.ra, se.dec, J, lat, __LON__);
    const stany = { "sun.sun": { attributes: { elevation: sp.alt, azimuth: sp.az } } };
    let nadHoryzontem = 0;
    for (const [b, eq] of Object.entries(PLANETY_EQ)) {
      const p = altaz(eq.ra, eq.dec, J, lat, __LON__);
      if (p.alt > 0) nadHoryzontem++;
      stany["sensor.sol_" + b + "_azimuth"] = { state: p.az.toFixed(1) };
      stany["sensor.sol_" + b + "_elevation"] = { state: p.alt.toFixed(1) };
    }
    karta.hass = { states: stany, config: { latitude: lat, longitude: __LON__ } };

    $("o-elev").textContent = sp.alt.toFixed(1);
    $("o-az").textContent = sp.az.toFixed(0);
    $("o-planet").textContent = nadHoryzontem;
    // Pas mierzony, nie deklarowany: przy `frame` krycie bywa 1, a w oknie
    // nieba nie ma ani piksela zdjęcia, bo ten kawałek nieba jest pod Ziemią.
    // Kanwa rysuje się przy przemalowaniu karty, więc pomiar idzie po nim.
    setTimeout(() => {
      const mw = document.querySelector(".sun-cycle-milky");
      if (!mw || !mw.width) { $("o-pas").textContent = "wyłączony"; return; }
      const g = mw.getContext("2d");
      const d = g.getImageData(0, 0, mw.width, mw.height).data;
      let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 2) n++;
      const proc = (100 * n / (mw.width * mw.height)).toFixed(0);
      $("o-pas").textContent = "krycie " + (mw.style.opacity || "0") +
        ", " + proc + "% kadru";
    }, 140);


    const przyciety = yamlConfig();
    $("yaml").textContent = yaml(przyciety);
    const ile = yaml(przyciety).split("\n").length - 1;
    $("ile").textContent = ile === 0
      ? "Zero linii poza typem: to są ustawienia domyślne karty."
      : ile + (ile === 1 ? " linia" : ile < 5 ? " linie" : " linii") +
        " poza typem — reszta zostaje domyślna.";
  }

  /* ---------- start ---------- */
  zbudujPanel();
  const wersja = (document.currentScript && "") ||
    (window.sunCycleBg ? "" : "");
  const nagl = document.querySelector("script").textContent.match(/sun-cycle-bg ([\d.]+)/);
  $("wersja").textContent = nagl ? nagl[1] : "?";
  $("o-migawka").textContent = MIGAWKA.pobrano.slice(0, 16).replace("T", " ");

  const bledy = sprawdzDomyslne();
  if (bledy.length) {
    $("banner").classList.add("jest");
    $("banner").innerHTML = "<b>Strona rozjechała się z kartą.</b> Domyślne w tabeli " +
      "kontrolek nie zgadzają się z tym, co zwraca karta — YAML poniżej może pomijać " +
      "klucze, które w rzeczywistości nie są domyślne:<br>" +
      bledy.map((b) => "• " + b).join("<br>");
  }

  document.addEventListener("input", (e) => { if (e.target.tagName !== "TEXTAREA") zastosuj(); });
  document.addEventListener("change", zastosuj);
  $("zeruj").addEventListener("click", zeruj);
  $("kopiuj").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("yaml").textContent);
    const m = $("skopiowane"); m.classList.add("jest");
    setTimeout(() => m.classList.remove("jest"), 1400);
  });
  $("graj").addEventListener("click", () => {
    if (graTimer) { clearInterval(graTimer); graTimer = null; $("graj").textContent = "▶ doba w 60 s"; return; }
    $("graj").textContent = "■ stop";
    graTimer = setInterval(() => {
      const t = $("t");
      t.value = String((Number(t.value) + 6) % 1440);
      zastosuj();
    }, 250);
  });
  zastosuj();
})();
</script>
"""


def grupy():
    """Tabela kontrolek. `spr` wskazuje, skąd karta podaje tę samą domyślną."""
    return [
        {"tytul": "Niebo", "pola": [
            {"klucz": "__az0", "etykieta": "okno: wschód", "typ": "zakres",
             "min": 0, "max": 360, "krok": 1, "dom": 50},
            {"klucz": "__az1", "etykieta": "okno: zachód", "typ": "zakres",
             "min": 0, "max": 360, "krok": 1, "dom": 310},
            {"klucz": "twilight_palette", "etykieta": "cieplejszy zmierzch", "typ": "bool",
             "dom": False},
            {"klucz": "moon", "etykieta": "księżyc", "typ": "bool", "dom": True},
            {"klucz": "rays.blur", "etykieta": "promienie: rozmycie", "typ": "zakres",
             "min": 0, "max": 60, "krok": 1, "dom": 28},
            {"klucz": "rays.strength", "etykieta": "promienie: siła", "typ": "zakres",
             "min": 0, "max": 1, "krok": 0.05, "dom": 0.5},
        ]},
        {"tytul": "Gwiazdy", "wlacznik": "stars", "domWl": True, "skrotWl": True, "pola": [
            {"klucz": "stars", "etykieta": "pole gwiazd", "typ": "bool", "dom": True,
             "glowna": True},
            {"klucz": "stars.count", "etykieta": "liczba", "typ": "zakres",
             "min": 0, "max": 300, "krok": 5, "dom": 90, "spr": "stars.count"},
            {"klucz": "stars.drift", "etykieta": "dryf (s/szer.)", "typ": "zakres",
             "min": 0, "max": 3600, "krok": 60, "dom": 1800, "spr": "stars.drift"},
            {"klucz": "stars.rotate", "etykieta": "obrót wokół bieguna", "typ": "bool",
             "dom": False, "spr": "stars.rotate"},
            {"klucz": "stars.pivot", "etykieta": "biegun (× wys.)", "typ": "zakres",
             "min": 0.5, "max": 6, "krok": 0.1, "dom": 2.2, "spr": "stars.pivot"},
            {"klucz": "stars.sizes", "etykieta": "wielkości", "typ": "wybor",
             "opcje": ["flat", "mixed"], "dom": "flat", "spr": "stars.sizes"},
            {"klucz": "stars.size", "etykieta": "rozmiar", "typ": "zakres",
             "min": 0.25, "max": 2, "krok": 0.05, "dom": 1, "spr": "stars.size"},
            {"klucz": "stars.glow", "etykieta": "poświata", "typ": "zakres",
             "min": 0, "max": 2, "krok": 0.05, "dom": 1, "spr": "stars.glow"},
            {"klucz": "stars.twinkle", "etykieta": "migotanie", "typ": "zakres",
             "min": 0, "max": 1.4, "krok": 0.05, "dom": 1, "spr": "stars.twinkle"},
        ]},
        {"tytul": "Rozbłyski", "zalezyOd": "stars",
         "opis": "Kilka gwiazd, które co jakiś czas błyskają.", "pola": [
            {"klucz": "stars.flares.count", "etykieta": "ile gwiazd", "typ": "zakres",
             "min": 0, "max": 12, "krok": 1, "dom": 0, "spr": "stars.flares.count"},
            {"klucz": "stars.flares.every", "etykieta": "co ile s", "typ": "zakres",
             "min": 4, "max": 120, "krok": 1, "dom": 26, "spr": "stars.flares.every"},
            {"klucz": "stars.flares.strength", "etykieta": "siła", "typ": "zakres",
             "min": 0, "max": 1, "krok": 0.05, "dom": 1, "spr": "stars.flares.strength"},
            {"klucz": "stars.flares.spikes", "etykieta": "promienie dyfrakcyjne",
             "typ": "bool", "dom": True, "spr": "stars.flares.spikes"},
        ]},
        {"tytul": "Meteory", "zalezyOd": "stars",
         "opis": "Rate 0 wyłącza. Radiant (rój) tylko z YAML-a.", "pola": [
            {"klucz": "stars.meteors.rate", "etykieta": "na godzinę", "typ": "zakres",
             "min": 0, "max": 120, "krok": 1, "dom": 0, "spr": "stars.meteors.rate"},
            {"klucz": "stars.meteors.length", "etykieta": "długość (px)", "typ": "zakres",
             "min": 40, "max": 500, "krok": 10, "dom": 190, "spr": "stars.meteors.length"},
            {"klucz": "stars.meteors.speed", "etykieta": "czas smugi (s)", "typ": "zakres",
             "min": 0.3, "max": 4, "krok": 0.1, "dom": 1.1, "spr": "stars.meteors.speed"},
            {"klucz": "stars.meteors.angle", "etykieta": "kąt (°)", "typ": "zakres",
             "min": 0, "max": 80, "krok": 1, "dom": 24, "spr": "stars.meteors.angle"},
            {"klucz": "stars.meteors.pair", "etykieta": "szansa na drugą", "typ": "zakres",
             "min": 0, "max": 1, "krok": 0.05, "dom": 0, "spr": "stars.meteors.pair"},
        ]},
        {"tytul": "ISS", "wlacznik": "stars.iss", "domWl": False, "skrotWl": True,
         "zalezyOd": "stars",
         "opis": "Prawdziwe przeloty z Satellite Tracker; `co ile s` to tryb pokazowy.",
         "pola": [
            {"klucz": "stars.iss", "etykieta": "ISS", "typ": "bool", "dom": False,
             "glowna": True},
            {"klucz": "stars.iss.trail", "etykieta": "smuga (px)", "typ": "zakres",
             "min": 0, "max": 200, "krok": 5, "dom": 0},
            {"klucz": "stars.iss.label", "etykieta": "podpis", "typ": "bool", "dom": False},
            {"klucz": "stars.iss.every", "etykieta": "pokaz co (s)", "typ": "zakres",
             "min": 0, "max": 120, "krok": 5, "dom": 0},
        ]},
        {"tytul": "Planety", "wlacznik": "planets", "domWl": False, "skrotWl": True, "pola": [
            {"klucz": "planets", "etykieta": "planety", "typ": "bool", "dom": False,
             "start": True, "glowna": True},
            {"klucz": "planets.size", "etykieta": "wielkość (% szer.)", "typ": "zakres",
             "min": 0.4, "max": 6, "krok": 0.1, "dom": 2.4, "spr": "planets.size"},
            {"klucz": "planets.scale", "etykieta": "szereg", "typ": "wybor",
             "opcje": ["brightness", "diameters", "equal"], "dom": "brightness"},
            {"klucz": "planets.glow", "etykieta": "poświata", "typ": "zakres",
             "min": 0, "max": 2, "krok": 0.05, "dom": 0.5, "spr": "planets.glow"},
            {"klucz": "planets.points", "etykieta": "punkt w dzień (px)", "typ": "zakres",
             "min": 0, "max": 10, "krok": 0.5, "dom": 3.5, "spr": "planets.points"},
            {"klucz": "planets.day", "etykieta": "podłoga dzienna", "typ": "zakres",
             "min": 0, "max": 1, "krok": 0.05, "dom": 0, "spr": "planets.day"},
            {"klucz": "planets.min_elevation", "etykieta": "próg wysokości (°)",
             "typ": "zakres", "min": -10, "max": 30, "krok": 1, "dom": 0,
             "spr": "planets.min_elevation"},
            {"klucz": "planets.labels", "etykieta": "podpisy", "typ": "bool", "dom": False,
             "spr": "planets.labels"},
        ]},
        {"tytul": "Droga Mleczna", "wlacznik": "milky_way", "domWl": False, "skrotWl": {},
         "opis": "frame = jedno zdjęcie tam, gdzie powstało (l/b/rot/fov mają sens tylko tu); "
                 "equirect = panorama całego nieba, zawsze połowa pasa nad horyzontem.",
         "pola": [
            {"klucz": "milky_way", "etykieta": "pas", "typ": "bool", "dom": False,
             "start": True, "glowna": True},
            {"klucz": "milky_way.projection", "etykieta": "rzut", "typ": "wybor",
             "opcje": ["frame", "equirect"], "dom": "frame", "spr": "milky_way.projection"},
            {"klucz": "milky_way.strength", "etykieta": "jasność", "typ": "zakres",
             "min": 0, "max": 1, "krok": 0.05, "dom": 0.9, "spr": "milky_way.strength"},
            {"klucz": "milky_way.horizon", "etykieta": "próg wygaszania (°)",
             "typ": "zakres", "min": 0, "max": 60, "krok": 1, "dom": 22,
             "spr": "milky_way.horizon"},
            {"klucz": "milky_way.mesh", "etykieta": "siatka", "typ": "zakres",
             "min": 6, "max": 64, "krok": 2, "dom": 32, "spr": "milky_way.mesh"},
            {"klucz": "milky_way.l", "etykieta": "kadr: l (°)", "typ": "zakres",
             "min": -180, "max": 180, "krok": 1, "dom": -5, "spr": "milky_way.l"},
            {"klucz": "milky_way.b", "etykieta": "kadr: b (°)", "typ": "zakres",
             "min": -90, "max": 90, "krok": 1, "dom": -2, "spr": "milky_way.b"},
            {"klucz": "milky_way.rot", "etykieta": "kadr: obrót (°)", "typ": "zakres",
             "min": -180, "max": 180, "krok": 1, "dom": -24, "spr": "milky_way.rot"},
            {"klucz": "milky_way.fov", "etykieta": "kadr: pole (°)", "typ": "zakres",
             "min": 20, "max": 150, "krok": 1, "dom": 62, "spr": "milky_way.fov"},
        ]},
        {"tytul": "Tarcze i pliki",
         "opis": "Puste pole = zostaje to, co karta instaluje. `assets` przesuwa wszystkie "
                 "domyślne ścieżki naraz; na tej stronie jest ustawione na "
                 "/local/sun-cycle/ i dlatego nie ma go w YAML-u.",
         "pola": [
            {"klucz": "sun_image_width", "etykieta": "słońce: szer. (%)", "typ": "zakres",
             "min": 3, "max": 25, "krok": 0.5, "dom": 10.5},
            {"klucz": "sun_image_blur", "etykieta": "słońce: rozmycie (%)", "typ": "zakres",
             "min": 0, "max": 40, "krok": 0.5, "dom": 11.5},
            {"klucz": "moon_image_width", "etykieta": "księżyc: szer. (%)", "typ": "zakres",
             "min": 3, "max": 30, "krok": 0.5, "dom": 13},
            {"klucz": "sun_image", "etykieta": "słońce: plik", "typ": "tekst", "dom": "",
             "hint": "/local/moje/sun.png"},
            {"klucz": "moon_image", "etykieta": "księżyc: plik", "typ": "tekst", "dom": "",
             "hint": "/local/moje/moon.png"},
            {"klucz": "sun_entity", "etykieta": "encja słońca", "typ": "tekst", "dom": "",
             "hint": "sun.sun"},
        ]},
    ]


def main() -> int:
    if not KARTA.exists():
        sys.exit(f"brak {KARTA}")
    migawka = json.loads((ROOT / "demo" / "sol_snapshot.json").read_text())
    html = (STRONA
            .replace("__KARTA__", KARTA.read_text())
            .replace("__GRUPY__", json.dumps(grupy(), ensure_ascii=False))
            .replace("__MIGAWKA__", json.dumps(migawka, ensure_ascii=False))
            .replace("__ZASOBY__", ZASOBY)
            .replace("__LAT__", str(LAT))
            .replace("__LON__", str(LON)))
    OUT.write_text(html)
    OUT.with_suffix(".meta.json").write_text(
        json.dumps(META, ensure_ascii=False, indent=1) + "\n")
    wersja = KARTA.read_text().split("\n")[0]
    print(f"{OUT} ({len(html) // 1024} kB) — {wersja[3:36]}")
    print(f"kontrolek: {sum(len(g['pola']) for g in grupy())}, "
          f"zbudowano {datetime.date.today()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
