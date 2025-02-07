from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import queue
import time
import os
import random
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import ThreadPoolExecutor, as_completed

CHUNK_SIZE = 1024 * 1024  # 1MB
PORT = random.randint(10000, 60000)
exit_flag = threading.Event()

def calculate_checksum(data):
    return hashlib.sha256(data).hexdigest()

def compute_file_checksum(file_name):
    with open(file_name, "rb") as f:
        data = f.read()
    return calculate_checksum(data)

def split_file(file_name):
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
    try:
        with open(chunk_name, "rb") as f:
            data = f.read()
        return xmlrpc.client.Binary(data)
    except FileNotFoundError:
        return f"Erro: Chunk '{chunk_name}' não encontrado."
    except Exception as e:
        return f"Erro: {e}"

def get_files():
    return [f for f in os.listdir() if os.path.isfile(f) and f.endswith(".txt") and ".chunk" not in f]

def receive_message(message, from_peer):
    print(f"\n{from_peer}: {message}")
    return True

def send_message(peer_name, peer_address, sender_name):
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



def assemble_file(original_file_name, output_file=None):
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

def register_chunks(proxy, peer_name, file_name, chunks, file_checksum=None):
    try:
        proxy.register_chunks(peer_name, file_name, chunks, file_checksum)
        print(f"Chunks do arquivo '{file_name}' registrados no tracker (por {peer_name}).")
    except Exception as e:
        print(f"Erro ao registrar chunks: {e}")

def share_file(file_name, proxy, peer_name):
    if not os.path.exists(file_name):
        print(f"Arquivo '{file_name}' não encontrado.")
        return
    if not file_name.endswith(".txt"):
        print("Apenas arquivos com extensão .txt podem ser compartilhados.")
        return
    try:
        file_checksum = compute_file_checksum(file_name)
        chunks = split_file(file_name)
        if chunks:
            register_chunks(proxy, peer_name, file_name, chunks, file_checksum)
            print(f"Arquivo '{file_name}' compartilhado com sucesso.")
        else:
            print("Nenhum chunk foi criado.")
    except Exception as e:
        print(f"Erro ao compartilhar arquivo: {e}")

def share_all_txt_files(proxy, peer_name):
    files = get_files()
    if not files:
        print("Nenhum arquivo .txt encontrado para compartilhar automaticamente.")
    for file in files:
        try:
            file_checksum = compute_file_checksum(file)
            chunks = split_file(file)
            if chunks:
                register_chunks(proxy, peer_name, file, chunks, file_checksum)
        except Exception as e:
            print(f"Erro ao compartilhar {file}: {e}")

def list_files_from_peers(proxy):
    try:
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
    except Exception as e:
        print(f"Erro ao listar peers: {e}")

# Armazena conexões abertas no dicionário self.pool.
# Evita criar novas conexões repetidamente.
# Controla o número máximo de conexões simultâneas (max_connections).
# Garante que apenas uma thread por vez modifique o pool (self.lock).
class PeerConnectionPool:
    def __init__(self, max_connections=10):
        self.pool = {}  # Dicionário para armazenar conexões abertas
        self.max_connections = max_connections  # Número máximo de conexões simultâneas
        self.lock = threading.Lock()  # Controle de acesso às conexões

    def get_connection(self, peer_address):
        with self.lock:  # Garante que apenas uma thread por vez acessa o pool
            if peer_address not in self.pool:  # Se não houver conexão para esse peer
                transport = xmlrpc.client.Transport(use_datetime=True)
                transport.timeout = 30  # Define um tempo limite para evitar travamentos
                self.pool[peer_address] = xmlrpc.client.ServerProxy(
                    peer_address, 
                    transport=transport,
                    allow_none=True
                )  # Cria uma nova conexão e a armazena no pool
            return self.pool[peer_address]  # Retorna a conexão persistente


# Cria um objeto de conexão persistente com o tracker.
# Garante que apenas uma thread acesse o tracker por vez, evitando conflitos.
# Usa execute(method_name, *args) para chamar métodos remotos de forma segura.
class TrackerProxy:
    def __init__(self, address):
        self.address = address  # Endereço do tracker
        self.semaphore = threading.Semaphore(1)  # Controle de acesso a chamadas simultâneas
        self.transport = xmlrpc.client.Transport(use_datetime=True)
        self.transport.timeout = 30  # Tempo limite para as requisições

    def get_proxy(self):
        return xmlrpc.client.ServerProxy(self.address, 
                                         transport=self.transport,
                                         allow_none=True)  # Cria um proxy XML-RPC para se conectar ao tracker

    def execute(self, method_name, *args):
        with self.semaphore:  # Garante que apenas uma thread execute uma requisição ao tracker por vez
            proxy = self.get_proxy()
            method = getattr(proxy, method_name)  # Obtém o método a ser chamado
            return method(*args)  # Executa o método remoto e retorna a resposta

def count_local_chunks():
    """Conta o número de chunks no diretório atual"""
    return len([f for f in os.listdir() if '.chunk' in f])

def calculate_max_connections():
    """
    Calcula o número máximo de conexões permitidas baseado no número de chunks
    Regras:
    - 0-5 chunks: 1 conexão
    - 6-15 chunks: 2 conexões
    - 16-25 chunks: 3 conexões
    - 26+ chunks: 4 conexões
    """
    num_chunks = count_local_chunks()
    if num_chunks <= 2:
        return 1
    elif num_chunks <= 5:
        return 2
    elif num_chunks <= 7:
        return 3
    else:
        return 4

def download_file(proxy, local_peer_name):
    try:
        file_to_get = input("Digite o nome do arquivo que deseja baixar: ").strip()

        max_connections = calculate_max_connections()
        print(f"\nBaseado na sua contribuição ({count_local_chunks()} chunks), " 
              f"você pode usar até {max_connections} conexões paralelas.")
        
        while True:
            try:
                num_connections = int(input(f"Digite o número de conexões paralelas desejado (1 até {max_connections}): "))
                if 1 <= num_connections <= max_connections:
                    break
                else:
                    print(f"Por favor, escolha um número entre 1 e {max_connections}.")
            except ValueError:
                print(f"Entrada inválida. Digite um número entre 1 e {max_connections}.")

        tracker = TrackerProxy('http://localhost:9000')
        chunks = tracker.execute('get_file_chunks', file_to_get)

        if not chunks:
            print(f"Nenhum chunk encontrado para o arquivo '{file_to_get}'.")
            return

        final_checksum = tracker.execute('get_file_checksum', file_to_get)
        if final_checksum == "Checksum não encontrado.":
            print(f"Checksum final do arquivo '{file_to_get}' não encontrado.")
            return

        chunk_to_peers = {}
        for peer, chunk_id, chunk_name, chunk_checksum in chunks:
            if peer != local_peer_name:
                if not os.path.exists(chunk_name):
                    if chunk_name not in chunk_to_peers:
                        chunk_to_peers[chunk_name] = []
                    chunk_to_peers[chunk_name].append((peer, chunk_id, chunk_name, chunk_checksum))

        if not chunk_to_peers:
            print(f"Não há chunks para baixar do arquivo '{file_to_get}'. Talvez você já tenha todos os chunks.")
            return

        # Resto do código permanece igual...
        chunks_to_download = []
        for chunk_name, peer_list in chunk_to_peers.items():
            selected_peer = random.choice(peer_list)
            chunks_to_download.append(selected_peer)

        random.shuffle(chunks_to_download)

        start_time = time.time()

        downloaded_chunks = set()
        in_progress_chunks = set()
        chunk_locks = {chunk[2]: threading.Lock() for chunk in chunks_to_download}

        downloaded_lock = threading.Lock()
        in_progress_lock = threading.Lock()

        active_workers = threading.Semaphore(num_connections)
        chunks_queue = queue.Queue()

        for chunk in chunks_to_download:
            chunks_queue.put(chunk)

        failed_chunks = queue.Queue()

        def worker():
            while True:
                with active_workers:
                    try:
                        chunk_info = chunks_queue.get_nowait()
                    except queue.Empty:
                        break

                    peer, chunk_id, chunk_name, chunk_checksum = chunk_info

                    with in_progress_lock:
                        if chunk_name in in_progress_chunks:
                            chunks_queue.task_done()
                            continue
                        in_progress_chunks.add(chunk_name)

                    try:
                        with downloaded_lock:
                            if chunk_name in downloaded_chunks:
                                chunks_queue.task_done()
                                continue

                        peer_addr = tracker.execute('get_peer_address', peer)
                        if peer_addr == "Peer não encontrado.":
                            failed_chunks.put((chunk_name, "Peer não encontrado"))
                            continue

                        peer_proxy = PeerConnectionPool().get_connection(peer_addr)
                        print(f"Baixando {chunk_name} de {peer}...")

                        response = peer_proxy.send_chunk(chunk_name)

                        if isinstance(response, xmlrpc.client.Binary):
                            data = response.data
                            if chunk_checksum:
                                downloaded_checksum = calculate_checksum(data)
                                if downloaded_checksum != chunk_checksum:
                                    failed_chunks.put((chunk_name, "Checksum inválido"))
                                    continue

                            with chunk_locks[chunk_name]:
                                with open(chunk_name, "wb") as f:
                                    f.write(data)

                            tracker.execute('register_chunks', local_peer_name, file_to_get,
                                         [(chunk_id, chunk_name, chunk_checksum)],
                                         final_checksum)

                            with downloaded_lock:
                                downloaded_chunks.add(chunk_name)
                        else:
                            failed_chunks.put((chunk_name, response))

                    except Exception as e:
                        failed_chunks.put((chunk_name, str(e)))

                    finally:
                        with in_progress_lock:
                            in_progress_chunks.discard(chunk_name)
                        chunks_queue.task_done()

        threads = []
        for _ in range(num_connections):
            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()
            threads.append(thread)

        chunks_queue.join()

        end_time = time.time()
        duration = end_time - start_time

        if not failed_chunks.empty():
            print("\nFalhas no download:")
            while not failed_chunks.empty():
                chunk_name, error = failed_chunks.get()
                print(f"- {chunk_name}: {error}")
            return

        print("\nReagrupando o arquivo...")
        assemble_file(file_to_get)
        assembled_file = f"{file_to_get}.assembled"

        with open(assembled_file, "rb") as f:
            assembled_checksum = calculate_checksum(f.read())

        if assembled_checksum == final_checksum:
            print("Arquivo baixado com sucesso e checksum verificado!")
            if not os.path.exists(file_to_get):
                os.rename(assembled_file, file_to_get)
            else:
                os.remove(assembled_file)

            local_chunks = split_file(file_to_get)
            tracker.execute('register_chunks', local_peer_name, file_to_get, local_chunks, final_checksum)
        else:
            print("Erro: checksum do arquivo final não confere!")
            os.remove(assembled_file)

        print(f"\nTempo de transferência para {num_connections} conexões: {duration:.2f} segundos")

    except Exception as e:
        print(f"Erro durante o download: {e}")


def send_heartbeat(proxy, name):
    failures = 0
    max_failures = 3
    while not exit_flag.is_set():
        try:
            transport = xmlrpc.client.Transport(use_datetime=True)
            transport.timeout = 10
            with xmlrpc.client.ServerProxy('http://localhost:9000', 
                                         transport=transport) as temp_proxy:
                temp_proxy.heartbeat(name)
                failures = 0
                time.sleep(5)
        except Exception as e:
            failures += 1
            if failures >= max_failures:
                print(f"Perdeu conexão com o tracker após {failures} tentativas")
                exit_flag.set()
                break
            time.sleep(2)

def connect_to_tracker(name):
    transport = xmlrpc.client.Transport(use_datetime=True)
    transport.timeout = 10
    
    try:
        proxy = xmlrpc.client.ServerProxy('http://localhost:9000', 
                                        transport=transport,
                                        allow_none=True)
        response = proxy.register(name, f"http://localhost:{PORT}")
        if response.startswith("Error:"):
            print(response)
            return False
            
        print(response)
        
        # Compartilha arquivos existentes
        share_all_txt_files(proxy, name)
        
        # Inicia thread de heartbeat
        heartbeat_thread = threading.Thread(target=send_heartbeat, 
                                         args=(proxy, name),
                                         daemon=True)
        heartbeat_thread.start()
        
        # Inicia servidor local
        server = SimpleXMLRPCServer(('localhost', PORT), 
                                  allow_none=True,
                                  logRequests=False)
        server.timeout = 10
        server.register_function(send_chunk, 'send_chunk')
        server.register_function(get_files, 'get_files')
        server.register_function(receive_message, 'receive_message')
        
        server_thread = threading.Thread(target=server.serve_forever, 
                                      daemon=True)
        server_thread.start()
        
        print(f"Peer iniciado no endereço http://localhost:{PORT}")
        
        while not exit_flag.is_set():
            try:
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
                    original_file = input("Digite o nome original do arquivo: ").strip()
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
                    
            except xmlrpc.client.Error as e:
                print(f"Erro de comunicação: {e}")
                time.sleep(1)
            except Exception as e:
                print(f"Erro: {e}")
                time.sleep(1)
                
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
