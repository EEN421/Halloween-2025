#!/usr/bin/env python3
import RPi.GPIO as GPIO
import spidev
import time
import numpy as np

DC = 24
RST = 25

class GC9A01:
    def __init__(self):
        self.width = 240
        self.height = 240

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DC, GPIO.OUT)
        GPIO.setup(RST, GPIO.OUT)

        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 60000000

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

        # Full GC9A01 initialization with gamma correction
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
        self.cmd(0x3A, 0x05)
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
        self.cmd(0x62, 0x18, 0x0D, 0x71, 0xED, 0x70, 0x70,
                      0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70)
        self.cmd(0x63, 0x18, 0x11, 0x71, 0xF1, 0x70, 0x70,
                      0x18, 0x13, 0x71, 0xF3, 0x70, 0x70)
        self.cmd(0x64, 0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07)
        self.cmd(0x66, 0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45,
                      0x10, 0x00, 0x00, 0x00)
        self.cmd(0x67, 0x00, 0x3C, 0x00, 0x00, 0x00, 0x01,
                      0x54, 0x10, 0x32, 0x98)
        self.cmd(0x74, 0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00)
        self.cmd(0x98, 0x3E, 0x07)
        self.cmd(0x35)
        self.cmd(0x21)
        self.cmd(0x11)
        time.sleep(0.12)
        self.cmd(0x29)
        time.sleep(0.02)

    def show_numpy(self, image):
        """Fast display using numpy"""
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