import socket
import sys


def handler(sig):
    sys.exit(0)


if sys.platform == "win32":
    import win32api
    win32api.SetConsoleCtrlHandler(handler, True)

host = "localhost"
port = 6000
data_format = "ascii"

vertical_angle = 0.0
horizontal_angle = 0.0

while True:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen(1)
            print(f"ADevice listening at {host}:{port}")
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                while True:
                    data = conn.recv(512)
                    if data.decode(data_format) == "??????1STATUS":
                        print(f"RECEIVED: {data}")
                        conn.sendall(bytes(f"Dummy GET STATUS Vangle:{vertical_angle}Hangle:{horizontal_angle}", data_format))
                    elif "??????1AUTO00" in data.decode(data_format):
                        print(f"RECEIVED: {data}")
                        conn.sendall(bytes("Dummy AUTOMATIC response from Device", data_format))
                    elif data.decode(data_format) == "??????1LEFT":
                        print(f"RECEIVED: {data}")
                        conn.sendall(bytes("Dummy MOVE LEFT response from Device", data_format))
                    elif data.decode(data_format) == "??????1RIGHT":
                        print(f"RECEIVED: {data}")
                        conn.sendall(bytes("Dummy MOVE RIGHT response from Device", data_format))
                    elif data.decode(data_format) == "??????1UP":
                        print(f"RECEIVED: {data}")
                        conn.sendall(bytes("Dummy MOVE UP response from Device", data_format))
                    elif data.decode(data_format) == "??????1DOWN":
                        print(f"RECEIVED: {data}")
                        conn.sendall(bytes("Dummy MOVE DOWN response from Device", data_format))
                    elif data.decode(data_format) == "??????1STOP":
                        print(f"RECEIVED: {data}")
                        conn.sendall(bytes("Dummy STOP response from Device", data_format))
                    else:
                        conn.close()
    except KeyboardInterrupt as e:
        conn.close()
        sys.exit(0)
