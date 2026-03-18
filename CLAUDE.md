# Instruções para o Claude Code

Sempre responda em português brasileiro.

## Contexto do Projeto

Este é o projeto **MegaRoleta**, uma plataforma de gamificação e premiação para provedores de internet. O sistema integra com o Hubsoft (ERP do provedor) e usa validação via WhatsApp/OTP.

## Regras de Segurança

- **NUNCA** commitar arquivos com credenciais sensíveis
- **SEMPRE** usar variáveis de ambiente para senhas e chaves
- **VERIFICAR** se `.env` está no `.gitignore` antes de criar
- **ALERTAR** se detectar credenciais hardcoded no código

## Stack Tecnológica

- Backend: Django 4.2+ / Python 3.10+
- Frontend: HTML5, CSS3, JavaScript Vanilla
- Banco de Dados: PostgreSQL (produção) / SQLite3 (dev)
- Integrações: Hubsoft (PostgreSQL direto + webhook n8n)
- Deploy: Gunicorn + Nginx

## Comandos Úteis

### Desenvolvimento
```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Rodar migrations
.venv/bin/python manage.py migrate

# Criar superusuário
.venv/bin/python manage.py createsuperuser

# Rodar servidor de desenvolvimento
.venv/bin/python manage.py runserver
```

### Produção
```bash
# Coletar arquivos estáticos
.venv/bin/python manage.py collectstatic --noinput

# Reiniciar serviço Gunicorn
sudo systemctl restart megaroleta

# Ver logs do serviço
sudo journalctl -u megaroleta -n 50 -f

# Testar configuração do Nginx
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

## Arquitetura do Código

### Estrutura de Pastas
```
roleta/
├── models.py              # Modelos de dados (9 models)
├── admin.py               # Configuração do Django Admin
├── urls.py                # Rotas da aplicação
├── views/                 # Views separadas por domínio
│   ├── core_views.py      # Views principais
│   ├── api_views.py       # Endpoints JSON (sorteio, OTP)
│   ├── dashboard_views.py # Painel administrativo
│   └── docs_views.py      # Documentação
├── services/              # Lógica de negócio isolada
│   ├── sorteio_service.py     # Algoritmo de sorteio
│   ├── hubsoft_service.py     # Integração Hubsoft
│   ├── otp_service.py         # Envio de OTP via WhatsApp
│   └── gamification_service.py # Sistema de pontos/XP
└── templates/             # HTML/CSS/JS
```

### Modelos Principais

- **MembroClube**: CRM com gamificação (saldo, XP, níveis)
- **PremioRoleta**: Catálogo de prêmios com estoque e probabilidade
- **ParticipanteRoleta**: Histórico de giros realizados
- **RegraPontuacao**: Regras de gamificação (gatilhos e recompensas)
- **ExtratoPontuacao**: Histórico auditável de pontos ganhos

### Padrões de Código

- Use `@transaction.atomic` para operações que modificam múltiplos registros
- Proteção contra race condition: `select_for_update()` + `F()` expressions
- Serviços devem ser stateless (métodos estáticos)
- Logging via Django logger (não arquivos diretos)

## Integrações Críticas

### Hubsoft
- **Webhook n8n**: Consulta dados cadastrais do cliente
- **PostgreSQL direto**: Consulta cidade de instalação e pontos extras
- **Gatilhos de pontuação**: recorrência, pagamento adiantado, uso do app

### OTP via WhatsApp
- Rate limiting: 60 segundos entre requisições
- Expiração: 10 minutos
- Envio via webhook n8n

## Boas Práticas

- Sempre validar saldo antes de permitir giro
- Verificar limites de giros configurados
- Sincronizar pontos Hubsoft na validação do OTP
- Usar transações atômicas para operações críticas
- Logs detalhados para debug de produção

## Observações de Segurança

⚠️ **ATENÇÃO**: Este projeto contém dados sensíveis de clientes (CPF, telefone, endereço).
- Sempre seguir LGPD ao manipular dados pessoais
- Não expor informações sensíveis em logs
- Validar e sanitizar todos os inputs do usuário
