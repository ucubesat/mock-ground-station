import board
import busio
import digitalio
import adafruit_rfm9x
import displayio
from i2cdisplaybus import I2CDisplayBus
import adafruit_displayio_ssd1306

# Adafruit Library Bundle: https://github.com/adafruit/Adafruit_CircuitPython_Bundle
# DisplayIO SSD1306 Library: https://github.com/adafruit/Adafruit_CircuitPython_DisplayIO_SSD1306

# ==== Display setup =====
displayio.release_displays()

# Use for I2C
i2c = busio.I2C(board.GP9, board.GP8)
display_bus = I2CDisplayBus(i2c, device_address=0x3C)

WIDTH = 128
HEIGHT = 64  # Change to 64 if needed
BORDER = 5

display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

RADIO_FREQ_MHZ = 915.0
CS = digitalio.DigitalInOut(board.GP6)
RESET = digitalio.DigitalInOut(board.GP7)

# Initialize SPI bus.
spi = busio.SPI(board.GP2, MOSI=board.GP3, MISO=board.GP4)

# Initialze RFM radio
tries = 0
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
print("Waiting for packets...")
# rember the library can only receive and process 252 bytes at once
while True:
    packet = rfm9x.receive(timeout=5.0)

    if packet is None:
        print("\n(tries=" + str(tries) + ") Reached timeout, listening again...")
        tries += 1
    else:
        # print(f"Received (raw bytes): {packet}")

        packet_text = packet.decode("utf-8")
        rssi = rfm9x.last_rssi
        print(f"Received (ASCII): {packet_text} with signal strength: {rssi} dB")
        tries = 0
