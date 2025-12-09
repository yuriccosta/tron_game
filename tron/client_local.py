import socket
import json
import pyxel as py
import threading

HOST = '127.0.0.1'
PORT = 5555

class DualGameClient:
    """Cliente que conecta como AMBOS os jogadores para teste local"""
    
    def __init__(self):
        # Conecta como Player 0
        self.client0 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client0.connect((HOST, PORT))
        self.id0 = int(self.client0.recv(1024).decode().strip())
        print(f"Conectado como Player {self.id0}")
        
        # Conecta como Player 1
        self.client1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client1.connect((HOST, PORT))
        self.id1 = int(self.client1.recv(1024).decode().strip())
        print(f"Conectado como Player {self.id1}")

        # Fila de estados (só precisa escutar uma conexão, ambas recebem o mesmo estado)
        self.state_queue = [] 
        self.buffer = ""

        # Thread para escutar o servidor (usa client0)
        self.thread_escuta = threading.Thread(target=self.listen_server, daemon=True)
        self.thread_escuta.start()
        
        # Thread para drenar client1 (IMPORTANTE: evita travamento por buffer cheio)
        self.thread_drain = threading.Thread(target=self._drain_client1, daemon=True)
        self.thread_drain.start()

    def _drain_client1(self):
        """Consome e descarta dados do client1 para evitar travamento"""
        while True:
            try:
                self.client1.recv(4096)  # Lê e descarta
            except:
                break

    def listen_server(self):
        while True:
            try:
                data = self.client0.recv(4096).decode()
                if not data: break
                
                self.buffer += data
                
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if line.strip():
                        try:
                            state = json.loads(line)
                            self.state_queue.append(state)
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                print("Erro:", e)
                break

    def send_input_p0(self, key):
        """Envia input para Player 0"""
        try:
            self.client0.sendall(key.encode())
        except:
            pass

    def send_input_p1(self, key):
        """Envia input para Player 1"""
        try:
            self.client1.sendall(key.encode())
        except:
            pass


class App:
    def __init__(self):
        py.init(256, 256, title="Tron Local - P0: WASD | P1: Setas")
        self.net = DualGameClient()
        
        # Último input enviado para cada jogador
        self.last_key_p0 = None
        self.last_key_p1 = None
        self.waiting_reset = False
        
        # Guardamos o histórico localmente e as posições atuais
        self.players_local_data = {
            0: {"x": 0, "y": 0, "dead": False, "rastro": []},
            1: {"x": 0, "y": 0, "dead": False, "rastro": []}
        }
        
        # Placar
        self.score = {0: 0, 1: 0}
        self.match_winner = None
        
        py.run(self.update, self.draw)

    def update(self):
        # 0. RESET - Tecla ESPAÇO envia reset para AMBOS
        if py.btnp(py.KEY_SPACE):
            self.net.send_input_p0('RESET')
            self.net.send_input_p1('RESET')
            self.waiting_reset = True
        
        # 1. INPUT Player 0: WASD
        key_p0 = None
        if py.btn(py.KEY_W): key_p0 = 'UP'
        elif py.btn(py.KEY_S): key_p0 = 'DOWN'
        elif py.btn(py.KEY_A): key_p0 = 'LEFT'
        elif py.btn(py.KEY_D): key_p0 = 'RIGHT'

        if key_p0 and key_p0 != self.last_key_p0:
            self.net.send_input_p0(key_p0)
            self.last_key_p0 = key_p0

        # 2. INPUT Player 1: Setas
        key_p1 = None
        if py.btn(py.KEY_UP): key_p1 = 'UP'
        elif py.btn(py.KEY_DOWN): key_p1 = 'DOWN'
        elif py.btn(py.KEY_LEFT): key_p1 = 'LEFT'
        elif py.btn(py.KEY_RIGHT): key_p1 = 'RIGHT'

        if key_p1 and key_p1 != self.last_key_p1:
            self.net.send_input_p1(key_p1)
            self.last_key_p1 = key_p1

        # 3. PROCESSAR PACOTES DA REDE
        while len(self.net.state_queue) > 0:
            game_state = self.net.state_queue.pop(0)
            
            # Novo formato: {'players': {...}, 'score': {...}, 'match_winner': ...}
            players = game_state.get('players', game_state)
            
            # Converte score para chaves inteiras (JSON usa strings)
            score_raw = game_state.get('score', {})
            if score_raw:
                self.score = {int(k): v for k, v in score_raw.items()}
            
            self.match_winner = game_state.get('match_winner', None)
            
            for pid_str, p_data in players.items():
                pid = int(pid_str)
                
                # Detecta se o jogo foi reiniciado
                was_dead = self.players_local_data[pid]["dead"]
                is_dead = p_data["dead"]
                if was_dead and not is_dead:
                    self.players_local_data[0]["rastro"] = []
                    self.players_local_data[1]["rastro"] = []
                    self.waiting_reset = False
                    self.last_key_p0 = None
                    self.last_key_p1 = None
                
                # Atualiza posição atual e morte
                self.players_local_data[pid]["x"] = p_data["x"]
                self.players_local_data[pid]["y"] = p_data["y"]
                self.players_local_data[pid]["dead"] = p_data["dead"]
                
                # Adiciona rastro
                if p_data["rastro"]:
                    self.players_local_data[pid]["rastro"].extend(p_data["rastro"])

    def draw(self):
        py.cls(0)

        if not self.players_local_data[0]["rastro"] and not self.players_local_data[1]["rastro"]:
            py.text(80, 100, "Conectando...", 7)
            return
        
        # Legenda de controles e placar
        py.text(5, 5, "P0 (verde): WASD", 11)
        py.text(5, 15, "P1 (vermelho): Setas", 8)
        
        # Placar centralizado
        score_text = f"{self.score[0]} x {self.score[1]}"
        py.text(115, 5, score_text, 7)
        
        # Desenha baseado nos dados locais
        for pid, p_data in self.players_local_data.items():
            color = 11 if pid == 0 else 8 

            # Desenha rastro
            for r in p_data["rastro"]:
                py.rect(r[0], r[1], 2, 2, color)
            
            # Desenha cabeça
            py.rect(p_data["x"], p_data["y"], 2, 2, 7)
        
        # Mensagens de fim de rodada/partida
        if self.players_local_data[0]["dead"] or self.players_local_data[1]["dead"]:
            if self.match_winner is not None:
                winner_text = f"PLAYER {self.match_winner} VENCEU!"
                py.text(75, 100, winner_text, 10)
                py.text(65, 115, "ESPACO para nova partida", 7)
            else:
                py.text(80, 110, "Fim da rodada!", 8)
                py.text(60, 125, "ESPACO para continuar", 7)

App()
