import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer
import threading

def connect_to_tracker(name):
    server_address = 'http://localhost:8000'
    with xmlrpc.client.ServerProxy(server_address) as proxy:
        # Registrar no tracker
        print(proxy.register(name, f"http://localhost:8001"))

        # Listar clientes conectados
        clients = proxy.list_clients()
        print("Peers conectados:", clients)

        # Função para receber mensagens
        def receive_messages():
            server = SimpleXMLRPCServer(('localhost', 8001))
            server.register_function(receive_message, 'receive_message')
            server.serve_forever()

        # Inicia a thread para receber mensagens
        threading.Thread(target=receive_messages, daemon=True).start()
        
        # Comandos de chat
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
