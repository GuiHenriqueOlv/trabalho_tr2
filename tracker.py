from xmlrpc.server import SimpleXMLRPCServer
import threading
import time

clients = {}
heartbeat_status = {}
heart = 30  # Heartbeat timeout in seconds

def register(name, address):
    # Check if the name is already registered
    if name in clients:
        return f"Error: O nome '{name}' já está em uso. Escolha outro."
    else:
        clients[name] = address
        heartbeat_status[name] = time.time()  # Record the heartbeat timestamp
        return f"{name} registrado com sucesso."

def list_clients():
    # Remove clients that haven't sent a heartbeat in the last 30 seconds
    for name in list(heartbeat_status.keys()):
        if time.time() - heartbeat_status[name] > heart:
            print(f"O peer {name} foi removido.")  # Print the message
            del clients[name]
            del heartbeat_status[name]
    return clients

def get_peer_address(name):
    return clients.get(name, "Peer não encontrado.")

def heartbeat(name):
    if name in heartbeat_status:
        heartbeat_status[name] = time.time()
        return True
    else:
        return False

def monitor_heartbeat():
    while True:
        list_clients()  # Check for disconnected peers
        time.sleep(heart)

def start_server():
    server = SimpleXMLRPCServer(('localhost', 9000))
    server.register_function(register, 'register')
    server.register_function(list_clients, 'list_clients')
    server.register_function(get_peer_address, 'get_peer_address')
    server.register_function(heartbeat, 'heartbeat')
    print("Servidor rodando na porta 9000...")
    server.serve_forever()

if __name__ == "__main__":
    # Start the heartbeat monitoring thread
    heartbeat_thread = threading.Thread(target=monitor_heartbeat, daemon=True)
    heartbeat_thread.start()

    # Start the server
    try:
        start_server()
    except KeyboardInterrupt:
        print("Servidor interrompido.")
