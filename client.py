from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import time

def connect_to_tracker(name):
    server_address = 'http://localhost:9000'
    with xmlrpc.client.ServerProxy(server_address) as proxy:
        # Register with the tracker
        print(proxy.register(name, f"http://localhost:9001"))

        # Start a heartbeat thread
        def send_heartbeat():
            while True:
                try:
                    print(proxy.heartbeat(name))
                except Exception as e:
                    print(f"Erro ao enviar heartbeat: {e}")
                time.sleep(5)  # Send heartbeat every 5 seconds

        threading.Thread(target=send_heartbeat, daemon=True).start()

        # Start receiving messages
        def receive_messages():
            server = SimpleXMLRPCServer(('localhost', 9001))
            server.register_function(receive_message, 'receive_message')
            server.serve_forever()

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
                    chat_with_peer(peer_name, peer_address)
            elif command == 'exit':
                break

def receive_message(message, from_peer):
    print(f"{from_peer}: {message}")
    return True

def chat_with_peer(peer_name, peer_address):
    with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
        while True:
            message = input("Você: ")
            if message.lower() == 'exit':
                break
            peer_proxy.receive_message(message, "Seu_Nome")

if __name__ == "__main__":
    name = input("Digite seu nome de cliente: ")
    connect_to_tracker(name)
