import socket
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.clock import mainthread

# --- Configuration ---
SERVER_IP = '192.168.1.11'  # IP of your discovery server
SERVER_PORT = 2024

class ChatApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_socket = None # Socket for discovery server
        self.peer_socket = None   # Socket for P2P chat
        self.p2p_server_thread = None
        self.stop_thread = False

    def build(self):
        Window.size = (450, 700)
        self.title = "P2P Encrypted Chat"
        self.main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Build the initial registration screen
        self.build_registration_screen()

        return self.main_layout

    def build_registration_screen(self):
        self.main_layout.clear_widgets()
        
        reg_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=200)
        reg_layout.add_widget(Label(text="User Registration", font_size=24))
        self.nickname_input = TextInput(hint_text="Enter your nickname")
        self.p2p_port_input = TextInput(hint_text="Enter your listening port (e.g., 12345)")
        register_button = Button(text="Register and Go Online", on_press=self.register_with_server)
        
        reg_layout.add_widget(self.nickname_input)
        reg_layout.add_widget(self.p2p_port_input)
        reg_layout.add_widget(register_button)
        
        self.main_layout.add_widget(reg_layout)

    def register_with_server(self, instance):
        nickname = self.nickname_input.text
        p2p_port = self.p2p_port_input.text
        
        if not nickname or not p2p_port.isdigit():
            self.display_message("Invalid nickname or port.", "error")
            return
        
        # Start listening for P2P connections on a separate thread
        self.p2p_server_thread = threading.Thread(target=self.start_p2p_listener, args=(int(p2p_port),))
        self.p2p_server_thread.daemon = True
        self.p2p_server_thread.start()

        # Connect to the discovery server
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.connect((SERVER_IP, SERVER_PORT))
            self.server_socket.send(f"REGISTER:{nickname}:{p2p_port}".encode('utf-8'))
            response = self.server_socket.recv(1024).decode('utf-8')
            if response == "REGISTER_OK":
                self.build_chat_selection_screen()
            else:
                self.display_message("Registration failed.", "error")
        except Exception as e:
            self.display_message(f"Error connecting to server: {e}", "error")

    def build_chat_selection_screen(self):
        self.main_layout.clear_widgets()

        # User list display
        self.user_list_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.user_list_layout.bind(minimum_height=self.user_list_layout.setter('height'))
        scroll_view = ScrollView(size_hint=(1, 0.4))
        scroll_view.add_widget(self.user_list_layout)
        
        # Controls for connecting
        connect_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)
        self.target_user_input = TextInput(hint_text="Enter nickname to chat")
        connect_button = Button(text="Chat", on_press=self.request_peer_connection)
        refresh_button = Button(text="Refresh List", on_press=self.refresh_user_list)
        
        connect_layout.add_widget(self.target_user_input)
        connect_layout.add_widget(connect_button)

        # Chat display area
        self.chat_log = TextInput(readonly=True, size_hint=(1, 0.4), background_color=(0.9, 0.9, 0.9, 1))
        
        self.main_layout.add_widget(Label(text="Online Users"))
        self.main_layout.add_widget(scroll_view)
        self.main_layout.add_widget(refresh_button)
        self.main_layout.add_widget(connect_layout)
        self.main_layout.add_widget(Label(text="Chat Window"))
        self.main_layout.add_widget(self.chat_log)

        # Message sending area (initially hidden)
        self.message_input_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        self.message_input = TextInput(hint_text="Type your message...")
        send_button = Button(text="Send", on_press=self.send_p2p_message)
        self.message_input_layout.add_widget(self.message_input)
        self.message_input_layout.add_widget(send_button)
        
        self.refresh_user_list(None)

    def refresh_user_list(self, instance):
        self.server_socket.send("GET_USERS".encode('utf-8'))
        response = self.server_socket.recv(1024).decode('utf-8')
        if response.startswith("USERS:"):
            users = response.split(':', 1)[1].split(',')
            self.user_list_layout.clear_widgets()
            for user in users:
                if user:
                    self.user_list_layout.add_widget(Label(text=user))

    def request_peer_connection(self, instance):
        target_nickname = self.target_user_input.text
        if not target_nickname:
            return
        
        self.server_socket.send(f"GET_ADDR:{target_nickname}".encode('utf-8'))
        response = self.server_socket.recv(1024).decode('utf-8')

        if response.startswith("ADDR:"):
            parts = response.split(':')
            peer_ip, peer_port = parts[2], int(parts[3])
            try:
                self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.peer_socket.connect((peer_ip, peer_port))
                self.display_message(f"Connected to {target_nickname} for P2P chat!", "info")
                threading.Thread(target=self.receive_p2p_messages, daemon=True).start()
                self.main_layout.add_widget(self.message_input_layout) # Show message input
            except Exception as e:
                self.display_message(f"Failed to connect to peer: {e}", "error")
        else:
            self.display_message(response, "error")

    def start_p2p_listener(self, port):
        """Listens for incoming P2P chat requests."""
        listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener_socket.bind(('0.0.0.0', port))
        listener_socket.listen(1)
        
        while not self.stop_thread:
            try:
                # This will block until a peer connects
                conn, addr = listener_socket.accept()
                if self.peer_socket: # If already in a chat, reject
                    conn.close()
                    continue

                self.peer_socket = conn
                self.display_message(f"Accepted P2P connection from {addr}", "info")
                threading.Thread(target=self.receive_p2p_messages, daemon=True).start()
                self.main_layout.add_widget(self.message_input_layout) # Show message input
            except Exception as e:
                self.display_message(f"P2P listener error: {e}", "error")
                break
        listener_socket.close()
    
    @mainthread
    def display_message(self, message, msg_type="info"):
        """Safely updates the GUI from any thread."""
        color_map = {"info": "[color=666666]", "error": "[color=ff3333]", "self": "[color=3333ff]", "peer": "[color=339933]"}
        self.chat_log.text += f"{color_map.get(msg_type, '')}{message}[/color]\n"

    def send_p2p_message(self, instance):
        message = self.message_input.text
        if message and self.peer_socket:
            self.peer_socket.send(message.encode('utf-8'))
            self.display_message(f"You: {message}", "self")
            self.message_input.text = ""

    def receive_p2p_messages(self):
        while self.peer_socket:
            try:
                message = self.peer_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                self.display_message(f"Peer: {message}", "peer")
            except:
                self.display_message("Peer disconnected.", "error")
                self.peer_socket.close()
                self.peer_socket = None
                break

    def on_stop(self):
        """Clean up sockets on exit."""
        self.stop_thread = True
        if self.server_socket:
            self.server_socket.close()
        if self.peer_socket:
            self.peer_socket.close()


if __name__ == "__main__":
    ChatApp().run()