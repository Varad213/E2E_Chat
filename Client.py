import socket
client_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
def send_ser_request(name):
    client_socket.connect(("192.168.1.2",2024))
    client_socket.send(name.encode('utf-8'))
    print('connected')
