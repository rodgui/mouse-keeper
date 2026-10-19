# 🖱️ Mouse Keeper

Um utilitário Python leve e eficiente para manter seu computador sempre ativo, simulando movimentos e cliques periódicos do mouse em áreas pré-definidas da tela.

---

## ✨ Destaques

- **Zero Dependências no macOS:** Utiliza diretamente as APIs nativas do *CoreGraphics* via `ctypes` (não precisa instalar nada via `pip`).
- **Suporte Multiplataforma:** Suporta `PyAutoGUI` em Linux e Windows (ou como alternativa no macOS).
- **Área Discreta (2cm x 2cm por padrão):** O cursor se movimenta suavemente dentro de uma caixinha minúscula (~80x80px), sem tirar o mouse do seu campo de visão ou atrapalhar seu trabalho.
- **Áreas Nomeadas por Texto:** Suporta regiões como `centro`, `superior-esquerda`, `superior-direita`, `inferior-esquerda`, `inferior-direita` ou `tela-toda`.
- **Proteção contra Hot Corners:** Mantém margem de segurança das bordas para evitar disparar atalhos de canto do sistema operacional ou bloqueios.
- **Interrupção Rápida:** Encerramento limpo a qualquer momento com `Ctrl + C`.

---

## 🚀 Instalação e Execução

### No macOS (Nativo, sem instalação adicional)
Basta clonar e executar:

```bash
git clone https://github.com/rodgui/mouse-keeper.git
cd mouse-keeper
python3 mouse_keeper.py
```

> **Nota para macOS:** Na primeira execução, certifique-se de que o aplicativo de terminal (Terminal, iTerm2, VS Code, etc.) possua permissão de controle em:
> **Ajustes do Sistema > Privacidade e Segurança > Acessibilidade**.

### No Linux / Windows
Recomenda-se instalar as dependências opcionais:

```bash
pip install -r requirements.txt
python3 mouse_keeper.py
```

---

## 🛠️ Exemplos de Uso

### 1. Padrão (2cm x 2cm centralizado, move a cada 10s e clica a cada 30s)
```bash
python3 mouse_keeper.py
```

### 2. No canto inferior-direito
```bash
python3 mouse_keeper.py --area inferior-direita
```

### 3. Tempos customizados (move a cada 5s, clica a cada 15s)
```bash
python3 mouse_keeper.py --area superior-esquerda -m 5 -c 15
```

### 4. Ajustar tamanho da área para 1cm x 1cm
```bash
python3 mouse_keeper.py --area centro --cm 1.0
```

### 5. Apenas movimentar sem clicar (`-c 0`)
```bash
python3 mouse_keeper.py --area centro -m 10 -c 0
```

### 6. Usar quadrante amplo da tela
```bash
python3 mouse_keeper.py --area superior-direita --full-quadrant
```

---

## ⚙️ Parâmetros Disponíveis

| Parâmetro | Atalho | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `--area` | `-a` | `str` | `centro` | Região da tela (`centro`, `superior-esquerda`, `superior-direita`, `inferior-esquerda`, `inferior-direita`, `tela-toda`) |
| `--cm` / `--size-cm` | | `float` | `2.0` | Tamanho do lado da área em centímetros |
| `--move-interval` | `-m` | `float` | `10.0` | Intervalo em segundos **(X)** entre cada movimento |
| `--click-interval` | `-c` | `float` | `30.0` | Intervalo em segundos **(Xy)** entre cada clique (`0` desativa) |
| `--duration` | | `float` | `0.3` | Duração do deslize suave do cursor em segundos |
| `--full-quadrant` | | `flag` | `False` | Utiliza o quadrante amplo em vez da pequena área de 2cm x 2cm |

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para obter mais informações.
