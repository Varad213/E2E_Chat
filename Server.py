import socket

server_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)



try:
    server_socket.bind(('0.0.0.0',2024))
except socket.error as message:
    print('Failed: '+message[0]+' '+message[1])
    

server_socket.listen()
client_address={}
i=1
while True:

    conn,address=server_socket.accept()
    if conn!=None and address!=None:
        print("Connection recieved")
        client_address[i]=address
        print(client_address)
        
