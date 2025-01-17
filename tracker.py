import socket
import threading

clients = {}

def handle_client(client_socket, client_address):
    print(f"Novo cliente conectado: {client_address}")
    client_socket.sendall("Comandos: 'list' para ver clientes, 'chat' para conversar com outro peer, 'exit' para sair.\n".encode())
    
    client_name = client_socket.recv(1024).decode().strip()
    clients[client_name] = client_address
    
    try:
        while True:
            msg = client_socket.recv(1024).decode().strip()
            if msg == 'list':
                send_client_list(client_socket)
            elif msg == 'chat':
                initiate_chat(client_socket, client_name)
            elif msg == 'exit':
                break
            else:
                client_socket.sendall("Comando não reconhecido.".encode())
    except Exception as e:
        print(f"Erro na comunicação com {client_name}: {e}")
    finally:
        del clients[client_name]
        client_socket.close()

def send_client_list(client_socket):
    client_socket.sendall(f"Peers conectados: {clients}".encode())

def initiate_chat(client_socket, client_name):
    client_socket.sendall("Digite o nome do peer para chat: ".encode())
    peer_name = client_socket.recv(1024).decode().strip()
    
    if peer_name in clients:
        peer_address = clients[peer_name]
        send_chat_request(client_socket, client_name, peer_name, peer_address)
    else:
        client_socket.sendall(f"Peer {peer_name} não encontrado.".encode())

def send_chat_request(client_socket, client_name, peer_name, peer_address):
    """Envia a solicitação de chat para o Peer 2."""
    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer_socket.connect(peer_address)
    
    try:
        peer_socket.sendall(f"{client_name} quer iniciar um chat com você. Digite 'aceitar' para aceitar ou 'recusar' para recusar.".encode())
        
        # Aguarda a resposta do Peer 2
        response = peer_socket.recv(1024).decode().strip()
        if response == "aceitar":
            client_socket.sendall(f"{peer_name} aceitou seu pedido de chat.".encode())
            # Envia os detalhes da conexão para ambos os peers
            start_chat(client_socket, peer_name, peer_address)
        else:
            client_socket.sendall(f"{peer_name} recusou seu pedido de chat.".encode())
    except Exception as e:
        client_socket.sendall(f"Erro ao enviar solicitação para {peer_name}: {e}".encode())
    finally:
        peer_socket.close()

def start_chat(client_socket, peer_name, peer_address):
    """Inicia o chat entre os clientes."""
    try:
        # Envia o endereço do peer (IP e porta) para o cliente
        peer_port = peer_address[1]
        client_socket.sendall(f"{peer_address[0]}:{peer_port}".encode())
    except Exception as e:
        client_socket.sendall(f"Erro ao iniciar chat com {peer_name}: {e}".encode())

def run_server(host='127.0.0.1', port=5000):
    """Inicia o servidor e aguarda conexões de clientes."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"Servidor ouvindo em {host}:{port}")
    
    while True:
        client_socket, client_address = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_handler.start()

if __name__ == "__main__":
    run_server()
