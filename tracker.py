from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading

clients = {}

def register(name, address):
    clients[name] = address
    return f"{name} registrado com sucesso."

def list_clients():
    return clients

def get_peer_address(name):
    if name in clients:
        return clients[name]
    else:
        return "Peer não encontrado."

def start_server():
    server = SimpleXMLRPCServer(('localhost', 8000))
    server.register_function(register, 'register')
    server.register_function(list_clients, 'list_clients')
    server.register_function(get_peer_address, 'get_peer_address')
    print("Servidor rodando na porta 8000...")
    server.serve_forever()

# Inicia o servidor em uma thread separada
threading.Thread(target=start_server).start()
