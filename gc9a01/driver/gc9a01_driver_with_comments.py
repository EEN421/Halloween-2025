#!/usr/bin/env python3
"""
GC9A01 Display Driver for Raspberry Pi
1.28" Round LCD Display (240x240 pixels)
Communicates via SPI with RGB565 color format
"""

import RPi.GPIO as GPIO  # For controlling GPIO pins (DC and RST)
import spidev            # For SPI communication with the display
import time              # For delays during initialization
import numpy as np       # For fast image processing and RGB565 conversion

# Pin definitions (BCM numbering)
DC = 24   # Data/Command pin - tells display if we're sending a command or data
RST = 25  # Reset pin - used to hardware reset the display

class GC9A01:
    """
    Driver class for GC9A01 round LCD display
    Handles initialization, communication, and image rendering
    """
    
    def __init__(self):
        """
        Initialize GPIO pins and SPI connection
        Sets up the hardware interface to the display
        """
        self.width = 240   # Display width in pixels
        self.height = 240  # Display height in pixels

        # Configure GPIO pins
        GPIO.setmode(GPIO.BCM)      # Use BCM pin numbering (GPIO numbers, not physical pins)
        GPIO.setwarnings(False)     # Disable warnings if pins already in use
        GPIO.setup(DC, GPIO.OUT)    # Set DC pin as output (we control it)
        GPIO.setup(RST, GPIO.OUT)   # Set RST pin as output (we control it)

        # Configure SPI (Serial Peripheral Interface)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # Open SPI bus 0, device (CS) 0
        # Set SPI clock speed to 60MHz for fast data transfer
        # This determines how quickly we can push pixels to the display
        self.spi.max_speed_hz = 60000000

    def cmd(self, c, *data):
        """
        Send a command to the display, optionally followed by data bytes
        
        Args:
            c: Command byte (e.g., 0x11 for sleep out)
            *data: Optional data bytes to send after the command
        
        How it works:
        - DC pin LOW = sending a command
        - DC pin HIGH = sending data
        This is how the display knows whether we're telling it WHAT to do (command)
        or WHAT to display/configure (data)
        """
        GPIO.output(DC, GPIO.LOW)   # Pull DC LOW to indicate command mode
        self.spi.writebytes([c])    # Send the command byte via SPI
        
        if data:  # If there are data bytes to send
            GPIO.output(DC, GPIO.HIGH)      # Pull DC HIGH to indicate data mode
            self.spi.writebytes(list(data)) # Send the data bytes

    def reset(self):
        """
        Perform hardware reset of the display
        
        The reset sequence:
        1. Pull RST LOW for 100ms (puts display in reset state)
        2. Pull RST HIGH (releases reset)
        3. Wait 120ms for display to fully initialize
        
        This is like pressing the reset button - clears all settings
        """
        GPIO.output(RST, GPIO.LOW)   # Assert reset (active low)
        time.sleep(0.1)              # Hold reset for 100ms
        GPIO.output(RST, GPIO.HIGH)  # Release reset
        time.sleep(0.12)             # Wait for display to boot up

    def init(self):
        """
        Initialize the GC9A01 display with full configuration
        
        This method sends dozens of commands to configure:
        - Power settings
        - Display orientation
        - Color format (RGB565)
        - Gamma correction (for accurate colors)
        - Timing parameters
        
        The GC9A01 has many internal registers that control how it displays images.
        These commands set up optimal settings for our use case.
        """
        self.reset()  # Start with a clean slate

        # === Inter Register Enable Commands ===
        # These unlock hidden/advanced registers for configuration
        self.cmd(0xEF)           # Inter register enable 1
        self.cmd(0xEB, 0x14)     # Inter register enable 2

        self.cmd(0xFE)           # Inter register enable 1 (again)
        self.cmd(0xEF)           # Inter register enable 1 (again)
        
        self.cmd(0xEB, 0x14)     # Inter register enable 2 (again)
        
        # === Power Control Registers ===
        # These control voltage levels and power management
        self.cmd(0x84, 0x40)     # Power control 1
        self.cmd(0x85, 0xFF)     # Power control 2
        self.cmd(0x86, 0xFF)     # Power control 3
        self.cmd(0x87, 0xFF)     # Power control 4
        self.cmd(0x88, 0x0A)     # Power control 5
        self.cmd(0x89, 0x21)     # Power control 6
        self.cmd(0x8A, 0x00)     # Power control 7
        self.cmd(0x8B, 0x80)     # Power control 8
        self.cmd(0x8C, 0x01)     # Power control 9
        self.cmd(0x8D, 0x01)     # Power control 10
        self.cmd(0x8E, 0xFF)     # Power control 11
        self.cmd(0x8F, 0xFF)     # Power control 12
        
        # === Display Function Control ===
        # 0xB6: Controls display scanning direction and timing
        # Parameters: [0x00, 0x20] sets normal scan direction
        self.cmd(0xB6, 0x00, 0x20)
        
        # === Memory Access Control (MADCTL) ===
        # 0x36: Controls how memory is written (orientation, color order)
        # 0x48 means:
        #   - RGB color order (not BGR)
        #   - Normal horizontal and vertical refresh
        #   - Row/column address order for proper orientation
        self.cmd(0x36, 0x48)
        
        # === Pixel Format ===
        # 0x3A: Sets the color format for RGB interface
        # 0x05 = 16-bit RGB565 format
        #   - 5 bits red, 6 bits green, 5 bits blue
        #   - Total: 16 bits (2 bytes) per pixel
        #   - 65,536 possible colors
        self.cmd(0x3A, 0x05)
        
        # === Frame Rate Control ===
        # Controls how fast the display refreshes
        self.cmd(0x90, 0x08, 0x08, 0x08, 0x08)
        
        # === Display Inversion Control ===
        self.cmd(0xBD, 0x06)     # Display inversion control
        self.cmd(0xBC, 0x00)     # Display inversion control 2
        
        # === More Power/Voltage Settings ===
        self.cmd(0xFF, 0x60, 0x01, 0x04)  # Vreg1a/Vreg1b voltage
        self.cmd(0xC3, 0x13)               # Vreg1a voltage
        self.cmd(0xC4, 0x13)               # Vreg1b voltage
        self.cmd(0xC9, 0x22)               # Vreg2a voltage
        
        self.cmd(0xBE, 0x11)     # Frame rate control in normal mode
        
        self.cmd(0xE1, 0x10, 0x0E)  # Set equalize time
        
        self.cmd(0xDF, 0x21, 0x0C, 0x02)  # Set gate timing
        
        # === GAMMA CORRECTION ===
        # Gamma correction ensures colors look natural and accurate
        # Without it, colors would look washed out or incorrect
        # These are carefully tuned values for the GC9A01
        
        # Positive Voltage Gamma Control
        # Controls how colors appear in bright areas
        self.cmd(0xF0, 0x45, 0x09, 0x08, 0x08, 0x26, 0x2A)
        
        # Negative Voltage Gamma Control  
        # Controls how colors appear in dark areas
        self.cmd(0xF1, 0x43, 0x70, 0x72, 0x36, 0x37, 0x6F)
        
        # Positive Voltage Gamma Control (second set)
        self.cmd(0xF2, 0x45, 0x09, 0x08, 0x08, 0x26, 0x2A)
        
        # Negative Voltage Gamma Control (second set)
        self.cmd(0xF3, 0x43, 0x70, 0x72, 0x36, 0x37, 0x6F)
        
        # === Additional Display Settings ===
        self.cmd(0xED, 0x1B, 0x0B)  # Power control
        self.cmd(0xAE, 0x77)        # Unknown register
        self.cmd(0xCD, 0x63)        # Unknown register
        
        # Digital Gamma Control - fine-tunes gamma curves
        self.cmd(0x70, 0x07, 0x07, 0x04, 0x0E, 0x0F, 0x09, 0x07, 0x08, 0x03)
        
        self.cmd(0xE8, 0x34)  # Frame rate control
        
        # === Gate Control ===
        # These registers control the gate driver (row scanning)
        self.cmd(0x62, 0x18, 0x0D, 0x71, 0xED, 0x70, 0x70,
                      0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70)
        
        self.cmd(0x63, 0x18, 0x11, 0x71, 0xF1, 0x70, 0x70,
                      0x18, 0x13, 0x71, 0xF3, 0x70, 0x70)
        
        self.cmd(0x64, 0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07)
        
        # === Source Control ===
        # These control the source driver (column scanning)
        self.cmd(0x66, 0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45,
                      0x10, 0x00, 0x00, 0x00)
        
        self.cmd(0x67, 0x00, 0x3C, 0x00, 0x00, 0x00, 0x01,
                      0x54, 0x10, 0x32, 0x98)
        
        self.cmd(0x74, 0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00)
        
        self.cmd(0x98, 0x3E, 0x07)  # Unknown register
        
        # === Tearing Effect Line ===
        # 0x35: Enable tearing effect signal
        # Helps synchronize with the display refresh to prevent tearing
        self.cmd(0x35)
        
        # === Display Inversion ===
        # 0x21: Turn ON display inversion
        # Some GC9A01 displays need this for correct colors
        # If colors look wrong, try 0x20 (inversion OFF) instead
        self.cmd(0x21)
        
        # === Sleep Out ===
        # 0x11: Exit sleep mode
        # The display starts in sleep mode after reset
        # This wakes it up so it can display images
        self.cmd(0x11)
        time.sleep(0.12)  # Wait 120ms for display to wake up (required by datasheet)
        
        # === Display ON ===
        # 0x29: Turn on the display
        # After this command, the display will show whatever is in its memory
        self.cmd(0x29)
        time.sleep(0.02)  # Brief delay to ensure display is fully on

    def show_numpy(self, image):
        """
        Display a PIL Image on the screen using optimized numpy conversion
        
        This is the fastest way to send images to the display.
        
        Process:
        1. Convert PIL image to numpy array
        2. Extract R, G, B channels
        3. Convert RGB888 (24-bit) to RGB565 (16-bit)
        4. Pack into byte array
        5. Send to display via SPI
        
        Args:
            image: PIL Image object (240x240 pixels)
        """
        # Convert PIL image to numpy array
        # This gives us a 3D array: [height, width, 3]
        # where the 3 channels are R, G, B values (0-255 each)
        img_array = np.array(image.convert('RGB'))

        # Extract individual color channels and convert to 16-bit for math
        r = img_array[:, :, 0].astype(np.uint16)  # Red channel
        g = img_array[:, :, 1].astype(np.uint16)  # Green channel
        b = img_array[:, :, 2].astype(np.uint16)  # Blue channel

        # === RGB565 CONVERSION ===
        # RGB888 (24-bit): 8 bits per channel = 16.7 million colors
        # RGB565 (16-bit): 5 red, 6 green, 5 blue = 65,536 colors
        # 
        # Why 6 bits for green? Human eyes are most sensitive to green!
        #
        # Conversion formula:
        # - Red:   Take top 5 bits (& 0xF8), shift left 8 positions
        # - Green: Take top 6 bits (& 0xFC), shift left 3 positions  
        # - Blue:  Take top 5 bits (>> 3), no shift needed
        #
        # Example: RGB(255, 128, 64) becomes:
        # Red:   11111000 << 8  = 1111100000000000
        # Green: 10000000 << 3  = 0000001000000000
        # Blue:  01000000 >> 3  = 0000000000001000
        # Result: 1111101000001000 (0xFA08)
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

        # Split 16-bit values into high and low bytes
        # SPI sends 8 bits at a time, so we need to split each pixel
        # into 2 bytes: high byte first, then low byte
        high = (rgb565 >> 8).astype(np.uint8)   # Top 8 bits
        low = (rgb565 & 0xFF).astype(np.uint8)  # Bottom 8 bits

        # Interleave high and low bytes
        # Display expects: [high1, low1, high2, low2, high3, low3, ...]
        # We create a 3D array: [height, width, 2] where 2 = [high, low]
        buf = np.empty((self.height, self.width, 2), dtype=np.uint8)
        buf[:, :, 0] = high  # First byte of each pixel
        buf[:, :, 1] = low   # Second byte of each pixel

        # Flatten to 1D array for SPI transmission
        # Converts [240, 240, 2] array into [115,200] byte array
        # (240 * 240 pixels * 2 bytes per pixel = 115,200 bytes)
        data = buf.flatten().tolist()

        # === SET DRAWING WINDOW ===
        # Tell the display which area of the screen to update
        # We're updating the entire screen (0,0 to 239,239)
        
        # 0x2A: Column Address Set
        # Parameters: [start_high, start_low, end_high, end_low]
        # We're setting columns 0 to 239 (0x00EF)
        self.cmd(0x2A, 0, 0, 0, 239)
        
        # 0x2B: Row Address Set  
        # Parameters: [start_high, start_low, end_high, end_low]
        # We're setting rows 0 to 239 (0x00EF)
        self.cmd(0x2B, 0, 0, 0, 239)
        
        # 0x2C: Memory Write
        # After this command, all following data goes to display memory
        self.cmd(0x2C)

        # === SEND PIXEL DATA ===
        # Switch DC pin HIGH to send data (not commands)
        GPIO.output(DC, GPIO.HIGH)

        # Send data in 4KB chunks for efficiency
        # Sending all 115,200 bytes at once could cause issues
        # Chunking reduces memory usage and improves reliability
        chunk_size = 4096  # 4KB chunks
        for i in range(0, len(data), chunk_size):
            # Send one chunk at a time
            self.spi.writebytes(data[i:i+chunk_size])

    def cleanup(self):
        """
        Clean up GPIO and SPI resources
        
        IMPORTANT: Always call this when you're done!
        Releases the SPI bus and resets GPIO pins
        Failure to call this can cause issues with other programs
        """
        self.spi.close()    # Close SPI connection
        GPIO.cleanup()      # Reset all GPIO pins to default state
