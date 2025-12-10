# Tron Game Protocol (TGP) - Especificação Técnica

**Versão:** 1.0  
**Data:** Dezembro de 2024  
**Autores:** João Costa  
**Instituição:** UESC

---

## 📋 Sumário

1. [Visão Geral](#visão-geral)
2. [Camada de Transporte](#camada-de-transporte)
3. [Formato das Mensagens](#formato-das-mensagens)
4. [Especificação de Mensagens](#especificação-de-mensagens)
5. [Máquina de Estados](#máquina-de-estados)
6. [Diagramas de Sequência](#diagramas-de-sequência)
7. [Tratamento de Erros](#tratamento-de-erros)
8. [Considerações de Performance](#considerações-de-performance)

---

## 🌐 Visão Geral

### Descrição

O **Tron Game Protocol (TGP)** é um protocolo da camada de aplicação desenvolvido especificamente para sincronização de estado em jogos multiplayer do tipo Tron. O protocolo opera sobre TCP e utiliza JSON para serialização de dados complexos.

### Características Principais

- **Modelo**: Cliente-Servidor Autoritativo
- **Transporte**: TCP/IP
- **Porta Padrão**: 5555
- **Encoding**: UTF-8
- **Serialização**: JSON (JavaScript Object Notation)
- **Delimitador de Mensagem**: Line Feed (`\n`, ASCII 10)
- **Frequência de Atualização**: 30 Hz (30 mensagens por segundo)

### Filosofia de Design

1. **Servidor como Autoridade Única**: Toda lógica de jogo é processada no servidor
2. **Clientes como Interface**: Clientes apenas enviam inputs e renderizam estados
3. **Sincronização Determinística**: Estado é distribuído de forma idêntica para todos os clientes
4. **Confiabilidade sobre Latência**: TCP garante entrega ordenada em detrimento de latência mínima

---

## 🔌 Camada de Transporte

### TCP (Transmission Control Protocol)

#### Parâmetros de Conexão

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| **Protocolo** | TCP | Confiabilidade e ordenação garantidas |
| **Porta** | 5555 | Porta não privilegiada e não conflitante |
| **Backlog** | 2 | Máximo de 2 clientes simultâneos |
| **Timeout** | Padrão OS | Detecta desconexões automaticamente |
| **Keep-Alive** | Desabilitado | Conexões curtas em redes locais |

#### Estabelecimento de Conexão

```
Cliente                           Servidor
   │                                 │
   │───────── SYN ──────────────────►│
   │                                 │
   │◄────── SYN-ACK ────────────────│
   │                                 │
   │───────── ACK ──────────────────►│
   │                                 │
   │◄──── Player ID + "\n" ─────────│
   │                                 │
```

**Sequência:**
1. Cliente inicia handshake TCP (SYN)
2. Servidor aceita conexão (SYN-ACK)
3. Cliente confirma (ACK)
4. Servidor envia ID do jogador imediatamente após aceitar

---

## 📝 Formato das Mensagens

### Estrutura Geral

Todas as mensagens seguem o formato:

```
<PAYLOAD>\n
```

Onde:
- `<PAYLOAD>`: Conteúdo da mensagem (string ASCII ou JSON)
- `\n`: Line Feed (delimitador obrigatório)

### Tipos de Payload

#### 1. String Simples (Comandos Cliente → Servidor)
```
UP\n
DOWN\n
LEFT\n
RIGHT\n
RESET\n
```

#### 2. JSON (Estados Servidor → Cliente)
```json
{"players":{...},"score":{...},"match_winner":null}\n
```

---

## 📡 Especificação de Mensagens

### 1. Mensagens de Handshake

#### 1.1 PLAYER_ID (Servidor → Cliente)

**Enviado:** Imediatamente após aceitar conexão TCP

**Formato:**
```
<digit>\n
```

**Valores:**
- `0`: Primeiro cliente conectado (Player 0)
- `1`: Segundo cliente conectado (Player 1)

**Exemplo:**
```
0\n
```

**Propósito:**
- Identificar qual jogador o cliente controla
- Determinar posição inicial e cor na interface

**Implementação:**
```python
# Servidor
pid = len(self.conns)  # 0 ou 1
conn.send(f"{pid}\n".encode())
```

```python
# Cliente
self.my_id = int(self.client.recv(1024).decode().strip())
```

---

### 2. Mensagens de Input (Cliente → Servidor)

#### 2.1 DIRECTION (Comando de Movimentação)

**Enviado:** Quando jogador pressiona tecla direcional

**Formato:**
```
<direction>\n
```

**Valores Válidos:**
- `UP`: Mover para cima
- `DOWN`: Mover para baixo
- `LEFT`: Mover para esquerda
- `RIGHT`: Mover para direita

**Exemplo:**
```
RIGHT\n
```

**Regras de Validação:**

| Direção Atual | Input Válido | Input Inválido |
|---------------|--------------|----------------|
| UP (0) | LEFT, RIGHT | DOWN |
| LEFT (1) | UP, DOWN | RIGHT |
| RIGHT (2) | UP, DOWN | LEFT |
| DOWN (3) | LEFT, RIGHT | UP |

**Mapeamento de Códigos:**
```python
# Servidor usa códigos numéricos internamente
'0': UP
'1': LEFT
'2': RIGHT
'3': DOWN
```

**Implementação:**
```python
# Cliente - Captura e Envio
if py.btn(py.KEY_UP):
    self.net.send_input('UP')
elif py.btn(py.KEY_DOWN):
    self.net.send_input('DOWN')
# ...

# Servidor - Recepção e Validação
inp = self.last_inputs[pid]
if inp == 'UP' and direction != '3':  # Não permite inverter instantaneamente
    direction = '0'
elif inp == 'DOWN' and direction != '0':
    direction = '3'
# ...
```

---

#### 2.2 RESET (Comando de Reinício)

**Enviado:** Quando jogador pressiona ESPAÇO após fim de rodada/partida

**Formato:**
```
RESET\n
```

**Comportamento:**
1. Servidor marca `reset_requests[player_id] = True`
2. Quando ambos marcam `True`, servidor reinicia o jogo
3. Tipo de reset depende do estado:
   - **Reset de Rodada**: Se `match_winner == None` (mantém placar)
   - **Reset de Partida**: Se `match_winner != None` (zera placar)

**Fluxo:**
```
Player 0 → Servidor: RESET\n
[Servidor: reset_requests[0] = True, aguarda...]

Player 1 → Servidor: RESET\n
[Servidor: reset_requests[1] = True]
[Servidor: Ambos = True, executa reset_game()]

Servidor → Ambos: [Estado resetado, dead=False]
```

**Implementação:**
```python
# Cliente
if py.btnp(py.KEY_SPACE):
    self.net.send_input('RESET')
    self.waiting_reset = True

# Servidor
def try_reset(self, pid):
    self.reset_requests[pid] = True
    if self.reset_requests[0] and self.reset_requests[1]:
        full_reset = self.match_winner is not None
        self.reset_game(full_reset)
```

---

### 3. Mensagens de Estado (Servidor → Clientes)

#### 3.1 STATE_UPDATE (Atualização de Estado do Jogo)

**Enviado:** A cada frame do servidor (30 FPS)

**Formato:** JSON + Line Feed
```json
{
  "players": {
    "<player_id>": {
      "x": <int>,
      "y": <int>,
      "dir": <string>,
      "dead": <boolean>,
      "rastro": [[<int>, <int>]]
    }
  },
  "score": {
    "<player_id>": <int>
  },
  "match_winner": <int|null>
}\n
```

**Campos Detalhados:**

##### `players` (Obrigatório)
Dicionário contendo dados de ambos os jogadores.

**Estrutura:**
```json
"players": {
  "0": { /* dados Player 0 */ },
  "1": { /* dados Player 1 */ }
}
```

##### `players[id].x` (Obrigatório)
- **Tipo**: Integer
- **Range**: 0 - 256
- **Descrição**: Coordenada X atual do jogador

##### `players[id].y` (Obrigatório)
- **Tipo**: Integer
- **Range**: 0 - 256
- **Descrição**: Coordenada Y atual do jogador

##### `players[id].dir` (Obrigatório)
- **Tipo**: String
- **Valores**: `"0"` (UP), `"1"` (LEFT), `"2"` (RIGHT), `"3"` (DOWN)
- **Descrição**: Direção atual do jogador

##### `players[id].dead` (Obrigatório)
- **Tipo**: Boolean
- **Valores**: `true` | `false`
- **Descrição**: Status de morte do jogador
- **Transição**: `false → true` (morte), `true → false` (reset)

##### `players[id].rastro` (Obrigatório)
- **Tipo**: Array de arrays
- **Formato**: `[[x, y], ...]`
- **Descrição**: Posição(ões) mais recente(s) adicionadas ao rastro
- **Otimização**: Apenas últimas posições (não histórico completo)

**Nota Importante:**
- Servidor mantém `rastro_completo` (histórico total) para colisões
- Envia apenas `rastro` (incremento) para economizar banda
- Cliente acumula incrementos em histórico local

##### `score` (Obrigatório)
Dicionário contendo pontuação de cada jogador.

**Estrutura:**
```json
"score": {
  "0": 1,  // Player 0 ganhou 1 rodada
  "1": 0   // Player 1 não ganhou ainda
}
```

- **Tipo**: Integer
- **Range**: 0 - 2
- **Descrição**: Número de rodadas ganhas
- **Vitória**: Primeiro a atingir 2

##### `match_winner` (Obrigatório)
- **Tipo**: Integer ou Null
- **Valores**: `0`, `1`, `null`
- **Descrição**: ID do vencedor da partida
  - `null`: Partida em andamento
  - `0`: Player 0 venceu a partida
  - `1`: Player 1 venceu a partida

---

#### Exemplos Completos de STATE_UPDATE

##### Exemplo 1: Início de Jogo
```json
{
  "players": {
    "0": {
      "x": 20,
      "y": 100,
      "dir": "2",
      "dead": false,
      "rastro": [[20, 100]]
    },
    "1": {
      "x": 230,
      "y": 100,
      "dir": "1",
      "dead": false,
      "rastro": [[230, 100]]
    }
  },
  "score": {
    "0": 0,
    "1": 0
  },
  "match_winner": null
}
```

##### Exemplo 2: Durante Jogo
```json
{
  "players": {
    "0": {
      "x": 24,
      "y": 100,
      "dir": "2",
      "dead": false,
      "rastro": [[24, 100]]
    },
    "1": {
      "x": 226,
      "y": 102,
      "dir": "3",
      "dead": false,
      "rastro": [[226, 102]]
    }
  },
  "score": {
    "0": 0,
    "1": 0
  },
  "match_winner": null
}
```

##### Exemplo 3: Fim de Rodada (Player 1 morreu)
```json
{
  "players": {
    "0": {
      "x": 128,
      "y": 150,
      "dir": "0",
      "dead": false,
      "rastro": [[128, 150]]
    },
    "1": {
      "x": 0,
      "y": 200,
      "dir": "1",
      "dead": true,
      "rastro": [[0, 200]]
    }
  },
  "score": {
    "0": 1,
    "1": 0
  },
  "match_winner": null
}
```

##### Exemplo 4: Fim de Partida (Player 0 venceu)
```json
{
  "players": {
    "0": {
      "x": 64,
      "y": 80,
      "dir": "2",
      "dead": false,
      "rastro": [[64, 80]]
    },
    "1": {
      "x": 256,
      "y": 120,
      "dir": "2",
      "dead": true,
      "rastro": [[256, 120]]
    }
  },
  "score": {
    "0": 2,
    "1": 0
  },
  "match_winner": 0
}
```

---

#### Implementação do STATE_UPDATE

**Servidor (Geração):**
```python
def send_state(self):
    players_to_send = {}
    for pid, p_data in self.players.items():
        players_to_send[pid] = {
            'x': p_data['x'],
            'y': p_data['y'],
            'dir': p_data['dir'],
            'dead': p_data['dead'],
            'rastro': p_data['rastro']  # Apenas última posição
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
            print(f"Erro ao enviar estado: {e}")
```

**Cliente (Recepção):**
```python
def listen_server(self):
    while True:
        try:
            data = self.client.recv(4096).decode()
            if not data: break
            
            self.buffer += data  # Acumula dados
            
            # Processa JSONs completos
            while "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
                if line.strip():
                    try:
                        state = json.loads(line)
                        self.state_queue.append(state)  # Fila FIFO
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print("Erro:", e)
            break
```

---

## 🔄 Máquina de Estados

### Estados do Servidor

#### INITIALIZING
**Descrição:** Servidor iniciado, aguardando conexões

**Transições:**
- → `WAITING_START`: 2 clientes conectados

**Ações:**
- Aceita conexões TCP
- Envia PLAYER_ID para cada cliente

---

#### WAITING_START
**Descrição:** Countdown antes de iniciar jogo

**Duração:** 3 segundos

**Transições:**
- → `ROUND_ACTIVE`: Countdown finalizado

**Ações:**
- `print("Jogo começando em 3 segundos...")`
- `time.sleep(3)`
- `game_started = True`

---

#### ROUND_ACTIVE
**Descrição:** Rodada em andamento

**Transições:**
- → `ROUND_ENDED`: Algum jogador morreu
- → `ROUND_ACTIVE`: Loop contínuo (30 FPS)

**Ações:**
1. Processa inputs dos jogadores
2. Atualiza posições
3. Detecta colisões
4. Envia estados

**Loop:**
```python
while True:
    start_time = time.time()
    
    # 1. Processa turno
    self.process_turn()
    
    # 2. Envia estado
    self.send_state()
    
    # 3. Mantém 30 FPS
    elapsed = time.time() - start_time
    sleep_time = TICK_RATE - elapsed
    if sleep_time > 0:
        time.sleep(sleep_time)
```

---

#### ROUND_ENDED
**Descrição:** Rodada terminou, aguardando RESET

**Transições:**
- → `ROUND_ACTIVE`: Ambos enviaram RESET e `score < 2`
- → `MATCH_ENDED`: Ambos enviaram RESET e `score >= 2`

**Ações:**
- Continua enviando estados (com `dead=true`)
- Aguarda `reset_requests[0] == True` e `reset_requests[1] == True`
- Executa `reset_game(full_reset=False)`

---

#### MATCH_ENDED
**Descrição:** Partida terminou (alguém atingiu 2 vitórias)

**Transições:**
- → `ROUND_ACTIVE`: Ambos enviaram RESET

**Ações:**
- Envia estados com `match_winner != null`
- Aguarda RESET de ambos jogadores
- Executa `reset_game(full_reset=True)` (zera placar)

---

### Estados do Cliente

#### CONNECTING
**Descrição:** Estabelecendo conexão com servidor

**Transições:**
- → `WAITING_GAME`: Recebeu PLAYER_ID

**Ações:**
- `socket.connect((HOST, PORT))`
- Lê ID do jogador
- Inicia thread de escuta

---

#### WAITING_GAME
**Descrição:** Conectado, aguardando outro jogador

**Transições:**
- → `PLAYING`: Recebeu primeiro estado válido com ambos jogadores

**Ações:**
- Exibe mensagem "Esperando Oponente..."
- Processa state_queue

---

#### PLAYING
**Descrição:** Jogando normalmente

**Transições:**
- → `ROUND_OVER`: Recebe estado com `dead=true`

**Ações:**
- Captura e envia inputs
- Processa estados
- Renderiza jogo

---

#### ROUND_OVER
**Descrição:** Rodada terminou, exibindo mensagem

**Transições:**
- → `PLAYING`: Recebe estado com `dead=false` (após reset)

**Ações:**
- Exibe mensagem de fim
- Aguarda ESPAÇO
- Envia RESET quando pressionado

---

## 📊 Diagramas de Sequência

### Sequência 1: Conexão Inicial e Início de Jogo

```
Cliente 0          Servidor          Cliente 1
    │                  │                  │
    │──TCP Connect───►│                  │
    │◄────"0\n"───────│                  │
    │                  │                  │
    │ [Thread listen]  │                  │
    │◄─────────────────┤                  │
    │                  │                  │
    │                  │◄──TCP Connect───│
    │                  │────"1\n"───────►│
    │                  │                  │
    │                  │                  │ [Thread listen]
    │                  ├─────────────────►│
    │                  │                  │
    │   [Servidor detecta 2 clientes]    │
    │                  │                  │
    │     [Sleep 3s - Countdown]         │
    │                  │                  │
    │◄─STATE_UPDATE────│──STATE_UPDATE──►│
    │   (dead:false)   │   (dead:false)  │
    │                  │                  │
```

---

### Sequência 2: Gameplay Normal (Loop)

```
Cliente 0          Servidor          Cliente 1
    │                  │                  │
    │───"RIGHT"───────►│                  │
    │                  │                  │
    │                  │ [process_turn]   │
    │                  │  - Atualiza dir  │
    │                  │  - Move players  │
    │                  │  - Verifica col. │
    │                  │  - Adiciona rast.│
    │                  │                  │
    │◄─STATE_UPDATE────│──STATE_UPDATE──►│
    │  (x:22, y:100)   │  (x:228, y:100) │
    │                  │                  │
    │                  │◄───"DOWN"───────│
    │                  │                  │
    │                  │ [process_turn]   │
    │                  │                  │
    │◄─STATE_UPDATE────│──STATE_UPDATE──►│
    │  (x:24, y:100)   │  (x:228, y:102) │
    │                  │                  │
    │   [Loop continua a 30 FPS]         │
    │                  │                  │
```

---

### Sequência 3: Colisão e Fim de Rodada

```
Cliente 0          Servidor          Cliente 1
    │                  │                  │
    │───"UP"──────────►│                  │
    │                  │                  │
    │                  │ [process_turn]   │
    │                  │  - Move P1       │
    │                  │  - P1.y = 0      │
    │                  │  - COLISÃO!      │
    │                  │  - P1.dead=True  │
    │                  │  - score[0]++    │
    │                  │                  │
    │◄─STATE_UPDATE────│──STATE_UPDATE──►│
    │ (P1 dead:true)   │ (P1 dead:true)  │
    │ (score: 1-0)     │ (score: 1-0)    │
    │                  │                  │
    │ [Exibe: "Fim!"]  │                  │ [Exibe: "Fim!"]
    │                  │                  │
    │ [Pressiona SPC]  │                  │
    │───"RESET"───────►│                  │
    │                  │                  │
    │ [Exibe: Aguard.] │                  │
    │                  │                  │ [Pressiona SPC]
    │                  │◄───"RESET"──────│
    │                  │                  │
    │                  │ [reset_game()]   │
    │                  │  - Reseta pos.   │
    │                  │  - Limpa rastros │
    │                  │  - dead=False    │
    │                  │  - Mantém score  │
    │                  │                  │
    │◄─STATE_UPDATE────│──STATE_UPDATE──►│
    │ (dead:false)     │ (dead:false)    │
    │ (posições init)  │ (posições init) │
    │                  │                  │
```

---

### Sequência 4: Fim de Partida e Reset Completo

```
Cliente 0          Servidor          Cliente 1
    │                  │                  │
    │   [P0 venceu 2ª rodada]            │
    │                  │                  │
    │◄─STATE_UPDATE────│──STATE_UPDATE──►│
    │ (score: 2-0)     │ (score: 2-0)    │
    │ (match_winner:0) │ (match_winner:0)│
    │                  │                  │
    │ [Exibe: P0 VENC] │                  │ [Exibe: P0 VENC]
    │                  │                  │
    │───"RESET"───────►│                  │
    │                  │◄───"RESET"──────│
    │                  │                  │
    │                  │ [reset_game()]   │
    │                  │  full_reset=True │
    │                  │  - Zera score    │
    │                  │  - winner=null   │
    │                  │  - Reseta tudo   │
    │                  │                  │
    │◄─STATE_UPDATE────│──STATE_UPDATE──►│
    │ (score: 0-0)     │ (score: 0-0)    │
    │ (winner: null)   │ (winner: null)  │
    │                  │                  │
```

---

## 🛡️ Tratamento de Erros

### Erro 1: Fragmentação de Pacotes TCP

**Problema:** TCP não garante limites de mensagens

**Cenários:**
1. JSON incompleto chega primeiro
2. Múltiplos JSONs em um único recv()
3. Meio de um JSON + início de outro

**Solução:**
```python
# Buffer acumulativo
self.buffer = ""

def listen_server(self):
    while True:
        data = self.client.recv(4096).decode()
        self.buffer += data  # Acumula
        
        # Processa apenas mensagens completas
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():
                try:
                    state = json.loads(line)
                    self.state_queue.append(state)
                except json.JSONDecodeError:
                    pass  # Ignora JSON malformado
```

---

### Erro 2: Perda de Conexão

**Detecção (Servidor):**
```python
data = conn.recv(1024).decode().strip()
if not data:  # Cliente desconectou
    print(f"Player {pid} desconectado.")
    break
```

**Comportamento Atual:**
- Servidor continua rodando
- Jogo fica em estado inconsistente
- Requer reinicialização manual

**Melhorias Futuras:**
- Implementar timeout de reconexão
- Pausar jogo automaticamente
- Permitir substituição de jogador

---

### Erro 3: JSON Malformado

**Causa:** Corrupção de dados ou bug no encoder

**Tratamento:**
```python
try:
    state = json.loads(line)
    self.state_queue.append(state)
except json.JSONDecodeError as e:
    print(f"[ERRO] JSON inválido: {line[:50]}...")
    print(f"[ERRO] Detalhes: {e}")
    # Ignora e continua
```

---

### Erro 4: Buffer Overflow de Inputs

**Problema:** Cliente envia comandos muito rapidamente

**Solução (Servidor):**
```python
# Considera apenas ÚLTIMO comando recebido
commands = data.split('\n')
if commands:
    cmd = commands[-1]  # Mais recente
    if cmd == 'RESET':
        self.try_reset(pid)
    else:
        self.last_inputs[pid] = cmd
```

**Resultado:** Movimentos intermediários são ignorados, apenas direção final importa

---

### Erro 5: Estado Inconsistente Após Reset

**Problema:** Um cliente pode não receber mensagem de reset

**Solução:**
```python
# Cliente detecta transição dead: True → False
was_dead = self.players_local_data[pid]["dead"]
is_dead = p_data["dead"]

if was_dead and not is_dead:
    # Reset detectado! Limpa dados locais
    self.players_local_data[0]["rastro"] = []
    self.players_local_data[1]["rastro"] = []
    self.waiting_reset = False
```

---

## ⚡ Considerações de Performance

### Bandwidth Utilizado

#### Cálculo Teórico

**Tamanho de STATE_UPDATE:**
```json
{
  "players": {
    "0": {"x": 100, "y": 100, "dir": "2", "dead": false, "rastro": [[100, 100]]},
    "1": {"x": 200, "y": 200, "dir": "1", "dead": false, "rastro": [[200, 200]]}
  },
  "score": {"0": 1, "1": 0},
  "match_winner": null
}
```

**Tamanho aproximado:** 200 bytes (JSON minificado)

**Overhead TCP/IP:**
- TCP Header: 20 bytes
- IP Header: 20 bytes
- Ethernet: 14 bytes (camada de enlace)
- **Total overhead:** ~54 bytes

**Total por pacote:** 200 + 54 = **254 bytes**

**Frequência:** 30 FPS

**Bandwidth por cliente:**
- Servidor → Cliente: 254 bytes × 30 FPS = **7.62 KB/s** (~61 Kbps)

**Bandwidth total do servidor:**
- 2 clientes: 7.62 KB/s × 2 = **15.24 KB/s** (~122 Kbps)

**Inputs Cliente → Servidor:**
- Tamanho: ~10 bytes por comando
- Frequência: Variável (máx. ~60/s)
- Bandwidth: 10 × 60 = **600 bytes/s** (~5 Kbps)

---

### Latência

#### Componentes de Latência

1. **Latência de Rede (RTT/2)**
   - LAN: 1-5ms
   - Internet (mesma cidade): 10-30ms
   - Internet (nacional): 30-100ms

2. **Latência de Processamento Servidor**
   - process_turn(): ~1-2ms
   - json.dumps(): ~0.5ms
   - Total: ~2-3ms

3. **Latência de Renderização Cliente**
   - Pyxel frame time: ~16ms (60 FPS cliente)

**Latência Total (LAN):** 1ms + 2ms + 16ms = **~19ms**

**Latência Total (Internet):** 30ms + 2ms + 16ms = **~48ms**

---

### Otimizações Implementadas

#### 1. Envio Incremental de Rastros

**Problema Original:**
- Enviar rastro completo a cada frame
- Crescimento linear: ~1 ponto/frame × 30 FPS = 30 pontos/s
- Após 10s: 300 pontos × 8 bytes = 2.4 KB adicional

**Solução:**
```python
# Servidor mantém dois rastros
'rastro': [pos]              # Apenas último ponto (enviado)
'rastro_completo': [...]     # Histórico completo (colisões)

# Cliente acumula localmente
self.players_local_data[pid]["rastro"].extend(p_data["rastro"])
```

**Economia:** ~95% de banda após 10 segundos

---

#### 2. Direções como Strings de 1 Char

**Alternativa:** Enviar strings completas
```json
"dir": "UP"  // 2 bytes
```

**Implementação:**
```json
"dir": "0"  // 1 byte
```

**Economia:** 50% no campo de direção

---

#### 3. JSON Minificado

**Não usar:**
```json
{
  "players": {
    "0": {
      "x": 100,
      "y": 100
    }
  }
}
```

**Usar:**
```json
{"players":{"0":{"x":100,"y":100}}}
```

**Economia:** ~40% em whitespace

---

### Otimizações Potenciais Futuras

#### 1. Protocolo Binário

**Formato Atual:** JSON (texto)
**Alternativa:** MessagePack, Protocol Buffers

**Exemplo (MessagePack):**
```python
import msgpack

# Serialização
data = msgpack.packb(game_state)  # ~80 bytes em vez de 200

# Desserialização
state = msgpack.unpackb(data)
```

**Economia:** ~60% de banda

---

#### 2. Compressão

**Algoritmo:** gzip, zlib

**Aplicação:**
```python
import zlib

json_str = json.dumps(game_state)
compressed = zlib.compress(json_str.encode())
```

**Trade-off:**
- ✅ Redução de banda (50-70%)
- ❌ CPU adicional (5-10ms)

**Conclusão:** Não recomendado para <1KB de dados

---

#### 3. Delta Encoding

**Conceito:** Enviar apenas diferenças desde último estado

**Exemplo:**
```json
// Frame 1 (estado completo)
{"players": {"0": {"x": 20, "y": 100, ...}}}

// Frame 2 (apenas mudanças)
{"players": {"0": {"x": 22}}}  // y não mudou
```

**Economia:** ~50% em estados similares

**Complexidade:** Alta (requer gerenciamento de baseline)

---

## 📏 Conformidade com Padrões

### RFC Relevantes

1. **RFC 793 - TCP**
   - Protocolo de transporte utilizado
   - https://datatracker.ietf.org/doc/html/rfc793

2. **RFC 8259 - JSON**
   - Formato de serialização
   - https://datatracker.ietf.org/doc/html/rfc8259

3. **RFC 3629 - UTF-8**
   - Encoding de caracteres
   - https://datatracker.ietf.org/doc/html/rfc3629

---

## 🔬 Análise Técnica Comparativa

### TGP vs Protocolos Comuns de Jogos

| Aspecto | TGP | Quake 3 | Minecraft | Valorant |
|---------|-----|---------|-----------|----------|
| **Transporte** | TCP | UDP | TCP | UDP |
| **Formato** | JSON | Binário | Binário | Protobuf |
| **Frequência** | 30 Hz | 60-125 Hz | 20 Hz | 128 Hz |
| **Latência Tolerada** | 50-100ms | <20ms | 100-200ms | <30ms |
| **Predição Cliente** | Não | Sim | Sim | Sim |
| **Complexidade** | Baixa | Alta | Média | Muito Alta |

**Conclusão:** TGP prioriza simplicidade e confiabilidade sobre performance extrema, adequado para jogos casuais e fins educacionais.

---

## 📚 Referências Técnicas

1. **Game Networking**
   - Glazer, G. (2015). *Multiplayer Game Programming*. Addison-Wesley.
   - Fiedler, G. *Networking for Game Programmers*. https://gafferongames.com/

2. **Protocol Design**
   - Tanenbaum, A. S. (2003). *Computer Networks*. Prentice Hall.
   - Stevens, W. R. (1994). *TCP/IP Illustrated, Vol. 1*. Addison-Wesley.

3. **JSON Specification**
   - RFC 8259: The JavaScript Object Notation (JSON) Data Interchange Format

---

**Versão do Documento:** 1.0  
**Última Atualização:** Dezembro de 2024  
**Autor:** João Costa (UESC)  
**Status:** ✅ Especificação Completa e Implementada
