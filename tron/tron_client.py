import pyxel as py



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
        py.rect(self.x, self.y, self.w, self.h, 9)
        py.blt()
        for rastro in self.rastros[0:-1]:
            py.rect(rastro[0], rastro[1], self.w, self.h, 8)

        #print(self.rastros)

    




class App:
    def __init__(self):
        py.init(200, 150)
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
        py.text(py.width/2, py.height/2, "Ola yuri", 4)
        self.player.draw()

App()