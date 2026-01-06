import board
import busio
import digitalio
import displayio
import struct
from i2cdisplaybus import I2CDisplayBus
import adafruit_displayio_ssd1306
import binascii
import usb_cdc

from pysquared.hardware.radio.packetizer.packet_manager import PacketManager
from lib.pysquared.hardware.radio.manager.rfm9x import RFM9xManager
from lib.pysquared.logger import Logger, LogLevel
from lib.pysquared.config.config import Config
from lib.pysquared.hardware.digitalio import initialize_pin
from lib.pysquared.nvm.counter import Counter
from lib.proveskit_rp2040_v4.register import Register

# Adafruit Library Bundle: https://github.com/adafruit/Adafruit_CircuitPython_Bundle
# DisplayIO SSD1306 Library: https://github.com/adafruit/Adafruit_CircuitPython_DisplayIO_SSD1306

# ==== Display setup =====
displayio.release_displays()

# Use for I2C
i2c = busio.I2C(board.GP9, board.GP8)
display_bus = I2CDisplayBus(i2c, device_address=0x3C)

WIDTH = 128
HEIGHT = 64
BORDER = 5

# Image chunk data type indicators
INDICATE_START = 0x01
INDICATE_DATA = 0x02
INDICATE_END = 0x03

# usb_cdc terminator
USB_TERMINATOR = b"\r\n"

display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

# RADIO_FREQ_MHZ = 915.0
# CS = digitalio.DigitalInOut(board.GP6)
# RESET = digitalio.DigitalInOut(board.GP7)

# Initialize SPI bus.
spi = busio.SPI(board.GP2, MOSI=board.GP3, MISO=board.GP4)

# Initialze RFM radio

# rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
# rfm9x.spreading_factor = 8
# rfm9x.ack_delay = 0.2
# rfm9x.enable_crc = True

# if rfm9x.spreading_factor > 9:
#     rfm9x.preamble_length = 8


error_count: Counter = Counter(index=Register.error_count)
logger: Logger = Logger(error_counter=error_count, log_level=LogLevel.DEBUG)
config: Config = Config("config.json")

radio = RFM9xManager(
    logger,
    config.radio,
    spi,
    initialize_pin(logger, board.GP6, digitalio.Direction.OUTPUT, True),
    initialize_pin(logger, board.GP7, digitalio.Direction.OUTPUT, True),
)

packet_manager = PacketManager(
    logger,
    radio,
    config.radio.license,
    Counter(Register.message_count),
    0.2,
)

serial = usb_cdc.data


def receive_and_verify_image(packet_manager: PacketManager) -> bool:
    start_packet = struct.unpack("<BII", packet_manager.listen(timeout=1.0))

    if start_packet[0] == INDICATE_START:
        total_chunks = start_packet[1]
        file_crc = start_packet[2]
        received_total_crc = 0
        print(
            f"start_packet was INDICATE_START with {total_chunks} chunks and crc of {file_crc}"
        )

        serial.write(start_packet + USB_TERMINATOR)

        for i in range(total_chunks):
            print("listening for next chunk")
            packed_chunk = packet_manager.listen(timeout=30.0)
            print(f"got chunk with size {len(packed_chunk)}")

            serial.write(packed_chunk + USB_TERMINATOR)

            HEADER_FMT = "<BII"
            HEADER_SIZE = struct.calcsize(HEADER_FMT)

            indicator, crc32, chunk_index = struct.unpack(
                HEADER_FMT, packed_chunk[:HEADER_SIZE]
            )

            chunk = packed_chunk[HEADER_SIZE:]
            received_total_crc = binascii.crc32(chunk, received_total_crc)

            if indicator != INDICATE_DATA:
                print(
                    f"data packet type indicator byte was not data, was instead {indicator}"
                )
            elif indicator == INDICATE_END:
                print("data packet type indicator byte is end")

            if binascii.crc32(chunk) != crc32:
                print("chunk crc does not match")

            if i != chunk_index:
                print(f"loop index ({i}) is not chunk index ({chunk_index})")

        end_packet = struct.unpack("<B", packet_manager.listen(timeout=1.0))
        if end_packet[0] != INDICATE_END:
            print("last data packet was not end packet")
        else:
            serial.write(end_packet + USB_TERMINATOR)

        return file_crc == received_total_crc
    else:
        print(
            f"initial image packet type indicator byte was not start, was instead {start_packet[0]}"
        )
        return False


tries = 0
received_images = 0
bad_images = 0

print("Waiting for packets...")
while True:
    packet = packet_manager.listen(timeout=5.0)

    if packet is None:
        print(
            "tries="
            + str(tries)
            + "\nimages_recv="
            + str(received_images)
            + "\nimages_fail="
            + str(bad_images)
        )
        tries += 1
    else:
        try:
            packet_text = packet.decode("utf-8")

            if packet_text == "fmstl":
                print("got an image packet indicator")
                if receive_and_verify_image(packet_manager):
                    print("succesfully received and verified an file!")
                    received_images += 1
                else:
                    print("failed to receive and or verify image.")
                    bad_images += 1

        except UnicodeError as e:
            print(
                f"could not decode unicode. raw packet: {str(packet)}\nerror: {e}\nmost likely this is an beacon or something similar!"
            )
