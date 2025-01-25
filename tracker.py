from xmlrpc.server import SimpleXMLRPCServer
import threading
import time

# Dicionário que armazena os clientes registrados e seus endereços
clients = {}

# Dicionário que armazena o status do heartbeat de cada cliente
heartbeat_status = {}

# Tempo limite para heartbeat (em segundos)
heart = 30  # Heartbeat timeout

def register(name, address):
    """
    Registra um novo cliente no tracker.
    :param name: Nome do cliente
    :param address: Endereço do cliente
    :return: Mensagem de sucesso ou erro
    """
    # Verifica se o nome já está registrado
    if name in clients:
        return f"Error: O nome '{name}' já está em uso. Escolha outro."
    else:
        # Adiciona o cliente ao dicionário de clientes e inicializa o status do heartbeat
        clients[name] = address
        heartbeat_status[name] = time.time()  # Marca o timestamp do heartbeat
        return f"{name} registrado com sucesso."

def list_clients():
    """
    Retorna a lista de clientes conectados ao tracker.
    Remove automaticamente os clientes que não enviaram heartbeat dentro do tempo limite.
    :return: Dicionário de clientes ativos
    """
    # Verifica o status de heartbeat para cada cliente
    for name in list(heartbeat_status.keys()):
        if time.time() - heartbeat_status[name] > heart:
            # Remove clientes inativos
            print(f"O peer {name} foi removido por inatividade.")  # Mensagem informativa
            del clients[name]
            del heartbeat_status[name]
    return clients

def get_peer_address(name):
    """
    Retorna o endereço de um cliente pelo nome.
    :param name: Nome do cliente
    :return: Endereço do cliente ou mensagem de erro
    """
    return clients.get(name, "Peer não encontrado.")

def heartbeat(name):
    """
    Atualiza o status do heartbeat de um cliente.
    :param name: Nome do cliente
    :return: True se o cliente foi encontrado, False caso contrário
    """
    if name in heartbeat_status:
        heartbeat_status[name] = time.time()  # Atualiza o timestamp do heartbeat
        return True
    else:
        return False

def monitor_heartbeat():
    """
    Função que monitora os heartbeats de todos os clientes.
    Remove clientes que estão inativos por mais tempo do que o limite definido.
    """
    while True:
        list_clients()  # Atualiza a lista de clientes ativos
        time.sleep(heart)  # Aguarda o intervalo antes de verificar novamente

def start_server():
    """
    Inicia o servidor XML-RPC para gerenciar os clientes conectados.
    """
    server = SimpleXMLRPCServer(('localhost', 9000))  # Configura o servidor na porta 9000
    server.register_function(register, 'register')  # Registra a função de cadastro
    server.register_function(list_clients, 'list_clients')  # Registra a função de listagem
    server.register_function(get_peer_address, 'get_peer_address')  # Registra a função de busca de endereço
    server.register_function(heartbeat, 'heartbeat')  # Registra a função de heartbeat
    print("Servidor rodando na porta 9000...")  # Mensagem informativa
    server.serve_forever()  # Mantém o servidor em execução

if __name__ == "__main__":
    # Inicia a thread para monitorar os heartbeats
    heartbeat_thread = threading.Thread(target=monitor_heartbeat, daemon=True)
    heartbeat_thread.start()

    # Inicia o servidor XML-RPC
    try:
        start_server()
    except KeyboardInterrupt:
        print("Servidor interrompido.")  # Mensagem de encerramento do servidor
