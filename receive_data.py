from adafruit_board_toolkit import circuitpython_serial as cps
import serial
import struct
import zlib
import os
import time

from dataclasses import dataclass


@dataclass
class StationStats:
    recv_images: int = 0
    failed_images: int = 0
    recv_bytes_total: int = 0
    recv_time: int = 0
    recent_image_path: str = ""
    recent_image_size: int = 0

    currently_receiving: bool = False
    recv_bytes: int = 0
    total_chunks: int = 0
    current_chunk: int = 0
    file_crc: int = 0
    received_total_crc: int = 0


# pretty colors
class Color:
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"


def get_incrementing_image_path():
    i = 0
    file_path = f"recv_image_{i}.jpg"

    while os.path.exists(file_path):
        i += 1
        file_path = f"recv_image_{i}.jpg"

    return file_path


def clear_console():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def pretty_station_stats(stats: StationStats):
    clear_console()
    print("================= Received Images =================")
    print(
        f"Succesfully received: {Color.GREEN}{stats.recv_images}{Color.RESET}\tFailed: {Color.RED}{stats.failed_images}{Color.RESET}\tRX Total: {Color.BLUE}{stats.recv_bytes_total}{Color.RESET}"
    )

    print("\n================== Current Image ==================")
    print(
        f"In progress: {Color.YELLOW if stats.currently_receiving == stats.received_total_crc else Color.RED}{stats.currently_receiving}{Color.RESET}\tRX Bytes: {Color.BLUE}{stats.recv_bytes}{Color.RESET}"
    )
    print(
        f"Total chunks: {Color.GREEN}{stats.total_chunks}{Color.RESET}\t\tCurrent chunk: {Color.YELLOW}{stats.current_chunk}{Color.RESET}"
    )
    print(
        f"Expected CRC: {Color.GREEN}{stats.file_crc}{Color.RESET}\tCurrent CRC: {Color.GREEN if stats.file_crc == stats.received_total_crc else Color.YELLOW}{stats.received_total_crc}{Color.RESET}"
    )

    print("\n================ Most Recent Image ================")
    print(
        f"File path: {Color.GREEN}{stats.recent_image_path}{Color.RESET}\tSize: {Color.BLUE}{stats.recent_image_size}{Color.RESET}"
    )

    if stats.recv_time != 0:
        print(
            f"Download speed: {Color.BLUE}{int(stats.recv_bytes_total / stats.recv_time)}{Color.RESET} B/s"
        )


stats = StationStats()

USB_TERMINATOR = b"\r\n"
START_OR_DATA_HEADER = "<BII"
END_HEADER = "<B"

# Image chunk data type indicators
INDICATE_START = 0x01
INDICATE_DATA = 0x02
INDICATE_END = 0x03

serial_port = cps.data_comports()[0]

if not serial:
    raise Exception("No CircuitPython boards found")

ser = serial.Serial(serial_port.device)

print(f"Listening on {ser.name}")

while True:
    received_bytes = ser.read_until(expected=USB_TERMINATOR)

    if received_bytes:
        received_bytes = received_bytes.rstrip(USB_TERMINATOR)

        START_OR_DATA_HEADER_SIZE = struct.calcsize(START_OR_DATA_HEADER)
        if len(received_bytes) == START_OR_DATA_HEADER_SIZE:
            packed_data = struct.unpack(START_OR_DATA_HEADER, received_bytes)

            stats.recv_bytes_total += len(received_bytes)

            if packed_data[0] == INDICATE_START:
                stats.total_chunks = packed_data[1]
                stats.file_crc = packed_data[2]
                stats.received_total_crc = 0
                stats.recv_bytes = 0
                stats.currently_receiving = True
                print(
                    f"start_packet was INDICATE_START with {stats.total_chunks} chunks and crc of {stats.file_crc}"
                )

                img_file_path = get_incrementing_image_path()
                img_file = open(img_file_path, "w")

                start = time.time()

                for i in range(stats.total_chunks):
                    packed_chunk = ser.read_until(expected=USB_TERMINATOR).rstrip(
                        USB_TERMINATOR
                    )

                    stats.recv_bytes_total += len(packed_chunk)
                    stats.recv_bytes += len(packed_chunk)

                    indicator, crc32, stats.current_chunk = struct.unpack(
                        START_OR_DATA_HEADER_SIZE,
                        packed_chunk[:START_OR_DATA_HEADER_SIZE],
                    )

                    chunk = packed_chunk[START_OR_DATA_HEADER_SIZE:]
                    stats.received_total_crc = zlib.crc32(
                        chunk, stats.received_total_crc
                    )

                    if indicator != INDICATE_DATA:
                        print(
                            f"data packet type indicator byte was not data, was instead {indicator}"
                        )
                        stats.failed_images += 1
                        break

                    if zlib.crc32(chunk) != crc32:
                        print("chunk crc does not match")
                        stats.failed_images += 1
                        break

                    if i != stats.current_chunk:
                        print(
                            f"loop index ({i}) is not chunk index ({stats.current_chunk})"
                        )
                        stats.failed_images += 1
                        break

                    img_file.write(chunk)

                    pretty_station_stats(stats)

                end = time.time()

                stats.recv_images += 1
                stats.recent_image_path = img_file_path.replace(os.getcwd(), "")
                stats.recent_image_size = os.path.getsize(img_file_path)
                stats.recv_time = start - end

                stats.currently_receiving = False
                stats.current_chunk = 0
                stats.total_chunks = 0

                pretty_station_stats(stats)
