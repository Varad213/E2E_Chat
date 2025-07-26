import socket
import threading

users={}
users_lock=threading.Lock()

def start_server():
    server_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        server_socket.bind(('0.0.0.0',2024))
    except socket.error as message:
        print('Failed: '+message[0]+' '+message[1])
    

    server_socket.listen()
    client_address={}
    while True:
        conn, addr = server_socket.accept()
        thread= threading.Thread(target=handle_client, args=(conn,addr))
        thread.daemon=True
        thread.start()

def handle_client(conn,addr):
    registered_nickname= None
    try:
        while True:
            data=conn.recv(1024).decode('utf-8')
            if not data:
                break
            parts = data.split(':',2)
            command=parts[0]
            if command==  "REGISTER" and len(parts)==3:
                nickname=parts[1]
                p2p_port=int(parts[2])
                with  users_lock:
                    users[nickname]=(addr[0],p2p_port)
                    registered_nickname=nickname
                print(f"{nickname} Registered")
                conn.send("REGISTER_OK".encode('utf-8'))
            
            elif command == "GET_USERS":
                with users_lock:
                    user_list=",".join(users.keys())
                conn.send(f'Users:{user_list}'.encode('utf-8'))

            elif  command=="GET_ADDR" and len(parts) == 2:
                target_nickname=parts[1]
                with users_lock:
                    target_addr=users[target_nickname]
                    print(f"{target_nickname}:{target_addr}")
                if target_addr:
                    conn.send(f'ADDR:{target_nickname}: {target_addr[0]}:{target_addr[1]}'.encode('utf-8'))
                else:
                    conn.send("Error: user not found".encode('utf-8'))
    except ConnectionResetError:
        print(f"CONNECTION with {addr} disconnected")
    finally:
        if registered_nickname:
            with users_lock:
                if registered_nickname in users:
                    del users[registered_nickname]
                    print(f"UNREGISTERED {registered_nickname}")
        conn.close()
                
start_server()
        
