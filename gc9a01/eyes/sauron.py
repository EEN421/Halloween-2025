#!/usr/bin/env python3
"""
Eye of Sauron / Fiery Dragon Eye
Menacing textured eye with flames
"""

import RPi.GPIO as GPIO
import spidev
import time
import random
import math
import numpy as np
from PIL import Image, ImageDraw

DC = 24
RST = 25

# Fiery evil colors
BACKGROUND_COLOR = (20, 10, 5)          # Very dark
SCLERA_BASE = (60, 30, 10)              # Dark burnt
FLAME_INNER = (255, 255, 100)           # Bright yellow-orange
FLAME_MID = (255, 100, 20)              # Orange
FLAME_OUTER = (200, 40, 10)             # Dark red
IRIS_COLOR = (255, 80, 0)               # Bright orange
IRIS_INNER = (255, 220, 100)            # Yellow hot center
PUPIL_COLOR = (5, 5, 5)                 # Almost black
EYELID_COLOR = (40, 20, 10)             # Dark burnt skin

class GC9A01:
    def __init__(self):
        self.width = 240
        self.height = 240

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DC, GPIO.OUT)
        GPIO.setup(RST, GPIO.OUT)

        self.spi = spidev.SpiDev()
        # Try CE0 first, then CE1 (some GC9A01 breakouts wire CS to CE1)
        opened = False
        for dev in (0, 1):
            try:
                self.spi.open(0, dev)
                opened = True
                break
            except FileNotFoundError:
                continue
        if not opened:
            raise RuntimeError("SPI device not found. Enable SPI and check wiring (CE0/CE1).")

        # Pi Zero 2 is usually stable at 48–60 MHz for GC9A01
        self.spi.max_speed_hz = 48_000_000
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

        # GC9A01 init sequence
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
        self.cmd(0x3A, 0x05)            # 16-bit color (RGB565)
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
        self.cmd(0x35)                  # TE on
        self.cmd(0x21)                  # Inversion on
        self.cmd(0x11)                  # Sleep out
        time.sleep(0.12)
        self.cmd(0x29)                  # Display on
        time.sleep(0.02)

    def show_numpy(self, image):
        img_array = np.array(image.convert('RGB'))

        r = img_array[:, :, 0].astype(np.uint16)
        g = img_array[:, :, 1].astype(np.uint16)
        b = img_array[:, :, 2].astype(np.uint16)

        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

        high = (rgb565 >> 8).astype(np.uint8)
        low = (rgb565 & 0xFF).astype(np.uint8)

        buf = np.empty((self.height, self.width, 2), dtype=np.uint8)
        buf[:, :, 0] = high
        buf[:, :, 1] = low
        data = buf.flatten().tolist()

        # Full-window write
        self.cmd(0x2A, 0, 0, 0, 239)
        self.cmd(0x2B, 0, 0, 0, 239)
        self.cmd(0x2C)

        GPIO.output(DC, GPIO.HIGH)

        chunk_size = 4096
        for i in range(0, len(data), chunk_size):
            self.spi.writebytes(data[i:i+chunk_size])

    def cleanup(self):
        self.spi.close()
        GPIO.cleanup()

class SauronEye:
    def __init__(self):
        self.x = self.y = 0.0
        self.tx = self.ty = 0.0
        self.blink_state = 0
        self.blink = 0.0
        self.pupil_width = 14  # wider center by default for Zero 2 display
        self.flame_offset = 0  # For animated flames

    def update(self):
        self.x += (self.tx - self.x) * 0.4
        self.y += (self.ty - self.y) * 0.4

        # Animate flames
        self.flame_offset += 0.05

        if random.random() < 0.01:  # Very rare movement
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, 20)
            self.tx = dist * math.cos(angle)
            self.ty = dist * math.sin(angle)

        if random.random() < 0.003 and self.blink_state == 0:  # Rare blink
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

    def draw(self, draw):
        cx, cy = 120, 120

        # Dark background
        draw.rectangle([0, 0, 240, 240], fill=BACKGROUND_COLOR)

        # Draw fiery texture radiating from center
        for i in range(24):  # 24 flame rays
            angle = i * (2 * math.pi / 24) + self.flame_offset
            for seg in range(8):
                dist_start = 40 + seg * 15
                dist_end = 40 + (seg + 1) * 15

                if seg < 2:
                    color = FLAME_INNER
                elif seg < 4:
                    color = FLAME_MID
                else:
                    color = FLAME_OUTER

                dist_end += random.randint(-3, 3)
                width = 8 - seg

                x1 = cx + int(dist_start * math.cos(angle))
                y1 = cy + int(dist_start * math.sin(angle))
                x2 = cx + int(dist_end * math.cos(angle))
                y2 = cy + int(dist_end * math.sin(angle))

                draw.line([x1, y1, x2, y2], fill=color, width=width)

        # Eye position with offset
        ix = cx + int(self.x)
        iy = cy + int(self.y)

        # Outer iris ring (glowing)
        draw.ellipse([ix-60, iy-60, ix+60, iy+60], fill=FLAME_OUTER)
        draw.ellipse([ix-55, iy-55, ix+55, iy+55], fill=FLAME_MID)
        draw.ellipse([ix-50, iy-50, ix+50, iy+50], fill=IRIS_COLOR)

        # Hot inner iris
        draw.ellipse([ix-40, iy-40, ix+40, iy+40], fill=IRIS_INNER)

        # Radial texture in iris
        for i in range(16):
            angle = i * (2 * math.pi / 16)
            x1 = ix + int(15 * math.cos(angle))
            y1 = iy + int(15 * math.sin(angle))
            x2 = ix + int(45 * math.cos(angle))
            y2 = iy + int(45 * math.sin(angle))
            draw.line([x1, y1, x2, y2], fill=FLAME_OUTER, width=2)

        # ===== TAPERED (CAT-EYE) PUPIL =====
        slit_height = 90
        max_width = self.pupil_width  # width at the center
        power = 1.8                    # higher = sharper tips

        half_h = slit_height // 2
        for dy in range(-half_h, half_h + 1):
            t = abs(dy) / half_h if half_h else 1.0
            # Smooth width curve: center=wide, ends=point
            width_f = max_width * (1.0 - (t ** power))
            w = int(round(width_f))
            if w > 0:
                y = iy + dy
                draw.line([ix - w // 2, y, ix + w // 2, y], fill=PUPIL_COLOR)

        # Soft glow highlight (keeps your original vibe)
        draw.ellipse([ix - 12, iy - 48, ix + 12, iy - 32],
                     fill=(255, 255, 150), outline=None)

        # Dark burnt eyelids (blink)
        if self.blink > 0:
            h = int(120 * self.blink)
            for y in range(0, h, 4):
                darkness = int(40 * (1 - y / max(h, 1)))
                color = (darkness, darkness//2, darkness//4)
                draw.rectangle([0, y, 240, y+3], fill=color)
            for y in range(240-h, 240, 4):
                darkness = int(40 * ((y-(240-h))/max(h, 1)))
                color = (darkness, darkness//2, darkness//4)
                draw.rectangle([0, y, 240, y+3], fill=color)

print("="*60)
print("🔥 EYE OF SAURON 🔥")
print("The Great Eye is watching...")
print("="*60)

print("\nInitializing...")
lcd = GC9A01()
lcd.init()
print("✓ Display ready!")

eye = SauronEye()
print("The Eye sees all... 👁️‍🗨️\n")

frame_count = 0
start_time = time.time()

try:
    while True:
        img = Image.new('RGB', (240, 240), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        eye.update()
        eye.draw(draw)

        lcd.show_numpy(img)

        frame_count += 1
        if frame_count % 30 == 0:
            fps = frame_count / (time.time() - start_time)
            print(f"🔥 Running at {fps:.1f} FPS - The Eye burns...")

        time.sleep(0.001)

except KeyboardInterrupt:
    print("\n\nThe Eye closes...")
finally:
    lcd.cleanup()
    print("✓ Darkness falls.")
