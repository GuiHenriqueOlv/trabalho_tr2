import random
import string

def create_big_text_file(filename, size_in_mb):
    """
    Cria um arquivo de texto grande com conteúdo aleatório.
    :param filename: Nome do arquivo a ser criado.
    :param size_in_mb: Tamanho desejado do arquivo em megabytes.
    """
    with open(filename, 'w') as file:
        # 1 MB é aproximadamente 1.000.000 bytes
        target_size = size_in_mb * 1_000_000  
        current_size = 0

        # Escreve conteúdo até atingir o tamanho desejado
        while current_size < target_size:
            # Gera uma linha de texto aleatório (com cerca de 100 caracteres por linha)
            line = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=100)) + '\n'
            file.write(line)
            current_size += len(line)
    
    print(f"Arquivo '{filename}' criado com sucesso, com aproximadamente {size_in_mb} MB.")

# Criar um arquivo de 50 MB
create_big_text_file("bigfile.txt", 50)
