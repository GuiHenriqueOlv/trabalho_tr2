from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import time
import os
import hashlib

# Dicionários para armazenar clientes e seus heartbeats
clients = {}
heartbeat_status = {}
heart = 15  # Tempo limite para heartbeat (em segundos)

# Dicionário para armazenar chunks dos arquivos
# Cada registro é uma tupla: (peer_name, chunk_id, chunk_name, checksum)
file_chunks = {}

# Dicionário para armazenar o checksum final de cada arquivo compartilhado
final_file_checksums = {}

def register(name, address):
    """ Registra um novo cliente no tracker """
    if name in clients:
        return f"Error: O nome '{name}' já está em uso. Escolha outro."
    clients[name] = address
    heartbeat_status[name] = time.time()
    return f"{name} registrado com sucesso."

def list_clients():
    """ Retorna a lista de clientes conectados ao tracker e remove os peers inativos.
        Ao remover um peer, também remove seus chunks do dicionário file_chunks.
    """
    for name in list(heartbeat_status.keys()):
        if time.time() - heartbeat_status[name] > heart:
            print(f"O peer {name} foi removido por inatividade.")
            # Remove o peer dos dicionários de clientes e heartbeats
            del clients[name]
            del heartbeat_status[name]
            # Remove os chunks registrados pertencentes a este peer
            for file in list(file_chunks.keys()):
                # Filtra removendo os chunks cujo primeiro elemento (peer_name) é o peer inativo
                file_chunks[file] = [entry for entry in file_chunks[file] if entry[0] != name]
                # Se não houver mais chunks para este arquivo, remove a chave
                if not file_chunks[file]:
                    del file_chunks[file]
    return clients

def get_peer_address(name):
    """ Retorna o endereço de um cliente pelo nome """
    return clients.get(name, "Peer não encontrado.")

def heartbeat(name):
    """ Atualiza o status do heartbeat de um cliente """
    if name in heartbeat_status:
        heartbeat_status[name] = time.time()
        return True
    return False

def register_chunks(peer_name, file_name, chunks, file_checksum=None):
    """
    Registra os chunks de um arquivo disponíveis em um peer.
    Cada chunk deve ser uma tupla (chunk_id, chunk_name, checksum).
    Se for informado o checksum final do arquivo, ele é armazenado.
    """
    if file_name not in file_chunks:
        file_chunks[file_name] = []
    for chunk in chunks:
        if len(chunk) == 3:
            chunk_id, chunk_name, checksum = chunk
        else:
            # Fallback para formato antigo
            chunk_id = None
            chunk_name, checksum = chunk
        file_chunks[file_name].append((peer_name, chunk_id, chunk_name, checksum))
    if file_checksum is not None:
        final_file_checksums[file_name] = file_checksum
    print(f"Chunks do arquivo '{file_name}' registrados no tracker (por {peer_name}).")
    return True

def get_file_chunks(file_name):
    """ Retorna a lista de chunks de um arquivo e seus respectivos peers """
    return file_chunks.get(file_name, [])

def get_file_checksum(file_name):
    """ Retorna o checksum final do arquivo, se registrado """
    return final_file_checksums.get(file_name, "Checksum não encontrado.")

def send_message(peer_name, message):
    """ Permite que um peer envie mensagens para outro """
    if peer_name in clients:
        peer_address = clients[peer_name]
        try:
            with xmlrpc.client.ServerProxy(peer_address) as peer_proxy:
                return peer_proxy.receive_message(message, peer_name)
        except Exception as e:
            return f"Erro ao enviar mensagem para {peer_name}: {e}"
    return f"Erro: Peer '{peer_name}' não encontrado."

def start_server():
    """ Inicia o servidor XML-RPC """
    server = SimpleXMLRPCServer(('localhost', 9000), 
                               allow_none=True)
    server.timeout = 60
    
    # Registra as funções
    server.register_function(register, 'register')
    server.register_function(list_clients, 'list_clients')
    server.register_function(get_peer_address, 'get_peer_address')
    server.register_function(heartbeat, 'heartbeat')
    server.register_function(register_chunks, 'register_chunks')
    server.register_function(get_file_chunks, 'get_file_chunks')
    server.register_function(get_file_checksum, 'get_file_checksum')
    server.register_function(send_message, 'send_message')
    
    print("Servidor rodando na porta 9000...")
    
    while True:
        try:
            server.handle_request()
        except Exception as e:
            print(f"Erro no servidor: {e}")
            continue

if __name__ == "__main__":
    heartbeat_thread = threading.Thread(target=list_clients, daemon=True)
    heartbeat_thread.start()
    try:
        start_server()
    except KeyboardInterrupt:
        print("Servidor interrompido.")
