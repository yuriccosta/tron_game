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
        self.net = GameClient()
        self.last_sent_key = None
        
        # Guardamos o histórico localmente e as posições atuais
        self.players_local_data = {
            0: {"x": 0, "y": 0, "dead": False, "rastro": []},
            1: {"x": 0, "y": 0, "dead": False, "rastro": []}
        }
        
        py.run(self.update, self.draw)

    def update(self):
        # 1. INPUT
        key = None
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
            state = self.net.state_queue.pop(0)
            
            # Atualiza os dados locais com esse pacote
            for pid_str, p_data in state.items():
                pid = int(pid_str)
                
                # Atualiza posição atual e morte
                self.players_local_data[pid]["x"] = p_data["x"]
                self.players_local_data[pid]["y"] = p_data["y"]
                self.players_local_data[pid]["dead"] = p_data["dead"]
                
                # Adiciona os novos pedaços de rastro ao nosso histórico
                # O servidor manda [[x,y]], nós adicionamos isso à nossa lista gigante
                if p_data["rastro"]:
                    self.players_local_data[pid]["rastro"].extend(p_data["rastro"])

    def draw(self):
        py.cls(0)

        state = self.net.game_state
        if not state:
            py.text(100, 100, "Esperando Oponente...", 7)
            return
        
        # Desenha baseado nos dados locais
        for pid, p_data in self.players_local_data.items():
            color = 11 if pid == 0 else 8 

            # Desenha rastro
            for r in p_data["rastro"]:
                py.rect(r[0], r[1], 2, 2, color)
            
            # Desenha cabeça
            py.rect(p_data["x"], p_data["y"], 2, 2, 7)
            
            if p_data["dead"]:
                py.text(100, 120, "ALGUEM MORREU", 8)

App()