#!/usr/bin/env python3
"""food-picture-01 V3 — "The Emperor's Pull".

A tonkotsu ramen rendered procedurally with PIL: chopsticks lift a tall,
glossy noodle pull out of a dark ceramic bowl while a molten ajitama yolk
drips, torched chashu fans across the broth, chili oil spirals, and steam
rises. Drawn at 2x and downsampled for smooth anti-aliasing. Fully
deterministic: fixed seed, no network, no clock, no environment input
other than MAKEFUN_OUTPUT_DIR.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

S = 2                      # supersample factor
W = 1024 * S
H = 1024 * S
RNG = random.Random(20261114)

# ---------------------------------------------------------------- palette
INK       = (16, 11, 8)        # near-black warm background
TABLE     = (38, 26, 17)
GLOW      = (122, 66, 28)      # warm halo behind the bowl
BOWL      = (24, 22, 26)       # black ceramic
BOWL_LIT  = (74, 66, 70)
BROTH_A   = (226, 190, 132)    # creamy tonkotsu, lit side
BROTH_B   = (176, 128, 74)     # broth, shadow side
CHILI     = (178, 52, 18)
CHILI_LIT = (232, 104, 36)
NOODLE_A  = (246, 222, 168)    # noodle highlight
NOODLE_B  = (214, 172, 104)    # noodle body
NOODLE_C  = (164, 118, 62)     # noodle shadow
YOLK_A    = (255, 196, 66)
YOLK_B    = (214, 128, 24)
EGG_WHITE = (250, 244, 232)
CHASHU_A  = (230, 172, 142)    # seared pork, lit
CHASHU_B  = (180, 108, 82)
CHAR      = (52, 26, 18)       # torch char
SCALLION  = (86, 150, 62)
SCALLION_D= (46, 96, 34)
WOOD      = (150, 104, 62)
WOOD_D    = (104, 68, 38)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


def vertical_gradient(size, top, bottom):
    """RGB image, top colour fading to bottom colour."""
    w, h = size
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        px[0, y] = lerp(top, bottom, y / max(1, h - 1))
    return img.resize((w, h))


def radial_glow(size, centre, radius, colour, peak=150):
    """RGBA glow disc fading to transparent."""
    glow = Image.new("L", size, 0)
    d = ImageDraw.Draw(glow)
    steps = 24
    for i in range(steps, 0, -1):
        t = i / steps
        r = radius * t
        d.ellipse([centre[0] - r, centre[1] - r, centre[0] + r, centre[1] + r],
                  fill=int(peak * (1 - t) ** 1.6))
    glow = glow.filter(ImageFilter.GaussianBlur(radius * 0.12))
    solid = Image.new("RGBA", size, colour + (255,))
    solid.putalpha(glow)
    return solid


def soft_ellipse(draw, box, fill):
    draw.ellipse(box, fill=fill)


def wavy_points(x0, y0, x1, y1, amp, freq, phase, n=90):
    """Points of a gently waving line from (x0,y0) to (x1,y1)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t + amp * math.sin(2 * math.pi * freq * t + phase) * (1 - 0.35 * t)
        y = y0 + (y1 - y0) * t
        pts.append((x, y))
    return pts


def draw_strand(layer, pts, width, colour, highlight=None):
    """One noodle strand: soft body + optional glossy core line."""
    d = ImageDraw.Draw(layer)
    d.line(pts, fill=colour + (255,), width=width, joint="curve")
    if highlight:
        off = [(x - width * 0.22, y) for x, y in pts]
        d.line(off, fill=highlight + (235,), width=max(2, width // 3), joint="curve")


# ------------------------------------------------------------------ scene
def build():
    img = vertical_gradient((W, H), (26, 18, 12), INK)
    base = img.convert("RGBA")

    # warm halo behind the bowl + faint table grain at the bottom
    base.alpha_composite(radial_glow((W, H), (W // 2, H * 0.62), W * 0.46, GLOW, 120))
    grain = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grain)
    for i in range(26):
        y = int(H * 0.78 + i * H * 0.009)
        gd.line([(0, y), (W, y + RNG.randint(-6, 6))],
                fill=(90, 60, 36, RNG.randint(8, 22)), width=2)
    base.alpha_composite(grain)

    # soft contact shadow under the bowl
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([W * 0.16, H * 0.86, W * 0.84, H * 0.955], fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    base.alpha_composite(shadow)

    draw_bowl(base)
    draw_broth(base)
    draw_toppings(base)
    draw_noodle_pull(base)
    draw_chopsticks(base)
    draw_steam(base)
    draw_garnish(base)

    # warm grade + vignette
    out = base.convert("RGB")
    out = grade(out)
    return out


def grade(img):
    """Slight warm lift and a dark vignette so the bowl pops."""
    w, h = img.size
    vig = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-w * 0.28, -h * 0.28, w * 1.28, h * 1.28], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(180))
    black = Image.new("RGB", (w, h), (8, 5, 3))
    img = Image.composite(img, black, vig)
    # warm lift: raise reds a touch, keep blues down
    r, g, b = img.split()
    r = r.point(lambda v: clamp(v * 1.04 + 4))
    b = b.point(lambda v: clamp(v * 0.96))
    return Image.merge("RGB", (r, g, b))


# ------------------------------------------------------------------- bowl
def draw_bowl(img):
    cx, cy = W // 2, int(H * 0.665)
    rx, ry = int(W * 0.335), int(H * 0.115)
    d = ImageDraw.Draw(img, "RGBA")
    # visible belly: the bowl is a deep vessel, not a flat plate
    belly = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(belly)
    bd.ellipse([cx - rx * 0.90, cy - ry * 0.10, cx + rx * 0.90, cy + ry * 1.05],
               fill=(30, 28, 30, 255))
    bd.ellipse([cx - rx * 0.42, cy + ry * 0.72, cx + rx * 0.42, cy + ry * 1.05],
               fill=(48, 44, 48, 255))
    belly = belly.filter(ImageFilter.GaussianBlur(4))
    img.alpha_composite(belly)
    # outer ceramic rim
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=BOWL + (255,))
    # lower body shading: darker belly
    belly2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd2 = ImageDraw.Draw(belly2)
    bd2.ellipse([cx - rx, cy - ry * 0.35, cx + rx, cy + ry], fill=(0, 0, 0, 90))
    belly2 = belly2.filter(ImageFilter.GaussianBlur(18))
    img.alpha_composite(belly2)
    # rim: lit arc on the upper-left, shadow on the lower-right
    d.arc([cx - rx, cy - ry, cx + rx, cy + ry], start=200, end=340,
          fill=BOWL_LIT + (255,), width=int(10 * S))
    d.arc([cx - rx, cy - ry, cx + rx, cy + ry], start=20, end=160,
          fill=(8, 7, 9, 255), width=int(12 * S))
    # inner wall ring
    d.ellipse([cx - rx * 0.93, cy - ry * 0.86, cx + rx * 0.93, cy + ry * 0.86],
              outline=(10, 9, 11, 255), width=int(6 * S))


def draw_broth(img):
    cx, cy = W // 2, int(H * 0.665)
    rx, ry = int(W * 0.30), int(H * 0.095)
    # creamy broth with a lit upper-left
    broth = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(broth)
    bd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=BROTH_A + (255,))
    bd.ellipse([cx - rx * 0.55, cy - ry * 0.45, cx + rx, cy + ry],
               fill=BROTH_B + (255,))
    broth = broth.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(broth)
    d = ImageDraw.Draw(img, "RGBA")
    # chili-oil spiral: two sweeping arcs + droplets
    for start, width, col in ((200, 26, CHILI), (30, 18, CHILI_LIT),
                              (300, 10, CHILI_LIT)):
        d.arc([cx - rx * 0.72, cy - ry * 0.66, cx + rx * 0.72, cy + ry * 0.66],
              start=start, end=start + 210, fill=col + (215,), width=width)
    for _ in range(9):
        a = RNG.uniform(0, 2 * math.pi)
        rr = RNG.uniform(0.15, 0.8)
        x = cx + math.cos(a) * rx * rr
        y = cy + math.sin(a) * ry * rr
        r = RNG.randint(4, 11) * S // 2
        d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6],
                  fill=CHILI + (200,))
    # glossy sheen streaks on the broth
    sheen = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shd = ImageDraw.Draw(sheen)
    shd.ellipse([cx - rx * 0.62, cy - ry * 0.78, cx - rx * 0.05, cy - ry * 0.18],
                fill=(255, 240, 210, 60))
    sheen = sheen.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(sheen)


# --------------------------------------------------------------- toppings
def draw_chashu(img, cx, cy, w, h, angle, flip=False):
    """One torched chashu slice: pink-brown disc, charred rim, gloss."""
    layer = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    box = [w // 2, h // 2, w * 3 // 2, h * 3 // 2]
    ld.ellipse(box, fill=CHASHU_A + (255,))
    # seared outer ring: dark caramelised edge, not a flat disc
    ld.ellipse(box, outline=CHAR + (255,), width=max(3, w // 20))
    # pale fat ring between edge and centre
    ld.ellipse([box[0] + w // 10, box[1] + h // 10, box[2] - w // 10, box[3] - h // 10],
               outline=(242, 220, 196, 255), width=max(3, w // 24))
    ld.ellipse([box[0] + w // 6, box[1] + h // 6, box[2] - w // 6, box[3] - h // 6],
               fill=CHASHU_B + (255,))
    # fat marbling: pale arcs
    for a0 in (15, 120, 235):
        ld.arc([box[0] + w // 8, box[1] + h // 8, box[2] - w // 8, box[3] - h // 8],
               start=a0, end=a0 + 70, fill=(240, 214, 186, 220), width=w // 22)
    # torch char: dark streaks along the rim, not dots
    for _ in range(5):
        a = RNG.uniform(0, 2 * math.pi)
        x = w + math.cos(a) * w * 0.40
        y = h + math.sin(a) * h * 0.40
        ld.arc([x - w // 6, y - h // 6, x + w // 6, y + h // 6],
               start=RNG.uniform(0, 180), end=RNG.uniform(180, 360),
               fill=CHAR + (210,), width=w // 18)
    # gloss streak
    ld.ellipse([box[0] + w // 5, box[1] + h // 8, box[0] + w // 2, box[1] + h // 3],
               fill=(255, 235, 205, 70))
    layer = layer.filter(ImageFilter.GaussianBlur(2))
    layer = layer.rotate(angle, resample=Image.BICUBIC, expand=False)
    if flip:
        layer = layer.transpose(Image.FLIP_LEFT_RIGHT)
    img.alpha_composite(layer, (cx - w, cy - h))


def draw_ajitama(img, cx, cy, r, drip=False):
    """Halved seasoned egg: white shell, molten golden yolk, optional drip."""
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([cx - r, cy - r * 0.82, cx + r, cy + r * 0.82],
              fill=EGG_WHITE + (255,))
    d.ellipse([cx - r * 0.62, cy - r * 0.55, cx + r * 0.62, cy + r * 0.55],
              fill=YOLK_A + (255,))
    d.ellipse([cx - r * 0.38, cy - r * 0.34, cx + r * 0.30, cy + r * 0.30],
              fill=YOLK_B + (255,))
    d.ellipse([cx - r * 0.30, cy - r * 0.42, cx + r * 0.05, cy - r * 0.12],
              fill=(255, 226, 140, 255))
    if drip:
        # golden yolk stream falling from the yolk into the broth
        x0 = cx + r * 0.18
        y0 = cy + r * 0.45
        pts = wavy_points(x0, y0, x0 + r * 0.22, y0 + r * 0.95,
                          amp=r * 0.10, freq=1.5, phase=0.6, n=40)
        d.line(pts, fill=YOLK_A + (255,), width=int(r * 0.24), joint="curve")
        d.line(pts, fill=YOLK_B + (255,), width=int(r * 0.10), joint="curve")
        bx, by = pts[-1]
        d.ellipse([bx - r * 0.20, by - r * 0.12, bx + r * 0.20, by + r * 0.20],
                  fill=YOLK_A + (255,))


def draw_toppings(img):
    cx, cy = W // 2, int(H * 0.665)
    # nori sheet standing at the back of the bowl, tilted, with a sheen
    nori = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    nd = ImageDraw.Draw(nori)
    nd.rounded_rectangle([cx + int(W * 0.17), int(H * 0.47),
                          cx + int(W * 0.235), int(H * 0.655)],
                         radius=12, fill=(20, 30, 16, 255))
    nd.line([(cx + int(W * 0.182), int(H * 0.485)),
             (cx + int(W * 0.182), int(H * 0.64))],
            fill=(74, 104, 60, 255), width=4)
    nd.line([(cx + int(W * 0.222), int(H * 0.49)),
             (cx + int(W * 0.222), int(H * 0.60))],
            fill=(52, 78, 44, 200), width=3)
    nori = nori.filter(ImageFilter.GaussianBlur(2))
    nori = nori.rotate(-7, resample=Image.BICUBIC,
                       center=(cx + int(W * 0.20), int(H * 0.56)))
    img.alpha_composite(nori)
    # torched chashu fan on the right side of the broth
    draw_chashu(img, cx + int(W * 0.155), cy + int(H * 0.012),
                int(W * 0.105), int(H * 0.052), -18)
    draw_chashu(img, cx + int(W * 0.21), cy + int(H * 0.030),
                int(W * 0.098), int(H * 0.049), 12, flip=True)
    draw_chashu(img, cx + int(W * 0.10), cy + int(H * 0.048),
                int(W * 0.092), int(H * 0.046), 28)
    # ajitama halves on the left, one dripping molten yolk
    draw_ajitama(img, cx - int(W * 0.185), cy - int(H * 0.012),
                 int(W * 0.052), drip=True)
    draw_ajitama(img, cx - int(W * 0.105), cy + int(H * 0.038),
                 int(W * 0.046))
    # narutomaki: white disc, pink spiral
    nx, ny = cx + int(W * 0.02), cy - int(H * 0.045)
    d = ImageDraw.Draw(img, "RGBA")
    nr = int(W * 0.028)
    d.ellipse([nx - nr, ny - nr * 0.8, nx + nr, ny + nr * 0.8],
              fill=(248, 246, 240, 255), outline=(214, 150, 160, 255), width=3)
    for i in range(3):
        t = i / 3
        rr = nr * (0.75 - 0.2 * t)
        d.arc([nx - rr, ny - rr * 0.8, nx + rr, ny + rr * 0.8],
              start=200 + i * 130, end=200 + i * 130 + 150,
              fill=(226, 110, 128, 255), width=5)
    # menma bamboo shoots near the chashu
    for i, (mx, my, ang) in enumerate((
            (cx + int(W * 0.065), cy - int(H * 0.052), -24),
            (cx + int(W * 0.095), cy - int(H * 0.058), -8),
            (cx + int(W * 0.125), cy - int(H * 0.050), 10))):
        shoot = Image.new("RGBA", (int(W * 0.05), int(H * 0.03)), (0, 0, 0, 0))
        sd2 = ImageDraw.Draw(shoot)
        sd2.rounded_rectangle([2, 2, int(W * 0.05) - 2, int(H * 0.03) - 2],
                              radius=8, fill=(206, 158, 92, 255))
        sd2.line([(6, 8), (int(W * 0.05) - 6, 8)], fill=(168, 118, 62, 255), width=3)
        shoot = shoot.rotate(ang, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(shoot, (mx - shoot.width // 2, my - shoot.height // 2))


# ------------------------------------------------------------ noodle pull
def draw_noodle_pull(img):
    cx = W // 2
    top_y = int(H * 0.175)          # grip point, high in the frame
    base_y = int(H * 0.66)          # broth surface
    grip_x = cx + int(W * 0.045)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # dense core: a wavy, tapering bundle body so the pull reads as one
    # thick glossy mass, not a fan of dry straw
    core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(core)
    left = wavy_points(cx - int(W * 0.055), base_y, grip_x - int(W * 0.012),
                       top_y, amp=16 * S, freq=1.4, phase=0.4)
    right = wavy_points(cx + int(W * 0.065), base_y, grip_x + int(W * 0.014),
                        top_y, amp=16 * S, freq=1.4, phase=2.2)
    cd.polygon(left + right[::-1], fill=NOODLE_B + (255,))
    core = core.filter(ImageFilter.GaussianBlur(6))
    layer.alpha_composite(core)
    # the lifted bundle: thick wavy strands fanning from the bowl to the grip
    for i in range(26):
        spread = RNG.uniform(-1, 1)
        x0 = cx + int(spread * W * 0.11)
        x1 = grip_x + int(spread * W * 0.010)
        amp = RNG.uniform(14, 34) * S
        freq = RNG.uniform(0.8, 1.9)
        phase = RNG.uniform(0, 6.28)
        pts = wavy_points(x0, base_y, x1, top_y, amp, freq, phase)
        shade = RNG.random()
        col = NOODLE_A if shade > 0.62 else (NOODLE_B if shade > 0.25 else NOODLE_C)
        draw_strand(layer, pts, RNG.randint(11, 18) * S // 2,
                    col, highlight=NOODLE_A if col != NOODLE_A else None)
    # a few loose strands cascade back down into the bowl
    for i in range(6):
        x0 = cx + int(RNG.uniform(-0.13, 0.13) * W)
        x1 = cx + int(RNG.uniform(-0.20, 0.02) * W)
        pts = wavy_points(x0, base_y - int(H * 0.02), x1,
                          base_y + int(H * 0.055), RNG.uniform(10, 26) * S,
                          RNG.uniform(1.0, 2.0), RNG.uniform(0, 6.28))
        draw_strand(layer, pts, RNG.randint(9, 13) * S // 2, NOODLE_B,
                    highlight=NOODLE_A)
    # broth coating: the lower third of the pull is wet and golden
    coat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cod = ImageDraw.Draw(coat)
    cod.polygon([(grip_x - int(W * 0.05), int(H * 0.44)),
                 (grip_x + int(W * 0.05), int(H * 0.44)),
                 (cx + int(W * 0.12), base_y),
                 (cx - int(W * 0.12), base_y)],
                fill=(196, 128, 52, 70))
    coat = coat.filter(ImageFilter.GaussianBlur(24))
    layer.alpha_composite(coat)
    # gloss: a soft warm sheen over the whole bundle
    sheen = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shd = ImageDraw.Draw(sheen)
    shd.polygon([(grip_x - int(W * 0.02), top_y),
                 (grip_x + int(W * 0.02), top_y),
                 (cx + int(W * 0.10), base_y),
                 (cx - int(W * 0.10), base_y)],
                fill=(255, 236, 190, 46))
    sheen = sheen.filter(ImageFilter.GaussianBlur(30))
    layer.alpha_composite(sheen)
    layer = layer.filter(ImageFilter.GaussianBlur(1.2))
    img.alpha_composite(layer)


def draw_chopsticks(img):
    grip_x = W // 2 + int(W * 0.045)
    grip_y = int(H * 0.175)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # two sticks, entering from the top-right, tips pinching the noodle bundle
    for off, tip in ((0, (grip_x - 8, grip_y - 6)),
                     (int(16 * S), (grip_x + 14, grip_y + 10))):
        x0 = int(W * 0.97)
        y0 = int(H * 0.02) + off
        x1, y1 = tip
        # tapered stick: draw as a thick line, wider at the top end
        d.line([(x0, y0), (x1, y1)], fill=WOOD + (255,), width=int(13 * S))
        d.line([(x0, y0), (x1, y1)], fill=WOOD_D + (255,), width=int(4 * S))
        # grain lines
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        d.line([(mx - 40, my - 14), (mx + 40, my + 6)],
               fill=(120, 82, 46, 255), width=2)
    layer = layer.filter(ImageFilter.GaussianBlur(1))
    img.alpha_composite(layer)


# ------------------------------------------------------------------ steam
def draw_steam(img):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = W // 2
    for i, (sx, height, alpha) in enumerate((
            (-0.16, 0.30, 70), (-0.05, 0.38, 90), (0.07, 0.34, 80),
            (0.17, 0.26, 60))):
        x0 = cx + int(sx * W)
        y0 = int(H * 0.60)
        y1 = int(H * (0.60 - height))
        pts = wavy_points(x0, y0, x0 + int(RNG.uniform(-30, 30)), y1,
                          amp=26 * S, freq=1.6, phase=i * 1.7, n=60)
        d.line(pts, fill=(255, 250, 240, alpha), width=int(16 * S), joint="curve")
    layer = layer.filter(ImageFilter.GaussianBlur(18))
    img.alpha_composite(layer)


# --------------------------------------------------------------- garnish
def draw_garnish(img):
    cx, cy = W // 2, int(H * 0.665)
    rx, ry = int(W * 0.30), int(H * 0.095)
    d = ImageDraw.Draw(img, "RGBA")
    # scallion rings scattered on the broth
    for _ in range(26):
        a = RNG.uniform(0, 2 * math.pi)
        rr = RNG.uniform(0.1, 0.88)
        x = cx + math.cos(a) * rx * rr
        y = cy + math.sin(a) * ry * rr
        r = RNG.randint(5, 10) * S // 2
        col = SCALLION if RNG.random() > 0.4 else SCALLION_D
        d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7],
                  outline=col + (255,), width=3)
        d.ellipse([x - r * 0.4, y - r * 0.28, x + r * 0.4, y + r * 0.28],
                  fill=col + (255,))
    # sesame seeds
    for _ in range(40):
        a = RNG.uniform(0, 2 * math.pi)
        rr = RNG.uniform(0.1, 0.9)
        x = cx + math.cos(a) * rx * rr
        y = cy + math.sin(a) * ry * rr
        r = RNG.randint(2, 4) * S // 2
        d.ellipse([x - r, y - r // 2, x + r, y + r // 2],
                  fill=(240, 224, 190, 230))
    # chili flakes
    for _ in range(14):
        a = RNG.uniform(0, 2 * math.pi)
        rr = RNG.uniform(0.2, 0.85)
        x = cx + math.cos(a) * rx * rr
        y = cy + math.sin(a) * ry * rr
        d.ellipse([x - 4, y - 2, x + 4, y + 2], fill=(150, 30, 10, 230))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    img = build()
    img = img.resize((1024, 1024), Image.LANCZOS)
    img.save(os.path.join(out_dir, "entry.png"), format="JPEG",
             quality=88, optimize=True)


if __name__ == "__main__":
    main()
