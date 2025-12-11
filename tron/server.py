import socket
import threading
import json
import time

HOST = '0.0.0.0'
PORT = 5555
WIDTH = 256
HEIGHT = 256
TICK_RATE = 1 / 30

class GameServer:
    def __init__(self):
        # Estado inicial
        self.players = {}
        self.score = {0: 0, 1: 0}
        self.match_winner = None
        self.last_inputs = {0: None, 1: None}
        self.conns = {} # Dicionário {id: socket}
        
        # LOBBY E CORES
        self.lobby_colors = {0: 0, 1: 1} # Default: P0 Verde, P1 Vermelho
        self.players_ready = {0: False, 1: False}
        self.game_started = False
        
        self.reset_requests = {0: False, 1: False}
        
        # Inicializa as posições
        self.reset_game(full_reset=True)

    def reset_game(self, full_reset=False):
        """Reinicia posições e estados. full_reset=True zera o placar."""
        self.players = {
            0: {'x': 20, 'y': 100, 'dir': '2', 'dead': False, 'rastro': [], 'rastro_completo': []}, 
            1: {'x': 230, 'y': 100, 'dir': '1', 'dead': False, 'rastro': [], 'rastro_completo': []}
        }
        self.last_inputs = {0: None, 1: None}
        self.reset_requests = {0: False, 1: False}

        if full_reset:
            self.score = {0: 0, 1: 0}
            self.match_winner = None
            print("Jogo resetado completamente.")
        else:
            print("Nova rodada iniciada.")

    def handle_client_input(self, pid, conn):
        """Gerencia a conexão de UM jogador."""
        try:
            while True:
                data = conn.recv(1024).decode().strip()
                if not data: break 
                
                commands = data.split('\n')
                for cmd in commands:
                    if not cmd: continue

                    # --- COMANDOS DO LOBBY ---
                    if cmd.startswith("COLOR:"):
                        if not self.game_started:
                            wanted = int(cmd.split(":")[1])
                            # Verifica se o outro jogador já tem essa cor
                            other_pid = 1 - pid
                            if self.lobby_colors.get(other_pid) != wanted:
                                self.lobby_colors[pid] = wanted
                                # Se mudou de cor, tira o "Pronto"
                                self.players_ready[pid] = False

                    elif cmd == "READY":
                        if not self.game_started:
                            self.players_ready[pid] = True

                    # --- COMANDOS DO JOGO ---
                    elif cmd == 'RESET':
                        self.try_reset(pid)
                    else:
                        self.last_inputs[pid] = cmd
        except:
            pass # Erros de conexão normais quando fecha a janela
        finally:
            # --- ÁREA DE LIMPEZA ---
            print(f"Player {pid} desconectou.")
            # 1. Remove da lista de conexões ativas
            if pid in self.conns:
                del self.conns[pid]
            
            # 2. Para o jogo imediatamente
            self.game_started = False
            
            # 3. Fecha o socket para garantir
            try:
                conn.close()
            except:
                pass
            
            # 4. Reseta o jogo para quando o próximo entrar, começar limpo
            self.reset_game(full_reset=True)

    def try_reset(self, pid):
        self.reset_requests[pid] = True
        if self.reset_requests[0] and self.reset_requests[1]:
            full_reset = self.match_winner is not None
            self.reset_game(full_reset)

    def process_turn(self):
        # Se não tem 2 jogadores ou alguém morreu, não processa movimento
        if len(self.conns) < 2 or self.players[0]['dead'] or self.players[1]['dead']:
            return
        
        # Se alguém morreu, não move mais até resetar
        if self.players[0]['dead'] or self.players[1]['dead']:
            return

        # 1. Movimentação
        for pid in self.players:
            player = self.players[pid]
            direction = player['dir']
            inp = self.last_inputs[pid]

            # Validação de input (impedir volta em U)
            if inp == 'UP' and direction != '3': direction = '0'
            elif inp == 'DOWN' and direction != '0': direction = '3'
            elif inp == 'LEFT' and direction != '2': direction = '1'
            elif inp == 'RIGHT' and direction != '1': direction = '2'
            player['dir'] = direction

            # Atualiza posição
            if direction == '0': player['y'] -= 2
            elif direction == '3': player['y'] += 2
            elif direction == '1': player['x'] -= 2
            elif direction == '2': player['x'] += 2

        # 2. Colisão
        for pid in self.players:
            player = self.players[pid]
            pos_atual = [player['x'], player['y']]
            
            # Borda
            if player['x'] <= 0 or player['x'] >= WIDTH - 1 or player['y'] <= 0 or player['y'] >= HEIGHT - 1:
                player['dead'] = True
                continue

            # Rastros
            for other_pid, other_player in self.players.items():
                if pos_atual in other_player['rastro_completo']:
                    player['dead'] = True
                    break
        
        # Colisão frontal
        if self.players[0]['x'] == self.players[1]['x'] and self.players[0]['y'] == self.players[1]['y']:
            self.players[0]['dead'] = True
            self.players[1]['dead'] = True

        # 3. Atualiza Placar e Histórico
        any_dead = self.players[0]['dead'] or self.players[1]['dead']
        if any_dead and self.match_winner is None:
            if self.players[0]['dead'] and not self.players[1]['dead']:
                self.score[1] += 1
            elif self.players[1]['dead'] and not self.players[0]['dead']:
                self.score[0] += 1
            
            # Checa vitória da partida (Melhor de 3)
            if self.score[0] >= 2: self.match_winner = 0
            elif self.score[1] >= 2: self.match_winner = 1
        
        # Adiciona rastro (Delta para rede + Histórico para colisão)
        for pid in self.players:
            if not self.players[pid]['dead']:
                pos = [self.players[pid]['x'], self.players[pid]['y']]
                self.players[pid]['rastro_completo'].append(pos)
                self.players[pid]['rastro'] = [pos] # Envia só o novo

    def send_state(self):
        # Filtra dados para economizar rede
        players_to_send = {}
        for pid, p_data in self.players.items():
            players_to_send[pid] = {
                'x': p_data['x'],
                'y': p_data['y'],
                'dir': p_data['dir'],
                'dead': p_data['dead'],
                'rastro': p_data['rastro']
            }
        
        state = json.dumps({
            'players': players_to_send,
            'score': self.score,
            'match_winner': self.match_winner,
            'lobby': {
                'colors': self.lobby_colors,
                'ready': self.players_ready,
                'started': self.game_started
            }
        }) + "\n"

        # IMPORTANTE: list(self.conns) cria uma cópia das chaves.
        # Isso evita erro se um cliente desconectar ENQUANTO estamos enviando.
        for pid in list(self.conns):
            try:
                self.conns[pid].sendall(state.encode())
            except:
                pass # Se falhar, o handle_client_input vai limpar depois

    def game_loop(self):
        print("Loop de jogo iniciado.")
        while True:
            # Pausa se não tiver 2 jogadores
            if len(self.conns) < 2:
                self.game_started = False
                time.sleep(1)
                continue
            
            # Sequência de início
            if not self.game_started:
                # Verifica se ambos estão prontos
                if self.players_ready.get(0) and self.players_ready.get(1):
                    print("Jogadores prontos! Iniciando a partida...")
                    self.game_started = True
                    self.reset_game(full_reset=False) # Garante posições iniciais
                    time.sleep(0.5)

            start_time = time.time()
            self.process_turn()
            self.send_state()
            
            # Mantém FPS estável
            elapsed = time.time() - start_time
            sleep_time = TICK_RATE - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Permite reutilizar a porta 5555 imediatamente se o server cair
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Desativa o Nagle's Algorithm no socket principal
        server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        server.bind((HOST, PORT))
        server.listen(2)
        print(f"Servidor ONLINE em {HOST}:{PORT}")

        threading.Thread(target=self.game_loop, daemon=True).start()

        while True:
            try:
                conn, addr = server.accept()
                # Desativa o delay para CADA jogador que entra
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                # --- LÓGICA DE SLOT INTELIGENTE ---
                # Procura qual ID (0 ou 1) está livre
                pid = -1
                if 0 not in self.conns:
                    pid = 0
                elif 1 not in self.conns:
                    pid = 1
                
                # Se o servidor estiver cheio
                if pid == -1:
                    print(f"Rejeitando conexão de {addr}: Servidor Cheio")
                    conn.close()
                    continue

                self.conns[pid] = conn
                conn.send(f"{pid}\n".encode())
                print(f"Jogador {pid} conectado de {addr}")

                # Inicia thread dedicada
                threading.Thread(target=self.handle_client_input, args=(pid, conn), daemon=True).start()
            except Exception as e:
                print(f"Erro no accept: {e}")

if __name__ == "__main__":
    GameServer().start()