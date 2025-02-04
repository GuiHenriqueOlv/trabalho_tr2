from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import time
import os
import hashlib

# Dicionários para armazenar clientes e seus heartbeats
clients = {}
heartbeat_status = {}
heart = 30  # Tempo limite para heartbeat

# Dicionário para armazenar chunks dos arquivos
file_chunks = {}

def register(name, address):
    """ Registra um novo cliente no tracker """
    if name in clients:
        return f"Error: O nome '{name}' já está em uso. Escolha outro."
    clients[name] = address
    heartbeat_status[name] = time.time()
    return f"{name} registrado com sucesso."

def list_clients():
    """ Retorna a lista de clientes conectados ao tracker """
    for name in list(heartbeat_status.keys()):
        if time.time() - heartbeat_status[name] > heart:
            print(f"O peer {name} foi removido por inatividade.")
            del clients[name]
            del heartbeat_status[name]
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

def register_chunks(peer_name, file_name, chunks):
    """ Registra os chunks de um arquivo disponíveis em um peer """
    if file_name not in file_chunks:
        file_chunks[file_name] = []
    for chunk_name, checksum in chunks:
        file_chunks[file_name].append((peer_name, chunk_name, checksum))
    print(f"Chunks do arquivo '{file_name}' registrados no tracker.")
    return True

def get_file_chunks(file_name):
    """ Retorna a lista de chunks de um arquivo e seus respectivos peers """
    return file_chunks.get(file_name, [])

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
    server = SimpleXMLRPCServer(('localhost', 9000), allow_none=True)
    server.register_function(register, 'register')
    server.register_function(list_clients, 'list_clients')
    server.register_function(get_peer_address, 'get_peer_address')
    server.register_function(heartbeat, 'heartbeat')
    server.register_function(register_chunks, 'register_chunks')
    server.register_function(get_file_chunks, 'get_file_chunks')
    server.register_function(send_message, 'send_message')
    print("Servidor rodando na porta 9000...")
    server.serve_forever()

if __name__ == "__main__":
    heartbeat_thread = threading.Thread(target=list_clients, daemon=True)
    heartbeat_thread.start()
    try:
        start_server()
    except KeyboardInterrupt:
        print("Servidor interrompido.")
