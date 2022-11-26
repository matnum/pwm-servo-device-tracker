# PWM Servo Device Tracker

UDP server to listen pwm servo messages and send them to device with TCP after conversion.
Can be used to track or control device with pwm servo. Implementation needs to be refactored
based on user needs and setup.

## How to use

<ul>
<li> Set up correct parameters in start_socket_server.py and ranges in device_handler.py
<li> Execute start_socket_server.py in terminal or double click in explorer
<li> Tested with Python 3.8.10
</ul>

```shell
$ python3 start_socket_server.py
```

For mocking run mock_device.py in another terminal before start_socket_server.py.
You can use netcat to work as a pwm servo client and send UDP messages to server

```shell
$ netcat -u \<host\> \<port\>
```
