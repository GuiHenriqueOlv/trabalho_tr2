from xmlrpc.server import SimpleXMLRPCServer
import threading
import time

clients = {}
heartbeat_status = {}

def register(name, address):
    clients[name] = address
    heartbeat_status[name] = time.time()  # Record the heartbeat timestamp
    return f"{name} registrado com sucesso."

def list_clients():
    # Remove clients that haven't sent a heartbeat in the last 10 seconds
    for name in list(heartbeat_status.keys()):
        if time.time() - heartbeat_status[name] > 10:
            del clients[name]
            del heartbeat_status[name]
    return clients

def get_peer_address(name):
    return clients.get(name, "Peer não encontrado.")

def heartbeat(name):
    if name in heartbeat_status:
        heartbeat_status[name] = time.time()
        return f"Heartbeat received from {name}."
    else:
        return "Peer not registered."

def start_server():
    server = SimpleXMLRPCServer(('localhost', 9000))
    server.register_function(register, 'register')
    server.register_function(list_clients, 'list_clients')
    server.register_function(get_peer_address, 'get_peer_address')
    server.register_function(heartbeat, 'heartbeat')
    print("Servidor rodando na porta 9000...")
    server.serve_forever()

if __name__ == "__main__":
    # Start the server in a separate thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Keep the main thread alive
    try:
        print("Pressione Ctrl+C para encerrar o servidor.")
        threading.Event().wait()
    except KeyboardInterrupt:
        print("Servidor interrompido.")
