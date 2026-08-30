# demo/assets/milky-way.jpg

**The Milky Way panorama** — a 360° photographic panorama of the whole sky,
equirectangular in galactic coordinates.

- Author / credit line: **ESO/S. Brunier**
- Source: <https://www.eso.org/public/images/eso0932a/> (GigaGalaxy Zoom)
- Licence: **Creative Commons Attribution 4.0 International (CC BY 4.0)**, per
  <https://www.eso.org/public/outreach/copyright/> — "images and videos on
  ESO's public website are licensed under CC BY 4.0 unless specifically noted
  otherwise". The only note on the image page concerns the 800-megapixel
  original, which ESO does not publish; the 6000 × 3000 version used here is
  published there.
- What was done to it: downscaled 6000 × 3000 → 2048 × 1024 and saved as JPEG
  by `tools/prepare_milkyway_texture.py`, which also writes the credit into the
  file's own comment field. Nothing was retouched.

This file is **not** under the repository's MIT licence. Keep the credit line
with it, in the page and anywhere it is redisplayed.

---

# demo/assets/milky-way-cutout.png / .webp

A framed photograph of the galactic centre region, supplied by the repository
owner (`~/Pobrane/milky-way.jpg`, 1168 x 784), with its sky made transparent by
`tools/cutout_milkyway.py`: alpha comes from brightness, so empty sky vanishes
and the star clouds stay, and the frame edges are feathered because the sky has
no frame.

Where it sits on the sky was **measured, not guessed** — registered against the
ESO panorama above by correlation over centre, rotation and field of view:
l = -5 deg, b = -2 deg, rotation -24 deg, field 62 deg, r = 0.64, at which the
band angle, the core and the Great Rift line up with the panorama.

Provenance and licence of the source photograph: **not established here.** It
came from the owner's Downloads folder without a source. Do not publish or
redistribute this file until that is settled; it is in the working tree for the
tuning page only.
