#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reptilian Eye (Pi Zero W + GC9A01 240x240 SPI)
- Anisotropic, mottled iris with jagged limbal ring
- Jagged 'lava fissure' pupil (serrated slit with lightning-bolt center)
- Nictitating membrane sweep (inner eyelid)
- Scaly background (pre-rendered for FPS)
- Blink animation + subtle corneal shadow + enlarged eyeball footprint
"""

import time
import math
import random
import numpy as np
import RPi.GPIO as GPIO
import spidev
from PIL import Image, ImageDraw

# ------------- Pins (BCM) -------------
DC  = 24
RST = 25

# ------------- Eyeball scale -------------
# Master radius of the visible eyeball (iris+sclera footprint) in pixels.
# Max theoretical is 120 (half of 240), but leave a few pixels for rim/occlusion.
EYE_RADIUS = 112

# Derive ring radii from EYE_RADIUS (outermost iris ring out to the rim)
R_OUTER = EYE_RADIUS                     # outer limbal edge
R_MID   = max(0, EYE_RADIUS - 16)        # mid ring
R_INNER = max(0, EYE_RADIUS - 36)        # inner bright ring
R_STRIATION_OUT = max(0, EYE_RADIUS - 12)  # where fibers tend to end
R_FLECK_MAX     = max(0, EYE_RADIUS - 14)  # flecks limit

# ------------- Palette -------------
BACKGROUND_COLOR     = (12, 10, 10)            # behind scales
SCALE_DARK           = (18, 28, 18)            # scale outline
SCALE_BASE           = (36, 56, 30)            # scale fill
SCALE_HILITE         = (70, 100, 60)           # small dot highlight

# Iris rings
IRIS_REPTILE_OUTER   = (34, 90, 28)            # dirty swamp green
IRIS_REPTILE_MID     = (130, 200, 44)          # toxic green
IRIS_REPTILE_INNER   = (245, 245, 110)         # sulfurous yellow

# Fibers & veins
VEIN_COLOR           = (30, 80, 30)
STRIATION_DARK       = (25, 25, 25)

# Pupil & specular
PUPIL_COLOR          = (8, 8, 8)               # slight lift so edge reads on TFT
SPECULAR_A           = (255, 245, 190)
SPECULAR_B           = (255, 255, 255)

# ------------- GC9A01 Driver -------------
class GC9A01:
    def __init__(self):
        self.width  = 240
        self.height = 240

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DC, GPIO.OUT)
        GPIO.setup(RST, GPIO.OUT)

        self.spi = spidev.SpiDev()

        # Try CE0 then CE1 (some GC9A01 breakouts wire to CE1)
        opened = False
        for dev in (0, 1):
            try:
                self.spi.open(0, dev)
                opened = True
                break
            except FileNotFoundError:
                continue
        if not opened:
            raise RuntimeError("SPI device not found. Enable SPI and check CE0/CE1 wiring.")

        # Zero W is typically stable at 32–40 MHz
        self.spi.max_speed_hz = 40_000_000
        self.spi.mode = 0  # CPOL=0, CPHA=0

    def cmd(self, c, *data):
        GPIO.output(DC, GPIO.LOW)
        self.spi.writebytes([c])
        if data:
            GPIO.output(DC, GPIO.HIGH)
            self.spi.writebytes(list(data))

    def reset(self):
        GPIO.output(RST, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(RST, GPIO.HIGH)
        time.sleep(0.12)

    def init(self):
        self.reset()

        # Init sequence for GC9A01
        self.cmd(0xEF)
        self.cmd(0xEB, 0x14)
        self.cmd(0xFE)
        self.cmd(0xEF)
        self.cmd(0xEB, 0x14)
        self.cmd(0x84, 0x40)
        self.cmd(0x85, 0xFF)
        self.cmd(0x86, 0xFF)
        self.cmd(0x87, 0xFF)
        self.cmd(0x88, 0x0A)
        self.cmd(0x89, 0x21)
        self.cmd(0x8A, 0x00)
        self.cmd(0x8B, 0x80)
        self.cmd(0x8C, 0x01)
        self.cmd(0x8D, 0x01)
        self.cmd(0x8E, 0xFF)
        self.cmd(0x8F, 0xFF)
        self.cmd(0xB6, 0x00, 0x20)
        self.cmd(0x36, 0x48)
        self.cmd(0x3A, 0x05)  # 16-bit RGB565
        self.cmd(0x90, 0x08, 0x08, 0x08, 0x08)
        self.cmd(0xBD, 0x06)
        self.cmd(0xBC, 0x00)
        self.cmd(0xFF, 0x60, 0x01, 0x04)
        self.cmd(0xC3, 0x13)
        self.cmd(0xC4, 0x13)
        self.cmd(0xC9, 0x22)
        self.cmd(0xBE, 0x11)
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
        self.cmd(0x66, 0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45, 0x10, 0x00, 0x00, 0x00)
        self.cmd(0x67, 0x00, 0x3C, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98)
        self.cmd(0x74, 0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00)
        self.cmd(0x98, 0x3E, 0x07)
        self.cmd(0x35)      # TE on
        self.cmd(0x21)      # inversion on
        self.cmd(0x11)      # sleep out
        time.sleep(0.12)
        self.cmd(0x29)      # display on
        time.sleep(0.02)

    def show_numpy(self, image):
        """Send a PIL.Image (RGB) to the display as RGB565."""
        img_array = np.array(image.convert('RGB'))

        r = img_array[:, :, 0].astype(np.uint16)
        g = img_array[:, :, 1].astype(np.uint16)
        b = img_array[:, :, 2].astype(np.uint16)

        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        high = (rgb565 >> 8).astype(np.uint8)
        low  = (rgb565 & 0xFF).astype(np.uint8)

        buf = np.empty((self.height, self.width, 2), dtype=np.uint8)
        buf[:, :, 0] = high
        buf[:, :, 1] = low
        data = buf.flatten().tolist()

        # Full frame window
        self.cmd(0x2A, 0, 0, 0, 239)
        self.cmd(0x2B, 0, 0, 0, 239)
        self.cmd(0x2C)

        GPIO.output(DC, GPIO.HIGH)
        chunk = 4096
        for i in range(0, len(data), chunk):
            self.spi.writebytes(data[i:i+chunk])

    def cleanup(self):
        self.spi.close()
        GPIO.cleanup()

# ------------- Eyeball Model -------------
class ReptileEye:
    def __init__(self, w=240, h=240):
        self.w = w
        self.h = h
        self.cx = w // 2
        self.cy = h // 2

        # Eye position
        self.x = 0.0
        self.y = 0.0
        self.tx = 0.0
        self.ty = 0.0

        # Blink state
        self.blink_state = 0
        self.blink = 0.0

        # Pupil parameters (width/taper knobs still honored)
        self.pupil_width = 16        # widened a touch to suit larger eye (try 14–20)
        self.pupil_power = 2.0       # taper exponent (higher = pointier tips)

        # Nictitating membrane (inner eyelid)
        self.mem_t = 0.0             # 0..1 position
        self.mem_dir = 0             # 0 idle, +1 in, -1 out

        # Iris shimmer phase
        self.twinkle = 0.0

        # Pre-rendered scale background
        self.scale_bg = self._render_scales()

    # --------- Pre-rendered scales for speed ----------
    def _render_scales(self):
        img = Image.new('RGB', (self.w, self.h), BACKGROUND_COLOR)
        d = ImageDraw.Draw(img)
        tile = 18
        for row in range(-1, self.h // tile + 2):
            y0 = row * tile
            odd = row & 1
            for col in range(-1, self.w // tile + 2):
                x0 = col * tile + (tile // 2 if odd else 0)
                # Subtle jitter so grid isn't perfect
                rx = 0 if (row == 0 and col == 0) else random.randint(-1, 1)
                ry = 0 if (row == 0 and col == 0) else random.randint(-1, 1)
                x = x0 + rx
                y = y0 + ry
                r = tile // 2
                pts = [
                    (x, y - r),
                    (x + r, y - r // 3),
                    (x + r, y + r // 3),
                    (x, y + r),
                    (x - r, y + r // 3),
                    (x - r, y - r // 3),
                ]
                d.polygon(pts, fill=SCALE_BASE, outline=SCALE_DARK)
                d.ellipse([x-1, y-1, x+1, y+1], fill=SCALE_HILITE)
        return img

    # ----------------- Animation update ----------------
    def update(self):
        # Random gaze shift (small saccade) occasionally
        if random.random() < 0.01 and self.blink_state == 0 and self.mem_dir == 0:
            ang = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, 20)
            self.tx = dist * math.cos(ang)
            self.ty = dist * math.sin(ang)

        # Ease toward target
        self.x += (self.tx - self.x) * 0.35
        self.y += (self.ty - self.y) * 0.35

        # Blink (rare)
        if random.random() < 0.003 and self.blink_state == 0 and self.mem_dir == 0:
            self.blink_state = 1
        if self.blink_state == 1:
            self.blink += 0.5
            if self.blink >= 1:
                self.blink = 1
                self.blink_state = 2
        elif self.blink_state == 2:
            time.sleep(0.02)
            self.blink_state = 3
        elif self.blink_state == 3:
            self.blink -= 0.5
            if self.blink <= 0:
                self.blink = 0
                self.blink_state = 0

        # Nictitating membrane sweep (rare)
        if self.mem_dir == 0 and random.random() < 0.0015 and self.blink_state == 0:
            self.mem_dir = 1
        if self.mem_dir != 0:
            speed = 0.06  # 0.05–0.08 looks nice
            self.mem_t += speed * self.mem_dir
            if self.mem_t >= 1.0:
                self.mem_t = 1.0
                self.mem_dir = -1
            elif self.mem_t <= 0.0:
                self.mem_t = 0.0
                self.mem_dir = 0

        # Shimmer phase
        self.twinkle += 0.07

    # ----------------- Frame render --------------------
    def draw(self):
        # Start with the pre-rendered scaly background
        img = self.scale_bg.copy()
        d = ImageDraw.Draw(img)
        cx, cy = self.cx, self.cy
        ix, iy = cx + int(self.x), cy + int(self.y)

        # ---- IRIS RINGS (scaled out) ----
        d.ellipse([ix - R_OUTER, iy - R_OUTER, ix + R_OUTER, iy + R_OUTER], fill=IRIS_REPTILE_OUTER)
        d.ellipse([ix - R_MID,   iy - R_MID,   ix + R_MID,   iy + R_MID],   fill=IRIS_REPTILE_MID)
        d.ellipse([ix - R_INNER, iy - R_INNER, ix + R_INNER, iy + R_INNER], fill=IRIS_REPTILE_INNER)

        # ---- ANISOTROPIC STRIATIONS + MOTTLE (scaled extents) ----
        random.seed(int(time.time() * 9))
        count = 52  # slightly denser on larger iris
        for i in range(count):
            base = (i / count) * 2 * math.pi
            angle = (math.atan2(math.sin(base) * 1.4, math.cos(base))
                     + random.uniform(-0.05, 0.05)
                     + 0.10 * math.sin(self.twinkle + i * 0.27))
            inner = 18 + (4 if (i % 3) else 2)
            outer = random.randint(max(inner+20, R_INNER+6), R_STRIATION_OUT)
            x1 = ix + int(inner * math.cos(angle)); y1 = iy + int(inner * math.sin(angle))
            x2 = ix + int(outer * math.cos(angle)); y2 = iy + int(outer * math.sin(angle))
            w  = 1 if (i % 2) else 2
            col = STRIATION_DARK if (i % 3 == 0) else VEIN_COLOR
            d.line([x1, y1, x2, y2], fill=col, width=w)

        # pigment flecks (fill closer to the new outer radius)
        for _ in range(180):
            r = random.randint(22, R_FLECK_MAX)
            a = random.uniform(0, 2 * math.pi)
            x = ix + int(r * math.cos(a)); y = iy + int(r * math.sin(a))
            if (x - ix) ** 2 + (y - iy) ** 2 <= R_OUTER ** 2:
                col = (random.randint(80, 120), random.randint(140, 190), random.randint(35, 60))
                d.point((x, y), fill=col)

        # jagged limbal “teeth” hugging the bigger rim
        teeth = 48
        for t in range(teeth):
            a0 = (t / teeth) * 2 * math.pi
            jitter = random.uniform(-2.0, 2.0)
            r0 = max(0, R_MID + jitter)
            r1 = max(0, R_OUTER + jitter)
            x0 = ix + int(r0 * math.cos(a0)); y0 = iy + int(r0 * math.sin(a0))
            x1 = ix + int(r1 * math.cos(a0)); y1 = iy + int(r1 * math.sin(a0))
            d.line([x0, y0, x1, y1], fill=(20, 35, 20), width=1)

        # ==== LAVA FISSURE PUPIL (serrated slit with center zigzag), scaled up ====
        slit_height = 136                      # bigger vertical span
        half_h = slit_height // 2
        phase = int(self.twinkle * 13)         # slow animation of serration
        serration_amp  = 0.28                  # 0.0..0.4 edge jaggedness
        serration_freq = 0.33                  # cycles per pixel vertically
        center_zigzag  = 1.2                   # ±px lateral wiggle

        base_width = float(self.pupil_width)   # keep your knob
        pointiness = float(self.pupil_power)   # keep your knob

        for dy in range(-half_h, half_h + 1):
            t = abs(dy) / half_h if half_h else 1.0
            base_w = base_width * (1.0 - (t ** pointiness))
            serr = 1.0 \
                   + serration_amp * math.sin(serration_freq * dy + phase * 0.07) \
                   + 0.12 * math.sin(0.15 * dy + phase * 0.11)
            width_f = base_w * max(0.0, serr)
            w = int(round(width_f))
            x_bend = int(center_zigzag * (1 if (dy // 4) % 2 == 0 else -1))
            if w > 0:
                y = iy + dy
                d.line([ix - w // 2 + x_bend, y, ix + w // 2 + x_bend, y], fill=PUPIL_COLOR)

        # ---- RIM OCCLUSION (overlap scales onto larger iris) ----
        rim = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rim)
        # draw short radial strokes that slightly cover the limbus
        for a_deg in range(-120, 121, 10):
            a = math.radians(a_deg + random.uniform(-3, 3))
            r0, r1 = max(0, R_OUTER - 10), min(EYE_RADIUS + 12, R_OUTER + 12)
            x0 = ix + int(r0 * math.cos(a)); y0 = iy + int(r0 * math.sin(a))
            x1 = ix + int(r1 * math.cos(a)); y1 = iy + int(r1 * math.sin(a))
            rd.line([x0, y0, x1, y1], fill=(20, 25, 20, 180), width=3)
        img.paste(rim, (0, 0), rim)

        # ---- SPECULAR & SHADOW ----
        # dual “studio” highlights (their placement still looks good at this size)
        d.ellipse([ix - 7, iy - 44, ix + 7, iy - 34], fill=SPECULAR_A)
        d.ellipse([ix - 3, iy - 40, ix + 3, iy - 36], fill=SPECULAR_B)

        # soft top shadow (slightly taller band to fit larger eye)
        shadow = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        for r in range(48):
            alpha = int(120 * (1 - r / 48))
            sd.rectangle([0, r, self.w, r], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")

        # ---- NICTITATING MEMBRANE (inner eyelid sweep L->R), scaled coverage ----
        if self.mem_t > 0.0:
            mem = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
            md = ImageDraw.Draw(mem)
            t = self.mem_t
            alpha = int(120 * (0.7 + 0.3 * (1 - abs(0.5 - t) * 2)))  # denser mid-sweep
            color = (220, 230, 225, alpha)
            # curved polygon hugging the larger iris
            pts = []
            RX, RY = EYE_RADIUS + 4, int(EYE_RADIUS * 0.9)  # a bit wider than iris to fully cover
            for k in range(-90, 91, 10):
                a = math.radians(k)
                x = ix - int((1 - t) * 140) + int(RX * math.cos(a))
                y = iy + int(RY * math.sin(a))
                pts.append((x, y))
            pts += [(ix - 220, iy + 120), (ix - 220, iy - 120)]
            md.polygon(pts, fill=color)
            # faint membrane veins
            for _ in range(7):
                a0 = random.uniform(-0.6, 0.6)
                rr = random.randint(int(EYE_RADIUS * 0.4), int(EYE_RADIUS * 0.9))
                last = None
                for s in range(10):
                    a = a0 + s * 0.14
                    x = ix - int((1 - t) * 140) + int(rr * math.cos(a))
                    y = iy + int(48 * math.sin(a))
                    if last:
                        md.line([last, (x, y)], fill=(200, 205, 200, int(alpha * 0.5)), width=1)
                    last = (x, y)
            img.paste(mem, (0, 0), mem)

        # ---- BLINK LIDS ----
        if self.blink > 0:
            h = int(120 * self.blink)
            # top lid bars
            for y in range(0, h, 3):
                darkness = int(50 * (1 - y / max(h, 1)))
                col = (max(0, SCALE_DARK[0] - 5) + darkness // 3,
                       max(0, SCALE_DARK[1] - 5),
                       max(0, SCALE_DARK[2] - 5))
                d.rectangle([0, y, self.w, y+2], fill=col)
            # bottom lid bars
            for y in range(self.h - h, self.h, 3):
                darkness = int(50 * ((y - (self.h - h)) / max(h, 1)))
                col = (max(0, SCALE_DARK[0] - 5) + darkness // 3,
                       max(0, SCALE_DARK[1] - 5),
                       max(0, SCALE_DARK[2] - 5))
                d.rectangle([0, y, self.w, y+2], fill=col)

        return img

# ------------- Main Loop -------------
def main():
    print("="*60)
    print("🟢 Reptilian Eye — Enlarged — Pi Zero W + GC9A01")
    print("="*60)

    lcd = GC9A01()
    print("Initializing display...")
    lcd.init()
    print("✓ Display ready.")

    eye = ReptileEye(240, 240)
    print("Rendering creepy eye...\n")

    frame_count = 0
    start_time = time.time()

    try:
        while True:
            eye.update()
            frame = eye.draw()
            lcd.show_numpy(frame)

            frame_count += 1
            if frame_count % 30 == 0:
                fps = frame_count / max(0.001, (time.time() - start_time))
                print(f"FPS ~ {fps:.1f}")

            # Small sleep to avoid pegging 100% CPU
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        lcd.cleanup()
        print("✓ Cleaned up. Bye.")

if __name__ == "__main__":
    main()