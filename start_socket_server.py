from datetime import datetime
import device_handler
import sys
import signal
import socketserver
import logging
import time
import re
import threading

dt = datetime.now()
curr_time = dt.strftime('%d-%m-%Y-%H:%M:%S')

logging.basicConfig(format="%(asctime)s.%(msecs)03d %(levelname)s - %(message)s",
                    datefmt="%d-%b-%y %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SERVER = "localhost"  # Local server address
UDP_PORT = 5001             # Server port number
UDP_ADDR = (SERVER, UDP_PORT)

DEVICE_INDEX = 1
DEVICE_INSTALL_POSITION = "UP"
FORMAT = 'ascii'

curr_device_hangle = 0  # Starting point from 0 angle
curr_device_vangle = 0  # Starting point from 0 angle

msg_wait_in_seconds = 1      # Configure how many seconds to wait between sending TCP messages to device
receive_wait_in_seconds = 2  # Configure how many seconds to wait before receiving new UDP message

device_instance = None
pwm_msg = None


class ThreadedUDPRequestHandler(socketserver.BaseRequestHandler):
    """This class is a handler for oncoming UDP messages"""
    def handle(self, *args):
        global pwm_msg
        # Receive a message from a client
        data = self.request[0].strip()
        pwm_msg = data


class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    pass


def handle_message(msg):
    """Start a new thread to process the request."""
    global curr_device_hangle, curr_device_vangle
    try:
        if msg[0] == "UDP":
            if "TLT" in msg[1].decode(FORMAT):
                logger.info(msg[1].decode(FORMAT))

                # Return messages in a list [Horizontal, Vertical]
                command_msg = device_handler.convert_msg(msg, curr_device_hangle, curr_device_vangle)
                stop_message = device_handler.parse_command_message("stop")

                if isinstance(command_msg, list):
                    if command_msg[0]:
                        device_instance.send_tcp_message(command_msg[0])
                        time.sleep(msg_wait_in_seconds)
                        device_instance.send_tcp_message(stop_message)
                        time.sleep(msg_wait_in_seconds)
                    if command_msg[1]:
                        device_instance.send_tcp_message(command_msg[1])
                        time.sleep(msg_wait_in_seconds)
                        device_instance.send_tcp_message(stop_message)
                        time.sleep(msg_wait_in_seconds)
                    if any(command_msg):
                        response = device_instance.query_status()
                        if response:
                            if "Vangle" in response:
                                response_angles = re.findall(r'Vangle:(.*)', response)[0].replace("Hangle", "").split(":")
                                if "W" in response_angles[1]:
                                    response_angles[1] = response_angles[1].split("W", 1)[0]
                                curr_device_vangle, curr_device_hangle = float(response_angles[0]), float(response_angles[1])
                                logger.info(f"Current Hangle: {curr_device_hangle}, Vangle: {curr_device_vangle}")
                        else:
                            logger.info("Couldn't query status from device")
    except Exception as e:
        print(e)


def signal_handler(signum, frame):
    stop_server()


def stop_server(signal=None, frame=None):
    try:
        logger.info(f"[STOPPING] Server is shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.info(e)


def set_exit_signals() -> None:
    signal.signal(signal.SIGTERM, stop_server)
    signal.signal(signal.SIGABRT, stop_server)
    signal.signal(signal.SIGINT, stop_server)


def start_server():
    global device_instance
    logger.info("[STARTING] Server is starting...")
    signal.signal(signal.SIGINT, signal_handler)
    device_instance = device_handler.DeviceHandler()
    device_handler.device_install_position = DEVICE_INSTALL_POSITION
    device_instance.setup_device_to_zero_angle()

    try:
        with socketserver.ThreadingUDPServer(UDP_ADDR, ThreadedUDPRequestHandler) as udp_server:
            udp_server.allow_reuse_address = True
            udp_thread = threading.Thread(target=udp_server.serve_forever)
            udp_thread.daemon = True
            udp_thread.start()
            logger.info(f'[STATUS] UDP serving at {SERVER}:{UDP_PORT}')
            while True:
                if pwm_msg:
                    handle_message(("UDP", pwm_msg))
                    time.sleep(receive_wait_in_seconds)
    except Exception as e:
        raise e


if __name__ == "__main__":
    try:
        start_server()
    except Exception as e:
        logger.info(e)
        stop_server()


