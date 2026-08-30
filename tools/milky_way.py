#!/usr/bin/env python3
"""Where the Milky Way stands over a given place — the geometry only.

The band is a great circle on the sky, galactic latitude b = 0, so its place in
the frame is pure geometry: galactic (l, b) -> equatorial (RA, Dec) ->
horizontal (altitude, azimuth) for a latitude, longitude and instant.

The *light* is not modelled here and should not be. An analytic band, however
carefully the numbers are tuned, is a smooth smear; the real thing is resolved
star clouds and torn dust. That comes from a photograph — see
tools/prepare_milkyway_texture.py.

This module is the sanity check: run it and see where the band stands tonight.

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


def band(lat, lon, when, step_l=2.0, step_b=3.0, b_max=15.0):
    """The band, projected for the observer: (l, b, altitude, azimuth)."""
    jd = julian(when)
    out = []
    l = 0.0
    while l < 360.0:
        b = -b_max
        while b <= b_max:
            ra, dec = gal_to_eq(l, b)
            alt, az = eq_to_altaz(ra, dec, jd, lat, lon)
            out.append((l, b, alt, az))
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
        wys = max(widoczne, key=lambda p: p[2])
        print(f"najwyzszy punkt pasa:    l={wys[0]:.0f} b={wys[1]:+.0f}  "
              f"alt={wys[2]:.1f} az={wys[3]:.1f}")
        for nazwa, l, b in (("centrum Galaktyki", 0, 0), ("Labedz (Cygnus)", 80, 0),
                            ("antycentrum", 180, 0)):
            ra, dec = gal_to_eq(l, b)
            alt, az = eq_to_altaz(ra, dec, julian(when), a.lat, a.lon)
            print(f"{nazwa:24} alt={alt:+6.1f}  az={az:5.1f}")


if __name__ == "__main__":
    main()
