from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import time
import random
import os

# Define uma porta única para cada peer
PORT = random.randint(10000, 60000)
# Flag global para gerenciar o loop principal
exit_flag = threading.Event()


def receive_message(message, from_peer):
    # Função para receber mensagens de outro peer
    print(f"\n{from_peer}: {message}")
    return True


def get_files():
    # Lista os arquivos no diretório atual que terminam com .txt
    return [f for f in os.listdir() if f.endswith(".txt")]


def send_file(file_name):
    # Envia um arquivo solicitado para outro peer
    try:
        with open(file_name, "rb") as f:
            data = f.read()
        print(f"Arquivo '{file_name}' enviado com sucesso.")
        return xmlrpc.client.Binary(data)
    except FileNotFoundError:
        return f"Error: Arquivo '{file_name}' não encontrado."
    except Exception as e:
        return f"Error: {e}"


def download_file(peer_name, peer_address, file_name):
    # Faz o download de um arquivo de outro peer
    try:
        with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
            start_time = time.time()  # Marca o início do tempo de download
            response = peer_proxy.send_file(file_name)
            if isinstance(response, xmlrpc.client.Binary):
                # Salva o arquivo localmente
                with open(file_name, "wb") as f:
                    f.write(response.data)
                end_time = time.time()  # Marca o fim do tempo de download

                # Calcula o tamanho do arquivo em MB e a taxa de download
                file_size = len(response.data) / (1024 * 1024)  # Tamanho em MB
                download_rate = file_size / (end_time - start_time)  # MB/s
                
                print(f"Arquivo '{file_name}' baixado com sucesso de {peer_name}.")
                print(f"Tamanho do arquivo: {file_size:.2f} MB, Taxa de download: {download_rate:.2f} MB/s")
            else:
                print(response)
    except Exception as e:
        print(f"Erro ao baixar arquivo de {peer_name}: {e}")


def chat_with_peer(peer_name, peer_address, sender_name):
    # Função para conversar com outro peer
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
    # Lista os arquivos compartilhados por outros peers
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
    # Conecta ao tracker e registra o peer
    server_address = 'http://localhost:9000'
    try:
        with xmlrpc.client.ServerProxy(server_address) as proxy:
            response = proxy.register(name, f"http://localhost:{PORT}")
            if response.startswith("Error:"):
                print(response)
                return False

            print(response)

            # Cria um arquivo local para o peer
            file_name = f"{name}_example.txt"
            with open(file_name, "w") as f:
                f.write(f"Este é um arquivo para o peer {name}.")
            print(f"Arquivo '{file_name}' criado localmente.")

            # Inicia uma thread para enviar heartbeats periodicamente
            def send_heartbeat():
                while not exit_flag.is_set():
                    time.sleep(10)  # Envia heartbeat a cada 10 segundos
                    try:
                        proxy.heartbeat(name)
                    except Exception as e:
                        print(f"Erro ao enviar heartbeat: {e}")
                        break

            threading.Thread(target=send_heartbeat, daemon=True).start()

            # Função para receber mensagens
            def receive_messages():
                server = SimpleXMLRPCServer(('localhost', PORT), allow_none=True)
                server.register_function(receive_message, 'receive_message')
                server.register_function(get_files, 'get_files')
                server.register_function(send_file, 'send_file')  # Registra função de envio de arquivos
                print(f"Peer iniciado no endereço http://localhost:{PORT}.")
                server.serve_forever()

            threading.Thread(target=receive_messages, daemon=True).start()

            # Comandos do chat
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
