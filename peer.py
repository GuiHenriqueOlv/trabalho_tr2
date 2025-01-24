from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import time
import random
import os

# Assign a unique port for each peer
PORT = random.randint(10000, 60000)

# Global flag to manage the main loop
exit_flag = threading.Event()


def receive_message(message, from_peer):
    print(f"\n{from_peer}: {message}")
    return True


def get_files():
    # List files in the current directory for this peer
    return [f for f in os.listdir() if f.endswith(".txt")]


def send_file(file_name):
    try:
        with open(file_name, "rb") as f:
            data = f.read()
        return xmlrpc.client.Binary(data)
    except FileNotFoundError:
        return f"Error: Arquivo '{file_name}' não encontrado."
    except Exception as e:
        return f"Error: {e}"


def download_file(peer_name, peer_address, file_name):
    try:
        with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
            response = peer_proxy.send_file(file_name)
            if isinstance(response, xmlrpc.client.Binary):
                # Save the file locally
                with open(file_name, "wb") as f:
                    f.write(response.data)
                print(f"Arquivo '{file_name}' baixado com sucesso de {peer_name}.")
            else:
                print(response)
    except Exception as e:
        print(f"Erro ao baixar arquivo de {peer_name}: {e}")


def chat_with_peer(peer_name, peer_address, sender_name):
    try:
        with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
            while not exit_flag.is_set():
                message = input(f"{sender_name} (Você): ")
                if message.lower() == 'exit':
                    print("Saindo do chat...")
                    break
                peer_proxy.receive_message(message, sender_name)
    except Exception as e:
        print(f"Erro ao conversar com {peer_name}: {e}")


def list_files_from_peers(proxy):
    try:
        peers = proxy.list_clients()
        if not peers:
            print("Nenhum peer disponível.")
            return

        print("\nPeers conectados e seus arquivos:")
        for peer_name, peer_address in peers.items():
            try:
                with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
                    files = peer_proxy.get_files()
                    print(f"{peer_name}: {files}")
            except Exception as e:
                print(f"Não foi possível obter arquivos de {peer_name}: {e}")
    except Exception as e:
        print(f"Erro ao listar peers: {e}")


def connect_to_tracker(name):
    server_address = 'http://localhost:9000'
    try:
        with xmlrpc.client.ServerProxy(server_address) as proxy:
            # Attempt to register with the tracker
            response = proxy.register(name, f"http://localhost:{PORT}")
            if response.startswith("Error:"):
                print(response)
                return False

            print(response)

            # Create a local file for the peer
            file_name = f"{name}_example.txt"
            with open(file_name, "w") as f:
                f.write(f"This is a file for peer {name}.\n")
            print(f"Arquivo '{file_name}' criado localmente.")

            # Start a thread to send heartbeats
            def send_heartbeat():
                while not exit_flag.is_set():
                    time.sleep(10)  # Send heartbeat every 10 seconds
                    try:
                        proxy.heartbeat(name)
                    except Exception as e:
                        print(f"Erro ao enviar heartbeat: {e}")
                        break

            threading.Thread(target=send_heartbeat, daemon=True).start()

            # Function to receive messages
            def receive_messages():
                server = SimpleXMLRPCServer(('localhost', PORT), allow_none=True)
                server.register_function(receive_message, 'receive_message')
                server.register_function(get_files, 'get_files')
                server.register_function(send_file, 'send_file')  # Register file transfer function
                print(f"Peer iniciado no endereço http://localhost:{PORT}.")
                server.serve_forever()

            threading.Thread(target=receive_messages, daemon=True).start()

            # Chat commands
            while not exit_flag.is_set():
                command = input("\nDigite 'list' para ver peers, 'chat' para conversar, 'get' para baixar arquivo, 'exit' para sair: ").strip().lower()
                if command == 'list':
                    list_files_from_peers(proxy)
                elif command == 'chat':
                    peer_name = input("Digite o nome do peer para iniciar o chat: ").strip()
                    peer_address = proxy.get_peer_address(peer_name)
                    if peer_address == "Peer não encontrado.":
                        print(peer_address)
                    else:
                        chat_with_peer(peer_name, peer_address, name)
                elif command == 'get':
                    peer_name = input("Digite o nome do peer: ").strip()
                    file_name = input("Digite o nome do arquivo para baixar: ").strip()
                    peer_address = proxy.get_peer_address(peer_name)
                    if peer_address == "Peer não encontrado.":
                        print(peer_address)
                    else:
                        download_file(peer_name, peer_address, file_name)
                elif command == 'exit':
                    print("Saindo do programa...")
                    exit_flag.set()
                    break
                else:
                    print("Comando inválido. Tente novamente.")
            return True
    except Exception as e:
        print(f"Erro ao conectar ao tracker: {e}")
        return False


if __name__ == "__main__":
    try:
        while not exit_flag.is_set():
            name = input("Digite seu nome de cliente: ").strip()
            if connect_to_tracker(name):
                break
    except KeyboardInterrupt:
        print("\nEncerrando o programa.")
    finally:
        exit_flag.set()
