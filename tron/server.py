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
        # rastro: enviado ao cliente (apenas posição atual)
        # rastro_completo: usado para colisão (histórico completo)
        self.players = {
            0: {'x': 20, 'y': 100, 'dir': '2', 'dead': False, 'rastro': [], 'rastro_completo': []}, 
            1: {'x': 230, 'y': 100, 'dir': '1', 'dead': False, 'rastro': [], 'rastro_completo': []}
        }
        
        # Placar: melhor de 3 (primeiro a 2 vitórias)
        self.score = {0: 0, 1: 0}
        self.match_winner = None  # None = partida em andamento, 0 ou 1 = vencedor final
        
        # Buffer de inputs: Guarda a ultima intenção do jogador
        self.last_inputs = {0: None, 1: None} 
        self.conns = {}
        self.game_started = False
        # Rastreia quais jogadores pediram reset
        self.reset_requests = {0: False, 1: False}

    def reset_game(self, full_reset=False):
        """Reinicia o estado do jogo. full_reset=True reseta o placar também."""
        self.players = {
            0: {'x': 20, 'y': 100, 'dir': '2', 'dead': False, 'rastro': [], 'rastro_completo': []}, 
            1: {'x': 230, 'y': 100, 'dir': '1', 'dead': False, 'rastro': [], 'rastro_completo': []}
        }
        self.last_inputs = {0: None, 1: None}
        self.reset_requests = {0: False, 1: False}
        
        if full_reset:
            self.score = {0: 0, 1: 0}
            self.match_winner = None
            print("Partida reiniciada! Placar zerado.")
        else:
            print(f"Rodada reiniciada! Placar: P0 {self.score[0]} x {self.score[1]} P1")

    def try_reset(self, pid):
        """Marca que o jogador quer resetar e verifica se ambos querem"""
        self.reset_requests[pid] = True
        print(f"Player {pid} quer reiniciar...")
        
        # Se ambos pediram reset, reinicia o jogo
        if self.reset_requests[0] and self.reset_requests[1]:
            # Se a partida já teve um vencedor, reseta tudo
            full_reset = self.match_winner is not None
            self.reset_game(full_reset)

    def handle_client_input(self, pid, conn):
        # Essa função roda em paralelo para cada jogador
        while True:
            try:
                data = conn.recv(1024).decode().strip()
                if not data: break # Cliente desconectou
                
                # Só atualizamos o buffer
                commands = data.split('\n')
                if commands:
                    cmd = commands[-1]  # Pega o último comando válido
                    if cmd == 'RESET':
                        self.try_reset(pid)
                    else:
                        self.last_inputs[pid] = cmd
            except:
                break
        print(f"Player {pid} desconectado.")
    
    def process_turn(self):
        # Se alguém já morreu, não processa mais
        if self.players[0]['dead'] or self.players[1]['dead']:
            return
        
        # Primeiro: atualiza direção e posição de todos os jogadores
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

        # Segundo: verifica colisões
        for pid in self.players:
            player = self.players[pid]
            pos = [player['x'], player['y']]
            
            # Colisão com bordas
            if player['x'] <= 0 or player['x'] >= WIDTH - 1:
                player['dead'] = True
                print(f"Player {pid} colidiu com a borda horizontal!")
                continue
            if player['y'] <= 0 or player['y'] >= HEIGHT - 1:
                player['dead'] = True
                print(f"Player {pid} colidiu com a borda vertical!")
                continue
            
            # Colisão com rastros (próprio e do oponente)
            for other_pid, other_player in self.players.items():
                if pos in other_player['rastro_completo']:
                    player['dead'] = True
                    print(f"Player {pid} colidiu com o rastro do Player {other_pid}!")
                    break
        
        # Terceiro: colisão frontal (ambos na mesma posição)
        if self.players[0]['x'] == self.players[1]['x'] and self.players[0]['y'] == self.players[1]['y']:
            self.players[0]['dead'] = True
            self.players[1]['dead'] = True
            print("Colisão frontal! Ambos morreram!")
        
        # Quarto: atualiza placar se alguém morreu
        p0_dead = self.players[0]['dead']
        p1_dead = self.players[1]['dead']
        
        if (p0_dead or p1_dead) and self.match_winner is None:
            if p0_dead and not p1_dead:
                # Player 1 ganhou a rodada
                self.score[1] += 1
                print(f"Player 1 ganhou a rodada! Placar: P0 {self.score[0]} x {self.score[1]} P1")
            elif p1_dead and not p0_dead:
                # Player 0 ganhou a rodada
                self.score[0] += 1
                print(f"Player 0 ganhou a rodada! Placar: P0 {self.score[0]} x {self.score[1]} P1")
            # Empate (ambos morreram) - ninguém pontua
            
            # Verifica se alguém venceu a partida (melhor de 3 = primeiro a 2)
            if self.score[0] >= 2:
                self.match_winner = 0
                print("PLAYER 0 VENCEU A PARTIDA!")
            elif self.score[1] >= 2:
                self.match_winner = 1
                print("PLAYER 1 VENCEU A PARTIDA!")
        
        # Quinto: adiciona posição ao rastro (se ainda vivo)
        for pid in self.players:
            player = self.players[pid]
            if not player['dead']:
                pos = [player['x'], player['y']]
                player['rastro_completo'].append(pos)
                # rastro enviado ao cliente (apenas a posição atual para economizar banda)
                player['rastro'] = [pos]

    
    def send_state(self):
        # Envia o estado atualizado para os jogadores
        players_to_send = {}
        for pid, p_data in self.players.items():
            players_to_send[pid] = {
                'x': p_data['x'],
                'y': p_data['y'],
                'dir': p_data['dir'],
                'dead': p_data['dead'],
                'rastro': p_data['rastro'] # Envia somente o ultimo rastro
            }
        
        game_state = {
            'players': players_to_send,
            'score': self.score,
            'match_winner': self.match_winner
        }
            
        state = json.dumps(game_state) + "\n"
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
        