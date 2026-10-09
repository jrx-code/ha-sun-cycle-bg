/* Loads the sun-cycle-bg card from the sun_cycle_bg integration.

   The integration registers this file with frontend.add_extra_js_url, and the
   frontend imports it on every page (dashboards, the settings panel) with
   import(), not a <script> tag, so the card cannot find out where it was
   loaded from. This loader tells it: the card's pictures (sun, moon, Milky
   Way, planets, leaves) sit next to it. The ?v= of this URL, the integration's
   version, is passed on so an update fetches the new card. */
const here = new URL(import.meta.url);
window.SUN_CYCLE_BG_BASE = new URL('./', here).pathname;
import(new URL('./sun-cycle-bg.js' + here.search, here).href).catch((err) => {
  console.error('sun-cycle-bg: the card did not load', err);
});
