# LojaFlow

Sistema de gestão desktop para pequenos comércios — offline-first, moderno e simples.

## Funcionalidades

| Módulo | Descrição |
|---|---|
| **PDV** | Ponto de venda com suporte a leitor de código de barras, carrinho editável, desconto e múltiplas formas de pagamento |
| **Produtos** | Catálogo completo com categorias, preços, estoque e código de barras |
| **Estoque** | Controle de estoque com alertas de estoque baixo e histórico de movimentações |
| **Relatórios** | Vendas por período com gráfico diário, top produtos e breakdown por pagamento |
| **Clientes** | Cadastro simples de clientes (nome, telefone, CPF) |
| **Configurações** | Dados da loja, impressora térmica ESC/POS e gerenciamento de usuário |

## Stack Técnica

- **UI**: PySide6 (Qt6) com tema escuro customizado
- **Banco de dados**: SQLite via SQLAlchemy (offline)
- **Gráficos**: Matplotlib integrado ao Qt
- **Impressão**: python-escpos (térmicas ESC/POS) com fallback Qt
- **Leitor de barras**: Keyboard wedge — nenhum driver necessário
- **Empacotamento**: PyInstaller

## Instalação

```bash
# 1. Clone o repositório
git clone <url>
cd LojaFlow

# 2. Crie um ambiente virtual
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Execute
python main.py
```

## Credenciais padrão

| Campo | Valor |
|---|---|
| Usuário | `admin` |
| Senha | `admin123` |

> Altere a senha em **Configurações → Alterar Senha** após o primeiro acesso.

## Testes

```bash
pip install pytest
pytest tests/ -v
```

## Uso do PDV

1. Abra o módulo **PDV**
2. Aponte o leitor de código de barras para o produto — ele é capturado automaticamente
3. Ajuste quantidades direto na tabela do carrinho
4. Clique em **Finalizar Venda**, escolha a forma de pagamento e confirme
5. O estoque é atualizado automaticamente

## Configurar Impressora Térmica

Em **Configurações → Impressora Térmica**, informe:
- `USB` — impressora USB Epson padrão
- `/dev/ttyUSB0` — serial Linux
- `COM3` — serial Windows
- `192.168.1.100` — impressora de rede

## Empacotamento (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name LojaFlow main.py
# Executável gerado em: dist/LojaFlow
```

## Estrutura do Projeto

```
LojaFlow/
├── main.py               # Entry point
├── app/
│   ├── database.py       # SQLAlchemy + SQLite
│   ├── models/           # ORM models
│   ├── services/         # Lógica de negócio
│   ├── views/            # Telas PySide6
│   └── controllers/      # Conectores View ↔ Service
├── assets/
│   └── style.qss         # Tema escuro Qt
└── tests/                # Testes unitários (pytest)
```
