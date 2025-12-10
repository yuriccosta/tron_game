import socket
import json
import pyxel as py
import threading

HOST = '127.0.0.1'
PORT = 5555

class GameClient:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((HOST, PORT))
        self.my_id = int(self.client.recv(1024).decode().strip())
        print(f"Sou o Player {self.my_id}")

        # MUDANÇA 1: Usamos uma lista para guardar TUDO que chega
        self.state_queue = [] 
        self.buffer = ""

        self.thread_escuta = threading.Thread(target=self.listen_server, daemon=True)
        self.thread_escuta.start()

    def listen_server(self):
        while True:
            try:
                data = self.client.recv(4096).decode()
                if not data: break
                
                self.buffer += data
                
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if line.strip():
                        try:
                            # MUDANÇA 2: Em vez de sobrescrever, adicionamos na fila
                            state = json.loads(line)
                            self.state_queue.append(state)
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                print("Erro:", e)
                break

    def send_input(self, key):
        try:
            self.client.sendall(key.encode())
        except:
            pass

class App:
    def __init__(self):
        py.init(256, 256, title="Tron Client")
        py.load("tron.pyxres")
        py.mouse(True)

        # Estado do jogo para controlar o menu
        self.in_game = False

        self.net = None
        self.last_sent_key = None
        self.waiting_reset = False  # Se este jogador já pediu reset

        # Dimensão e posição do botão
        self.botao_x = 98
        self.botao_y = 130
        self.botao_w = 60
        self.botao_h = 20

        # Guardamos o histórico localmente e as posições atuais
        self.players_local_data = {
            0: {"x": 0, "y": 0, "dead": False, "rastro": [], "dir": "0"},
            1: {"x": 0, "y": 0, "dead": False, "rastro": [], "dir": "0"}
        }
        
        # Placar
        self.score = {0: 0, 1: 0}
        self.match_winner = None
        
        py.run(self.update, self.draw)

    # Função para conectar ao servidor
    def connect_to_server(self):
        self.net = GameClient()
        self.in_game = True

    def update(self):
        if not self.in_game:
            # Posição do mouse
            mouse_x = py.mouse_x
            mouse_y = py.mouse_y

            # Verifica se o mouse está dentro do retângulo do botão
            mouse_over = (
                mouse_x >= self.botao_x and 
                mouse_x <= self.botao_x + self.botao_w and 
                mouse_y >= self.botao_y and 
                mouse_y <= self.botao_y + self.botao_h
            )

            # Se clicou com botão esquerdo e estava em cima do botão ou se clicar em enter
            if (mouse_over and py.btnp(py.MOUSE_BUTTON_LEFT)) or py.btnp(py.KEY_RETURN):
                self.connect_to_server()
                
            return

        # 0. RESET - Tecla ESPAÇO para pedir reiniciar
        if py.btnp(py.KEY_SPACE):
            self.net.send_input('RESET')
            self.waiting_reset = True
        
        key = None

        # Player : Setas
        if py.btn(py.KEY_UP): key = 'UP'
        elif py.btn(py.KEY_DOWN): key = 'DOWN'
        elif py.btn(py.KEY_LEFT): key = 'LEFT'
        elif py.btn(py.KEY_RIGHT): key = 'RIGHT'

        if key and key != self.last_sent_key:
            self.net.send_input(key)
            self.last_sent_key = key

        # 2. PROCESSAR PACOTES DA REDE (MUDANÇA CRUCIAL)
        # Consumimos TUDO o que está na fila da rede
        while len(self.net.state_queue) > 0:
            # Pega o pacote mais antigo (FIFO)
            game_state = self.net.state_queue.pop(0)
            
            # Novo formato: {'players': {...}, 'score': {...}, 'match_winner': ...}
            players = game_state.get('players', game_state)  # Compatibilidade
            
            # Converte score para chaves inteiras (JSON usa strings)
            score_raw = game_state.get('score', {})
            if score_raw:
                self.score = {int(k): v for k, v in score_raw.items()}
            
            self.match_winner = game_state.get('match_winner', None)
            
            # Atualiza os dados locais com esse pacote
            for pid_str, p_data in players.items():
                pid = int(pid_str)
                
                # Detecta se o jogo foi reiniciado (dead passou de True para False)
                was_dead = self.players_local_data[pid]["dead"]
                is_dead = p_data["dead"]
                if was_dead and not is_dead:
                    # Jogo reiniciou! Limpa dados locais de AMBOS os jogadores
                    self.players_local_data[0]["rastro"] = []
                    self.players_local_data[1]["rastro"] = []
                    self.waiting_reset = False
                    self.last_sent_key = None
                
                # Atualiza posição atual e morte
                self.players_local_data[pid]["x"] = p_data["x"]
                self.players_local_data[pid]["y"] = p_data["y"]
                self.players_local_data[pid]["dead"] = p_data["dead"]
                self.players_local_data[pid]["dir"] = p_data["dir"]
                
                # Adiciona os novos pedaços de rastro ao nosso histórico
                # O servidor manda [[x,y]], nós adicionamos isso à nossa lista gigante
                if p_data["rastro"]:
                    self.players_local_data[pid]["rastro"].extend(p_data["rastro"])

    def draw(self):
        py.cls(0)

        # --- DESENHO DO MENU ---
        if not self.in_game:
            # Desenha cabeça
            u, v = 10, 22
            w, h = 112, 64

            py.blt(
            75, 80, 
            1,      
            u, v,  
            w, h
            )

            # Lógica visual do botão
            mx, my = py.mouse_x, py.mouse_y
            mouse_over = (
                mx >= self.botao_x and mx <= self.botao_x + self.botao_w and 
                my >= self.botao_y and my <= self.botao_y + self.botao_h
            )

            # Mudar de cor ao passar o mouse
            if mouse_over:
               cor_botao = 12
            else:
               cor_botao = 3
            
            # Fundo do botão
            py.rect(self.botao_x, self.botao_y, self.botao_w, self.botao_h, cor_botao)
            
            # Borda do botão
            py.rectb(self.botao_x, self.botao_y, self.botao_w, self.botao_h, 7)

            # START
            py.text(self.botao_x + 20, self.botao_y + 8, "START", 7)

            return 

        if not self.players_local_data[0]["rastro"] and not self.players_local_data[1]["rastro"]:
            py.text(85, 100, "Esperando Oponente...", 7)
            return
        
        # Desenha placar no topo
        score_text = f"P0 {self.score[0]} x {self.score[1]} P1"
        py.text(100, 5, score_text, 7)
        
        # Desenha baseado nos dados locais
        for pid, p_data in self.players_local_data.items():
            color = 11 if pid == 0 else 8 

            # Desenha rastro
            for r in p_data["rastro"]:
                py.rect(r[0], r[1], 2, 2, color)
            
            '''
            # Desenha o carro
            u, v = 1, 105
            w, h = 16, 24

            draw_x = p_data["x"] - (w // 2)
            draw_y = p_data["y"] - (h // 2)

            py.blt(
            draw_x, 
            draw_y, 
            1,      
            u, v,  
            w, h,   
            8,
            0, 0.7
            )
            '''
        
        # Mensagens de fim de rodada/partida
        if self.players_local_data[0]["dead"] or self.players_local_data[1]["dead"]:
            if self.match_winner is not None:
                # Partida acabou!
                winner_text = f"PLAYER {self.match_winner} VENCEU!"
                py.text(75, 100, winner_text, 10)
                py.text(65, 115, "ESPACO para nova partida", 7)
            else:
                # Rodada acabou
                py.text(80, 110, "Fim da rodada!", 8)
                if self.waiting_reset:
                    py.text(45, 125, "Esperando outro jogador...", 10)
                else:
                    py.text(50, 125, "ESPACO para proxima rodada", 7)

App()