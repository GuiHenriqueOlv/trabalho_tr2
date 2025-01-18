from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import time
import random

# Assign a unique port for each peer
PORT = random.randint(10000, 60000)

def receive_message(message, from_peer):
    print(f"{from_peer}: {message}")
    return True

def chat_with_peer(peer_name, peer_address, sender_name):
    with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
        while True:
            message = input(f"{sender_name} (Você): ")
            if message.lower() == 'exit':
                break
            peer_proxy.receive_message(message, sender_name)

def connect_to_tracker(name):
    server_address = 'http://localhost:9000'
    with xmlrpc.client.ServerProxy(server_address) as proxy:
        # Register with the tracker
        print(proxy.register(name, f"http://localhost:{PORT}"))

        # Start a thread to send heartbeats
        def send_heartbeat():
            while True:
                time.sleep(5)  # Send heartbeat every 5 seconds
                print(proxy.heartbeat(name))

        threading.Thread(target=send_heartbeat, daemon=True).start()

        # Function to receive messages
        def receive_messages():
            server = SimpleXMLRPCServer(('localhost', PORT), allow_none=True)
            server.register_function(receive_message, 'receive_message')
            server.serve_forever()

        # Start a thread to receive messages
        threading.Thread(target=receive_messages, daemon=True).start()

        # Chat commands
        while True:
            command = input("Digite 'list' para ver peers, 'chat' para conversar, 'exit' para sair: ")
            if command == 'list':
                print(proxy.list_clients())
            elif command == 'chat':
                peer_name = input("Digite o nome do peer para iniciar o chat: ")
                peer_address = proxy.get_peer_address(peer_name)
                if peer_address == "Peer não encontrado.":
                    print(peer_address)
                else:
                    chat_with_peer(peer_name, peer_address, name)
            elif command == 'exit':
                break

if __name__ == "__main__":
    name = input("Digite seu nome de cliente: ")
    connect_to_tracker(name)
