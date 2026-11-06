#!/usr/bin/env python3
"""Phim hoạt hình 10 giây: bình minh -> ngôi nhà tự dựng (có đường kích thước kiểu CAD)
-> bé Tròn nhảy tới -> "Chào ngày mới!".
Chạy:  python3 phim10s.py   ->  phim10s.mp4   (cần ffmpeg, Pillow, numpy)"""
import math, os, random, subprocess, wave
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR, S = 1280, 720, 30, 10.0, 2   # S: vẽ ở 2x rồi thu nhỏ cho nét mịn
SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phim10s.mp4")
FONTS = ["/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arialbd.ttf"]


@lru_cache(None)
def font(size):
    for p in FONTS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


# ---- easing ----
def prog(t, a, b): return max(0.0, min(1.0, (t - a) / (b - a)))
def ease_out(p): return 1 - (1 - p) ** 3
def ease_io(p): return p * p * (3 - 2 * p)
def ease_back(p, k=1.70158): return 1 + (k + 1) * (p - 1) ** 3 + k * (p - 1) ** 2
def bounce(p):
    n, d = 7.5625, 2.75
    if p < 1 / d: return n * p * p
    if p < 2 / d: p -= 1.5 / d; return n * p * p + 0.75
    if p < 2.5 / d: p -= 2.25 / d; return n * p * p + 0.9375
    p -= 2.625 / d; return n * p * p + 0.984375
def lerp(a, b, k): return tuple(int(x + (y - x) * k) for x, y in zip(a, b))
def P(*v): return [x * S for x in v]


# ---- phông nền ----
def grad(top, bot):
    k = np.linspace(0, 1, H * S)[:, None]
    row = np.array(top) * (1 - k) + np.array(bot) * k
    return Image.fromarray(np.repeat(row[:, None, :], W * S, axis=1).astype(np.uint8))

NIGHT = grad((10, 14, 40), (45, 40, 95))
DAWN = grad((70, 80, 160), (255, 165, 120))
DAY = grad((90, 170, 240), (205, 232, 255))
rnd = random.Random(7)
STARS = [(rnd.uniform(0, W), rnd.uniform(0, 380), rnd.uniform(1, 2.5), rnd.uniform(0, 6)) for _ in range(70)]
def y_front(x): return 570 + 18 * (1 - math.cos((x - 560) / 220))
def y_back(x): return 470 + 35 * math.sin(x / 140) + 20 * math.sin(x / 63 + 1)


def frame(t):
    day = ease_io(prog(t, 0.3, 3.2))
    img = Image.blend(NIGHT, DAWN, day * 2) if day < .5 else Image.blend(DAWN, DAY, day * 2 - 1)
    d = ImageDraw.Draw(img, "RGBA")

    # sao tắt dần
    a = 1 - prog(t, 0.6, 2.6)
    for x, y, r, ph in STARS:
        d.ellipse(P(x - r, y - r, x + r, y + r), fill=(255, 255, 230, int(255 * a * (0.6 + 0.4 * math.sin(t * 5 + ph)))))

    # mặt trời mọc sau đồi
    sy = 650 - 480 * ease_out(prog(t, 0.4, 3.4))
    sc = lerp((255, 110, 60), (255, 225, 90), day)
    for r, al in ((110, 25), (85, 40), (68, 70)):
        d.ellipse(P(980 - r, sy - r, 980 + r, sy + r), fill=sc + (al,))
    d.ellipse(P(925, sy - 55, 1035, sy + 55), fill=sc)

    # mây trôi
    cc = lerp((70, 70, 115), (255, 255, 255), day)
    for cx, cy in ((170, 240), (760, 215), (1150, 320)):
        cx += 10 * t
        for x0, y0, x1, y1 in ((-60, -18, 60, 24), (-38, -42, 12, 8), (-8, -54, 46, 4)):
            d.ellipse(P(cx + x0, cy + y0, cx + x1, cy + y1), fill=cc)

    # đồi
    for fy, c0, c1 in ((y_back, (22, 48, 58), (95, 170, 100)), (y_front, (28, 62, 48), (125, 200, 95))):
        d.polygon([(0, H * S)] + [(x * S, fy(x) * S) for x in range(0, W + 1, 10)] + [(W * S, H * S)], fill=lerp(c0, c1, day))

    # ---- ngôi nhà tự dựng ----
    line = dict(width=3 * S)
    ch = 55 * ease_out(prog(t, 5.1, 5.4))                                   # ống khói
    if ch > 0:
        d.rectangle(P(628, 370 - ch, 660, 370), fill=(165, 75, 60), outline=(100, 45, 35), **line)
    wh = 160 * ease_out(prog(t, 3.6, 4.4))                                  # tường mọc lên
    if wh > 0:
        d.rectangle(P(430, 555 - wh, 690, 555), fill=(246, 226, 186), outline=(125, 92, 60), **line)

    def pop(p, box, anchor, **kw):                                          # phóng to bật ra
        if p <= 0: return
        s, (ax, ay) = ease_back(p), anchor
        x0, y0, x1, y1 = box
        d.rectangle(P(ax + (x0 - ax) * s, ay + (y0 - ay) * s, ax + (x1 - ax) * s, ay + (y1 - ay) * s), **kw)

    pop(prog(t, 5.4, 5.8), (535, 475, 585, 555), (560, 555), fill=(135, 82, 50), outline=(80, 50, 30), **line)
    if t > 5.8:
        d.ellipse(P(571, 512, 579, 520), fill=(240, 200, 80))
    for x0, t0 in ((455, 5.7), (615, 5.9)):                                 # cửa sổ
        pop(prog(t, t0, t0 + 0.3), (x0, 440, x0 + 50, 490), (x0 + 25, 465), fill=(160, 215, 245), outline=(255, 255, 255), **line)
        if t > t0 + 0.3:
            d.line(P(x0 + 25, 440, x0 + 25, 490), fill=(255, 255, 255), **line)
            d.line(P(x0, 465, x0 + 50, 465), fill=(255, 255, 255), **line)
    if t > 4.4:                                                             # mái rơi xuống nảy
        oy = -480 * (1 - bounce(prog(t, 4.4, 5.1)))
        d.polygon(P(405, 397 + oy, 715, 397 + oy, 560, 298 + oy), fill=(205, 72, 60), outline=(120, 40, 35), **line)
    if t > 3.0:                                                             # móng rơi xuống nảy
        oy = -420 * (1 - bounce(prog(t, 3.0, 3.6)))
        d.rectangle(P(410, 553 + oy, 710, 575 + oy), fill=(150, 150, 162), outline=(90, 90, 100), **line)

    # đường kích thước kiểu CAD
    a = prog(t, 3.8, 4.1) * (1 - prog(t, 6.0, 6.6))
    if a > 0:
        g, c = ease_out(prog(t, 3.8, 4.4)), (255, 255, 255, int(230 * a))
        L, R = 560 - 130 * g, 560 + 130 * g
        for x in (430, 690):
            d.line(P(x, 582, x, 622), fill=c, width=2 * S)
        d.line(P(L, 612, R, 612), fill=c, width=2 * S)
        for x in (L, R):
            d.line(P(x - 7, 619, x + 7, 605), fill=c, width=3 * S)
        d.text((560 * S, 597 * S), "6000", font=font(22 * S), fill=c, anchor="mm")

    # khói
    for k in range(12):
        age = t - (6.4 + 0.45 * k)
        if 0 < age < 2.6:
            q = age / 2.6
            r, sx, sy = 9 + 22 * q, 644 + 30 * q + 6 * math.sin(age * 3 + k), 312 - 120 * q
            d.ellipse(P(sx - r, sy - r, sx + r, sy + r), fill=(235, 235, 240, int(170 * (1 - q))))

    # ---- bé Tròn ----
    if t > 6.0:
        p = prog(t, 6.0, 7.6)
        x = -60 + 850 * p
        up = abs(math.sin(math.pi * 4 * p)) * 65 + math.sin(math.pi * prog(t, 8.2, 8.8)) * 90
        R, ry = 32, 32 * (1 + 0.12 * min(1, up / 60))
        gy = y_front(x)
        cy = gy - ry - 4 - up
        w = 30 * (1 - 0.5 * min(1, up / 90))
        d.ellipse(P(x - w, gy - 5, x + w, gy + 5), fill=(0, 0, 0, 60))                  # bóng
        for fx in (-22, 4):
            d.ellipse(P(x + fx, cy + ry - 6, x + fx + 18, cy + ry + 5), fill=(215, 105, 30))
        d.ellipse(P(x - R, cy - ry, x + R, cy + ry), fill=(255, 150, 45), outline=(170, 85, 20), **line)
        d.ellipse(P(x - 18, cy, x + 18, cy + ry - 4), fill=(255, 205, 130))
        for ex in (-20, 20):
            d.ellipse(P(x + ex - 6, cy + 1, x + ex + 6, cy + 8), fill=(255, 110, 120, 150))  # má hồng
        dx, dy = (3, 0) if t < 7.6 else (-3, 0) if t < 8.0 else (0, -3)
        blink = any(abs(t - b) < 0.07 for b in (7.9, 9.3))
        for ex in (-11, 11):
            if blink:
                d.line(P(x + ex - 7, cy - 10, x + ex + 7, cy - 10), fill=(40, 30, 30), width=3 * S)
            else:
                d.ellipse(P(x + ex - 8, cy - 19, x + ex + 8, cy - 1), fill=(255, 255, 255))
                d.ellipse(P(x + ex + dx - 4, cy - 14 + dy, x + ex + dx + 4, cy - 6 + dy), fill=(40, 30, 30))
        d.arc(P(x - 8, cy - 4, x + 8, cy + 10), 20, 160, fill=(120, 50, 20), width=2 * S)

    # chữ
    p = prog(t, 8.0, 8.6)
    if p > 0:
        sz = max(1, int(78 * ease_back(p) * S))
        d.text((560 * S, 105 * S), "Chào ngày mới!", font=font(sz), fill=(255, 255, 255), anchor="mm",
               stroke_width=max(1, sz // 14), stroke_fill=(200, 75, 60))

    out = img.resize((W, H), Image.LANCZOS)
    f = min(prog(t, 0, 0.3), 1 - prog(t, 9.6, 10))
    return out if f >= 1 else Image.blend(Image.new("RGB", (W, H)), out, f)


def audio(path):
    n = int(SR * DUR)
    x_all, a = np.arange(n) / SR, np.zeros(n)

    def add(t0, dur, wave_fn):
        i = int(t0 * SR); m = min(n - i, int(dur * SR))
        a[i:i + m] += wave_fn(x_all[:m])

    def note(t0, midi, vol=0.18, dur=0.7, decay=6):          # tiếng hộp nhạc
        f = 440 * 2 ** ((midi - 69) / 12)
        add(t0, dur, lambda x: vol * np.exp(-x * decay) * (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x)))

    def blip(t0, f0, f1, vol=0.35, dur=0.15):                # "bụp" / "tưng"
        def fn(x):
            ph = 2 * np.pi * np.cumsum(np.linspace(f0, f1, len(x))) / SR
            return vol * np.exp(-x * 25) * np.sin(ph)
        add(t0, dur, fn)

    mel = [76, 79, 84, 79, 81, 76, 72, 76, 77, 81, 84, 81, 79, 74, 71, 74]
    for i, m in enumerate(mel):
        note(0.3 + 0.5 * i, m)
    for i, m in enumerate([48, 45, 41, 43]):
        note(0.3 + 2 * i, m, 0.3, 2.0, 1.5)
    for i, m in enumerate([72, 76, 79, 84]):                  # hợp âm khi chữ hiện
        note(8.0 + 0.1 * i, m, 0.2, 1.6, 2.5)
    note(8.0, 48, 0.3, 2.0, 1.5)
    for t0 in (3.22, 4.65): blip(t0, 230, 80, 0.6, 0.2)      # móng, mái chạm đất
    for t0 in (5.1, 5.4, 5.7, 5.9): blip(t0, 500, 950)        # ống khói, cửa, cửa sổ
    for t0 in (6.0, 6.4, 6.8, 7.2, 8.2): blip(t0, 300, 850, 0.25)  # bé Tròn nhảy

    a *= np.clip((DUR - x_all) / 0.4, 0, 1)
    a = a / np.abs(a).max() * 0.8
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    wav = OUT[:-4] + ".wav"
    audio(wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                           "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", OUT],
                          stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        ff.stdin.write(frame(i / FPS).tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print("Xong:", OUT)
