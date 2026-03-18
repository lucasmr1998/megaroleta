# 🎰 MegaRoleta

> Plataforma de engajamento e premiação para provedores de internet — roleta digital com gamificação, integração Hubsoft e validação via WhatsApp.

---

## 📖 Visão Geral

O **MegaRoleta** é um sistema completo em Django para campanhas de fidelização de clientes. O cliente informa seu CPF, valida sua identidade via código OTP no WhatsApp e gira uma roleta de prêmios. O resultado é decidido pelo backend (algoritmo ponderado por probabilidade e estoque) — o frontend apenas anima onde a roleta para.

---

## 🏗️ Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.10+ / Django |
| Frontend | HTML5, CSS3, JavaScript Vanilla |
| Animações | Canvas + CSS Transitions |
| Libs JS | jQuery (máscaras), SweetAlert2 (alertas), Chart.js (dashboard) |
| Banco (dev) | SQLite3 |
| Banco (prod) | PostgreSQL (Hubsoft: `177.10.118.77:9432`) |
| Servidor (prod) | Gunicorn + Nginx + Certbot (HTTPS) |
| Automações | n8n (webhooks WhatsApp/OTP) |

---

## ✨ Recursos Principais

### Fluxo do Cliente
- **Identificação dinâmica** — usuário informa o CPF; o sistema consulta o Hubsoft para preencher dados automaticamente
- **Validação OTP** — código enviado via WhatsApp (n8n) para confirmar identidade
- **Roleta inteligente** — backend sorteia o prêmio por peso/probabilidade antes de animar o frontend

### Gamificação (Clube MegaLink)
- **Saldo de Giros** — moeda interna para girar a roleta
- **XP e Níveis** — Bronze, Prata, Ouro etc., ganhos por ações do cliente
- **Missões** — tarefas que concedem giros extras (pagar adiantado, usar app, ativar recorrência)

### Integração Hubsoft
Consultado em dois momentos:
1. **Webhook n8n** → dados cadastrais do cliente (nome, email, endereço)
2. **Banco PostgreSQL direto** → pontuações extras baseadas em comportamento:
   - `hubsoft_recorrencia` — pagamento em cartão recorrente (+3 giros, +30 XP)
   - `hubsoft_adiantado` — fatura paga antes do vencimento, mensal (+5 giros, +50 XP)
   - `hubsoft_app` — cliente usa o App Central (+2 giros, +20 XP)

### Dashboard Administrativo (`/roleta/dashboard/`)
- Funil de conversão (Iniciados → Validados → Jogadores)
- Gráficos de giros diários (últimos 7 dias)
- Distribuição de prêmios
- Gestão de prêmios, cidades, assets visuais, gamificação e configurações
- **🔬 Diagnóstico Hubsoft** — testa consulta de cidade e pontuações por CPF em tempo real

---

## 🗄️ Modelos de Dados

| Model | Responsabilidade |
|---|---|
| `MembroClube` | CRM do cliente autenticado (saldo, XP, validação) |
| `ParticipanteRoleta` | Histórico de cada giro realizado |
| `PremioRoleta` | Catálogo de prêmios com estoque e probabilidade por cidade |
| `RegraPontuacao` | Regras de gamificação (gatilho, pontos, limite) |
| `ExtratoPontuacao` | Histórico de pontos ganhos por membro |
| `NivelClube` | Definição de níveis e XP necessário |
| `Cidade` | Segmentação geográfica dos prêmios |
| `RoletaConfig` | Configurações gerais (custo do giro, XP por giro, nome do clube) |
| `RouletteAsset` | Imagens da roleta (frames, fundo, logo, ponteiro) |

---

## 🔒 Segurança

- **OTP via WhatsApp** — sessão autenticada apenas após validação do código
- **Rate limiting** — bloqueio de 60s entre solicitações de OTP (`HTTP 429`)
- **Sessão segura** — `request.session` com cookie HttpOnly; nenhum dado sensível exposto no frontend
- **Verificação de saldo** — backend valida saldo antes de executar qualquer giro

---

## 💻 Executar Localmente

```bash
# 1. Clonar e entrar na pasta
git clone https://github.com/consulteplus/megaroleta.git
cd megaroleta

# 2. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Banco de dados
.venv/bin/python manage.py migrate

# 5. Criar superusuário
.venv/bin/python manage.py createsuperuser

# 6. Rodar servidor de desenvolvimento
.venv/bin/python manage.py runserver
```

Acesse:
- Roleta: http://127.0.0.1:8000/roleta/
- Admin Django: http://127.0.0.1:8000/admin/
- Dashboard: http://127.0.0.1:8000/roleta/dashboard/

---

## 🚀 Deploy em Produção (Gunicorn + Nginx)

O projeto usa um socket Unix para comunicação Gunicorn ↔ Nginx.

### Serviço Gunicorn (`/etc/systemd/system/megaroleta.service`)

```ini
[Unit]
Description=Gunicorn MegaRoleta
After=network.target

[Service]
User=lucas
Group=www-data
WorkingDirectory=/home/lucas/megaroleta
ExecStart=/home/lucas/megaroleta/.venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/home/lucas/megaroleta/megaroleta.sock \
    sorteio.wsgi:application

[Install]
WantedBy=multi-user.target
```

### Comandos do Serviço

```bash
# Iniciar
sudo systemctl start megaroleta

# Reiniciar (após mudanças no código Python ou templates)
sudo systemctl restart megaroleta

# Verificar status e logs
sudo systemctl status megaroleta
sudo journalctl -u megaroleta -n 50

# Habilitar para iniciar com o sistema
sudo systemctl enable megaroleta
```

### Coletar arquivos estáticos (após mudanças em CSS/JS)

```bash
cd /home/lucas/megaroleta
.venv/bin/python manage.py collectstatic --noinput
```

### Nginx

O Nginx atua como proxy reverso, servindo os arquivos estáticos e redirecionando o restante para o socket do Gunicorn. Após editar a config do Nginx:

```bash
sudo nginx -t                        # Verificar sintaxe
sudo systemctl reload nginx          # Aplicar mudanças
```

---

## 🗺️ URLs Principais

| URL | Descrição |
|---|---|
| `/roleta/` | Página da roleta (frontend do cliente) |
| `/roleta/dashboard/` | Painel administrativo |
| `/roleta/dashboard/diagnostico-hubsoft/` | 🔬 Diagnóstico de consulta Hubsoft por CPF |
| `/roleta/dashboard/gamificacao/` | Gerenciar regras de pontuação e níveis |
| `/roleta/dashboard/participantes/` | Lista de membros do clube |
| `/roleta/api/init-dados/` | Endpoint JSON com dados iniciais da roleta |
| `/roleta/verificar-cliente/` | Consulta CPF no Hubsoft (AJAX) |
| `/roleta/solicitar-otp/` | Envia OTP via WhatsApp |
| `/roleta/validar-otp/` | Valida o código OTP e sincroniza pontuações |

---

*Desenvolvido para engajar clientes e alavancar métricas do hub comercial. 🎰*