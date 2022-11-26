from start_socket_server import DEVICE_INDEX, FORMAT
from dataclasses import dataclass
import logging
import socket
import time

logger = logging.getLogger(__name__)

# Set up pwm servo and device angles here (MAX - MIN)
pwm_servo_range_azimuth = (1700 - 1300)
pwm_servo_range_elevation = (1700 - 1500)
device_range_azimuth = (45.0 - -45.0)
device_range_elevation = (30.0 - 0.0)

received_udp_msgs = []
device_install_position = None
device_to_zero_angle = False
angle_threshold = 5


@dataclass
class DeviceHandler:
    """
    Handler for Device control
    """
    device_ip_addr = "127.0.0.1"
    device_port = 6000

    def query_status(self):
        try:
            msg = parse_command_message("get_status")
            response = self.send_tcp_message_and_receive_response(msg)
            if response:
                logger.info(f"Response from device: {response}")
            return response
        except Exception as e:
            logger.error(f"Error while querying device position: {e}")

    def setup_device_to_zero_angle(self):
        global device_to_zero_angle
        device_to_zero_angle = True
        msg = parse_command_message("automatic", 0, 0)
        device_to_zero_angle = False
        self.send_tcp_message(msg)
        logger.info("Setting device to zero angle...")
        time_in_seconds = 10
        for i in range(time_in_seconds):
            print(f"Please wait for socket to be ready {i+1}/{time_in_seconds}")
            time.sleep(1)
        logger.info("Device ready!")

    def send_tcp_message(self, msg: str):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.connect((self.device_ip_addr, self.device_port))
                s.sendall(bytes(msg, FORMAT))
            except socket.error as e:
                logger.error(f"Problem with connection to Device: {e}")
                raise

    def send_tcp_message_and_receive_response(self, msg: str) -> str:
        data = None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.connect((self.device_ip_addr, self.device_port))
                s.sendall(bytes(msg, FORMAT))
                data = str(s.recv(512), FORMAT)
            except Exception as e:
                logger.error(f"Problem with connection to Devicer: {e}")
        return data


def parse_command_message(override_operation: str, elevation_angle=None, azimuth_angle=None) -> str:
    """
    Get operational message by override_operation, elevation_angle and azimuth_angle.
    Check device_install_position if upsidedown and convert angles with "{0:03}" format
    """
    elevation_angle_converted = None
    azimuth_angle_converted = None
    if elevation_angle and azimuth_angle:
        if device_install_position == "DOWN":
            if elevation_angle > 0:
                elevation_angle = -abs(elevation_angle)
            elif elevation_angle < 0:
                elevation_angle = abs(elevation_angle)
        elevation_angle_converted = "{0:03}".format(int(abs(elevation_angle) * 10.0))
        azimuth_angle_converted = "{0:03}".format(int(abs(azimuth_angle) * 10.0))
        if elevation_angle < 0:
            elevation_angle_converted = f"-{elevation_angle_converted}"
        if azimuth_angle < 0:
            azimuth_angle_converted = f"-{azimuth_angle_converted}"
    # Set up device operation messages here
    operation_msg = {
        "automatic": f"??????{DEVICE_INDEX}AUTO{elevation_angle_converted}{azimuth_angle_converted}",
        "get_status": f"??????{DEVICE_INDEX}STATUS",
        "left": f"??????{DEVICE_INDEX}LEFT",
        "right": f"??????{DEVICE_INDEX}RIGHT",
        "up": f"??????{DEVICE_INDEX}UP",
        "down": f"??????{DEVICE_INDEX}DOWN",
        "stop": f"??????{DEVICE_INDEX}STOP"
    }
    if device_to_zero_angle:
        override_operation = "??????AUTO00"
    else:
        override_operation = operation_msg.get(override_operation, None)
    return override_operation


def calculate_angle(azimuth_value: int, elevation_value: int) -> int:
    """Calculate angle and convert to correct ranges"""
    converted_azimuth_angle = (((azimuth_value - 1300) * device_range_azimuth) / pwm_servo_range_azimuth) + -abs(45.0)
    converted_elevation_angle = (((elevation_value - 1500) * device_range_elevation) / pwm_servo_range_elevation) + 0.0
    return converted_azimuth_angle, converted_elevation_angle


def angle_out_of_bounds(elevation_angle: float, azimuth_angle: float) -> bool:
    """Check whether received angle is out of bounds"""
    out_of_bounds = False
    if elevation_angle < 0.0 or elevation_angle > 30.0:
        logger.warning("Device elevation angle out of allowed range")
    if azimuth_angle < -45.0 or azimuth_angle > 45.0:
        out_of_bounds = True
        logger.warning("Device azimuth angle out of allowed range")
    return out_of_bounds


def convert_msg(msg: list, curr_device_hangle: float, curr_device_vangle: float):
    """Convert message to a format that is accepted by the device"""
    try:
        msg = msg[1].decode(FORMAT).split(",")
        pan, tlt = int(msg[0][-4:]), int(msg[1][-4:])
        desired_azimuth, desired_elevation = calculate_angle(pan, tlt)
        if not angle_out_of_bounds(desired_elevation, desired_azimuth):
            if tlt < 1500:
                desired_elevation = 0.0
            converted_msg = get_movement_by_angle_compare(desired_azimuth, desired_elevation,
                                                          curr_device_hangle, curr_device_vangle)
            if not any(converted_msg):
                logger.info(f"Desired angle too close to current device angle, Angle threshold: {angle_threshold} "
                            f"degrees")
                return
            return converted_msg
        else:
            return
    except TypeError as e:
        logger.warning(f"Wrong data format: {e}")
        
        
def get_movement_by_angle_compare(desired_azimuth: float, desired_elevation: float, curr_device_hangle: float,
                                  curr_device_vangle: float) -> list:
    """
    Compare angles and get right direction of movement. Check also angle threshold here and don't
    send message if threshold reached
    """
    converted_msg_horizontal = None
    converted_msg_vertical = None
    print(f"Current Device Hangle: {curr_device_hangle}, Desired Hangle: {desired_azimuth}")
    print(f"Current Device Vangle: {curr_device_vangle}, Desired Vangle: {desired_elevation}")
    print(f"Threshold Hangle: {abs(curr_device_hangle - desired_azimuth)}, "
          f"Threshold Vangle: {abs(curr_device_vangle - desired_elevation)}")
    if abs(curr_device_hangle - desired_azimuth) > angle_threshold:
        if desired_azimuth < curr_device_hangle:
            converted_msg_horizontal = parse_command_message("left")
        elif desired_azimuth > curr_device_hangle:
            converted_msg_horizontal = parse_command_message("right")
    if abs(curr_device_vangle - desired_elevation) > angle_threshold:
        if desired_elevation > curr_device_vangle:
            if device_install_position == "UP":
                converted_msg_vertical = parse_command_message("down")
            else:
                converted_msg_vertical = parse_command_message("up")
        elif desired_elevation < curr_device_vangle:
            if device_install_position == "UP":
                converted_msg_vertical = parse_command_message("up")
            else:
                converted_msg_vertical = parse_command_message("down")
    return [converted_msg_horizontal, converted_msg_vertical]

