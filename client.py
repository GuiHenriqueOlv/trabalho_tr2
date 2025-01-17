import socket
import threading

def connect_to_server():
    """Conecta ao servidor e gerencia a interação com o usuário."""
    server_address = ('127.0.0.1', 5000)
    buffer_size = 1024

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(server_address)

        client_name = input("Digite seu nome de cliente: ")
        client_socket.sendall(client_name.encode())
        server_response = client_socket.recv(buffer_size).decode()
        print(server_response)

        while True:
            command = input("Digite um comando: 'list' para ver clientes, 'chat' para conversar com outro peer, 'exit' para sair.\n")
            client_socket.sendall(command.encode())

            if command == 'list':
                response = client_socket.recv(buffer_size).decode()
                print(f"Peers conectados: {response}")
            elif command == 'chat':
                peer_name = input("Digite o nome do peer para iniciar o chat: ")
                client_socket.sendall(peer_name.encode())

                response = client_socket.recv(buffer_size).decode()
                if "não encontrado" in response:
                    print(response)
                elif "aceitou" in response:
                    print(f"Conectando-se com {peer_name}...")
                    start_chat(client_socket, peer_name, buffer_size, response)
                elif "recusou" in response:
                    print(f"{peer_name} recusou seu pedido de chat.")
            elif command == 'exit':
                break
            else:
                print("Comando não reconhecido. Tente novamente.")

def start_chat(client_socket, peer_name, buffer_size, peer_address):
    """Gerencia a troca de mensagens com o peer."""
    
    # Extrai o IP e a porta do peer
    peer_ip, peer_port = peer_address.split(":")
    peer_port = int(peer_port)
    
    # Função para enviar mensagens
    def send_messages(peer_socket):
        while True:
            msg = input("Você: ")
            peer_socket.sendall(msg.encode())
            if msg.lower() == 'exit':
                break

    # Função para receber mensagens
    def receive_messages(peer_socket):
        while True:
            msg = peer_socket.recv(buffer_size).decode().strip()
            if msg.lower() == 'exit' or not msg:
                print(f"{peer_name} saiu do chat.")
                break
            print(f"{peer_name}: {msg}")

    # Criando socket de escuta para o peer
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
        peer_socket.connect((peer_ip, peer_port))
        print(f"Conectado com {peer_name}.")

        # Criando threads para enviar e receber mensagens simultaneamente
        threading.Thread(target=send_messages, args=(peer_socket,), daemon=True).start()
        threading.Thread(target=receive_messages, args=(peer_socket,), daemon=True).start()

if __name__ == "__main__":
    connect_to_server()
