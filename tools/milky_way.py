#!/usr/bin/env python3
"""Where the Milky Way stands over a given place, and how bright it is there.

The band is a great circle on the sky — galactic latitude b = 0 — so its place
in the frame is pure geometry: galactic (l, b) -> equatorial (RA, Dec) ->
horizontal (altitude, azimuth) for a latitude, longitude and instant. Nothing
about it is drawn by hand or fetched from anywhere.

What *is* modelled rather than measured is the light: surface brightness along
the band, its thickness, and the Great Rift — the dust lane that splits it from
Cygnus down to Sagittarius. Those come from a small analytic model with the
numbers written next to them, so the picture is honest about being a model of
the Milky Way and not a photograph of it.

    python3 tools/milky_way.py --lat 53.5182 --lon 14.4570 --when 2026-08-30T23:30
"""
import argparse
import datetime
import math

D2R = math.pi / 180.0
R2D = 180.0 / math.pi

# North galactic pole and the galactic longitude of the north celestial pole,
# J2000 (IAU 1958 definition, as used by every catalogue).
NGP_RA, NGP_DEC, L_NCP = 192.85948, 27.12825, 122.93192


def gal_to_eq(l, b):
    """Galactic (l, b) -> equatorial (RA, Dec), degrees, J2000."""
    l, b = l * D2R, b * D2R
    ra_p, dec_p, l_ncp = NGP_RA * D2R, NGP_DEC * D2R, L_NCP * D2R
    sin_dec = (math.sin(dec_p) * math.sin(b) +
               math.cos(dec_p) * math.cos(b) * math.cos(l_ncp - l))
    dec = math.asin(max(-1.0, min(1.0, sin_dec)))
    y = math.cos(b) * math.sin(l_ncp - l)
    x = (math.cos(dec_p) * math.sin(b) -
         math.sin(dec_p) * math.cos(b) * math.cos(l_ncp - l))
    ra = math.atan2(y, x) + ra_p
    return (ra * R2D) % 360.0, dec * R2D


def julian(dt):
    """Julian day from an aware datetime."""
    t = dt.astimezone(datetime.timezone.utc)
    y, m = t.year, t.month
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    b = 2 - a + a // 4
    day = (t.day + (t.hour + t.minute / 60 + t.second / 3600) / 24)
    return (math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1))
            + day + b - 1524.5)


def gmst(jd):
    """Greenwich mean sidereal time in degrees."""
    d = jd - 2451545.0
    return (280.46061837 + 360.98564736629 * d) % 360.0


def eq_to_altaz(ra, dec, jd, lat, lon):
    """Equatorial -> altitude/azimuth in degrees; azimuth from north, eastwards."""
    h = (gmst(jd) + lon - ra) * D2R          # hour angle
    dec, lat = dec * D2R, lat * D2R
    sin_alt = (math.sin(dec) * math.sin(lat) +
               math.cos(dec) * math.cos(lat) * math.cos(h))
    alt = math.asin(max(-1.0, min(1.0, sin_alt)))
    # same formula as altaz() in sun-cycle-bg.js, which places the moon: the
    # two must agree or the band and the moon would sit in different skies
    az = math.atan2(-math.sin(h) * math.cos(dec),
                    math.cos(lat) * math.sin(dec) - math.sin(lat) * math.cos(dec) * math.cos(h))
    return alt * R2D, (az * R2D) % 360.0


def brightness(l, b):
    """A crude surface-brightness model of the band, 0..1.

    Three things decide how the Milky Way actually looks to the eye:

      - it is far brighter towards the galactic centre (l = 0, Sagittarius)
        than towards the anticentre (l = 180, Auriga) — roughly a factor of
        four in surface brightness,
      - it is thin: most of the light is inside |b| < 10 deg, and the bulge
        around the centre is the one part that is genuinely wide,
      - the Great Rift, a dust lane, cuts a dark channel along the band from
        Cygnus (l ~ 80) down past Aquila to the centre — without it the band
        reads as a plain smear and stops looking like the sky.
    """
    lr = math.radians(((l + 180) % 360) - 180)          # -pi..pi, 0 = centre
    # thickness: a wide bulge at the centre, thin arms away from it
    sigma = 4.5 + 6.5 * math.exp(-(lr / 0.55) ** 2)
    core = math.exp(-0.5 * (b / sigma) ** 2)
    # along the band: bright towards the centre, a second rise in Cygnus
    along = (0.30 + 0.70 * math.exp(-(lr / 1.15) ** 2)
             + 0.28 * math.exp(-(((l - 80 + 180) % 360 - 180) / 22.0) ** 2))
    # the rift: a dark lane, offset a degree or so off the midline
    rift_l = ((l + 180) % 360) - 180
    if -10 < rift_l < 90:
        w = 2.4 + 1.2 * math.sin(rift_l / 90 * math.pi)
        depth = 0.62 * math.exp(-(((rift_l - 40) / 45.0) ** 2))
        core *= 1 - depth * math.exp(-0.5 * ((b - 1.2) / w) ** 2)
    return max(0.0, min(1.0, core * along))


def band(lat, lon, when, step_l=1.0, step_b=1.5, b_max=18.0):
    """Every patch of the band, projected for the observer.

    Returns (l, b, altitude, azimuth, brightness) for a grid over the band.
    """
    jd = julian(when)
    out = []
    l = 0.0
    while l < 360.0:
        b = -b_max
        while b <= b_max:
            i = brightness(l, b)
            if i > 0.012:
                ra, dec = gal_to_eq(l, b)
                alt, az = eq_to_altaz(ra, dec, jd, lat, lon)
                out.append((l, b, alt, az, i))
            b += step_b
        l += step_l
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=53.5182)
    ap.add_argument("--lon", type=float, default=14.4570)
    ap.add_argument("--when", default=None, help="local ISO time, default now")
    a = ap.parse_args()
    when = (datetime.datetime.fromisoformat(a.when) if a.when
            else datetime.datetime.now()).astimezone()
    pts = band(a.lat, a.lon, when)
    widoczne = [p for p in pts if p[2] > 0]
    print(f"{when.isoformat(timespec='minutes')}  lat={a.lat} lon={a.lon}")
    print(f"punktow pasa: {len(pts)}, nad horyzontem: {len(widoczne)} "
          f"({100 * len(widoczne) / len(pts):.0f} %)")
    if widoczne:
        naj = max(widoczne, key=lambda p: p[4])
        wys = max(widoczne, key=lambda p: p[2])
        print(f"najjasniejszy widoczny punkt: l={naj[0]:.0f} b={naj[1]:+.0f}  "
              f"alt={naj[2]:.1f} az={naj[3]:.1f}  jasnosc={naj[4]:.2f}")
        print(f"najwyzszy punkt pasa:         l={wys[0]:.0f} b={wys[1]:+.0f}  "
              f"alt={wys[2]:.1f} az={wys[3]:.1f}")
        # where the centre of the Galaxy itself is
        ra, dec = gal_to_eq(0, 0)
        alt, az = eq_to_altaz(ra, dec, julian(when), a.lat, a.lon)
        print(f"centrum Galaktyki (l=0):      alt={alt:+.1f} az={az:.1f}")


if __name__ == "__main__":
    main()
