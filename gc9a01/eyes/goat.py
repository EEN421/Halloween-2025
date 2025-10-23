#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goat Eye (Rectangular Pupil — Squared & Smooth) — Pi Zero W + GC9A01 240x240 SPI
- Golden iris with fibers/flecks
- Wide horizontal rectangular pupil (large flat center, soft/tame ends, low serration)
- Soft corneal shadow + blink lids
"""

import time, math, random
import numpy as np
import RPi.GPIO as GPIO
import spidev
from PIL import Image, ImageDraw

# ---------- Pins (BCM) ----------
DC  = 24
RST = 25

# ---------- Eyeball scaling ----------
EYE_RADIUS       = 112
R_OUTER          = EYE_RADIUS
R_MID            = max(0, EYE_RADIUS - 16)
R_INNER          = max(0, EYE_RADIUS - 36)
R_STRIATION_OUT  = max(0, EYE_RADIUS - 12)
R_FLECK_MAX      = max(0, EYE_RADIUS - 14)

# ---------- Palette ----------
BACKGROUND_COLOR   = (14, 12, 11)
HIDE_LOW           = (28, 24, 22)
HIDE_MID           = (36, 32, 30)
HIDE_HI            = (52, 48, 46)

IRIS_OUTER         = (90, 60, 15)
IRIS_MID           = (165, 130, 35)
IRIS_INNER         = (240, 220, 110)

FIBER_DARK         = (45, 35, 18)
FIBER_WARM         = (130, 100, 30)

PUPIL_COLOR        = (5, 5, 5)
SPECULAR_A         = (255, 245, 200)
SPECULAR_B         = (255, 255, 255)

# ---------- GC9A01 Driver ----------
class GC9A01:
    def __init__(self):
        self.width, self.height = 240, 240
        GPIO.setmode(GPIO.BCM); GPIO.setwarnings(False)
        GPIO.setup(DC, GPIO.OUT); GPIO.setup(RST, GPIO.OUT)

        self.spi = spidev.SpiDev()
        opened = False
        for dev in (0, 1):
            try:
                self.spi.open(0, dev); opened = True; break
            except FileNotFoundError:
                pass
        if not opened:
            raise RuntimeError("SPI device not found. Enable SPI and check CE0/CE1.")

        self.spi.max_speed_hz = 40_000_000  # drop to 32_000_000 if you see tearing
        self.spi.mode = 0

    def cmd(self, c, *data):
        GPIO.output(DC, GPIO.LOW); self.spi.writebytes([c])
        if data:
            GPIO.output(DC, GPIO.HIGH); self.spi.writebytes(list(data))

    def reset(self):
        GPIO.output(RST, GPIO.LOW); time.sleep(0.1)
        GPIO.output(RST, GPIO.HIGH); time.sleep(0.12)

    def init(self):
        self.reset()
        self.cmd(0xEF); self.cmd(0xEB, 0x14); self.cmd(0xFE); self.cmd(0xEF); self.cmd(0xEB, 0x14)
        self.cmd(0x84, 0x40); self.cmd(0x85, 0xFF); self.cmd(0x86, 0xFF); self.cmd(0x87, 0xFF)
        self.cmd(0x88, 0x0A); self.cmd(0x89, 0x21); self.cmd(0x8A, 0x00); self.cmd(0x8B, 0x80)
        self.cmd(0x8C, 0x01); self.cmd(0x8D, 0x01); self.cmd(0x8E, 0xFF); self.cmd(0x8F, 0xFF)
        self.cmd(0xB6, 0x00, 0x20)
        self.cmd(0x36, 0x48)
        self.cmd(0x3A, 0x05)  # RGB565
        self.cmd(0x90, 0x08, 0x08, 0x08, 0x08)
        self.cmd(0xBD, 0x06); self.cmd(0xBC, 0x00)
        self.cmd(0xFF, 0x60, 0x01, 0x04)
        self.cmd(0xC3, 0x13); self.cmd(0xC4, 0x13)
        self.cmd(0xC9, 0x22); self.cmd(0xBE, 0x11)
        self.cmd(0xE1, 0x10, 0x0E)
        self.cmd(0xDF, 0x21, 0x0C, 0x02)
        self.cmd(0xF0, 0x45, 0x09, 0x08, 0x08, 0x26, 0x2A)
        self.cmd(0xF1, 0x43, 0x70, 0x72, 0x36, 0x37, 0x6F)
        self.cmd(0xF2, 0x45, 0x09, 0x08, 0x08, 0x26, 0x2A)
        self.cmd(0xF3, 0x43, 0x70, 0x72, 0x36, 0x37, 0x6F)
        self.cmd(0xED, 0x1B, 0x0B)
        self.cmd(0xAE, 0x77)
        self.cmd(0xCD, 0x63)
        self.cmd(0x70, 0x07, 0x07, 0x04, 0x0E, 0x0F, 0x09, 0x07, 0x08, 0x03)
        self.cmd(0xE8, 0x34)
        self.cmd(0x62, 0x18, 0x0D, 0x71, 0xED, 0x70, 0x70, 0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70)
        self.cmd(0x63, 0x18, 0x11, 0x71, 0xF1, 0x70, 0x70, 0x18, 0x13, 0x71, 0xF3, 0x70, 0x70)
        self.cmd(0x64, 0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07)
        self.cmd(0x66, 0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45, 0x10, 0, 0, 0)
        self.cmd(0x67, 0x00, 0x3C, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98)
        self.cmd(0x74, 0x10, 0x85, 0x80, 0, 0, 0x4E, 0)
        self.cmd(0x98, 0x3E, 0x07)
        self.cmd(0x35)  # TE
        self.cmd(0x21)  # inversion
        self.cmd(0x11); time.sleep(0.12)
        self.cmd(0x29); time.sleep(0.02)

    def show_numpy(self, image):
        arr = np.array(image.convert('RGB'))
        r = arr[:, :, 0].astype(np.uint16)
        g = arr[:, :, 1].astype(np.uint16)
        b = arr[:, :, 2].astype(np.uint16)
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        high = (rgb565 >> 8).astype(np.uint8)
        low  = (rgb565 & 0xFF).astype(np.uint8)
        buf = np.empty((self.height, self.width, 2), dtype=np.uint8)
        buf[:, :, 0] = high; buf[:, :, 1] = low
        data = buf.flatten().tolist()

        self.cmd(0x2A, 0, 0, 0, 239)
        self.cmd(0x2B, 0, 0, 0, 239)
        self.cmd(0x2C)
        GPIO.output(DC, GPIO.HIGH)
        for i in range(0, len(data), 4096):
            self.spi.writebytes(data[i:i+4096])

    def cleanup(self):
        self.spi.close()
        GPIO.cleanup()

# ---------- Eye Model ----------
class GoatEye:
    def __init__(self, w=240, h=240):
        self.w, self.h = w, h
        self.cx, self.cy = w // 2, h // 2

        # Gaze
        self.x = self.y = 0.0
        self.tx = self.ty = 0.0

        # Blink
        self.blink_state = 0
        self.blink = 0.0

        # >>> Rectangular pupil tuning (squared & smoother) <<<
        self.pupil_width   = 126   # overall width across the iris
        self.pupil_height  = 20    # taller for squarer look
        self.flat_ratio    = 0.78  # larger flat midsection
        self.pointiness    = 1.6   # duller ends
        self.serration_amp = 0.06  # much lower serration
        self.serration_fq1 = 0.18
        self.serration_fq2 = 0.06
        self.center_bow    = 0.30  # mild bow so it's not ruler-straight

        self.twinkle = 0.0

        # Pre-rendered background (goat hide)
        self.hide_bg = self._render_hide()

    # -- Background: coarse "hide" texture (fast) --
    def _render_hide(self):
        img = Image.new('RGB', (self.w, self.h), BACKGROUND_COLOR)
        d = ImageDraw.Draw(img)
        rng = random.Random(1337)
        # broad mottling
        for _ in range(180):
            w = rng.randint(16, 36)
            h = rng.randint(8, 24)
            x = rng.randint(-8, self.w-8)
            y = rng.randint(-8, self.h-8)
            col = (
                rng.randint(HIDE_LOW[0], HIDE_MID[0]),
                rng.randint(HIDE_LOW[1], HIDE_MID[1]),
                rng.randint(HIDE_LOW[2], HIDE_MID[2]),
            )
            d.ellipse([x, y, x+w, y+h], fill=col)
        # fine hairs/highlights
        for _ in range(120):
            x = rng.randint(0, self.w-1)
            y = rng.randint(0, self.h-1)
            d.point((x, y), fill=HIDE_HI)
        return img

    # -- Update animation --
    def update(self):
        # rare gaze shift (small)
        if random.random() < 0.01 and self.blink_state == 0:
            ang = random.uniform(0, 2*math.pi); dist = random.uniform(0, 18)
            self.tx, self.ty = dist*math.cos(ang), dist*math.sin(ang)

        # ease toward target
        self.x += (self.tx - self.x) * 0.35
        self.y += (self.ty - self.y) * 0.35

        # blink
        if random.random() < 0.003 and self.blink_state == 0:
            self.blink_state = 1
        if self.blink_state == 1:
            self.blink += 0.5
            if self.blink >= 1: self.blink = 1; self.blink_state = 2
        elif self.blink_state == 2:
            time.sleep(0.02); self.blink_state = 3
        elif self.blink_state == 3:
            self.blink -= 0.5
            if self.blink <= 0: self.blink = 0; self.blink_state = 0

        self.twinkle += 0.06

    # -- Draw iris rings & texture --
    def _draw_iris(self, d, ix, iy):
        d.ellipse([ix-R_OUTER, iy-R_OUTER, ix+R_OUTER, iy+R_OUTER], fill=IRIS_OUTER)
        d.ellipse([ix-R_MID,   iy-R_MID,   ix+R_MID,   iy+R_MID],   fill=IRIS_MID)
        d.ellipse([ix-R_INNER, iy-R_INNER, ix+R_INNER, iy+R_INNER], fill=IRIS_INNER)

        random.seed(int(time.time()*9))
        count = 48
        for i in range(count):
            base = (i / count) * 2 * math.pi
            angle = math.atan2(math.sin(base) * 1.1, math.cos(base)) \
                    + random.uniform(-0.05, 0.05) \
                    + 0.06 * math.sin(self.twinkle + i * 0.23)
            inner = 18 + (3 if (i % 3 == 0) else 2)
            outer = random.randint(max(inner+24, R_INNER+8), R_STRIATION_OUT)
            x1 = ix + int(inner * math.cos(angle)); y1 = iy + int(inner * math.sin(angle))
            x2 = ix + int(outer * math.cos(angle)); y2 = iy + int(outer * math.sin(angle))
            w  = 1 if (i % 2) else 2
            col = FIBER_DARK if (i % 3 == 0) else FIBER_WARM
            d.line([x1, y1, x2, y2], fill=col, width=w)

        # flecks
        for _ in range(160):
            r = random.randint(22, R_FLECK_MAX)
            a = random.uniform(0, 2*math.pi)
            x = ix + int(r * math.cos(a)); y = iy + int(r * math.sin(a))
            if (x-ix)**2 + (y-iy)**2 <= R_OUTER**2:
                col = (random.randint(120, 170), random.randint(90, 140), random.randint(15, 35))
                d.point((x, y), fill=col)

        # limbal “teeth” to dirty up the rim (keep subtle)
        teeth = 40
        for t in range(teeth):
            a0 = (t / teeth) * 2 * math.pi
            jitter = random.uniform(-1.5, 1.5)
            r0 = max(0, R_MID + jitter)
            r1 = max(0, R_OUTER + jitter)
            x0 = ix + int(r0 * math.cos(a0)); y0 = iy + int(r0 * math.sin(a0))
            x1 = ix + int(r1 * math.cos(a0)); y1 = iy + int(r1 * math.sin(a0))
            d.line([x0, y0, x1, y1], fill=(30, 24, 18), width=1)

    # -- Rectangular pupil (horizontal), *smoother* edges --
    def _draw_rect_pupil(self, d, ix, iy):
        total_w   = int(self.pupil_width)
        half_w    = total_w // 2
        base_h    = float(self.pupil_height)
        flat_w    = int(self.flat_ratio * total_w)
        flat_half = flat_w // 2
        phase     = int(self.twinkle * 10)

        # Draw column-by-column for fine control of height
        for dx in range(-half_w, half_w + 1):
            adx = abs(dx)
            if adx <= flat_half:
                h = base_h
            else:
                t = (adx - flat_half) / max(1, (half_w - flat_half))
                h = base_h * (1.0 - (t ** self.pointiness))

            # very subtle edge wobble (nearly straight)
            wobble = (
                self.serration_amp * math.sin(self.serration_fq1 * dx + phase * 0.08)
                + 0.03 * math.sin(self.serration_fq2 * dx + phase * 0.11)
            )
            h = max(1.0, h * (1.0 + wobble))

            # mild center bow
            y_bend = int(self.center_bow * math.sin(dx * 0.05 + phase * 0.06))

            hh = int(round(h))
            if hh > 0:
                x = ix + dx
                d.line([x, iy - hh // 2 + y_bend, x, iy + hh // 2 + y_bend], fill=PUPIL_COLOR)

    def draw(self):
        img = self.hide_bg.copy()
        d = ImageDraw.Draw(img)
        ix, iy = self.cx + int(self.x), self.cy + int(self.y)

        # iris
        self._draw_iris(d, ix, iy)

        # pupil (square/smooth)
        self._draw_rect_pupil(d, ix, iy)

        # specular highlights
        d.ellipse([ix - 7, iy - 44, ix + 7, iy - 34], fill=SPECULAR_A)
        d.ellipse([ix - 3, iy - 40, ix + 3, iy - 36], fill=SPECULAR_B)

        # soft top shadow
        shadow = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        for r in range(46):
            alpha = int(110 * (1 - r / 46))
            sd.rectangle([0, r, self.w, r], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")

        # blink lids
        if self.blink > 0:
            h = int(120 * self.blink)
            for y in range(0, h, 3):
                darkness = int(55 * (1 - y / max(h, 1)))
                col = (HIDE_MID[0] + darkness // 4, HIDE_MID[1], HIDE_MID[2])
                d.rectangle([0, y, self.w, y + 2], fill=col)
            for y in range(self.h - h, self.h, 3):
                darkness = int(55 * ((y - (self.h - h)) / max(h, 1)))
                col = (HIDE_MID[0] + darkness // 4, HIDE_MID[1], HIDE_MID[2])
                d.rectangle([0, y, self.w, y + 2], fill=col)

        return img

# ---------- Main ----------
def main():
    print("="*60)
    print("🐐 Goat Eye — Rectangular (Squared & Smooth) — Pi Zero W + GC9A01")
    print("="*60)

    lcd = GC9A01()
    print("Initializing display...")
    lcd.init()
    print("✓ Display ready.")

    eye = GoatEye(240, 240)
    start = time.time(); frames = 0

    try:
        while True:
            eye.update()
            frame = eye.draw()
            lcd.show_numpy(frame)

            frames += 1
            if frames % 30 == 0:
                fps = frames / max(0.001, (time.time() - start))
                print(f"FPS ~ {fps:.1f}")

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        lcd.cleanup()
        print("✓ Cleaned up. Bye.")

if __name__ == "__main__":
    main()