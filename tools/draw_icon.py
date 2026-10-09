"""Sun Cycle Background brand icon: a round sky from night to dusk, the sun
on the horizon with its day arc, a few stars. Drawn at 2048 px, saved at 512
and 256 px with alpha."""
import math, sys
from PIL import Image, ImageDraw, ImageFilter
out = sys.argv[1]
N = 2048; c = N / 2; R = N * 0.47
img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
# sky: vertical gradient, deep night at the top to dusk orange at the horizon
sky = Image.new("RGBA", (N, N))
top, mid, bot = (16, 24, 66), (74, 63, 140), (247, 150, 82)
hor = 0.64 * N
for y in range(N):
    t = y / hor
    if t < 0.62: a, b, u = top, mid, t / 0.62
    else: a, b, u = mid, bot, min(1, (t - 0.62) / 0.38)
    col = tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3)) + (255,)
    ImageDraw.Draw(sky).line([(0, y), (N, y)], fill=col)
# ground below the horizon
gd = ImageDraw.Draw(sky)
gd.rectangle([0, hor, N, N], fill=(28, 34, 58, 255))
# stars
for (x, y, r) in [(0.30, 0.20, 16), (0.47, 0.13, 11), (0.66, 0.19, 18), (0.40, 0.31, 9), (0.22, 0.36, 9)]:
    gd.ellipse([x * N - r, y * N - r, x * N + r, y * N + r], fill=(255, 248, 230, 255))
# the sun's day arc, dashed
arc_r = 0.30 * N
for k in range(0, 172, 12):
    gd.arc([c - arc_r, hor - arc_r, c + arc_r, hor + arc_r], 180 + k, 180 + k + 7, fill=(255, 226, 170, 235), width=26)
# glow + sun half above the horizon, right of centre (setting)
sx, sr = c + arc_r, 0.115 * N      # setting at the end of its arc
glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
ImageDraw.Draw(glow).ellipse([sx - sr * 1.9, hor - sr * 1.9, sx + sr * 1.9, hor + sr * 1.9], fill=(255, 185, 90, 140))
glow = glow.filter(ImageFilter.GaussianBlur(70))
glow = glow.crop((0, 0, N, int(hor)))     # the glow belongs to the sky, not the ground
sky.alpha_composite(glow, (0, 0))
sun = Image.new("RGBA", (N, N), (0, 0, 0, 0))
sd = ImageDraw.Draw(sun)
sd.ellipse([sx - sr, hor - sr, sx + sr, hor + sr], fill=(255, 214, 102, 255))
sun = sun.crop((0, 0, N, int(hor)))
sky.alpha_composite(sun, (0, 0))
# horizon line
ImageDraw.Draw(sky).line([(0, hor), (N, hor)], fill=(255, 200, 140, 255), width=16)
# round badge
mask = Image.new("L", (N, N), 0)
ImageDraw.Draw(mask).ellipse([c - R, c - R, c + R, c + R], fill=255)
img.paste(sky, (0, 0), mask)
for size, name in ((512, "icon@2x.png"), (256, "icon.png")):
    img.resize((size, size), Image.LANCZOS).save(f"{out}/{name}", optimize=True)
print("ok")
