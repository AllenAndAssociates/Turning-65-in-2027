"""Render the 9:16 edit: top 55% graphics stage, bottom 45% keyed speaker.

python3 render.py                 -> out/Turning-65-in-2027_final.mp4
python3 render.py --stills 3 12   -> out/still_3.00.png ... (preview frames)
"""
import math
import os
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from timeline import *

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "Untitled video.mp4")
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

NAVY = (0, 87, 154)       # brand Deep Blue
NAVY2 = (19, 49, 92)
GOLD = (76, 175, 46)      # brand Green
GOLD_LT = (141, 194, 31)  # brand Lime Green
WHITE = (255, 255, 255)
RED = (214, 40, 57)
RED_DK = (176, 18, 34)
GREEN = (62, 165, 53)
BLUE = (0, 114, 188)      # brand Blue
INK = (48, 48, 48)        # brand Charcoal
BG = (246, 244, 239)

FD = "/usr/share/fonts/opentype/inter/"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


@lru_cache(None)
def F(name, size):
    return ImageFont.truetype(FD + name + ".otf", size)


BLACK_D = "InterDisplay-Black"
XB_D = "InterDisplay-ExtraBold"
BOLD_D = "InterDisplay-Bold"
SEMI = "Inter-SemiBold"
BOLD = "Inter-Bold"


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, t0, dur):
    return clamp((t - t0) / dur)


def out_cubic(p):
    return 1 - (1 - p) ** 3


def out_back(p, s=1.9):
    p -= 1
    return p * p * ((s + 1) * p + s) + 1


def in_cubic(p):
    return p ** 3


def pop(t, t0, dur=0.38, start=0.35):
    """(scale, alpha) for a pop-in starting at t0, or None before it."""
    if t < t0:
        return None
    p = prog(t, t0, dur)
    return start + (1 - start) * out_back(p), clamp(p * 3)


# ---------------------------------------------------------------- sprite helpers
def text_sprite(s, font, fill, stroke=0, stroke_fill=None, pad=4):
    l, t, r, b = font.getbbox(s, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), s, font=font, fill=fill,
                            stroke_width=stroke, stroke_fill=stroke_fill)
    return im


@lru_cache(None)
def emoji(ch, px):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((px, round(im.height * px / im.width)), Image.LANCZOS)


def place(dst, spr, cx, cy, s=1.0, a=1.0, rot=0.0, anchor="c"):
    """Alpha-composite sprite centred (or left-anchored) at (cx, cy), clipped to dst."""
    if spr is None or a <= 0.003 or s <= 0.01:
        return
    if rot:
        spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(s - 1) > 1e-3:
        spr = spr.resize((max(1, round(spr.width * s)), max(1, round(spr.height * s))), Image.BICUBIC)
    if a < 0.999:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * a)))
    x = round(cx - spr.width / 2) if anchor == "c" else round(cx)
    y = round(cy - spr.height / 2)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dst.width, x + spr.width), min(dst.height, y + spr.height)
    if x1 <= x0 or y1 <= y0:
        return
    dst.alpha_composite(spr.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def shadowed(w, h, r, fill, blur=18, off=10, alpha=70, outline=None, ow=0):
    m = blur * 2
    im = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((m, m + off, m + w, m + h + off), r, fill=alpha)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    im.paste((10, 20, 40, 255), (0, 0), sh)
    ImageDraw.Draw(im).rounded_rectangle((m, m, m + w, m + h), r, fill=fill, outline=outline, width=ow)
    return im, m


def check_icon(d, color_bg, color_fg):
    im = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((0, 0, d - 1, d - 1), fill=color_bg)
    w = max(3, d // 9)
    dr.line([(d * .27, d * .52), (d * .44, d * .68), (d * .74, d * .34)], fill=color_fg, width=w, joint="curve")
    return im


@lru_cache(None)
def icon_disc(ch, d):
    im = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((0, 0, d - 1, d - 1), fill=WHITE)
    place(im, emoji(ch, int(d * 0.62)), d / 2, d / 2)
    return im


LOGO_PATH = os.path.join(HERE, "..", ".claude", "skills", "allen-associates-brand", "assets", "logo_transparent.png")


@lru_cache(None)
def logo(width):
    """Official Allen & Associates logo (from the brand skill); place on white only."""
    im = Image.open(LOGO_PATH).convert("RGBA")
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def calendar_icon(d):
    im = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((0, d * .1, d - 1, d - 1), d // 8, fill=WHITE)
    dr.rounded_rectangle((0, d * .1, d - 1, d * .38), d // 8, fill=RED_DK)
    dr.rectangle((0, d * .26, d - 1, d * .38), fill=RED_DK)
    for x in (d * .28, d * .72):
        dr.rounded_rectangle((x - d * .05, 0, x + d * .05, d * .22), d // 20, fill=(90, 20, 30))
    place(im, text_sprite("7", F(BLACK_D, int(d * .45)), RED_DK), d / 2, d * .69)
    return im


def gray_out(im, amt):
    g = im.convert("LA").convert("RGBA")
    g.putalpha(im.getchannel("A"))
    return Image.blend(im, g, amt)


# ---------------------------------------------------------------- static layers
STAGE_H = SPLIT


def build_background():
    bg = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(bg)
    for x in range(0, W, 60):
        d.line((x, 0, x, STAGE_H), fill=(236, 232, 223), width=2)
    for y in range(0, STAGE_H, 60):
        d.line((0, y, W, y), fill=(236, 232, 223), width=2)
    # bottom speaker stage: soft vertical gradient + glow
    top, bot = np.array((233, 228, 218), float), np.array((206, 199, 186), float)
    k = np.linspace(0, 1, H - STAGE_H)[:, None]
    grad = (top * (1 - k) + bot * k)[:, None, :].repeat(W, 1)
    yy, xx = np.mgrid[0:H - STAGE_H, 0:W]
    glow = np.exp(-(((xx - 540) / 430) ** 2 + ((yy - 330) / 360) ** 2))[..., None]
    grad = grad * (1 - glow * .55) + np.array((250, 248, 244)) * glow * .55
    bg.paste(Image.fromarray(grad.astype(np.uint8)), (0, STAGE_H))
    d.rectangle((0, STAGE_H - 3, W, STAGE_H + 3), fill=GOLD)
    return bg.convert("RGBA")


# Banner
BANNER_H = 232


def build_banner():
    im = Image.new("RGBA", (W, BANNER_H + 30), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).rectangle((0, 0, W, BANNER_H + 4), fill=90)
    im.paste((10, 20, 40, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, BANNER_H), fill=NAVY)
    d.rectangle((0, BANNER_H - 12, W, BANNER_H), fill=GOLD)
    f = F(BLACK_D, 82)
    a = text_sprite("TURNING 65 IN ", f, WHITE)
    b = text_sprite("2027?", f, GOLD_LT)
    x = (W - a.width - b.width + 8) / 2
    place(im, a, x, 140, anchor="l")
    place(im, b, x + a.width - 8, 140, anchor="l")
    return im


# Tabs
TAB_Y0, TAB_H = 262, 92
TAB_W = 316
TAB_X = [40, 382, 724]
TAB_LABELS = ["Dec 7 Rule", "Your Timeline", "Two Paths"]


@lru_cache(None)
def tab_sprite(i, state):
    w, h = TAB_W, TAB_H
    fill, txt, num_bg, num_fg, outline = {
        "idle": (WHITE, INK, NAVY, WHITE, (200, 205, 214)),
        "active": (NAVY, WHITE, GOLD, WHITE, GOLD),
        "done": (GREEN, WHITE, WHITE, GREEN, (20, 120, 66)),
    }[state]
    im, m = shadowed(w, h, h // 2, fill, blur=8, off=5, alpha=50, outline=outline, ow=3)
    d = ImageDraw.Draw(im)
    cx, cy = m + 46, m + h / 2
    if state == "done":
        place(im, check_icon(54, WHITE, GREEN), cx, cy)
    else:
        d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=num_bg)
        place(im, text_sprite(str(i + 1), F(BLACK_D, 32), num_fg), cx, cy)
    place(im, text_sprite(TAB_LABELS[i], F(BOLD, 29), txt), m + 88, cy, anchor="l")
    if state == "active":
        d.polygon([(m + w / 2 - 16, m + h - 1), (m + w / 2 + 16, m + h - 1), (m + w / 2, m + h + 16)], fill=NAVY)
    return im


# Cards
CARD_X, CARD_Y, CARD_W, CARD_H = 40, 392, 1000, 632


def card_base(num, title):
    im, m = shadowed(CARD_W, CARD_H, 34, WHITE, blur=20, off=12, alpha=60)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((m, m, m + CARD_W, m + 14), 7, fill=GOLD)
    d.rectangle((m, m + 7, m + CARD_W, m + 14), fill=GOLD)
    d.ellipse((m + 36, m + 46, m + 118, m + 128), fill=NAVY)
    place(im, text_sprite(f"#{num}", F(BLACK_D, 36), WHITE), m + 77, m + 87)
    place(im, text_sprite(title, F(XB_D, 48), NAVY), m + 140, m + 87, anchor="l")
    d.line((m + 36, m + 150, m + CARD_W - 36, m + 150), fill=(228, 224, 214), width=3)
    return im, m


def reveal(card, m, t, t_in, t_out, tab_i, dst):
    """Expand the card down out of its tab (t_in), collapse back into it (t_out)."""
    if t < t_in or (t_out is not None and t >= t_out + 0.28):
        return
    p = out_cubic(prog(t, t_in, 0.40))
    if t_out is not None and t >= t_out:
        p = 1 - in_cubic(prog(t, t_out, 0.28))
    if p <= 0:
        return
    tx0, tx1 = TAB_X[tab_i], TAB_X[tab_i] + TAB_W
    x0 = tx0 + (CARD_X - tx0) * p
    x1 = tx1 + (CARD_X + CARD_W - tx1) * p
    y0 = TAB_Y0 + TAB_H - 6 + (CARD_Y - (TAB_Y0 + TAB_H - 6)) * p
    h = max(2, CARD_H * p)
    mask = Image.new("L", card.size, 0)
    cx0 = x0 - CARD_X + m
    cx1 = x1 - CARD_X + m
    ImageDraw.Draw(mask).rounded_rectangle((cx0, m + (y0 - CARD_Y), cx1, m + (y0 - CARD_Y) + h + 14),
                                           34, fill=255)
    c = card.copy()
    c.putalpha(Image.composite(card.getchannel("A"), mask, mask))
    a = clamp(p * 2.5)
    place(dst, c, CARD_X - m + c.width / 2, CARD_Y - m + c.height / 2, a=a)


# ---------------------------------------------------------------- scene content
def hook(layer, t):
    if t >= S2 + 0.3:
        return
    ex = prog(t, S2, 0.28)
    ex_s, ex_a = 1 - 0.25 * in_cubic(ex), 1 - ex
    pp = pop(t, 0.50, 0.5, 0.2)
    if pp:
        s, a = pp
        sh = text_sprite("2027", F(BLACK_D, 330), NAVY)
        g = text_sprite("2027", F(BLACK_D, 330), GOLD, stroke=4, stroke_fill=(40, 125, 35))
        place(layer, sh, 548, 612, s * ex_s, a * ex_a * .9)
        place(layer, g, 540, 600, s * ex_s, a * ex_a)
    pp = pop(t, T_DO_NOT, 0.4, 0.5)
    if pp:
        s, a = pp
        pw, ph = 900, 196
        pill, m = shadowed(pw, ph, 40, NAVY, blur=14, off=8, alpha=70, outline=GOLD, ow=5)
        # TV static until the click-off
        if t < T_STATIC_OFF + 0.22:
            rng = np.random.default_rng(int(t * 1000))
            n = rng.integers(0, 255, (ph, pw), dtype=np.uint8)
            n[::3] = (n[::3] * 0.5).astype(np.uint8)
            st = Image.fromarray(n).convert("RGBA")
            k = prog(t, T_STATIC_OFF, 0.22)
            if k > 0:  # CRT collapse: squeeze to a bright line, then out
                hh = max(4, int(ph * (1 - out_cubic(clamp(k * 1.6)))))
                ww = int(pw * (1 - clamp((k - .6) / .4)))
                st = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
                if ww > 2:
                    ImageDraw.Draw(st).rectangle(((pw - ww) / 2, (ph - hh) / 2, (pw + ww) / 2, (ph + hh) / 2),
                                                 fill=(235, 240, 255, 255))
                alpha = 0.9
            else:
                alpha = 0.42
            msk = Image.new("L", (pw, ph), 0)
            ImageDraw.Draw(msk).rounded_rectangle((0, 0, pw - 1, ph - 1), 40, fill=int(255 * alpha))
            stc = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            stc.paste(st, (0, 0), Image.fromarray(np.minimum(np.asarray(msk), np.asarray(st.getchannel("A")))))
            pill.alpha_composite(stc, (m, m))
        place(pill, text_sprite("Don't Let Fall TV Ads", F(XB_D, 64), WHITE, 3, NAVY), m + pw / 2, m + 62)
        place(pill, text_sprite("Confuse You", F(BLACK_D, 72), WHITE, 3, NAVY), m + pw / 2, m + 140)
        place(layer, pill, 540, 880, s * ex_s, a * ex_a)


def authority(layer, t):
    if t < S2 or t >= S3 + 0.3:
        return
    p = out_back(prog(t, S2, 0.55), 1.3)
    ex = prog(t, S3, 0.26)
    w, h = 900, 430
    card, m = shadowed(w, h, 36, WHITE, blur=20, off=12, alpha=70)
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((m, m, m + 22, m + h), 11, fill=GOLD)
    d.rectangle((m + 11, m, m + 22, m + h), fill=GOLD)
    place(card, logo(600), m + 22 + (w - 22) / 2, m + 125)
    d.line((m + 70, m + 248, m + w - 50, m + 248), fill=(228, 224, 214), width=3)
    place(card, text_sprite("Arric Allen", F(BLACK_D, 82), NAVY), m + 80, m + 330, anchor="l")
    pill = Image.new("RGBA", (300, 78), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle((0, 0, 299, 77), 39, fill=GOLD)
    place(pill, text_sprite("SINCE 1994", F(BLACK_D, 38), WHITE), 150, 39)
    pp = pop(t, S2 + 0.45, 0.4)
    if pp:
        place(card, pill, m + w - 60 - 150, m + 330, pp[0], pp[1])
    y = 700 - (1 - p) * 760
    place(layer, card, 540, y, 1 - 0.2 * in_cubic(ex), 1 - ex)


def card1(layer, t):
    if t < S3:
        return
    card, m = card_base(1, "Who Dec 7th Is Actually For")
    d = ImageDraw.Draw(card)
    ox, oy = m, m
    # red calendar badge
    bx0, by0, bx1, by1 = ox + 36, oy + 178, ox + CARD_W - 36, oy + 372
    badge = Image.new("RGBA", (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.rounded_rectangle((0, 0, badge.width - 1, badge.height - 1), 28, fill=RED)
    place(badge, calendar_icon(128), 100, badge.height / 2)
    for tt, s_, x in ((T_OCT15, "Oct 15", 200), (T_DEC7, "–  Dec 7", 450)):
        pp = pop(t, tt, 0.3, 0.4)
        if pp:
            place(badge, text_sprite(s_, F(BLACK_D, 76), WHITE), x, 78, pp[0], pp[1], anchor="l")
    place(badge, text_sprite("Annual Election Period", F(SEMI, 38), (255, 225, 228)), 202, 150, anchor="l")
    ks = prog(t, T_STAMP, 0.15)
    if ks > 0:
        badge = gray_out(badge, 0.75 * ks)
    card.alpha_composite(badge, (bx0, by0))
    # ONLY line + highlighter
    if t >= T_DEC7 + 0.35:
        a = prog(t, T_DEC7 + 0.35, 0.25)
        arrow = text_sprite("→", F(BLACK_D, 56), GOLD)
        txt = text_sprite("ONLY If Already on Medicare", F(XB_D, 52), NAVY)
        hx = ox + 120
        hp = out_cubic(prog(t, T_ONLY, 0.45))
        if hp > 0:
            hl = Image.new("RGBA", (int((txt.width + 24) * hp) + 1, 62), (255, 222, 60, 215))
            card.alpha_composite(hl, (hx - 12, oy + 432 - 31 + 4))
        place(card, arrow, ox + 70, oy + 432, a=a)
        place(card, txt, hx, oy + 432, a=a, anchor="l")
    # NOT FOR YOU stamp
    if t >= T_STAMP:
        k = prog(t, T_STAMP, 0.14)
        st = Image.new("RGBA", (560, 136), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        sd.rounded_rectangle((4, 4, 555, 131), 18, outline=RED_DK, width=10, fill=(255, 255, 255, 235))
        place(st, text_sprite("NOT FOR YOU", F(BLACK_D, 76), RED_DK), 280, 70)
        place(card, st, (bx0 + bx1) / 2 + 40, (by0 + by1) / 2, 1.9 - 0.9 * out_cubic(k), clamp(k * 2) * .97, rot=8)
    # green reassurance box
    pp = pop(t, T_GREEN, 0.4, 0.6)
    if pp:
        s, a = pp
        g, gm = shadowed(CARD_W - 72, 140, 28, GREEN, blur=8, off=5, alpha=50)
        place(g, check_icon(92, WHITE, GREEN), gm + 76, gm + 70)
        place(g, text_sprite("Turning 65 in 2027 =", F(SEMI, 38), (220, 255, 232)), gm + 145, gm + 44, anchor="l")
        place(g, text_sprite("Skip the Dec 7 Rush", F(BLACK_D, 58), WHITE), gm + 143, gm + 98, anchor="l")
        place(card, g, ox + CARD_W / 2, oy + 552 + (1 - a) * 30, s, a)
    reveal(card, m, t, S3, S5, 0, layer)


def card2(layer, t):
    if t < S5 + 0.15:
        return
    card, m = card_base(2, "Your Real Prep Window")
    d = ImageDraw.Draw(card)
    ox, oy = m, m
    ly = oy + 340
    lx0, lx1 = ox + 90, ox + 905
    n1, n2 = ox + 250, ox + 760
    lp = out_cubic(prog(t, S5 + 0.55, 1.1))
    if lp > 0:
        xe = lx0 + (lx1 - lx0) * lp
        d.rounded_rectangle((lx0, ly - 7, xe, ly + 7), 7, fill=(200, 206, 216))
        if lp > 0.97:
            d.polygon([(lx1 - 4, ly - 22), (lx1 + 26, ly), (lx1 - 4, ly + 22)], fill=(200, 206, 216))
    gp = out_cubic(prog(t, T_SIX_NINE - 0.15, 0.6))
    if gp > 0:  # gold prep window
        d.rounded_rectangle((n1, ly - 11, n1 + (n2 - n1) * gp, ly + 11), 11, fill=GOLD)
        if gp > 0.6:
            a = clamp((gp - .6) / .4)
            place(card, text_sprite("YOUR PREP WINDOW", F(BLACK_D, 30), GOLD), (n1 + n2) / 2, ly - 46, a=a)
    # node 1: 6-9 months before 65
    pp = pop(t, S5 + 0.85, 0.35)
    if pp:
        s, a = pp
        hi = gp > 0.2
        r = 30
        if hi:
            ring = prog(t, T_SIX_NINE + 0.1, 0.7)
            if ring < 1:
                rr = r + 50 * ring
                d.ellipse((n1 - rr, ly - rr, n1 + rr, ly + rr), outline=GOLD_LT + (int(255 * (1 - ring)),), width=6)
        node = Image.new("RGBA", (2 * r + 2, 2 * r + 2), (0, 0, 0, 0))
        ImageDraw.Draw(node).ellipse((1, 1, 2 * r, 2 * r), fill=GOLD if hi else NAVY, outline=WHITE, width=6)
        place(card, node, n1, ly, s, a)
        lbl = Image.new("RGBA", (360, 150), (0, 0, 0, 0))
        ImageDraw.Draw(lbl).rounded_rectangle((0, 0, 359, 149), 26, fill=GOLD if hi else NAVY)
        place(lbl, text_sprite("6–9 Months", F(BLACK_D, 52), NAVY if hi else WHITE), 180, 52)
        place(lbl, text_sprite("Before 65", F(BOLD, 38), NAVY if hi else GOLD_LT), 180, 108)
        place(card, lbl, n1, ly + 140, s * (1 + 0.08 * math.sin(math.pi * prog(t, T_SIX_NINE + .1, .3))), a)
    # node 2: 65th birthday
    pp = pop(t, S5 + 1.4, 0.35)
    if pp:
        s, a = pp
        node = Image.new("RGBA", (62, 62), (0, 0, 0, 0))
        ImageDraw.Draw(node).ellipse((1, 1, 60, 60), fill=NAVY, outline=WHITE, width=6)
        place(card, node, n2, ly, s, a)
        place(card, emoji("🎂", 104), n2, ly - 102, s, a)
        lbl = Image.new("RGBA", (330, 104), (0, 0, 0, 0))
        ImageDraw.Draw(lbl).rounded_rectangle((0, 0, 329, 103), 26, fill=(236, 240, 247))
        place(lbl, text_sprite("65th Birthday", F(BLACK_D, 48), NAVY), 165, 52)
        place(card, lbl, n2, ly + 118, s, a)
    reveal(card, m, t, S5 + 0.15, S6, 1, layer)


def card3(layer, t):
    if t < S6 + 0.15:
        return
    card, m = card_base(3, "Compare the 2 Main Paths")
    ox, oy = m, m
    bw, bh = 432, 430
    cy = oy + 172 + bh / 2

    def box(fill, fg, sub, tag, lines):
        b, bm = shadowed(bw, bh, 30, fill, blur=10, off=6, alpha=55)
        tg = Image.new("RGBA", (190, 62), (0, 0, 0, 0))
        ImageDraw.Draw(tg).rounded_rectangle((0, 0, 189, 61), 31, fill=fg)
        place(tg, text_sprite(tag, F(BLACK_D, 32), fill), 95, 31)
        place(b, tg, bm + bw / 2, bm + 62)
        y = bm + 140
        for txt, font, col in lines:
            spr = text_sprite(txt, font, col)
            place(b, spr, bm + bw / 2, y + spr.height / 2)
            y += spr.height + 14
        return b

    pa = pop(t, T_PATH_A, 0.4, 0.4)
    if pa:
        b = box(BLUE, WHITE, None, "PATH A", [
            ("Original", F(BLACK_D, 54), WHITE), ("Medicare", F(BLACK_D, 54), WHITE),
            ("+ Medigap", F(XB_D, 44), (200, 222, 255)), ("+ Part D", F(XB_D, 44), (200, 222, 255))])
        place(card, b, ox + 36 + bw / 2, cy, pa[0], pa[1])
    pb = pop(t, T_PATH_B, 0.4, 0.4)
    if pb:
        b = box(GOLD, NAVY, None, "PATH B", [
            ("Medicare", F(BLACK_D, 54), NAVY), ("Advantage", F(BLACK_D, 54), NAVY),
            ("(All-in-One)", F(XB_D, 42), (18, 70, 20))])
        place(card, b, ox + CARD_W - 36 - bw / 2, cy, pb[0], pb[1])
        vs = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        ImageDraw.Draw(vs).ellipse((0, 0, 95, 95), fill=NAVY, outline=WHITE, width=6)
        place(vs, text_sprite("VS", F(BLACK_D, 34), WHITE), 48, 48)
        place(card, vs, ox + CARD_W / 2, cy, pb[0], pb[1])
    if not pa:  # placeholder slots before the paths are named
        g = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle((0, 0, bw - 1, bh - 1), 30, outline=(214, 210, 200), width=4)
        place(card, g, ox + 36 + bw / 2, cy)
        place(card, g, ox + CARD_W - 36 - bw / 2, cy)
        place(card, text_sprite("2", F(BLACK_D, 160), (232, 228, 219)), ox + CARD_W / 2, cy)
    reveal(card, m, t, S6 + 0.15, S7, 2, layer)


def contact(layer, t):
    if t < S7 + 0.2:
        return
    p = out_back(prog(t, S7 + 0.2, 0.6), 1.2)
    w, h = 1000, 632
    card, m = shadowed(w, h, 36, NAVY, blur=22, off=14, alpha=90, outline=GOLD, ow=6)
    d = ImageDraw.Draw(card)
    cx = m + w / 2
    d.rounded_rectangle((m + 40, m + 34, m + w - 40, m + 262), 26, fill=WHITE)
    place(card, logo(660), cx, m + 148)
    place(card, text_sprite("S I N C E   1 9 9 4", F(BOLD, 32), GOLD_LT), cx, m + 302)
    d.line((cx - 160, m + 338, cx + 160, m + 338), fill=GOLD_LT, width=3)
    # phone: digits light up as they're spoken
    groups = ["800", "-", "3", "2", "4", "-", "9", "9", "8", "6"]
    lit_at = [T_DIGITS[0], T_DIGITS[1], T_DIGITS[1], T_DIGITS[2], T_DIGITS[3], T_DIGITS[4],
              T_DIGITS[4], T_DIGITS[5], T_DIGITS[6], T_DIGITS[7]]
    fph = F(BLACK_D, 86)
    spr = [text_sprite(g, fph, GOLD_LT if t >= lt else WHITE, pad=0) for g, lt in zip(groups, lit_at)]
    adv = [fph.getlength(g) for g in groups]
    ico = icon_disc("📞", 92)
    total = ico.width + 26 + sum(adv)
    x = cx - total / 2
    place(card, ico, x, m + 420, anchor="l")
    x += ico.width + 26
    for g, sp, a_ in zip(groups, spr, adv):
        place(card, sp, x + fph.getbbox(g)[0], m + 420, anchor="l")
        x += a_
    # website + click
    clicked = t >= T_URL
    fw = F(XB_D, 50)
    url = text_sprite("allenandassociates.agency", fw, GOLD_LT if clicked else WHITE)
    gl = icon_disc("🌐", 70)
    total = gl.width + 22 + url.width
    x = cx - total / 2
    uy = m + 540
    place(card, gl, x, uy, anchor="l")
    place(card, url, x + gl.width + 22, uy, anchor="l")
    if clicked:
        up = out_cubic(prog(t, T_URL, 0.3))
        ux0 = x + gl.width + 22
        d.rectangle((ux0, uy + 34, ux0 + url.width * up, uy + 39), fill=GOLD_LT)
    # cursor glides in and clicks
    if t >= T_URL - 0.8:
        k = out_cubic(prog(t, T_URL - 0.8, 0.7))
        tx, ty = x + gl.width + 22 + url.width * 0.62, uy + 8
        px, py = tx + (1 - k) * 260, ty + (1 - k) * 160
        cur = Image.new("RGBA", (60, 80), (0, 0, 0, 0))
        ImageDraw.Draw(cur).polygon([(4, 4), (4, 62), (18, 49), (29, 74), (39, 70), (28, 45), (48, 45)],
                                    fill=WHITE, outline=NAVY)
        if clicked:
            r = prog(t, T_URL, 0.45)
            if r < 1:
                rr = 12 + 50 * r
                d.ellipse((tx - rr, ty - rr, tx + rr, ty + rr), outline=GOLD_LT + (int(255 * (1 - r)),), width=5)
        place(card, cur, px + 26, py + 36, 0.88 if clicked and t < T_URL + 0.12 else 1.0)
    y = 708 - (1 - p) * 800
    place(layer, card, 540, y)


def tabs(layer, t):
    state = ["idle"] * 3
    if t >= S3: state[0] = "active"
    if t >= T_GREEN: state[0] = "done"
    if t >= S5: state[1] = "active"
    if t >= S6: state[1] = "done"; state[2] = "active"
    if t >= S7: state[2] = "done"
    flips = {0: [S3, T_GREEN], 1: [S5, S6], 2: [S6, S7]}
    for i in range(3):
        pp = pop(t, 1.0 + 0.15 * i, 0.3, 0.3)
        if not pp:
            continue
        s, a = pp
        for tf in flips[i]:
            if tf <= t < tf + 0.3:
                s *= 1 + 0.1 * math.sin(math.pi * (t - tf) / 0.3)
        spr = tab_sprite(i, state[i])
        place(layer, spr, TAB_X[i] + TAB_W / 2, TAB_Y0 + spr.height / 2 - 8, s, a)


BANNER = None


def graphics(t):
    global BANNER
    if BANNER is None:
        BANNER = build_banner()
    layer = Image.new("RGBA", (W, STAGE_H), (0, 0, 0, 0))
    hook(layer, t)
    authority(layer, t)
    card1(layer, t)
    card2(layer, t)
    card3(layer, t)
    contact(layer, t)
    tabs(layer, t)
    by = -BANNER.height + BANNER.height * out_back(prog(t, 0.0, 0.45), 1.2)
    place(layer, BANNER, W / 2, by + BANNER.height / 2)
    return layer


# ---------------------------------------------------------------- speaker
BASE = 0.85
ANCHOR_SRC = (540, 300)   # face centre in source
ANCHOR_OUT = (540, 1262)


def zoom_at(t):
    z = ZOOMS[0][1]
    for t0, z1 in ZOOMS[1:]:
        if t >= t0:
            z += (z1 - z) * out_cubic(prog(t, t0, 0.22))
    return z


def speaker_frames():
    vf = (f"select='not(between(t\\,{CUT_IN}\\,{CUT_OUT - 0.001}))',setpts=N/FRAME_RATE/TB,"
          "chromakey=0x03A03E:0.12:0.05,despill=type=green:mix=0.6:expand=0.1,format=rgba")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", vf, "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE)
    size = W * H * 4
    last = None
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        last = Image.frombuffer("RGBA", (W, H), buf, "raw", "RGBA", 0, 1)
        yield last
    while True:
        yield last


def compose_speaker(canvas, fr, t):
    s = BASE * zoom_at(t)
    # only the part of the source that lands on screen
    sy1 = min(H, int(ANCHOR_SRC[1] + (H - ANCHOR_OUT[1]) / s) + 2)
    crop = fr.crop((0, 0, W, sy1))
    spr = crop.resize((round(W * s), round(sy1 * s)), Image.BILINEAR)
    x = round(ANCHOR_OUT[0] - ANCHOR_SRC[0] * s)
    y = round(ANCHOR_OUT[1] - ANCHOR_SRC[1] * s)
    place(canvas, spr, x, y + spr.height / 2, anchor="l")


# ---------------------------------------------------------------- main
def frame(bg, fr, t):
    c = bg.copy()
    compose_speaker(c, fr, t)
    c.alpha_composite(graphics(t), (0, 0))
    return c


def main():
    bg = build_background()
    if "--stills" in sys.argv:
        times = [float(x) for x in sys.argv[sys.argv.index("--stills") + 1:]]
        for tt in times:
            src_t = tt if tt < CUT_IN else tt + CUT_LEN
            src_t = min(src_t, SRC_END - 0.05)
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(src_t), "-i", SRC, "-frames:v", "1", "-vf",
                                  "chromakey=0x03A03E:0.12:0.05,despill=type=green:mix=0.6:expand=0.1,format=rgba",
                                  "-f", "rawvideo", "-"], capture_output=True).stdout
            fr = Image.frombuffer("RGBA", (W, H), raw, "raw", "RGBA", 0, 1)
            frame(bg, fr, tt).convert("RGB").save(os.path.join(OUT, f"still_{tt:05.2f}.png"))
        return
    n = int(round(END * FPS))
    out = os.path.join(HERE, "..", "Turning-65-in-2027_final.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", os.path.join(OUT, "mix.wav"),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)
    frames = speaker_frames()
    for i in range(n):
        t = i / FPS
        enc.stdin.write(frame(bg, next(frames), t).convert("RGB").tobytes())
        if i % 150 == 0:
            print(f"{i}/{n}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
