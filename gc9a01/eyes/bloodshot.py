#!/usr/bin/env python3
"""
Bloodshot Eye - Red veins, no blinking
"""

import time
import random
import math
from PIL import Image, ImageDraw
from gc9a01_driver import GC9A01

SCLERA_COLOR = (255, 255, 255)
IRIS_COLOR = (100, 200, 255)
PUPIL_COLOR = (20, 20, 40)
VEIN_COLOR = (200, 50, 50)
VEIN_DARK = (150, 30, 30)

class BloodshotEye:
    def __init__(self):
        self.x = self.y = 0.0
        self.tx = self.ty = 0.0
        self.veins = self.generate_veins()

    def generate_veins(self):
        veins = []
        cx, cy = 120, 120

        for i in range(12):
            angle = i * (2 * math.pi / 12) + random.uniform(-0.3, 0.3)

            start_dist = random.randint(55, 70)
            sx = cx + int(start_dist * math.cos(angle))
            sy = cy + int(start_dist * math.sin(angle))

            vein_path = [(sx, sy)]
            current_angle = angle
            current_x, current_y = sx, sy

            for step in range(random.randint(3, 6)):
                current_angle += random.uniform(-0.5, 0.5)
                step_length = random.randint(8, 15)

                current_x += int(step_length * math.cos(current_angle))
                current_y += int(step_length * math.sin(current_angle))

                dist = math.sqrt((current_x - cx)**2 + (current_y - cy)**2)
                if dist < 100:
                    vein_path.append((current_x, current_y))
                else:
                    break

            veins.append(vein_path)

            if len(vein_path) > 2:
                branch_start = vein_path[random.randint(1, len(vein_path)-1)]
                branch_angle = current_angle + random.uniform(-1.0, 1.0)

                branch_path = [branch_start]
                bx, by = branch_start

                for step in range(random.randint(2, 4)):
                    branch_angle += random.uniform(-0.3, 0.3)
                    step_length = random.randint(6, 10)

                    bx += int(step_length * math.cos(branch_angle))
                    by += int(step_length * math.sin(branch_angle))

                    dist = math.sqrt((bx - cx)**2 + (by - cy)**2)
                    if dist < 100:
                        branch_path.append((bx, by))
                    else:
                        break

                if len(branch_path) > 1:
                    veins.append(branch_path)

        return veins

    def update(self):
        self.x += (self.tx - self.x) * 0.6
        self.y += (self.ty - self.y) * 0.6

        if random.random() < 0.02:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, 30)
            self.tx = dist * math.cos(angle)
            self.ty = dist * math.sin(angle)

    def draw(self, draw):
        draw.ellipse([20, 20, 220, 220], fill=SCLERA_COLOR,
                     outline=(200, 200, 200), width=2)

        for vein_path in self.veins:
            if len(vein_path) > 1:
                draw.line(vein_path, fill=VEIN_COLOR, width=2)
                draw.line(vein_path, fill=VEIN_DARK, width=1)

        ix = 120 + int(self.x)
        iy = 120 + int(self.y)

        draw.ellipse([ix-50, iy-50, ix+50, iy+50], fill=IRIS_COLOR)
        draw.ellipse([ix-25, iy-25, ix+25, iy+25], fill=PUPIL_COLOR)
        draw.ellipse([ix-12, iy-28, ix-4, iy-20], fill=(255, 255, 255))

print("👁️ BLOODSHOT EYE 👁️")
print("Initializing...")

lcd = GC9A01()
lcd.init()
print("✓ Display ready!")

eye = BloodshotEye()
print("Bloodshot eye watching...\n")

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
            print(f"{fps:.1f} FPS")

        time.sleep(0.001)

except KeyboardInterrupt:
    print("\n\nShutting down...")
finally:
    lcd.cleanup()
    print("✓ Done!")