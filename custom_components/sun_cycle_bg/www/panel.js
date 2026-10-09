/* Sun Cycle Background: the settings page of the sun_cycle_bg integration.

   Reached from Settings, Devices & services, the integration's Configure
   button (the integration registers this panel with config_panel_domain, and
   no title, so it stays out of the sidebar). Lists the profiles, edits one
   with the card's own visual editor next to a live preview, and writes it on
   Save. The form is the card's own editor, shipped in the same integration,
   so a field added to the card shows up here as well. */

const WS = 'sun_cycle_bg/profile/';
const CARD = 'custom:sun-cycle-bg-card';
const NAME_OK = /^[A-Za-z0-9_-]{1,64}$/;

const CSS = `
  :host { display: block; min-height: 100vh; background: var(--primary-background-color);
          color: var(--primary-text-color); font-family: var(--ha-font-family-body, Roboto, sans-serif); }
  header { display: flex; align-items: center; gap: 12px; height: 56px; padding: 0 12px;
           background: var(--app-header-background-color, var(--primary-color));
           color: var(--app-header-text-color, #fff); position: sticky; top: 0; z-index: 2; }
  header a { color: inherit; text-decoration: none; font-size: 22px; line-height: 1; padding: 6px 10px; border-radius: 50%; }
  header h1 { font-size: 20px; font-weight: 400; margin: 0; flex: 1; }
  main { display: grid; grid-template-columns: 240px minmax(0, 1fr) minmax(0, 1fr); gap: 16px; padding: 16px;
         max-width: 1600px; margin: 0 auto; align-items: start; }
  :host([narrow]) main { grid-template-columns: 1fr; }
  section { background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px);
            border: 1px solid var(--divider-color, rgba(0,0,0,.12)); padding: 12px; }
  h2 { font-size: 15px; margin: 0 0 10px; font-weight: 500; }
  .profil { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px; border-radius: 8px; cursor: pointer;
            border: 1px solid transparent; }
  .profil:hover { background: rgba(127,127,127,.08); }
  .profil[aria-current] { border-color: var(--primary-color); background: rgba(3,169,244,.08); }
  .profil b { font-weight: 500; }
  .profil small, .muted { color: var(--secondary-text-color); font-size: 12px; }
  .akcje { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  button { font: inherit; font-size: 14px; padding: 6px 12px; border-radius: 8px; cursor: pointer;
           border: 1px solid var(--divider-color, rgba(127,127,127,.4)); background: none; color: var(--primary-text-color); }
  button.glowny { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
  button:disabled { opacity: .45; cursor: default; }
  .pasek { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 10px; }
  .pasek .stan { flex: 1; font-size: 13px; color: var(--secondary-text-color); }
  .blad { color: var(--error-color, #db4437); }
  .uwaga { margin: 0 0 10px; padding: 8px 10px; border-radius: 8px; font-size: 13px;
           background: rgba(255,152,0,.12); border: 1px solid var(--warning-color, #ff9800); }
  .podglad { position: sticky; top: 72px; }
  ul { margin: 6px 0 0; padding-left: 18px; font-size: 13px; }
`;

class SunCycleBgPanel extends HTMLElement {
  constructor() {
    super();
    // here, not in connectedCallback: the frontend sets `hass` before it attaches the panel
    this.attachShadow({ mode: 'open' });
  }

  set hass(h) {
    const pierwszy = !this._hass;
    this._hass = h;
    if (this._ed) this._ed.hass = h;
    if (this._podglad) this._podglad.hass = h;
    if (pierwszy) this._start();
  }
  get hass() { return this._hass; }

  set narrow(n) { this.toggleAttribute('narrow', !!n); }

  connectedCallback() {
    this._beforeUnload = (e) => { if (this._brudny) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', this._beforeUnload);
  }

  disconnectedCallback() {
    window.removeEventListener('beforeunload', this._beforeUnload);
    this._odsubskrybuj();
  }

  async _start() {
    this._szkielet();
    try {
      await this._zaladujKarte();
    } catch (err) {
      this._komunikat('The sun-cycle-bg card is not loaded: ' + err.message +
        ' Reload the page; if it stays, the browser console has the reason.', true);
      return;
    }
    await this._lista();
    const pierwszy = Object.keys(this._profile)[0];
    if (pierwszy) this._wybierz(pierwszy);
    else this._komunikat('No profile yet. Create one with New profile; a card with `profile: <name>` then takes it.');
    this._uzycie();
  }

  // the card ships with the integration and is loaded on every page; should
  // this page come up first, load it here through the same loader
  async _zaladujKarte() {
    if (customElements.get('sun-cycle-bg-card-editor')) return;
    const loader = new URL('./loader.js' + new URL(import.meta.url).search, import.meta.url).href;
    await Promise.race([
      import(loader).then(() => customElements.whenDefined('sun-cycle-bg-card-editor')),
      new Promise((_, nie) => setTimeout(() => nie(new Error('it did not load within 15 s.')), 15000)),
    ]);
  }

  _szkielet() {
    const r = this.shadowRoot;
    r.innerHTML = `<style>${CSS}</style>
      <header><a href="/config/integrations/integration/sun_cycle_bg" title="Back">&larr;</a>
        <h1>Sun Cycle Background</h1></header>
      <main>
        <section class="lista"><h2>Profiles</h2><div class="profile"></div>
          <div class="akcje">
            <button data-a="nowy">New profile</button>
            <button data-a="kopia" disabled>Duplicate</button>
            <button data-a="zmien" disabled>Rename</button>
            <button data-a="usun" disabled>Delete</button>
          </div>
          <div class="uzycie muted"></div>
        </section>
        <section class="edycja">
          <div class="pasek">
            <span class="stan">Loading the card&hellip;</span>
            <button data-a="cofnij" disabled>Discard changes</button>
            <button data-a="zapisz" class="glowny" disabled>Save</button>
          </div>
          <div class="komunikat"></div>
          <div class="formularz"></div>
        </section>
        <section class="podglad"><h2>Preview</h2><div class="kadr"></div>
          <p class="muted">With the unsaved changes, on the card's fixed demo sky (dusk, sun at -9.5&deg;) so stars,
          planets and the band show whatever the time. Save applies the changes to every card on this profile at
          once, wall kiosks included.</p></section>
      </main>`;
    r.querySelectorAll('button[data-a]').forEach((b) => b.addEventListener('click', () => this['_' + b.dataset.a]()));
  }

  _komunikat(tekst, blad) {
    const k = this.shadowRoot.querySelector('.komunikat');
    k.textContent = tekst || '';
    k.className = 'komunikat' + (tekst ? ' uwaga' : '') + (blad ? ' blad' : '');
  }

  _stan(tekst, blad) {
    const s = this.shadowRoot.querySelector('.stan');
    s.textContent = tekst;
    s.classList.toggle('blad', !!blad);
  }

  async _lista() {
    const r = await this._hass.callWS({ type: WS + 'list' });
    this._profile = r.profiles || {};
    const box = this.shadowRoot.querySelector('.profile');
    box.textContent = '';
    for (const [nazwa, info] of Object.entries(this._profile).sort(([a], [b]) => a.localeCompare(b))) {
      const d = document.createElement('div');
      d.className = 'profil';
      if (nazwa === this._nazwa) d.setAttribute('aria-current', 'true');
      d.innerHTML = '<b></b><small></small>';
      d.querySelector('b').textContent = nazwa;
      d.querySelector('small').textContent = info.updated
        ? new Date(info.updated).toLocaleString() + (info.updated_by ? ', ' + info.updated_by : '') : '';
      d.addEventListener('click', () => this._wybierz(nazwa));
      box.appendChild(d);
    }
    if (!Object.keys(this._profile).length) box.innerHTML = '<p class="muted">None yet.</p>';
    const jest = !!this._nazwa;
    for (const a of ['kopia', 'zmien', 'usun']) this.shadowRoot.querySelector(`[data-a="${a}"]`).disabled = !jest;
  }

  async _wybierz(nazwa) {
    if (nazwa === this._nazwa) return;
    if (this._brudny && !confirm('Discard the unsaved changes to "' + this._nazwa + '"?')) return;
    this._odsubskrybuj();
    this._nazwa = nazwa;
    this._brudny = false;
    this._komunikat('');
    await this._lista();
    // follow the profile: a save from another tab or the dashboard shows up here
    this._sub = this._hass.connection.subscribeMessage((m) => this._przyszlo(m),
      { type: WS + 'subscribe', profile: nazwa });
  }

  _odsubskrybuj() {
    const s = this._sub;
    this._sub = null;
    if (s) s.then((u) => u()).catch(() => {});
  }

  _przyszlo(m) {
    if (m.profile !== this._nazwa) return;
    const cfg = m.config || {};
    if (this._brudny) {
      if (JSON.stringify(cfg) !== JSON.stringify(this._zapisany)) {
        this._komunikat('This profile was just saved somewhere else. Save overwrites it; Discard changes loads that version.');
        this._obcy = cfg;
      }
      return;
    }
    // our own save coming back, or nothing new: keep the form as it is (open groups, scroll)
    if (!this._ed || JSON.stringify(cfg) !== JSON.stringify(this._zapisany)) this._pokaz(cfg);
    this._zapisany = cfg;
    this._stan(m.updated ? 'Saved ' + new Date(m.updated).toLocaleString() +
      (m.updated_by ? ' by ' + m.updated_by : '') : 'Not saved yet.');
    this._przyciski();
  }

  // a fresh editor and preview for this config (the editor only rebuilds on a config it did not send)
  _pokaz(cfg) {
    const pelny = Object.assign({ type: CARD }, JSON.parse(JSON.stringify(cfg)));
    this._robocza = pelny;
    const form = this.shadowRoot.querySelector('.formularz');
    form.textContent = '';
    this._ed = document.createElement('sun-cycle-bg-card-editor');
    this._ed.hass = this._hass;
    this._ed.setConfig(pelny);
    this._ed.addEventListener('config-changed', (e) => {
      e.stopPropagation();
      // a deep copy: the editor changes its nested objects in place, and a shared
      // `stars` would make the saved state follow every edit (Save never lit up)
      this._robocza = JSON.parse(JSON.stringify(e.detail.config));
      this._brudny = JSON.stringify(this._bez(this._robocza)) !== JSON.stringify(this._zapisany);
      this._odswiezPodglad();
      this._przyciski();
      this._stan(this._brudny ? 'Unsaved changes.' : 'No changes.');
    });
    form.appendChild(this._ed);
    const kadr = this.shadowRoot.querySelector('.kadr');
    kadr.textContent = '';
    this._podglad = document.createElement('sun-cycle-bg-card');
    this._podglad.setConfig(pelny);
    kadr.appendChild(this._podglad);
    this._podglad.hass = this._hass;
  }

  _odswiezPodglad() {
    clearTimeout(this._podgladT);
    this._podgladT = setTimeout(() => {
      if (!this._podglad) return;
      this._podglad.setConfig(this._robocza);
      this._podglad.hass = this._hass;
      if (typeof this._podglad._apply === 'function') this._podglad._apply(true);
    }, 250);
  }

  _bez(cfg) {
    const o = Object.assign({}, cfg);
    delete o.type; delete o.profile;
    return o;
  }

  _przyciski() {
    this.shadowRoot.querySelector('[data-a="zapisz"]').disabled = !this._brudny;
    this.shadowRoot.querySelector('[data-a="cofnij"]').disabled = !this._brudny;
  }

  async _zapisz() {
    const cfg = JSON.parse(JSON.stringify(this._bez(this._robocza)));
    try {
      await this._hass.callWS({ type: WS + 'set', profile: this._nazwa, config: cfg });
    } catch (err) {
      this._stan('Not saved: ' + (err.message || err.code || err), true);
      return;
    }
    this._zapisany = cfg;
    this._brudny = false;
    this._obcy = null;
    this._komunikat('');
    this._przyciski();
    this._stan('Saved ' + new Date().toLocaleTimeString() + ' for every card on this profile.');
    this._lista();
  }

  _cofnij() {
    const cfg = this._obcy || this._zapisany || {};
    this._zapisany = cfg;
    this._obcy = null;
    this._brudny = false;
    this._komunikat('');
    this._pokaz(cfg);
    this._przyciski();
    this._stan('Changes discarded.');
  }

  _pytajNazwe(tekst, domyslna) {
    const n = (prompt(tekst + ' (letters, digits, - and _)', domyslna || '') || '').trim();
    if (!n) return null;
    if (!NAME_OK.test(n)) { alert('"' + n + '" is not a valid name.'); return null; }
    if (this._profile[n]) { alert('A profile "' + n + '" already exists.'); return null; }
    return n;
  }

  async _utworz(nazwa, cfg) {
    await this._hass.callWS({ type: WS + 'set', profile: nazwa, config: cfg });
    this._brudny = false;
    await this._lista();
    await this._wybierz(nazwa);
  }

  async _nowy() {
    const n = this._pytajNazwe('Name of the new profile');
    if (!n) return;
    // starts from what the card adds to a dashboard by itself
    const stub = (customElements.get('sun-cycle-bg-card').getStubConfig || (() => ({})))();
    await this._utworz(n, stub);
  }

  async _kopia() {
    const n = this._pytajNazwe('Name of the copy of "' + this._nazwa + '"', this._nazwa + '-copy');
    if (n) await this._utworz(n, this._bez(this._robocza));
  }

  async _zmien() {
    const stara = this._nazwa;
    const n = this._pytajNazwe('New name for "' + stara + '". Cards with profile: ' + stara +
      ' keep the old name and fall back to their own config until you change them.', stara);
    if (!n) return;
    await this._hass.callWS({ type: WS + 'set', profile: n, config: this._bez(this._robocza) });
    await this._hass.callWS({ type: WS + 'delete', profile: stara });
    this._brudny = false;
    this._nazwa = null;
    await this._lista();
    await this._wybierz(n);
    this._uzycie();
  }

  async _usun() {
    const n = this._nazwa;
    if (!confirm('Delete the profile "' + n + '"? Cards with profile: ' + n +
      ' fall back to their own config.')) return;
    await this._hass.callWS({ type: WS + 'delete', profile: n });
    this._odsubskrybuj();
    this._nazwa = null;
    this._brudny = false;
    this.shadowRoot.querySelector('.formularz').textContent = '';
    this.shadowRoot.querySelector('.kadr').textContent = '';
    this._stan('Deleted "' + n + '".');
    await this._lista();
    const pierwszy = Object.keys(this._profile)[0];
    if (pierwszy) this._wybierz(pierwszy);
    this._uzycie();
  }

  // which dashboards carry which profile: storage dashboards only, YAML ones are not readable here
  async _uzycie() {
    const box = this.shadowRoot.querySelector('.uzycie');
    try {
      const tablice = await this._hass.callWS({ type: 'lovelace/dashboards/list' });
      const licz = {};
      const sciezki = [null, ...tablice.filter((t) => t.mode === 'storage').map((t) => t.url_path)];
      for (const url of sciezki) {
        let cfg;
        try { cfg = await this._hass.callWS({ type: 'lovelace/config', url_path: url }); } catch (e) { continue; }
        const szukaj = (o) => {
          if (Array.isArray(o)) { o.forEach(szukaj); return; }
          if (!o || typeof o !== 'object') return;
          if (o.type === CARD && typeof o.profile === 'string') {
            const k = licz[o.profile] = licz[o.profile] || {};
            k[url || 'lovelace'] = (k[url || 'lovelace'] || 0) + 1;
            return;
          }
          Object.values(o).forEach(szukaj);
        };
        szukaj(cfg);
      }
      box.innerHTML = '<h2 style="margin-top:16px">Used by</h2>';
      const ul = document.createElement('ul');
      for (const [p, gdzie] of Object.entries(licz)) {
        const li = document.createElement('li');
        li.textContent = p + ': ' + Object.entries(gdzie).map(([d, n]) => d + ' (' + n + ')').join(', ') +
          (this._profile[p] ? '' : ', no such profile');
        ul.appendChild(li);
      }
      if (!ul.children.length) box.insertAdjacentHTML('beforeend', '<p class="muted">No card names a profile.</p>');
      else box.appendChild(ul);
    } catch (e) {
      box.textContent = '';
    }
  }
}

customElements.define('sun-cycle-bg-panel', SunCycleBgPanel);
