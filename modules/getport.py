import socket

sock = socket.socket()
sock.bind(('', 0))
port = sock.getsockname()[1]
sock.close()
print(port)
