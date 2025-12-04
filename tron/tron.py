import pyxel as py

IMG_BANK = 2
COR_TRANSPARENTE = 0
SCALE = 0.07
ROTATE = 0

class Player:
    def __init__(self, x, y, direcao = 0, color=2):
        self.x = x
        self.y = y
        self.start = False
        self.w = 2
        self.h = 2
        self.rastros = []
        self.color = color
        self.direcao = direcao
        self.carro_w = 128
        self.carro_h = 256
        self.carro_u = 0
        self.carro_v = 16

    def update(self):
        if py.btn(py.KEY_SPACE):
            self.start = True

        if self.start is False:
            return

        # Atualiza direcao
        if py.btn(py.KEY_UP) and self.direcao != 3:
            self.direcao = 0
        elif py.btn(py.KEY_DOWN) and self.direcao != 0:
            self.direcao = 3
        elif py.btn(py.KEY_LEFT) and self.direcao != 2:
            self.direcao = 1
        elif py.btn(py.KEY_RIGHT) and self.direcao != 1:
            self.direcao = 2

        # Atualiza a posição
        if self.direcao == 3:
            self.y += 2
        elif self.direcao == 0:
            self.y -= 2
        elif self.direcao == 2:
            self.x += 2
        elif self.direcao == 1:
            self.x -= 2
        
        # Garante que a posição não ultrapasse a tela
        self.x = max(self.x, 0)
        self.x = min(self.x, py.width - self.w)
        self.y = max(self.y, 0)
        self.y = min(self.y, py.height - self.h)

        # Caso dê problemas de memória poderia salvar pontos para formar retas
        # Como no algoritmo de encontrar contornos
        self.rastros.append((self.x, self.y))


    def draw(self):

        desloc_rastro_x = self.w // 2
        desloc_rastro_y = self.h // 2

        desloc_carro_x = self.carro_w // 2
        desloc_carro_y = self.carro_h // 2


        py.rect(self.x - desloc_rastro_x, self.y - desloc_rastro_y, self.w, self.h, 9)
        for rastro in self.rastros[0:-1]:
            py.rect(rastro[0] - desloc_rastro_x, rastro[1] - desloc_rastro_y, self.w, self.h, 8)


        if self.direcao == 3:
            ROTATE = 180
        elif self.direcao == 0:
            ROTATE = 0
        elif self.direcao == 2:
            ROTATE = 90
        elif self.direcao == 1:
            ROTATE = 270

            
        py.blt(
            self.x - desloc_carro_x, self.y - desloc_carro_y,
            IMG_BANK,
            self.carro_u, self.carro_v,
            self.carro_w, self.carro_h,
            COR_TRANSPARENTE,
            ROTATE, SCALE
        )


class App:
    def __init__(self):
        py.init(320, 240)

        py.load("tron.pyxres")
        
        #self.x = 0
        self.player = Player(py.width/2, py.height/2)

        #py.mouse(True)
        py.run(self.update, self.draw)

    def update(self):
        #self.x = (self.x + 1) % py.width
        #print(self.x)
        #print('x: ', py.mouse_x,' y: ' , py.mouse_y)
        self.player.update()
        

    def draw(self):
        py.cls(0)
        #py.text(py.width/2, py.height/2, "Ola yuri", 4)
        self.player.draw()

App()