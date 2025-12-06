import socket
import threading
import json
import time


HOST = '0.0.0.0'
PORT = 5555
WIDTH = 256
HEIGHT = 256
TICK_RATE = 1 / 30  # 30 updates por segundo

class GameServer:
    def __init__(self):
        # Estado do jogo: Posições e Direções
        self.players = {0: {'x': 20, 'y': 100, 'dir': '2', 'dead': False, 'rastro': []}, 
                        1: {'x': 230, 'y': 100, 'dir': '1', 'dead': False, 'rastro': []}}
        
        # Buffer de inputs: Guarda a ultima intenção do jogador
        self.last_inputs = {0: None, 1: None} 
        self.conns = {}
        self.game_started = False

    def handle_client_input(self, pid, conn):
        # Essa função roda em paralelo para cada jogador
        while True:
            try:
                data = conn.recv(1024).decode().strip()
                if not data: break # Cliente desconectou
                
                # Só atualizamos o buffer
                commands = data.split('\n')
                if commands:
                    self.last_inputs[pid] = commands[-1] # Pega o último comando válido
            except:
                break
        print(f"Player {pid} desconectado.")
    
    def process_turn(self):
        for pid in self.players:
            player = self.players[pid]
            direction = player['dir']
            inp = self.last_inputs[pid]


            # Atualiza direção baseado no input recebido
            if inp == 'UP' and direction != '3':
                direction = '0'
            elif inp == 'DOWN' and direction != '0':
                direction = '3'
            elif inp == 'LEFT' and direction != '2':
                direction = '1'
            elif inp == 'RIGHT' and direction != '1':
                direction = '2'
            player['dir'] = direction

            # Move (Lógica do Player.update)
            if direction == '0':
                player['y'] -= 2
            elif direction == '3':
                player['y'] += 2
            elif direction == '1':
                player['x'] -= 2
            else:  # direction == '2'
                player['x'] += 2

            # Garante que a posição não ultrapasse a tela
            player['x'] = max(player['x'], 0)
            player['x'] = min(player['x'], WIDTH)
            player['y'] = max(player['y'], 0)
            player['y'] = min(player['y'], HEIGHT)

            # Adiciona ao rastro
            player['rastro'].append((player['x'], player['y']))

    
    def send_state(self):
        # Envia o estado atualizado para os jogadores
        state = json.dumps(self.players) + "\n"
        for pid in self.conns:
            try:
                self.conns[pid].sendall(state.encode())
            except Exception as e:
                print(f"Erro ao enviar estado para o jogador {pid}: {e}")

    def game_loop(self):
        # O Coração do Jogo: Roda a uma velocidade fixa
        print("Loop do jogo iniciado.")
        while True:
            if len(self.conns) < 2:
                time.sleep(1) # Espera ter 2 jogadores
                continue
            
            if not self.game_started:
                print("Todos conectados! Jogo começando em 3 segundos...")
                time.sleep(3)
                self.game_started = True

            start_time = time.time()

            # 1. Processa Lógica
            self.process_turn()
            
            # 2. Envia Estado
            self.send_state()

            # 3. Dorme o restante do tempo para manter o Ritmo (TICK_RATE)
            elapsed = time.time() - start_time
            sleep_time = TICK_RATE - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, PORT))
        server.listen(2)
        print(f"Servidor iniciado em {HOST}:{PORT}, aguardando jogadores...")


        # Thread separada para o loop do jogo não bloquear as conexões
        threading.Thread(target=self.game_loop, daemon=True).start()


        # Loop de aceitação de conexões
        while True:
            conn, addr = server.accept()
            pid = len(self.conns)
            
            
            if pid >= 2: # Evita mais de 2 players
                conn.close()
                continue

            self.conns[pid] = conn
            conn.send(f"{pid}\n".encode())
            print(f"Jogador {pid} conectado de {addr}")

            # Cria uma thread só para ouvir este jogador
            t = threading.Thread(target=self.handle_client_input, args=(pid, conn), daemon=True)
            t.start()

GameServer().start()
        