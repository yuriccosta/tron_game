import socket
import json
import pyxel as py
import threading

HOST = '172.20.10.3'
PORT = 5555

PALETTE_COLORS = [11, 8, 12, 10]

class GameClient:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # [NOVO] Desativa o delay antes mesmo de conectar
        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.client.connect((HOST, PORT))
        # Recebe o ID do jogador (0 ou 1)
        self.my_id = int(self.client.recv(1024).decode().strip())
        print(f"Sou o Player {self.my_id}")

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
                            state = json.loads(line)
                            self.state_queue.append(state)
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                print("Erro:", e)
                break

    def send_input(self, key):
        try:
            self.client.sendall((key + "\n").encode())
        except:
            pass

class App:
    def __init__(self):
        py.init(256, 256, title="Tron Client")
        try:
            py.load("tron.pyxres")
        except:
            pass # Evita crash se não tiver o arquivo de recursos
            
        py.mouse(True)

        # Controles de Estado
        self.in_game = False         # False = Menu Inicial, True = Lobby ou Jogo
        self.connected_to_server = False
        
        self.net = None
        self.last_sent_key = None
        self.waiting_reset = False   # Se já apertei espaço no final

        # Dados do Jogo Local (Replica do servidor)
        self.players_local_data = {
            0: {"x": 0, "y": 0, "dead": False, "rastro": [], "dir": "0"},
            1: {"x": 0, "y": 0, "dead": False, "rastro": [], "dir": "0"}
        }
        self.score = {0: 0, 1: 0}
        self.match_winner = None
        
        # Dados do Lobby
        self.lobby_colors = {0: 0, 1: 1} # IDs das cores (0..3)
        self.lobby_ready = {0: False, 1: False}
        self.game_started = False
        self.my_selection_idx = 0 

        # Config do Botão do Menu (Igual ao Original)
        self.botao_x = 98
        self.botao_y = 130
        self.botao_w = 60
        self.botao_h = 20

        py.run(self.update, self.draw)

    def connect_to_server(self):
        try:
            self.net = GameClient()
            self.connected_to_server = True
            self.in_game = True
            
            # Tenta sincronizar a seleção local com a cor padrão do ID
            self.my_selection_idx = self.net.my_id 
            self.net.send_input(f"COLOR:{self.my_selection_idx}")
        except:
            print("Servidor offline!")

    def update(self):
        # -----------------------------------
        # 1. MENU INICIAL (OFFLINE)
        # -----------------------------------
        if not self.in_game:
            mouse_x, mouse_y = py.mouse_x, py.mouse_y
            mouse_over = (
                mouse_x >= self.botao_x and mouse_x <= self.botao_x + self.botao_w and 
                mouse_y >= self.botao_y and mouse_y <= self.botao_y + self.botao_h
            )
            # Clique ou Enter conecta
            if (mouse_over and py.btnp(py.MOUSE_BUTTON_LEFT)) or py.btnp(py.KEY_RETURN):
                self.connect_to_server()
            return

        # -----------------------------------
        # 2. LER DADOS DA REDE
        # -----------------------------------
        while len(self.net.state_queue) > 0:
            game_state = self.net.state_queue.pop(0)
            
            # --- Atualiza Lobby ---
            lobby = game_state.get('lobby', {})
            if lobby:
                # Converte chaves de string para int
                self.lobby_colors = {int(k): v for k, v in lobby.get('colors', {}).items()}
                self.lobby_ready = {int(k): v for k, v in lobby.get('ready', {}).items()}
                
                # Verifica se o jogo começou
                server_started = lobby.get('started', False)
                if server_started and not self.game_started:
                    # Início da partida! Limpa tela.
                    self.game_started = True
                    self.players_local_data[0]["rastro"] = []
                    self.players_local_data[1]["rastro"] = []
                    self.waiting_reset = False

            # Se o jogo ainda não começou no servidor, não atualiza posições
            if not self.game_started:
                continue

            # --- Atualiza Jogo ---
            players = game_state.get('players', {})
            score_raw = game_state.get('score', {})
            if score_raw: self.score = {int(k): v for k, v in score_raw.items()}
            
            self.match_winner = game_state.get('match_winner', None)
            
            for pid_str, p_data in players.items():
                pid = int(pid_str)
                
                # Detecta reinício de rodada (passou de morto para vivo)
                was_dead = self.players_local_data[pid]["dead"]
                is_dead = p_data["dead"]
                if was_dead and not is_dead:
                    self.players_local_data[0]["rastro"] = []
                    self.players_local_data[1]["rastro"] = []
                    self.waiting_reset = False
                    self.last_sent_key = None
                
                # Sincroniza dados
                self.players_local_data[pid]["x"] = p_data["x"]
                self.players_local_data[pid]["y"] = p_data["y"]
                self.players_local_data[pid]["dead"] = p_data["dead"]
                self.players_local_data[pid]["dir"] = p_data["dir"]
                
                if p_data["rastro"]:
                    self.players_local_data[pid]["rastro"].extend(p_data["rastro"])

        # -----------------------------------
        # 3. INPUTS (LOBBY VS JOGO)
        # -----------------------------------
        
        # LOBBY: Seleção de Cor
        if not self.game_started:
            # Se eu já dei Ready, não mexo em nada, só posso cancelar (opcional)
            if self.lobby_ready.get(self.net.my_id):
                return

            change = 0
            if py.btnp(py.KEY_LEFT): change = -1
            elif py.btnp(py.KEY_RIGHT): change = 1

            if change != 0:
                # Tenta achar cor livre
                curr = self.my_selection_idx
                for _ in range(4): # 4 tentativas (ciclo)
                    curr = (curr + change) % 4
                    # Checa se oponente tem essa cor
                    opp_id = 1 - self.net.my_id
                    if self.lobby_colors.get(opp_id) != curr:
                        self.my_selection_idx = curr
                        self.net.send_input(f"COLOR:{curr}")
                        break
            
            # Confirmar (Ready)
            if py.btnp(py.KEY_RETURN) or py.btnp(py.KEY_KP_ENTER):
                self.net.send_input("READY")
            return

        # JOGO: Movimentação e Reset
        if py.btnp(py.KEY_SPACE):
            self.net.send_input('RESET')
            self.waiting_reset = True
        
        key = None
        if py.btn(py.KEY_UP): key = 'UP'
        elif py.btn(py.KEY_DOWN): key = 'DOWN'
        elif py.btn(py.KEY_LEFT): key = 'LEFT'
        elif py.btn(py.KEY_RIGHT): key = 'RIGHT'

        if key and key != self.last_sent_key:
            self.net.send_input(key)
            self.last_sent_key = key

    def draw(self):
        py.cls(0)

        # -----------------------------------
        # TELA 1: MENU ORIGINAL
        # -----------------------------------
        if not self.in_game:
            # Cabeça Tron (Image bank 1)
            py.blt(75, 80, 1, 10, 22, 112, 64)

            # Botão
            mx, my = py.mouse_x, py.mouse_y
            mouse_over = (
                mx >= self.botao_x and mx <= self.botao_x + self.botao_w and 
                my >= self.botao_y and my <= self.botao_y + self.botao_h
            )
            cor_botao = 12 if mouse_over else 3
            
            py.rect(self.botao_x, self.botao_y, self.botao_w, self.botao_h, cor_botao)
            py.rectb(self.botao_x, self.botao_y, self.botao_w, self.botao_h, 7)
            py.text(self.botao_x + 20, self.botao_y + 8, "START", 7)
            return 

        # -----------------------------------
        # TELA 2: LOBBY (Seleção Lado a Lado)
        # -----------------------------------
        if not self.game_started:
            py.text(100, 30, "LOBBY", 7)
            py.text(70, 45, "Escolha sua cor", 6)

            start_x = 68
            gap = 35
            base_y = 100

            # Desenha as 4 cores lado a lado
            for i in range(4):
                color_val = PALETTE_COLORS[i]
                x_pos = start_x + (i * gap)
                
                # Desenha quadrado da cor
                py.rect(x_pos, base_y, 20, 20, color_val)
                
                # Identifica quem escolheu
                is_me = (self.lobby_colors.get(self.net.my_id) == i)
                is_opp = (self.lobby_colors.get(1 - self.net.my_id) == i)

                if is_me:
                    py.rectb(x_pos-2, base_y-2, 24, 24, 7) # Borda Branca
                    py.text(x_pos+5, base_y+25, "EU", 7)
                
                if is_opp:
                    # Desenha um X sobre a cor
                    py.line(x_pos, base_y, x_pos+20, base_y+20, 0)
                    py.line(x_pos+20, base_y, x_pos, base_y+20, 0)
                    py.text(x_pos+5, base_y-10, "P" + str(1 - self.net.my_id), 8)

            # Mensagem de Status
            ready_me = self.lobby_ready.get(self.net.my_id)
            ready_opp = self.lobby_ready.get(1 - self.net.my_id)
            
            if ready_me:
                py.text(90, 150, "VOCE ESTA PRONTO!", 11)
                if not ready_opp:
                    py.text(60, 165, "Aguardando oponente...", 7)
            else:
                py.text(55, 150, "Setas: Mover | Enter: Confirmar", 7)
                
            return

        # -----------------------------------
        # TELA 3: JOGO (Com Palette Swap)
        # -----------------------------------
        
        # Placar
        score_text = f"P0 {self.score[0]} x {self.score[1]} P1"
        py.text(100, 5, score_text, 7)
        
        # Desenha Jogadores
        for pid in [0, 1]:
            p_data = self.players_local_data[pid]
            
            # Descobre a cor escolhida no lobby
            c_idx = self.lobby_colors.get(pid, 0)
            main_color = PALETTE_COLORS[c_idx]

            # Desenha rastro (simples retângulos)
            for r in p_data["rastro"]:
                py.rect(r[0], r[1], 2, 2, main_color)
            
            # Rotação do Sprite
            ROTATE = 0
            if p_data["dir"] == '0': ROTATE = 180   # UP
            elif p_data["dir"] == '3': ROTATE = 0   # DOWN
            elif p_data["dir"] == '1': ROTATE = 90  # LEFT
            else: ROTATE = 270                      # RIGHT

            draw_x = p_data["x"] - 64 
            draw_y = p_data["y"] - 128

            # --- PALETTE SWAP ---
            # Troca as cores originais do sprite (Verde 11 e Vermelho 8) 
            # pela cor escolhida pelo jogador atual.
            py.pal(11, main_color) 
            py.pal(8, main_color)
            py.pal(12, main_color) # Caso o sprite tenha azul

            py.blt(
                draw_x, draw_y, 
                2,      # Image Bank (Carro)
                0, 16,  # u, v
                128, 256,   
                0,      # Cor transp
                ROTATE, 
                0.06    # Scale
            )
            
            # Reseta paleta para não afetar o próximo jogador/UI
            py.pal()
        
        # Mensagens de Fim
        if self.players_local_data[0]["dead"] or self.players_local_data[1]["dead"]:
            if self.match_winner is not None:
                # FIM DA PARTIDA
                winner_text = f"PLAYER {self.match_winner} VENCEU!"
                py.text(75, 100, winner_text, 10)
                py.text(65, 115, "ESPACO para nova partida", 7)
            else:
                # FIM DA RODADA
                py.text(80, 110, "Fim da rodada!", 8)
                if self.waiting_reset:
                    py.text(45, 125, "Esperando outro jogador...", 10)
                else:
                    py.text(50, 125, "ESPACO para proxima rodada", 7)

App()