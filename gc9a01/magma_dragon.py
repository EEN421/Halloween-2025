#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Magma Salamander Eye — BIG (Pi Zero W + GC9A01 240x240 SPI)
- Molten iris with ember flecks + crack striations
- Jagged 'lava fissure' pupil (serrated slit w/ lightning-bolt center)
- Enlarged eyeball footprint (iris/sclera)
- Scaly background (pre-rendered), soft shadow, blink
"""

import time, math, random
import numpy as np
import RPi.GPIO as GPIO
import spidev
from PIL import Image, ImageDraw

# -------- Pins (BCM) --------
DC  = 24
RST = 25

# -------- Eyeball scale (bigger eye) --------
EYE_RADIUS = 112
R_OUTER = EYE_RADIUS
R_MID   = max(0, EYE_RADIUS - 16)
R_INNER = max(0, EYE_RADIUS - 36)
R_STRIATION_OUT = max(0, EYE_RADIUS - 12)
R_FLECK_MAX     = max(0, EYE_RADIUS - 14)

# -------- Palette (magma) --------
BACKGROUND_COLOR   = (12, 6, 4)
SCALE_OUTLINE      = (38, 14, 10)
SCALE_FILL         = (58, 24, 16)
SCALE_HILITE       = (180, 90, 40)

IRIS_OUTER         = (130, 24, 12)   # dark lava crust
IRIS_MID           = (210, 60, 20)   # molten red-orange
IRIS_INNER         = (255, 200, 60)  # bright ember core

FISSURE_DARK       = (40, 10, 6)
VEIN_ORANGE        = (220, 110, 30)

PUPIL_COLOR        = (6, 3, 2)
SPECULAR_A         = (255, 230, 180)
SPECULAR_B         = (255, 255, 255)

# -------- GC9A01 Driver --------
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
        self.spi.max_speed_hz = 40_000_000
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
        self.cmd(0xB6, 0x00, 0x20); self.cmd(0x36, 0x48); self.cmd(0x3A, 0x05)
        self.cmd(0x90, 0x08, 0x08, 0x08, 0x08); self.cmd(0xBD, 0x06); self.cmd(0xBC, 0x00)
        self.cmd(0xFF, 0x60, 0x01, 0x04); self.cmd(0xC3, 0x13); self.cmd(0xC4, 0x13)
        self.cmd(0xC9, 0x22); self.cmd(0xBE, 0x11); self.cmd(0xE1, 0x10, 0x0E)
        self.cmd(0xDF, 0x21, 0x0C, 0x02)
        self.cmd(0xF0, 0x45, 0x09, 0x08, 0x08, 0x26, 0x2A)
        self.cmd(0xF1, 0x43, 0x70, 0x72, 0x36, 0x37, 0x6F)
        self.cmd(0xF2, 0x45, 0x09, 0x08, 0x08, 0x26, 0x2A)
        self.cmd(0xF3, 0x43, 0x70, 0x72, 0x36, 0x37, 0x6F)
        self.cmd(0xED, 0x1B, 0x0B); self.cmd(0xAE, 0x77); self.cmd(0xCD, 0x63)
        self.cmd(0x70, 0x07, 0x07, 0x04, 0x0E, 0x0F, 0x09, 0x07, 0x08, 0x03)
        self.cmd(0xE8, 0x34)
        self.cmd(0x62, 0x18, 0x0D, 0x71, 0xED, 0x70, 0x70, 0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70)
        self.cmd(0x63, 0x18, 0x11, 0x71, 0xF1, 0x70, 0x70, 0x18, 0x13, 0x71, 0xF3, 0x70, 0x70)
        self.cmd(0x64, 0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07)
        self.cmd(0x66, 0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45, 0x10, 0, 0, 0)
        self.cmd(0x67, 0x00, 0x3C, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98)
        self.cmd(0x74, 0x10, 0x85, 0x80, 0, 0, 0x4E, 0); self.cmd(0x98, 0x3E, 0x07)
        self.cmd(0x35); self.cmd(0x21); self.cmd(0x11); time.sleep(0.12); self.cmd(0x29); time.sleep(0.02)

    def show_numpy(self, image):
        arr = np.array(image.convert('RGB'))
        r = arr[:,:,0].astype(np.uint16); g = arr[:,:,1].astype(np.uint16); b = arr[:,:,2].astype(np.uint16)
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        high = (rgb565 >> 8).astype(np.uint8); low = (rgb565 & 0xFF).astype(np.uint8)
        buf = np.empty((self.height, self.width, 2), dtype=np.uint8)
        buf[:,:,0] = high; buf[:,:,1] = low
        data = buf.flatten().tolist()
        self.cmd(0x2A, 0, 0, 0, 239); self.cmd(0x2B, 0, 0, 0, 239); self.cmd(0x2C)
        GPIO.output(DC, GPIO.HIGH)
        for i in range(0, len(data), 4096):
            self.spi.writebytes(data[i:i+4096])

    def cleanup(self):
        self.spi.close(); GPIO.cleanup()

# -------- Eye Model (magma, BIG) --------
class MagmaSalamanderEye:
    def __init__(self, w=240, h=240):
        self.w, self.h = w, h
        self.cx, self.cy = w//2, h//2
        self.x = self.y = 0.0; self.tx = self.ty = 0.0
        self.blink_state = 0; self.blink = 0.0
        self.twinkle = 0.0

        # Lava fissure slit parameters (scaled up)
        self.slit_height = 136
        self.base_width  = 16        # mid-width in the center (try 14–20)
        self.pointiness  = 2.1       # taper exponent
        self.serration_amp = 0.28
        self.serration_freq = 0.33
        self.center_zigzag = 1.2

        self.scale_bg = self._render_scales()

    def _render_scales(self):
        img = Image.new('RGB', (self.w, self.h), BACKGROUND_COLOR)
        d = ImageDraw.Draw(img)
        tile = 18
        for row in range(-1, self.h//tile + 2):
            y0 = row*tile; odd = row & 1
            for col in range(-1, self.w//tile + 2):
                x0 = col*tile + (tile//2 if odd else 0)
                rx = random.randint(-1,1); ry = random.randint(-1,1)
                x, y = x0+rx, y0+ry
                r = tile//2
                pts = [(x, y-r),(x+r, y-r//3),(x+r, y+r//3),(x, y+r),(x-r, y+r//3),(x-r, y-r//3)]
                d.polygon(pts, fill=SCALE_FILL, outline=SCALE_OUTLINE)
                d.ellipse([x-1, y-1, x+1, y+1], fill=SCALE_HILITE)
        return img

    def update(self):
        if random.random() < 0.01 and self.blink_state == 0:
            ang = random.uniform(0, 2*math.pi); dist = random.uniform(0, 18)
            self.tx, self.ty = dist*math.cos(ang), dist*math.sin(ang)
        self.x += (self.tx - self.x)*0.35; self.y += (self.ty - self.y)*0.35

        if random.random() < 0.003 and self.blink_state == 0:
            self.blink_state = 1
        if self.blink_state == 1:
            self.blink += 0.5
            if self.blink >= 1: self.blink=1; self.blink_state=2
        elif self.blink_state == 2:
            time.sleep(0.02); self.blink_state=3
        elif self.blink_state == 3:
            self.blink -= 0.5
            if self.blink <= 0: self.blink=0; self.blink_state=0

        self.twinkle += 0.07

    def _draw_iris(self, d, ix, iy):
        d.ellipse([ix-R_OUTER, iy-R_OUTER, ix+R_OUTER, iy+R_OUTER], fill=IRIS_OUTER)
        d.ellipse([ix-R_MID,   iy-R_MID,   ix+R_MID,   iy+R_MID],   fill=IRIS_MID)
        d.ellipse([ix-R_INNER, iy-R_INNER, ix+R_INNER, iy+R_INNER], fill=IRIS_INNER)

        random.seed(int(time.time()*9))
        count = 52
        for i in range(count):
            base = (i/count)*2*math.pi
            angle = math.atan2(math.sin(base)*1.3, math.cos(base)) \
                    + random.uniform(-0.06,0.06) + 0.12*math.sin(self.twinkle + i*0.23)
            inner = 18 + (4 if i%3==0 else 2)
            outer = random.randint(max(inner+24, R_INNER+8), R_STRIATION_OUT)
            x1 = ix + int(inner*math.cos(angle)); y1 = iy + int(inner*math.sin(angle))
            x2 = ix + int(outer*math.cos(angle)); y2 = iy + int(outer*math.sin(angle))
            w = 1 if i%2 else 2
            col = FISSURE_DARK if i%3==0 else VEIN_ORANGE
            d.line([x1,y1,x2,y2], fill=col, width=w)

        # ember flecks
        for _ in range(180):
            r = random.randint(22, R_FLECK_MAX); a = random.uniform(0, 2*math.pi)
            x = ix + int(r*math.cos(a)); y = iy + int(r*math.sin(a))
            if (x-ix)**2 + (y-iy)**2 <= R_OUTER**2:
                col = (random.randint(220,255), random.randint(120,170), random.randint(20,50))
                d.point((x,y), fill=col)

        # jagged limbal ring
        teeth = 50
        for t in range(teeth):
            a0 = (t/teeth)*2*math.pi; jitter = random.uniform(-2.0, 2.0)
            r0, r1 = max(0, R_MID+jitter), max(0, R_OUTER+jitter)
            x0 = ix + int(r0*math.cos(a0)); y0 = iy + int(r0*math.sin(a0))
            x1 = ix + int(r1*math.cos(a0)); y1 = iy + int(r1*math.sin(a0))
            d.line([x0,y0,x1,y1], fill=(30, 12, 8), width=1)

    def _draw_lava_fissure_pupil(self, d, ix, iy):
        half_h = self.slit_height // 2
        phase = int(self.twinkle * 13)
        for dy in range(-half_h, half_h+1):
            t = abs(dy) / half_h if half_h else 1.0
            base_w = self.base_width * (1.0 - (t ** self.pointiness))
            serr = 1.0 + self.serration_amp * math.sin(self.serration_freq * dy + phase*0.07) \
                        + 0.12 * math.sin(0.15*dy + phase*0.11)
            width_f = base_w * max(0.0, serr)
            w = int(round(width_f))
            x_bend = int(self.center_zigzag * (1 if (dy//4)%2==0 else -1))
            if w > 0:
                y = iy + dy
                d.line([ix - w//2 + x_bend, y, ix + w//2 + x_bend, y], fill=PUPIL_COLOR)

    def draw(self):
        img = self.scale_bg.copy()
        d = ImageDraw.Draw(img)
        ix, iy = self.cx + int(self.x), self.cy + int(self.y)

        self._draw_iris(d, ix, iy)
        self._draw_lava_fissure_pupil(d, ix, iy)

        # highlights
        d.ellipse([ix - 7, iy - 44, ix + 7, iy - 34], fill=SPECULAR_A)
        d.ellipse([ix - 3, iy - 40, ix + 3, iy - 36], fill=SPECULAR_B)

        # soft top shadow (taller band for big eye)
        shadow = Image.new("RGBA", (self.w, self.h), (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        for r in range(48):
            alpha = int(120 * (1 - r / 48))
            sd.rectangle([0, r, self.w, r], fill=(0,0,0,alpha))
        img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")

        # blink lids
        if self.blink > 0:
            h = int(120*self.blink)
            for y in range(0, h, 3):
                darkness = int(60*(1 - y/max(h,1)))
                col = (SCALE_OUTLINE[0]+darkness//4, SCALE_OUTLINE[1], SCALE_OUTLINE[2])
                d.rectangle([0, y, self.w, y+2], fill=col)
            for y in range(self.h - h, self.h, 3):
                darkness = int(60*((y-(self.h-h))/max(h,1)))
                col = (SCALE_OUTLINE[0]+darkness//4, SCALE_OUTLINE[1], SCALE_OUTLINE[2])
                d.rectangle([0, y, self.w, y+2], fill=col)

        return img

# -------- Main --------
def main():
    print("🔥 Magma Salamander Eye — BIG — Pi Zero W + GC9A01")
    lcd = GC9A01(); lcd.init(); eye = MagmaSalamanderEye(240,240)
    start = time.time(); frames = 0
    try:
        while True:
            eye.update(); frame = eye.draw(); lcd.show_numpy(frame)
            frames += 1
            if frames % 30 == 0:
                fps = frames / max(0.001, (time.time()-start))
                print(f"FPS ~ {fps:.1f}")
            time.sleep(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        lcd.cleanup(); print("✓ Clean exit.")

if __name__ == "__main__":
    main()
