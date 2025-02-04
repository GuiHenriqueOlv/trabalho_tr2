from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import time
import os
import random
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

CHUNK_SIZE = 1024 * 1024  # 1MB
PORT = random.randint(10000, 60000)
exit_flag = threading.Event()

def calculate_checksum(data):
    """ Calcula o checksum SHA-256 de um bloco de dados """
    return hashlib.sha256(data).hexdigest()

def compute_file_checksum(file_name):
    """ Calcula o checksum SHA-256 de um arquivo inteiro """
    with open(file_name, "rb") as f:
        data = f.read()
    return calculate_checksum(data)

def split_file(file_name):
    """
    Divide um arquivo em chunks de 1MB, calcula seus checksums e atribui um identificador único para cada bloco.
    Cada chunk é identificado por um número sequencial (index) utilizado também no nome do arquivo do chunk.
    Retorna uma lista de tuplas: (chunk_id, chunk_name, checksum)
    """
    chunks = []
    if not os.path.exists(file_name):
        return chunks

    with open(file_name, "rb") as f:
        index = 0
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            checksum = calculate_checksum(chunk)
            chunk_name = f"{file_name}.chunk{index}"
            with open(chunk_name, "wb") as chunk_file:
                chunk_file.write(chunk)
            chunks.append((index, chunk_name, checksum))
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
    """
    Lista os arquivos .txt disponíveis no diretório do peer,
    excluindo os arquivos de chunk (que contêm '.chunk' no nome).
    """
    return [f for f in os.listdir() if os.path.isfile(f) and f.endswith(".txt") and ".chunk" not in f]

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

def download_chunk(peer_name, peer_address, chunk_name, expected_checksum=None):
    """
    Faz o download de um chunk de outro peer.
    Se expected_checksum for informado, verifica a integridade do bloco baixado.
    """
    try:
        with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
            response = peer_proxy.send_chunk(chunk_name)
            if isinstance(response, xmlrpc.client.Binary):
                data = response.data
                if expected_checksum:
                    downloaded_checksum = calculate_checksum(data)
                    if downloaded_checksum != expected_checksum:
                        print(f"Erro: Checksum do chunk '{chunk_name}' não confere.")
                        return False
                with open(chunk_name, "wb") as f:
                    f.write(data)
                print(f"Chunk '{chunk_name}' baixado com sucesso de {peer_name}.")
                return True
            else:
                print(response)
                return False
    except Exception as e:
        print(f"Erro ao baixar chunk de {peer_name}: {e}")
        return False

def assemble_file(original_file_name, output_file=None):
    """
    Reconstroi o arquivo original a partir dos seus chunks.
    Procura por arquivos no formato '{original_file_name}.chunkX' e os une na ordem.
    """
    if output_file is None:
        output_file = f"{original_file_name}.assembled"
    index = 0
    with open(output_file, "wb") as outfile:
        while True:
            chunk_file = f"{original_file_name}.chunk{index}"
            if not os.path.exists(chunk_file):
                break
            with open(chunk_file, "rb") as infile:
                outfile.write(infile.read())
            index += 1
    print(f"Arquivo reassemblado como {output_file}.")
    
def list_files_from_peers(proxy):
    """ Lista arquivos .txt disponíveis nos peers conectados """
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

def register_chunks(proxy, peer_name, file_name, chunks, file_checksum=None):
    """
    Registra os chunks de um arquivo no tracker.
    Cada chunk é uma tupla (chunk_id, chunk_name, checksum).
    O checksum final do arquivo (se calculado) também é enviado.
    """
    proxy.register_chunks(peer_name, file_name, chunks, file_checksum)
    print(f"Chunks do arquivo '{file_name}' registrados no tracker (por {peer_name}).")

def share_file(file_name, proxy, peer_name):
    """
    Compartilha um arquivo .txt específico: quebra-o em chunks, calcula seu checksum final
    e registra os dados no tracker.
    """
    if not os.path.exists(file_name):
        print(f"Arquivo '{file_name}' não encontrado.")
        return
    if not file_name.endswith(".txt"):
        print("Apenas arquivos com extensão .txt podem ser compartilhados.")
        return
    file_checksum = compute_file_checksum(file_name)
    chunks = split_file(file_name)
    if chunks:
        register_chunks(proxy, peer_name, file_name, chunks, file_checksum)
        print(f"Arquivo '{file_name}' compartilhado com sucesso.")
    else:
        print("Nenhum chunk foi criado.")

def share_all_txt_files(proxy, peer_name):
    """
    Percorre todos os arquivos .txt do diretório (exceto chunks),
    quebra cada um em chunks e os registra no tracker.
    """
    files = get_files()
    if not files:
        print("Nenhum arquivo .txt encontrado para compartilhar automaticamente.")
    for file in files:
        file_checksum = compute_file_checksum(file)
        chunks = split_file(file)
        if chunks:
            register_chunks(proxy, peer_name, file, chunks, file_checksum)

def download_file(proxy, local_peer_name):
    """
    Realiza o download completo de um arquivo:
      - O usuário informa o nome do arquivo a ser baixado.
      - São consultados todos os chunks do arquivo no tracker.
      - O usuário informa quantas conexões paralelas deseja usar.
      - Cada chunk é baixado em paralelo e, assim que for baixado com sucesso,
        ele é imediatamente registrado no tracker para que este peer passe a ser seeder daquele chunk.
      - Ao final, o arquivo é reagrupado, seu checksum é verificado e, se completo,
        todos os chunks são registrados novamente.
    """
    file_to_get = input("Digite o nome do arquivo que deseja baixar: ").strip()
    chunks = proxy.get_file_chunks(file_to_get)
    if not chunks:
        print("Nenhum chunk encontrado para esse arquivo.")
        return
    final_checksum = proxy.get_file_checksum(file_to_get)
    if final_checksum == "Checksum não encontrado.":
        print("Checksum final do arquivo não encontrado.")
        return
    try:
        num_connections = int(input("Digite o número de conexões paralelas: "))
    except ValueError:
        print("Valor inválido para conexões.")
        return

    # Ordena os chunks pela ordem do chunk_id (ou 0 se None)
    chunks.sort(key=lambda x: x[1] if x[1] is not None else 0)

    def download_individual_chunk(chunk_info):
        peer, chunk_id, chunk_name, chunk_checksum = chunk_info
        peer_addr = proxy.get_peer_address(peer)
        if peer_addr == "Peer não encontrado.":
            print(f"Peer {peer} não encontrado para chunk {chunk_name}.")
            return False
        result = download_chunk(peer, peer_addr, chunk_name, chunk_checksum)
        if result:
            # Assim que o chunk for baixado, registra-o no tracker para que este peer passe a oferecê-lo
            proxy.register_chunks(local_peer_name, file_to_get, [(chunk_id, chunk_name, chunk_checksum)], final_checksum)
            return True
        return False

    print("Iniciando download dos chunks...")
    with ThreadPoolExecutor(max_workers=num_connections) as executor:
        futures = {executor.submit(download_individual_chunk, c): c for c in chunks}
        for future in as_completed(futures):
            c = futures[future]
            try:
                result = future.result()
                if not result:
                    print(f"Falha ao baixar o chunk {c[2]}.")
            except Exception as e:
                print(f"Erro ao baixar chunk {c[2]}: {e}")

    print("Todos os chunks foram baixados. Reagrupando o arquivo...")
    assemble_file(file_to_get)
    assembled_file = f"{file_to_get}.assembled"
    if not os.path.exists(assembled_file):
        print("Erro: arquivo reassemblado não encontrado.")
        return
    with open(assembled_file, "rb") as f:
        assembled_data = f.read()
    assembled_checksum = calculate_checksum(assembled_data)
    if assembled_checksum == final_checksum:
        print("Arquivo baixado com sucesso e o checksum confere!")
        # Renomeia o arquivo reassemblado para o nome original, se necessário.
        if not os.path.exists(file_to_get):
            os.rename(assembled_file, file_to_get)
        else:
            os.remove(assembled_file)
        # Registra novamente todos os chunks para garantir que o peer tem o arquivo completo
        local_chunks = split_file(file_to_get)
        register_chunks(proxy, local_peer_name, file_to_get, local_chunks, final_checksum)
    else:
        print("O checksum do arquivo reagrupado não confere!")

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

            # Compartilha automaticamente todos os arquivos .txt do diretório
            share_all_txt_files(proxy, name)

            def send_heartbeat():
                while not exit_flag.is_set():
                    time.sleep(5)
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

            # Menu interativo
            while not exit_flag.is_set():
                command = input(
                    "\nDigite 'list' para ver peers, 'chunks' para ver blocos de um arquivo,\n"
                    "'chat' para conversar, 'get' para baixar um arquivo completo,\n"
                    "'assemble' para reconstituir um arquivo (se necessário),\n"
                    "'share' para compartilhar um novo arquivo, 'exit' para sair: "
                ).strip().lower()
                if command == 'list':
                    list_files_from_peers(proxy)
                elif command == 'chunks':
                    file_name_input = input("Digite o nome do arquivo para listar os blocos: ").strip()
                    chunks_list = proxy.get_file_chunks(file_name_input)
                    if not chunks_list:
                        print(f"Nenhum chunk registrado para o arquivo '{file_name_input}'.")
                    else:
                        print(f"Chunks para o arquivo '{file_name_input}':")
                        for info in chunks_list:
                            peer, chunk_id, chunk_name, checksum = info
                            print(f"Peer: {peer}, ID: {chunk_id}, Nome: {chunk_name}, Checksum: {checksum}")
                elif command == 'chat':
                    peer_name_input = input("Digite o nome do peer para iniciar o chat: ").strip()
                    peer_address = proxy.get_peer_address(peer_name_input)
                    if peer_address == "Peer não encontrado.":
                        print(peer_address)
                    else:
                        send_message(peer_name_input, peer_address, name)
                elif command == 'get':
                    download_file(proxy, name)
                elif command == 'assemble':
                    original_file = input("Digite o nome original do arquivo (sem a extensão de chunk): ").strip()
                    assemble_file(original_file)
                elif command == 'share':
                    file_to_share = input("Digite o nome do arquivo .txt para compartilhar: ").strip()
                    share_file(file_to_share, proxy, name)
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
