from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import time
import os
import random
import hashlib

CHUNK_SIZE = 1024 * 1024  # 1MB
PORT = random.randint(10000, 60000)
exit_flag = threading.Event()

def calculate_checksum(data):
    """ Calcula o checksum SHA-256 de um bloco de dados """
    return hashlib.sha256(data).hexdigest()

def split_file(file_name):
    """ Divide um arquivo em chunks de 1MB e calcula seus checksums """
    chunks = []
    if not os.path.exists(file_name):
        return chunks

    with open(file_name, "rb") as f:
        index = 0
        while chunk := f.read(CHUNK_SIZE):
            checksum = calculate_checksum(chunk)
            chunk_name = f"{file_name}.chunk{index}"
            with open(chunk_name, "wb") as chunk_file:
                chunk_file.write(chunk)
            chunks.append((chunk_name, checksum))
            index += 1
    
    return chunks

def send_chunk(chunk_name):
    """ Envia um chunk específico para outro peer """
    try:
        with open(chunk_name, "rb") as f:
            data = f.read()
        return xmlrpc.client.Binary(data)
    except FileNotFoundError:
        return f"Erro: Chunk '{chunk_name}' não encontrado."
    except Exception as e:
        return f"Erro: {e}"

def get_files():
    """ Lista os arquivos disponíveis no diretório do peer """
    return [f for f in os.listdir() if os.path.isfile(f)]

def receive_message(message, from_peer):
    """ Recebe mensagens de outro peer e as exibe """
    print(f"\n{from_peer}: {message}")
    return True

def send_message(peer_name, peer_address, sender_name):
    """ Envia uma mensagem para outro peer """
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

def download_chunk(peer_name, peer_address, chunk_name):
    """ Faz o download de um chunk de outro peer """
    try:
        with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
            response = peer_proxy.send_chunk(chunk_name)
            if isinstance(response, xmlrpc.client.Binary):
                with open(chunk_name, "wb") as f:
                    f.write(response.data)
                print(f"Chunk '{chunk_name}' baixado com sucesso de {peer_name}.")
            else:
                print(response)
    except Exception as e:
        print(f"Erro ao baixar chunk de {peer_name}: {e}")

def list_files_from_peers(proxy):
    """ Lista arquivos disponíveis nos peers conectados """
    peers = proxy.list_clients()
    if not peers:
        print("Nenhum peer disponível.")
        return
    print("\nPeers conectados e arquivos disponíveis:")
    for peer_name, peer_address in peers.items():
        try:
            with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
                files = peer_proxy.get_files()
                print(f"{peer_name}: {files}")
        except Exception as e:
            print(f"Não foi possível obter arquivos de {peer_name}: {e}")

def register_chunks(proxy, peer_name, file_name, chunks):
    """ Registra os chunks de um arquivo no tracker """
    chunk_info = [(chunk, checksum) for chunk, checksum in chunks]
    proxy.register_chunks(peer_name, file_name, chunk_info)
    print(f"Chunks do arquivo '{file_name}' registrados no tracker.")

def connect_to_tracker(name):
    """ Conecta ao tracker e registra o peer """
    server_address = 'http://localhost:9000'
    try:
        with xmlrpc.client.ServerProxy(server_address) as proxy:
            response = proxy.register(name, f"http://localhost:{PORT}")
            if response.startswith("Error:"):
                print(response)
                return False
            print(response)
            file_name = f"{name}_example.txt"
            with open(file_name, "w") as f:
                f.write(f"Este é um arquivo de teste do peer {name}.")
            chunks = split_file(file_name)
            register_chunks(proxy, name, file_name, chunks)
            def send_heartbeat():
                while not exit_flag.is_set():
                    time.sleep(10)
                    try:
                        proxy.heartbeat(name)
                    except Exception as e:
                        print(f"Erro ao enviar heartbeat: {e}")
                        break
            threading.Thread(target=send_heartbeat, daemon=True).start()
            def receive_requests():
                server = SimpleXMLRPCServer(('localhost', PORT), allow_none=True)
                server.register_function(send_chunk, 'send_chunk')
                server.register_function(get_files, 'get_files')
                server.register_function(receive_message, 'receive_message')
                print(f"Peer iniciado no endereço http://localhost:{PORT}.")
                server.serve_forever()
            threading.Thread(target=receive_requests, daemon=True).start()
            while not exit_flag.is_set():
                command = input("\nDigite 'list' para ver peers, 'chat' para conversar, 'get' para baixar chunk, 'exit' para sair: ").strip().lower()
                if command == 'list':
                    list_files_from_peers(proxy)
                elif command == 'chat':
                    peer_name = input("Digite o nome do peer para iniciar o chat: ").strip()
                    peer_address = proxy.get_peer_address(peer_name)
                    if peer_address == "Peer não encontrado.":
                        print(peer_address)
                    else:
                        send_message(peer_name, peer_address, name)
                elif command == 'get':
                    peer_name = input("Digite o nome do peer: ").strip()
                    chunk_name = input("Digite o nome do chunk para baixar: ").strip()
                    peer_address = proxy.get_peer_address(peer_name)
                    if peer_address == "Peer não encontrado.":
                        print(peer_address)
                    else:
                        download_chunk(peer_name, peer_address, chunk_name)
                elif command == 'exit':
                    print("Saindo...")
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
