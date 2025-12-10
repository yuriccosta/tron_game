# Tron Game - Jogo Multiplayer Distribuído

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 📋 Sumário

1. [Descrição do Projeto](#descrição-do-projeto)
2. [Propósito e Motivação](#propósito-e-motivação)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Protocolo de Comunicação](#protocolo-de-comunicação)
5. [Justificativa Técnica do TCP](#justificativa-técnica-do-tcp)
6. [Requisitos do Sistema](#requisitos-do-sistema)
7. [Instalação e Configuração](#instalação-e-configuração)
8. [Como Executar](#como-executar)
9. [Estrutura do Projeto](#estrutura-do-projeto)
10. [Fluxo de Funcionamento](#fluxo-de-funcionamento)
11. [Referências](#referências)

---

## 📖 Descrição do Projeto

**Tron Game** é uma implementação multiplayer distribuída do clássico jogo Tron, onde dois jogadores controlam "motos de luz" que deixam rastros luminosos atrás de si. O objetivo é forçar o adversário a colidir com as bordas da arena ou com os rastros, enquanto evita sua própria eliminação. O projeto utiliza a arquitetura cliente-servidor com comunicação via **sockets TCP**, proporcionando uma experiência de jogo em tempo real sincronizada entre múltiplas máquinas.

### Características Principais:
- **Arquitetura Cliente-Servidor**: Servidor autoritativo que gerencia toda a lógica do jogo
- **Comunicação em Tempo Real**: Sincronização de estados a 30 FPS via TCP
- **Sistema de Pontuação**: Partidas no formato "melhor de 3" (primeiro a 2 vitórias)
- **Interface Gráfica**: Renderização usando a biblioteca Pyxel
- **Protocolo Customizado**: Protocolo da camada de aplicação especialmente desenvolvido para o jogo

---

## 🎯 Propósito e Motivação

### Propósito

O projeto foi desenvolvido como trabalho acadêmico da disciplina de **Redes de Computadores** com os seguintes objetivos:

1. **Educacional**: Demonstrar conceitos práticos de programação distribuída e redes
2. **Técnico**: Implementar um protocolo de aplicação robusto e eficiente
3. **Prático**: Criar um sistema funcional que evidencia desafios reais de sincronização em jogos multiplayer

### Motivação da Escolha

O jogo Tron foi escolhido por apresentar desafios técnicos relevantes para o estudo de redes:

- **Sincronização Crítica**: Requer atualização frequente e consistente do estado entre clientes
- **Baixa Tolerância a Perda**: Qualquer perda de pacote pode causar dessincronização visual
- **Detecção de Colisão Autoritativa**: Necessita validação centralizada para evitar trapaças
- **Estado Crescente**: O rastro aumenta continuamente, exigindo gerenciamento eficiente de dados

---

## 🏗️ Arquitetura do Sistema

O sistema segue o modelo **Cliente-Servidor Autoritativo**, uma arquitetura comum em jogos multiplayer modernos.

```
┌─────────────┐                           ┌─────────────┐
│   Cliente   │◄──────────────────────────│   Servidor  │
│  (Player 0) │          TCP              │  (Árbitro)  │
│             │──────────────────────────►│             │
└─────────────┘                           └─────────────┘
                                                 ▲
                                                 │ TCP
                                                 ▼
                                          ┌─────────────┐
                                          │   Cliente   │
                                          │  (Player 1) │
                                          │             │
                                          └─────────────┘
```

### Componentes do Sistema

#### 1. **Servidor (`server.py`)**
   - **Função**: Autoridade central do jogo
   - **Responsabilidades**:
     - Manter o estado autoritativo do jogo
     - Processar lógica de movimentação e colisão
     - Validar e aplicar comandos dos jogadores
     - Distribuir estado atualizado para todos os clientes
     - Gerenciar placar e condições de vitória
   - **Loop Principal**: Executa a 30 FPS (TICK_RATE = 1/30s)

#### 2. **Cliente (`client.py`)**
   - **Função**: Interface do jogador
   - **Responsabilidades**:
     - Capturar e enviar inputs do usuário
     - Receber e processar estados do servidor
     - Renderizar interface gráfica
     - Manter histórico local de rastros
   - **Threads**:
     - Thread principal: Renderização e input
     - Thread secundária: Recepção de estados do servidor

#### 3. **Camada de Transporte**
   - **Protocolo**: TCP (Transmission Control Protocol)
   - **Porta**: 5555
   - **Encoding**: UTF-8 para todas as mensagens

---

## 📡 Protocolo de Comunicação

O protocolo de aplicação **Tron Game Protocol (TGP)** foi especialmente desenvolvido para este projeto, operando sobre TCP e utilizando JSON para serialização de dados.

### 📋 Especificação do Protocolo

#### **1. Estabelecimento de Conexão**

**Fase:** Handshake Inicial

```
Cliente → Servidor: [Conexão TCP estabelecida]
Servidor → Cliente: "<player_id>\n"
```

**Descrição:**
- Quando um cliente se conecta, o servidor imediatamente atribui um ID (0 ou 1)
- O servidor aceita exatamente 2 clientes e rejeita conexões adicionais
- Este ID é usado pelo cliente para identificar qual jogador ele controla

**Exemplo:**
```
Servidor → Cliente: "0\n"  // Você é o Player 0
```

---

#### **2. Mensagens Cliente → Servidor**

##### 2.1 **INPUT - Comando de Movimentação**

**Formato:**
```
<DIRECTION>
```

**Valores Válidos:**
- `UP` - Move para cima
- `DOWN` - Move para baixo
- `LEFT` - Move para esquerda
- `RIGHT` - Move para direita

**Regras:**
- Enviado sempre que o jogador pressiona uma tecla direcional
- O servidor valida movimentos impossíveis (180° de rotação instantânea)
- Múltiplos comandos podem ser enviados rapidamente (última direção válida é considerada)

**Exemplo:**
```
Cliente → Servidor: "RIGHT"
Cliente → Servidor: "UP"
```

**Validação no Servidor:**
```python
# Impede mudança de direção 180° instantânea
if inp == 'UP' and direction != '3':      # Não pode ir para cima se está indo para baixo
    direction = '0'
elif inp == 'DOWN' and direction != '0':  # Não pode ir para baixo se está indo para cima
    direction = '3'
```

---

##### 2.2 **RESET - Comando de Reinício**

**Formato:**
```
RESET
```

**Descrição:**
- Enviado quando o jogador pressiona ESPAÇO após uma rodada terminar
- Servidor aguarda AMBOS os jogadores enviarem RESET
- Após confirmação de ambos, o jogo é reiniciado

**Fluxo de Reset:**
```
Cliente 0 → Servidor: "RESET"
[Servidor marca reset_requests[0] = True]
[Servidor aguarda...]

Cliente 1 → Servidor: "RESET"
[Servidor marca reset_requests[1] = True]
[Servidor detecta ambos = True]
[Servidor reinicia o jogo]

Servidor → Ambos Clientes: [Novo estado com dead=False]
```

**Tipos de Reset:**
- **Reset de Rodada**: Mantém placar, reseta posições (quando placar < 2 vitórias)
- **Reset de Partida**: Zera placar e reseta posições (quando há vencedor da partida)

---

#### **3. Mensagens Servidor → Clientes**

##### 3.1 **STATE_UPDATE - Atualização de Estado**

**Formato:** JSON seguido de newline
```json
{
  "players": {
    "0": {
      "x": <int>,
      "y": <int>,
      "dir": <string>,
      "dead": <boolean>,
      "rastro": [[x, y]]
    },
    "1": {
      "x": <int>,
      "y": <int>,
      "dir": <string>,
      "dead": <boolean>,
      "rastro": [[x, y]]
    }
  },
  "score": {
    "0": <int>,
    "1": <int>
  },
  "match_winner": <int|null>
}\n
```

**Campos:**
- `players`: Dados de ambos os jogadores
  - `x`, `y`: Coordenadas atuais (0-256)
  - `dir`: Direção atual ('0'=cima, '1'=esquerda, '2'=direita, '3'=baixo)
  - `dead`: Status de morte (true/false)
  - `rastro`: Array com a posição mais recente adicionada ao rastro
- `score`: Placar atual (número de rodadas ganhas)
- `match_winner`: ID do vencedor da partida (null se partida em andamento)

**Frequência:** 30 vezes por segundo (30 FPS)

**Exemplo Completo:**
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
    "0": 1,
    "1": 0
  },
  "match_winner": null
}
```

---

### 🔄 Máquina de Estados

#### **Estados do Servidor**

```
┌──────────────────┐
│   INITIALIZING   │  Servidor iniciado, aguardando jogadores
└────────┬─────────┘
         │ 2 clientes conectados
         ▼
┌──────────────────┐
│   WAITING_START  │  Countdown de 3 segundos
└────────┬─────────┘
         │ Countdown finalizado
         ▼
┌──────────────────┐
│   ROUND_ACTIVE   │◄─┐  Rodada em andamento
└────────┬─────────┘  │
         │ Colisão     │
         ▼             │
┌──────────────────┐  │
│   ROUND_ENDED    │  │  Aguardando RESET de ambos jogadores
└────────┬─────────┘  │
         │ Ambos enviaram RESET
         │ E score < 2  │
         └──────────────┘
         │ score >= 2
         ▼
┌──────────────────┐
│   MATCH_ENDED    │  Aguardando RESET para nova partida
└────────┬─────────┘
         │ Ambos enviaram RESET
         ▼
    (Volta para ROUND_ACTIVE com placar zerado)
```

#### **Estados do Cliente**

```
┌──────────────────┐
│   CONNECTING     │  Conectando ao servidor
└────────┬─────────┘
         │ Recebe player_id
         ▼
┌──────────────────┐
│   WAITING_GAME   │  Aguardando outro jogador
└────────┬─────────┘
         │ Recebe primeiro estado válido
         ▼
┌──────────────────┐
│   PLAYING        │◄─┐  Jogando normalmente
└────────┬─────────┘  │
         │ Recebe dead=true
         ▼             │
┌──────────────────┐  │
│   ROUND_OVER     │  │  Exibindo mensagem de fim de rodada
└────────┬─────────┘  │
         │ Pressiona ESPAÇO
         │ Recebe dead=false
         └──────────────┘
```

---

### 📊 Diagrama de Sequência

#### **Sequência Completa de uma Rodada**

```
Cliente 0          Servidor          Cliente 1
    │                  │                  │
    │──TCP Connect───►│                  │
    │◄────"0\n"───────│                  │
    │                  │◄──TCP Connect───│
    │                  │────"1\n"───────►│
    │                  │                  │
    │       [Countdown: 3 segundos]      │
    │                  │                  │
    │                  │──STATE_UPDATE──►│
    │◄─STATE_UPDATE────│                  │
    │                  │                  │
    │───"RIGHT"───────►│                  │
    │                  │◄───"LEFT"───────│
    │                  │                  │
    │     [Servidor processa turno]      │
    │                  │                  │
    │◄─STATE_UPDATE────│──STATE_UPDATE──►│
    │                  │                  │
    │   (loop a 30 FPS continuamente)    │
    │                  │                  │
    │     [Player 1 colide com borda]    │
    │                  │                  │
    │◄─STATE(dead:T)───│──STATE(dead:T)─►│
    │                  │                  │
    │───"RESET"───────►│                  │
    │                  │◄───"RESET"──────│
    │                  │                  │
    │     [Servidor reseta o jogo]       │
    │                  │                  │
    │◄─STATE(dead:F)───│──STATE(dead:F)─►│
    │                  │                  │
```

---

### 🛡️ Tratamento de Erros e Casos Especiais

#### **1. Desconexão de Cliente**

**Detecção:**
```python
# No servidor, dentro de handle_client_input()
data = conn.recv(1024).decode().strip()
if not data:  # Cliente desconectou
    break
```

**Comportamento Atual:**
- Servidor detecta desconexão mas continua executando
- Requer reinicialização manual do servidor
- **Melhoria Futura**: Implementar reconexão ou pausa automática

---

#### **2. Colisão Simultânea**

**Cenário:** Ambos os jogadores colidem no mesmo frame

**Tratamento:**
```python
# Colisão frontal (mesma posição)
if self.players[0]['x'] == self.players[1]['x'] and 
   self.players[0]['y'] == self.players[1]['y']:
    self.players[0]['dead'] = True
    self.players[1]['dead'] = True
    # Empate - nenhum jogador pontua
```

**Resultado:** Rodada termina em empate, nenhum jogador ganha ponto

---

#### **3. Buffer Overflow de Comandos**

**Problema:** Cliente pode enviar múltiplos comandos rapidamente

**Solução:**
```python
# Servidor sempre pega o ÚLTIMO comando válido
commands = data.split('\n')
if commands:
    cmd = commands[-1]  # Mais recente
    self.last_inputs[pid] = cmd
```

---

#### **4. Fragmentação de JSON**

**Problema:** Pacote TCP pode chegar fragmentado

**Solução no Cliente:**
```python
self.buffer += data  # Acumula dados recebidos

while "\n" in self.buffer:
    line, self.buffer = self.buffer.split("\n", 1)
    if line.strip():
        state = json.loads(line)  # Só processa JSON completo
        self.state_queue.append(state)
```

---

### 📏 Especificação de Dados

#### **Constantes do Jogo**

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `WIDTH` | 256 | Largura da arena em pixels |
| `HEIGHT` | 256 | Altura da arena em pixels |
| `TICK_RATE` | 1/30 (≈33ms) | Intervalo entre atualizações do servidor |
| `PLAYER_SPEED` | 2 pixels/tick | Velocidade de movimento |
| `MAX_PLAYERS` | 2 | Número máximo de jogadores simultâneos |
| `WIN_SCORE` | 2 | Pontos necessários para vencer a partida |

#### **Mapeamento de Direções**

| Código | Direção | Movimento |
|--------|---------|-----------|
| `'0'` | UP | y -= 2 |
| `'1'` | LEFT | x -= 2 |
| `'2'` | RIGHT | x += 2 |
| `'3'` | DOWN | y += 2 |

---

## 🔐 Justificativa Técnica do TCP

### Por que TCP foi escolhido em vez de UDP?

A escolha do **TCP (Transmission Control Protocol)** foi fundamentada em análise técnica dos requisitos do jogo:

#### ✅ **Vantagens do TCP para este Projeto**

1. **Garantia de Entrega Ordenada**
   - **Crítico**: O estado do jogo deve ser recebido na ordem exata
   - **Problema com UDP**: Pacotes podem chegar fora de ordem
   - **Impacto**: Rastros seriam desenhados incorretamente, causando inconsistências visuais graves

2. **Confiabilidade na Sincronização**
   - **Crítico**: Perder um pacote de estado significa dessincronização permanente
   - **Problema com UDP**: Sem retransmissão automática, estados podem ser perdidos
   - **Impacto**: Jogadores veriam rastros diferentes, causando colisões "fantasmas"

3. **Controle de Fluxo Integrado**
   - **Vantagem**: TCP ajusta automaticamente a taxa de envio
   - **Benefício**: Evita sobrecarga de rede sem implementação manual

4. **Simplicidade de Implementação**
   - **Vantagem**: API mais simples, sem necessidade de implementar ACKs manualmente
   - **Benefício**: Código mais limpo e manutenível para fins acadêmicos

#### ⚠️ **Desvantagens Aceitáveis do TCP**

1. **Latência Adicional (TCP Head-of-Line Blocking)**
   - **Trade-off**: Pequeno atraso é preferível a dados incorretos
   - **Mitigação**: Jogo funciona bem em redes locais (latência < 50ms)

2. **Overhead de Protocolo**
   - **Trade-off**: ~40 bytes de overhead vs garantias de entrega
   - **Aceitável**: Para 30 FPS, bandwidth é ~15KB/s (insignificante)

---

### 📊 Análise Comparativa: TCP vs UDP

| Critério | TCP | UDP | Melhor para Tron? |
|----------|-----|-----|-------------------|
| **Confiabilidade** | Garantida | Não garantida | ✅ TCP |
| **Ordenação** | Mantida | Não garantida | ✅ TCP |
| **Latência** | Maior (~20-50ms) | Menor (~10-20ms) | ⚖️ Empate* |
| **Complexidade** | Baixa | Alta (requer implementar confiabilidade) | ✅ TCP |
| **Overhead** | ~40 bytes/pacote | ~8 bytes/pacote | ⚠️ UDP |
| **Adequação ao Projeto** | ✅ Excelente | ❌ Inadequado | ✅ **TCP** |

*\*Em redes locais, a diferença de latência é negligenciável*

---

### 🎮 Cenários de Uso

#### **Quando UDP seria mais adequado:**
- Jogos FPS competitivos (ex: Counter-Strike, Valorant)
- Transmissão de vídeo/áudio em tempo real
- Jogos com predição no cliente (client-side prediction)

#### **Por que TCP é ideal para este projeto:**
- Jogo multiplayer casual
- Servidor autoritativo puro (sem predição)
- Estado crítico que não pode ser perdido
- Implementação acadêmica com foco em simplicidade

---

### 📝 Conclusão Técnica

Para um jogo como **Tron**, onde a **consistência do estado** é mais importante que a **latência mínima**, o TCP oferece:

1. ✅ **Confiabilidade garantida** sem esforço adicional
2. ✅ **Simplicidade de código** para fins educacionais
3. ✅ **Comportamento previsível** em diversas condições de rede
4. ✅ **Performance adequada** para redes locais e internet de qualidade

A escolha do TCP demonstra compreensão dos **trade-offs entre protocolos** e prioriza a **corretude do sistema** sobre otimização prematura, alinhando-se com os princípios de engenharia de software.

---

## 💻 Requisitos do Sistema

### Requisitos Mínimos de Hardware

- **Processador**: Dual-core 1.5 GHz ou superior
- **Memória RAM**: 2 GB
- **Espaço em Disco**: 100 MB livres
- **Placa de Vídeo**: Suporte a OpenGL 3.3+ (integrada é suficiente)
- **Rede**: 
  - Servidor: Upload mínimo de 1 Mbps
  - Cliente: Download mínimo de 500 Kbps

### Requisitos de Software

- **Sistema Operacional**:
  - Linux (Ubuntu 20.04+, Debian 10+, Fedora 30+)
  - macOS (10.14 Mojave ou superior)
  - Windows (10 ou 11)

- **Python**: Versão 3.8 ou superior
- **Bibliotecas Python**:
  - `pyxel` (≥1.9.0) - Engine gráfica
  - Bibliotecas padrão: `socket`, `json`, `threading`, `time`

### Requisitos de Rede

- **Conexão Local (LAN)**: Recomendado para melhor experiência
- **Porta**: 5555 deve estar disponível e não bloqueada por firewall
- **Latência**: Máximo de 100ms para experiência fluida (idealmente < 50ms)
- **Perda de Pacotes**: < 1% (TCP recupera automaticamente)

---

## 🚀 Instalação e Configuração

### 1. Pré-requisitos

Certifique-se de ter Python 3.8+ instalado:

```bash
# Verificar versão do Python
python3 --version
```

### 2. Clonar o Repositório

```bash
git clone https://github.com/yuriccosta/tron_game.git
cd tron_game
```
### 3. Criar o ambiente virtual

#### **MacOS/Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar Dependências

```bash
# Instalar Pyxel
pip3 install pyxel

# Ou usando requirements.txt (se disponível)
pip3 install -r requirements.txt
```

### 5. Configuração de Rede

#### **Servidor**

Edite `tron/server.py` se necessário:

```python
HOST = '0.0.0.0'  # Aceita conexões de qualquer IP
PORT = 5555       # Porta TCP
```

#### **Cliente**

Edite `tron/client.py` para conectar ao servidor:

```python
HOST = '127.0.0.1'  # IP do servidor (localhost para teste local)
PORT = 5555          # Porta TCP (mesma do servidor)
```

**Exemplos de Configuração:**

- **Jogo local (mesma máquina)**: `HOST = '127.0.0.1'`
- **Servidor em rede local**: `HOST = '192.168.1.100'` (IP local do servidor)
- **Servidor em internet**: `HOST = '203.0.113.10'` (IP público do servidor)

### 6. Configuração de Firewall

**No servidor:**

```bash
# Linux (UFW)
sudo ufw allow 5555/tcp

# Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 5555 -j ACCEPT

# macOS
# Sistema de Preferências → Segurança e Privacidade → Firewall → Opções de Firewall
# Adicionar Python e permitir conexões de entrada

# Windows
# Painel de Controle → Firewall do Windows → Configurações Avançadas
# Nova Regra de Entrada → Porta → TCP 5555 → Permitir
```

---

## 🎮 Como Executar

### Execução Local (Mesma Máquina)

#### Terminal 1 - Servidor
```bash
cd tron_game/tron
python3 server.py
```

**Saída esperada:**
```
Servidor iniciado em 0.0.0.0:5555, aguardando jogadores...
Loop do jogo iniciado.
```

#### Terminal 2 - Cliente 1
```bash
cd tron_game/tron
python3 client.py
```

**Saída esperada:**
```
Sou o Player 0
```

#### Terminal 3 - Cliente 2
```bash
cd tron_game/tron
python3 client.py
```

**Saída esperada:**
```
Sou o Player 1
Todos conectados! Jogo começando em 3 segundos...
```

---

### Execução em Rede Local

#### Máquina 1 (Servidor)
```bash
# Descobrir IP local
# Linux/macOS
ifconfig | grep "inet "
# ou
ip addr show

# Windows
ipconfig

# Exemplo: IP local = 192.168.1.100

# Executar servidor
cd tron_game/tron
python3 server.py
```

#### Máquinas 2 e 3 (Clientes)

1. Editar `client.py`:
```python
HOST = '192.168.1.100'  # IP do servidor
```

2. Executar cliente:
```bash
cd tron_game/tron
python3 client.py
```

---

### Controles do Jogo

| Tecla | Ação |
|-------|------|
| `↑` (Seta para Cima) | Mover para cima |
| `↓` (Seta para Baixo) | Mover para baixo |
| `←` (Seta para Esquerda) | Mover para esquerda |
| `→` (Seta para Direita) | Mover para direita |
| `ESPAÇO` | Reiniciar rodada/partida (após fim) |

---

### Regras do Jogo

1. **Objetivo**: Forçar o adversário a colidir enquanto evita colisões
2. **Colisões Fatais**:
   - Colidir com as bordas da arena
   - Colidir com seu próprio rastro
   - Colidir com o rastro do oponente
   - Colisão frontal (ambos morrem - empate)
3. **Sistema de Pontos**:
   - Cada rodada ganha = 1 ponto
   - Primeiro a atingir 2 pontos vence a partida
4. **Reinício**:
   - Após fim de rodada: ESPAÇO (ambos jogadores devem confirmar)
   - Após fim de partida: ESPAÇO (reseta placar completo)

---

## 📂 Estrutura do Projeto

```
tron_game/
│
├── README.md                    # Este arquivo - Documentação completa
├── README.pt.md                 # Documentação em português
│
└── tron/
    ├── server.py                # Servidor do jogo (autoridade)
    ├── client.py                # Cliente do jogo (interface)
    ├── tron.py                  # Versão local single-player (referência)
    ├── tron_client.py           # (Não utilizado)
    ├── client_local.py          # (Não utilizado)
    ├── tron.pyxres              # Recursos gráficos Pyxel
    │
    └── assets/
        └── bomberman.pyxres     # Assets adicionais
```

### Descrição dos Arquivos Principais

#### **`server.py`** (255 linhas)
- **Classe Principal**: `GameServer`
- **Métodos Importantes**:
  - `__init__()`: Inicializa estado do jogo
  - `reset_game()`: Reinicia rodada ou partida
  - `handle_client_input()`: Processa comandos dos clientes (thread por cliente)
  - `process_turn()`: Lógica de movimentação e colisão (30 FPS)
  - `send_state()`: Envia estado para clientes
  - `game_loop()`: Loop principal do jogo
  - `start()`: Inicia servidor e aceita conexões

#### **`client.py`** (168 linhas)
- **Classe de Rede**: `GameClient`
  - Thread para receber estados do servidor
  - Buffer para acumular pacotes fragmentados
  - Fila de estados (`state_queue`) para processamento FIFO
  
- **Classe de Interface**: `App`
  - Loop de renderização Pyxel
  - Captura de input do usuário
  - Renderização de rastros e interface
  - Gerenciamento de mensagens de estado

#### **`tron.py`**
- Versão single-player original (referência)
- Não utilizado no modo multiplayer

---

## 🔄 Fluxo de Funcionamento

### 1️⃣ Inicialização do Sistema

```
┌─────────────────────────────────────────────────────┐
│ 1. Servidor Inicia                                   │
│    - Bind em 0.0.0.0:5555                           │
│    - Inicia thread de game_loop()                   │
│    - Aguarda 2 conexões                             │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ 2. Cliente 1 Conecta                                 │
│    - Estabelece conexão TCP                         │
│    - Recebe player_id = 0                           │
│    - Inicia thread de escuta                        │
│    - Aguarda outro jogador                          │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ 3. Cliente 2 Conecta                                 │
│    - Estabelece conexão TCP                         │
│    - Recebe player_id = 1                           │
│    - Inicia thread de escuta                        │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ 4. Countdown                                         │
│    - Servidor detecta 2 jogadores                   │
│    - Sleep(3 segundos)                              │
│    - game_started = True                            │
└─────────────────────────────────────────────────────┘
```

---

### 2️⃣ Loop de Jogo (Executado a 30 FPS)

```
┌─────────────────────────────────────────────────────┐
│ SERVIDOR: process_turn()                            │
│                                                      │
│ 1. Verifica se alguém está morto                    │
│    └─ Se sim, pula processamento                    │
│                                                      │
│ 2. Atualiza direções                                │
│    └─ Lê last_inputs[pid] de cada jogador          │
│    └─ Valida movimentos (proíbe 180°)              │
│                                                      │
│ 3. Move jogadores                                    │
│    └─ x/y += 2 pixels na direção atual             │
│                                                      │
│ 4. Detecta colisões                                  │
│    ├─ Bordas (x=0, x=256, y=0, y=256)              │
│    ├─ Rastros (próprio e adversário)               │
│    └─ Colisão frontal (mesma posição)              │
│                                                      │
│ 5. Atualiza placar                                   │
│    └─ Se alguém morreu, incrementa score           │
│    └─ Verifica vitória (score >= 2)                │
│                                                      │
│ 6. Adiciona posição ao rastro                       │
│    └─ rastro_completo (histórico completo)         │
│    └─ rastro (apenas último ponto - enviado)       │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ SERVIDOR: send_state()                              │
│                                                      │
│ - Serializa estado em JSON                          │
│ - Envia para ambos os clientes via TCP             │
│ - Adiciona '\n' como delimitador                    │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ CLIENTE: listen_server() [thread separada]          │
│                                                      │
│ 1. Recebe dados via TCP                             │
│ 2. Acumula em buffer                                │
│ 3. Separa por '\n'                                  │
│ 4. Parse JSON                                        │
│ 5. Adiciona à state_queue                           │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ CLIENTE: update() [thread principal Pyxel]          │
│                                                      │
│ 1. Captura input do usuário                         │
│    └─ Envia comandos para servidor                 │
│                                                      │
│ 2. Processa state_queue (FIFO)                      │
│    ├─ Detecta reset (dead: false após true)        │
│    ├─ Atualiza posições                            │
│    ├─ Atualiza placar                              │
│    └─ Adiciona novos rastros ao histórico local   │
│                                                      │
│ 3. Renderiza frame                                   │
│    ├─ Limpa tela                                   │
│    ├─ Desenha placar                               │
│    ├─ Desenha rastros de ambos jogadores          │
│    ├─ Desenha cabeças (posição atual)             │
│    └─ Mensagens de estado (fim de rodada/partida) │
└─────────────────────────────────────────────────────┘
```

---

### 3️⃣ Fim de Rodada

```
┌─────────────────────────────────────────────────────┐
│ 1. Colisão Detectada (Servidor)                     │
│    - player['dead'] = True                          │
│    - Incrementa score do vencedor                   │
│    - Envia estado com dead=True                     │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ 2. Cliente Exibe Mensagem                            │
│    - "Fim da rodada!"                               │
│    - "ESPACO para proxima rodada" ou                │
│      "Esperando outro jogador..."                   │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ 3. Ambos Jogadores Pressionam ESPAÇO                │
│    - Cliente envia "RESET"                          │
│    - Servidor marca reset_requests[pid] = True     │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ 4. Servidor Reinicia                                 │
│    - Reseta posições                                │
│    - Reseta direções                                │
│    - Limpa rastros                                  │
│    - Mantém placar (se score < 2)                  │
│    - Envia estado com dead=False                    │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ 5. Cliente Detecta Reset                             │
│    - Limpa rastros locais                           │
│    - Volta para estado PLAYING                      │
└─────────────────────────────────────────────────────┘
```

---

### 4️⃣ Detalhes de Sincronização

#### **Problema: Pacotes TCP Fragmentados**

TCP não preserva limites de mensagens. Um pacote pode conter:
- Parte de um JSON
- Múltiplos JSONs
- JSON completo + parte de outro

**Solução Implementada:**

```python
# Cliente acumula dados em buffer
self.buffer += data

# Processa apenas JSONs completos (delimitados por '\n')
while "\n" in self.buffer:
    line, self.buffer = self.buffer.split("\n", 1)
    if line.strip():
        state = json.loads(line)
        self.state_queue.append(state)
```

#### **Problema: Multiple Updates por Frame**

A 30 FPS, o servidor pode enviar atualizações mais rápido que o cliente renderiza.

**Solução Implementada:**

```python
# Cliente processa TODOS os estados acumulados antes de renderizar
while len(self.net.state_queue) > 0:
    game_state = self.net.state_queue.pop(0)  # FIFO
    # Processa estado...
    # Adiciona rastros ao histórico local
```

---

## 🧪 Testando o Sistema

### Testes Funcionais

#### **Teste 1: Conexão Básica**
```bash
# Servidor
python3 server.py

# Cliente 1
python3 client.py

# Cliente 2
python3 client.py

✅ Esperado: Ambos clientes conectam e jogo inicia após countdown
```

#### **Teste 2: Colisão com Borda**
```
1. Movimente jogador até a borda
✅ Esperado: Player morre, placar incrementa, mensagem de fim de rodada
```

#### **Teste 3: Colisão com Rastro**
```
1. Crie um rastro circular
2. Colida com seu próprio rastro
✅ Esperado: Player morre, adversário pontua
```

#### **Teste 4: Sistema de Placar**
```
1. Vença 2 rodadas consecutivas
✅ Esperado: Mensagem "PLAYER X VENCEU!" e placar é exibido
```

#### **Teste 5: Reset de Rodada**
```
1. Termine uma rodada (placar < 2)
2. Pressione ESPAÇO em ambos clientes
✅ Esperado: Jogo reinicia, placar mantido, posições resetadas
```

#### **Teste 6: Reset de Partida**
```
1. Termine a partida (placar = 2)
2. Pressione ESPAÇO em ambos clientes
✅ Esperado: Jogo reinicia, placar ZERADO
```

---

### Testes de Rede

#### **Teste de Latência**
```bash
# Medir latência
ping <IP_DO_SERVIDOR>

✅ Ideal: < 50ms
⚠️ Aceitável: < 100ms
❌ Problemático: > 100ms
```

#### **Teste de Perda de Pacotes**
```bash
# Simular perda de pacotes (Linux)
sudo tc qdisc add dev eth0 root netem loss 5%

# Executar jogo e observar comportamento
# TCP deve recuperar automaticamente

# Remover simulação
sudo tc qdisc del dev eth0 root
```

---

## 🐛 Troubleshooting

### Problema 1: "Address already in use"

**Causa:** Porta 5555 já está em uso

**Solução:**
```bash
# Linux/macOS - Encontrar processo usando a porta
lsof -i :5555
kill -9 <PID>

# Windows
netstat -ano | findstr :5555
taskkill /PID <PID> /F

# Ou alterar a porta em server.py e client.py
```

---

### Problema 2: Cliente não conecta

**Verificações:**
1. ✅ Servidor está rodando?
2. ✅ IP correto em `client.py`?
3. ✅ Firewall permite conexões na porta 5555?
4. ✅ Ambas máquinas na mesma rede?

**Teste de conectividade:**
```bash
# Testar se porta está acessível
telnet <IP_SERVIDOR> 5555
# ou
nc -zv <IP_SERVIDOR> 5555
```

---

### Problema 3: Rastros não aparecem

**Causa:** Cliente não está processando estados do servidor

**Debug:**
```python
# Adicionar prints em client.py
def listen_server(self):
    while True:
        data = self.client.recv(4096).decode()
        print(f"[DEBUG] Recebido: {data[:100]}")  # Primeiros 100 chars
        # ...
```

---

### Problema 4: Jogo muito lento

**Causas Possíveis:**
- Latência de rede alta
- CPU sobrecarregado

**Soluções:**
```python
# Reduzir TICK_RATE (menos FPS)
TICK_RATE = 1 / 20  # 20 FPS em vez de 30

# Ou otimizar detecção de colisão (usar set em vez de list)
self.rastro_completo = set()  # Em vez de []
```

---

## 🔮 Melhorias Futuras

### Curto Prazo
- [ ] Reconexão automática de clientes
- [ ] Tratamento de desconexão durante partida
- [ ] Logs estruturados (logging module)
- [ ] Configuração via arquivo (config.json)

### Médio Prazo
- [ ] Suporte a mais de 2 jogadores
- [ ] Modo espectador
- [ ] Replay de partidas
- [ ] Estatísticas de jogo (histórico de vitórias)

### Longo Prazo
- [ ] Matchmaking automático
- [ ] Cliente web (WebSockets)
- [ ] Predição no cliente (client-side prediction)
- [ ] Migração para UDP com confiabilidade customizada

---

## 📚 Referências

### Documentação Técnica
1. **Python Socket Programming**
   - Documentação Oficial: https://docs.python.org/3/library/socket.html
   - Real Python Tutorial: https://realpython.com/python-sockets/

2. **TCP/IP Protocol Suite**
   - RFC 793 (TCP): https://datatracker.ietf.org/doc/html/rfc793
   - Tanenbaum, A. S. (2003). *Computer Networks* (4ª ed.). Prentice Hall.

3. **Game Networking**
   - Glazer, G., & Madhav, S. (2015). *Multiplayer Game Programming*. Addison-Wesley.
   - Fiedler, G. (2010). *Networking for Game Programmers*. https://gafferongames.com/

4. **Pyxel Engine**
   - Documentação Oficial: https://github.com/kitao/pyxel
   - API Reference: https://github.com/kitao/pyxel/blob/main/docs/README.md

### Conceitos de Redes
- **Modelo OSI e TCP/IP**: Kurose, J. F., & Ross, K. W. (2017). *Computer Networking: A Top-Down Approach* (7ª ed.).
- **Client-Server Architecture**: Microsoft Docs - Client/Server Architecture
- **JSON Serialization**: RFC 8259 - The JavaScript Object Notation (JSON) Data Interchange Format

---

## 👥 Autores e Contribuidores

- **Desenvolvedor Principal**: Ana Luiza Oliveira, João Vitor Guimarães, Ryan Araújo, Yuri Coutinho
- **Instituição**: UESC (Universidade Estadual de Santa Cruz)
- **Disciplina**: Redes de Computadores
- **Professor**: Joorge Lima de Oliveira Filho

---

## 📄 Licença

Este projeto foi desenvolvido para fins acadêmicos como parte da disciplina de Redes de Computadores.

---

## 📞 Contato

Para dúvidas ou sugestões sobre o projeto:
- **GitHub**: https://github.com/yuriccosta/tron_game
- **Email**: jlofilho@uesc.br (Professor)

---

## 🏆 Critérios de Avaliação

### Programa (3,5 pontos) ✅
- [x] Implementação completa cliente-servidor
- [x] Comunicação via socket TCP funcional
- [x] Lógica de jogo implementada e testada
- [x] Código organizado e comentado

### Protocolo de Aplicação (3,0 pontos) ✅
- [x] Protocolo customizado documentado
- [x] Todos os eventos mapeados
- [x] Estados do sistema definidos
- [x] Mensagens especificadas com formato e semântica

### Documentação (2,5 pontos) ✅
- [x] README.md completo e organizado
- [x] Propósito do software explicado
- [x] Motivação da escolha do TCP documentada
- [x] Requisitos mínimos especificados
- [x] Instruções de instalação e execução claras

### Originalidade (1,0 ponto) ✅
- [x] Implementação de sistema de placar (melhor de 3)
- [x] Sistema de reset colaborativo (ambos devem concordar)
- [x] Otimização de banda (envio incremental de rastros)
- [x] Tratamento robusto de fragmentação de pacotes TCP

---

**Versão:** 1.0  
**Data:** Dezembro de 2025  
**Status:** ✅ Completo e Funcional
