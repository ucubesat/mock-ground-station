import board
import busio
import digitalio

import adafruit_rfm9x

import terminalio
from adafruit_display_text import label
from i2cdisplaybus import I2CDisplayBus

import adafruit_displayio_ssd1306

# Adafruit Library Bundle: https://github.com/adafruit/Adafruit_CircuitPython_Bundle
# DisplayIO SSD1306 Library: https://github.com/adafruit/Adafruit_CircuitPython_DisplayIO_SSD1306

# ==== Display setup =====
displayio.release_displays()
oled_reset = board.D9

# Use for I2C
i2c = board.I2C()  # uses board.SCL and board.SDA
display_bus = I2CDisplayBus(i2c, device_address=0x3C, reset=oled_reset)

WIDTH = 128
HEIGHT = 64  # Change to 64 if needed
BORDER = 5

display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

# Make the display context
splash = displayio.Group()
display.root_group = splash

color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF  # White

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

# Draw a smaller inner rectangle
inner_bitmap = displayio.Bitmap(WIDTH - BORDER * 2, HEIGHT - BORDER * 2, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0x000000  # Black
inner_sprite = displayio.TileGrid(
    inner_bitmap, pixel_shader=inner_palette, x=BORDER, y=BORDER
)
splash.append(inner_sprite)

# Draw a label
text = "Hello World!"
text_area = label.Label(
    terminalio.FONT, text=text, color=0xFFFFFF, x=28, y=HEIGHT // 2 - 1
)
splash.append(text_area)

# ===== Radio setup =====
# Define radio parameters.

RADIO_FREQ_MHZ = 915.0  # Frequency of the radio in Mhz. Must match your

# module! Can be a value like 915.0, 433.0, etc.

# Define pins connected to the chip, use these if wiring up the breakout according to the guide:

CS = digitalio.DigitalInOut(board.GP6)
RESET = digitalio.DigitalInOut(board.GP7)

# Initialize SPI bus.

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialze RFM radio

rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
print("Waiting for packets...")
# rember the library can only receive and process 252 bytes at once
while True:
    packet = rfm9x.receive(timeout=5.0)

    # Optionally change the receive timeout from its default of 0.5 seconds:

    # packet = rfm9x.receive(timeout=5.0)

    # If no packet was received during the timeout then None is returned.

    if packet is None:
        print("timed out listening for packet, listening again")

    else:
        # Received a packet!
        # Print out the raw bytes of the packet:

        print(f"Received (raw bytes): {packet}")
        # And decode to ASCII text and print it too.  Note that you always

        # receive raw bytes and need to convert to a text format like ASCII

        # if you intend to do string processing on your data.  Make sure the

        # sending side is sending ASCII data before you try to decode!

        packet_text = str(packet, "ascii")

        print(f"Received (ASCII): {packet_text}")

        # Also read the RSSI (signal strength) of the last received message and

        # print it.

        rssi = rfm9x.last_rssi

        print(f"Received signal strength: {rssi} dB")
