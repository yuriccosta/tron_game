import socket
import json
import pyxel as py
import threading

HOST = '127.0.0.1'
PORT = 5555

class GameClient:
    def __init__(self):
        # Conecta ao servidor
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((HOST, PORT))

        # Recebe ID (0 ou 1)
        self.my_id = int(self.client.recv(1024).decode().strip())
        print(f"Sou o Player {self.my_id}")

        # Estado inicial vazio até chegar algo do servidor
        self.game_state = {}

        # Thread para ouvir atualizações do servidor sem travar o loop do Pyxel
        self.thread_escuta = threading.Thread(target=self.listen_server, daemon=True)
        self.thread_escuta.start()

    def listen_server(self):
        c = 0
        while True:
            print("Funcionando listen_server")
            try:
                # Recebe o JSON
                data = self.client.recv(4096).decode()
                # Pode vir mais de um pacote colado, pegamos o último válido
                if data:
                    print(c)
                    c += 1
                    print(data)
                    parts = data.strip().split("\n")
                    last_json = parts[-1] 
                    self.game_state = json.loads(last_json)
            except Exception as e:
                print("Erro de rede:", e)
                break

    def send_input(self, key):
        self.client.sendall(key.encode())

class App:
    def __init__(self):
        py.init(256, 256, title="Tron Client")
        self.net = GameClient()
        self.last_sent_key = None
        py.run(self.update, self.draw)

    def update(self):
        # Detecta Input e Manda pra Rede
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
        
        state = self.net.game_state
        if not state:
            py.text(100, 100, "Esperando Oponente...", 7)
            return

        # Desenha os players baseados no estado recebido
        for pid_str, p_data in state.items():
            pid = int(pid_str)
            color = 11 if pid == 0 else 8 # Verde e Vermelho
            
            # Desenha rastro
            for r in p_data["rastro"]:
                py.rect(r[0], r[1], 2, 2, color)
            
            # Desenha cabeça
            py.rect(p_data["x"], p_data["y"], 2, 2, 7)
            
            if p_data["dead"]:
                py.text(100, 120, "ALGUEM MORREU", 8)

App()
