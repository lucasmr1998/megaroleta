# Instruções para o Claude Code

Sempre responda em português brasileiro.

## Contexto do Projeto

Este é o **Clube Megalink**, uma plataforma de fidelidade gamificada para a Megalink Telecom (provedor de internet do Piauí e Maranhão). O sistema integra com o Hubsoft (ERP do provedor) e usa validação via WhatsApp/OTP.

O projeto opera em um **triângulo de valor**: parceiro B2B (recebe clientes), cliente assinante (recebe benefícios) e Megalink (retém, engaja e se diferencia).

## Documentação Estratégica

Antes de fazer qualquer alteração significativa, consulte:

- `docs/ESTRATEGIA.md` — Visão, triângulo de valor, modelo de negócio, diferenciais
- `docs/ROADMAP.md` — Entregas realizadas, plano de lançamento Floriano, próximos passos
- `docs/DECISOES.md` — Registro de decisões arquiteturais e de produto
- `docs/REGRAS_NEGOCIO.md` — Regras que NUNCA devem ser quebradas
- `DOCUMENTACAO.md` — Documentação técnica completa
- `docs/agentes/` — Time de agentes IA (executivo + comercial + tools)
- `docs/entregas/` — Documentos produzidos pelos agentes (planejamentos, specs, etc.)
- `docs/contexto/` — Base de conhecimento (brandbook, metas, financeiro, sessões)

## Regras de Segurança

- **NUNCA** commitar arquivos com credenciais sensíveis
- **SEMPRE** usar variáveis de ambiente para senhas e chaves (`.env`)
- **VERIFICAR** se `.env` está no `.gitignore` antes de criar
- **ALERTAR** se detectar credenciais hardcoded no código
- **TODAS** as credenciais já foram migradas para `.env` (DB principal, Hubsoft, OpenAI, Django SECRET_KEY)
- **DEBUG/ALLOWED_HOSTS** controlados via `.env` (padrão seguro em produção)
- **Markdown** sanitizado com `bleach` no backend e `DOMPurify` no frontend
- **CSRF** obrigatório em todos os endpoints (sem exceções `@csrf_exempt`)

## Stack Tecnológica

- Backend: Django 4.2+ / Python 3.10+
- Frontend: HTML5, CSS3, JavaScript Vanilla (jQuery)
- Banco de Dados: PostgreSQL (produção)
- Integrações: Hubsoft (PostgreSQL direto + webhook n8n), OpenAI API (sala de agentes)
- Deploy: Gunicorn + Nginx
- Variáveis de ambiente: python-dotenv (`.env`)
- Sanitização: bleach (backend), DOMPurify (frontend)
- Cache: Django cache framework — LocMemCache (contexto IA 5min, Hubsoft 1h)
- Logging: `logging` module (estruturado, sem `print()`)

## Arquitetura de Apps Django

```
megaroleta/
├── roleta/          # Core: roleta, membros, prêmios, gamificação, área do membro
├── parceiros/       # B2B: parceiros, cupons, resgates, painel do parceiro
├── indicacoes/      # Indicações, embaixadores, página pública
├── carteirinha/     # Carteirinhas virtuais, modelos, regras de atribuição
├── gestao/          # Gestão de projetos, Kanban, documentos, agentes IA, tools, sala de agentes
└── sorteio/         # Projeto Django (settings, urls raiz)
```

### Views por App

- `roleta/views/core_views.py` — index, logout
- `roleta/views/api_views.py` — init-dados, cadastrar, OTP, resgate cupom, indicação
- `roleta/views/dashboard_views.py` — Admin: dashboard, prêmios, membros, giros, relatórios
- `roleta/views/membro_views.py` — Hub, jogar, cupons, indicar, perfil, missões, carteirinha
- `parceiros/views.py` — Admin: parceiros, cupons, resgates, detalhe
- `parceiros/views_painel.py` — Painel do parceiro: dashboard, cupons, resgates, validar
- `indicacoes/views.py` — Admin: indicações, embaixadores, visual + página pública
- `carteirinha/views.py` — Admin: modelos, regras, preview + membro: carteirinha
- `gestao/views/` — Módulo split em 10 arquivos (ver seção Módulo de Gestão)

### Modelos Principais

**roleta**: MembroClube, PremioRoleta, ParticipanteRoleta, RegraPontuacao, ExtratoPontuacao, NivelClube, RoletaConfig, RouletteAsset, Cidade
**parceiros**: Parceiro (com FK User), CupomDesconto, ResgateCupom
**indicacoes**: Indicacao, IndicacaoConfig
**carteirinha**: ModeloCarteirinha, RegraAtribuicao, CarteirinhaMembro
**gestao**: Projeto, Etapa, Tarefa, Nota, Documento, Agente, ToolAgente, MensagemChat, LogTool, Reuniao, MensagemReuniao, Automacao, Alerta, Proposta, FAQCategoria, FAQItem

## Dashboard Admin — Topbar de Módulos

```
[Roleta] [Parceiros] [Indicações] [Carteirinha] [Operação] [Relatórios] [Gestão]  📖 ⚙ ↗
```

Cada módulo tem sidebar própria que muda conforme selecionado.

## Área do Membro — Hub com 6 Cards

```
[Roleta] [Cupons] [Indicar] [Perfil] [Carteirinha] [Missões]
```

Fundo `#000b4a`, cards brancos, mobile-first.

## Painel do Parceiro

Acesso via `/roleta/parceiro/login/` — independente do admin.
Páginas: Dashboard, Cupons (com solicitação), Resgates, Validar.

## Módulo de Gestão

Tudo gerenciável pelo painel — zero dependência de filesystem. Doc técnico completo no banco (slug: `doc-tecnico-modulo-gestao`, v4.0).

### Models principais (14 + 2 FAQ)
- **Projeto, Etapa, Tarefa, Nota** — gestão de projetos com Kanban
- **Documento** — modelo unificado (estratégia, regras, roadmap, entregas, sessões, contexto)
- **Agente** — configurável (prompt, modelo, ícone, cor, time, ativar/desativar)
- **ToolAgente** — 69 tools (25 executáveis + 44 conhecimento)
- **MensagemChat, Reuniao, MensagemReuniao** — chat 1:1 e reuniões
- **Automacao** — 10 automações, 2 modos: tool (execução direta) e agente (rotina 3 etapas)
- **Alerta** — gerado por monitoramento (tipo, severidade, resolvido)
- **Proposta** — ação proposta por agente com `dados_execucao` para execução diferida
- **LogTool** — log unificado de execução (com `tempo_ms` e histórico completo sem truncamento)
- **FAQCategoria, FAQItem** — FAQ gerada por IA

### Agentes IA (17 ativos, 5 times)
- **C-Level (4):** CEO, CTO, CPO, CFO — estratégia e decisões
- **Marketing (5):** CMO, PMM, Content, Customer Marketing, Growth — comunicação e aquisição
- **Customer Success (3):** CS Manager, Support, Community — retenção e atendimento
- **Parcerias (1):** B2B — prospecção de parceiros
- **Produto & Tech (4):** PM, QA (gpt-4o), DevOps, Analista de Dados — construção e qualidade

### Tools (69)
- **25 executáveis**: salvar doc, criar tarefa, consulta_dados (16 queries), explorar_codigo, validar_agentes, verificar_integridade
- **44 conhecimento**: análise, copy, ROI, spec, planejamento
- **consulta_dados**: inclui minhas_tarefas e verificar_integridade
- **validar_agentes**: testa todos os 17 agentes
- **verificar_integridade**: checa consistência de dados

### Automações (10, 2 modos)
- **modo=tool**: execução direta. Se `encaminhar_para` configurado, agente analisa resultado.
- **modo=agente**: rotina 3 etapas — etapa1 (coleta dados) → etapa2 (analisa + age) → etapa3 (conclui tarefas)
- Monitoramento gera alertas, ações geram propostas com `dados_execucao`.

### Sidebar Gestão
```
Gestão: Dashboard | Propostas [N] | Alertas [N] | Documentos | Projetos
Inteligência: Sala | Mapa
Sistema: Agentes | Ferramentas | Automações
```

### Management Commands
```
python manage.py testar_agentes --rapido     # 122+ testes estrutura
python manage.py testar_agentes              # + testes com IA
python manage.py executar_automacoes         # scheduler de automações
```

### Arquivos-Chave
- `gestao/models.py`, `urls.py`
- `gestao/views/` — Split em módulos:
  - `helpers.py` — `_render_md_text`, `_sanitizar_markdown`
  - `dashboard.py` — dashboard_ceo, gestao_mapa
  - `projetos.py` — CRUD projetos, kanban, tarefas
  - `documentos.py` — CRUD documentos, sessões, entregas
  - `agentes.py` — CRUD agentes + tools
  - `sala.py` — sala_agentes, sala_chat, sala_reuniao, api_chat
  - `api.py` — api_slash_command
  - `automacoes.py` — automações, TOOL_EXECUTORS, executores, logs, FAQ
  - `propostas_alertas.py` — propostas + alertas
- `gestao/ai_service.py` — chat com IA, contexto cacheado (5min), moderador
- `gestao/agent_actions.py` — parser de blocos de ação (case-insensitive)
- `gestao/signals.py` — invalidação de cache ao salvar Projeto/Tarefa/Documento
- `gestao/consulta_dados_service.py` (16 queries)
- `gestao/faq_service.py`, `health_service.py`
- `gestao/context_processors.py`, `templatetags/gestao_tags.py`
- `gestao/management/commands/testar_agentes.py`, `executar_automacoes.py`

## Padrões de Código

- Use `@transaction.atomic` para operações que modificam saldo/estoque
- Proteção contra race condition: `select_for_update()` + `F()` expressions
- Performance: `annotate`, `select_related`, `prefetch_related`, paginação 50/pg
- **N+1 proibido**: usar `dict()` + `annotate()` em vez de queries dentro de loops
- Serviços stateless (métodos estáticos)
- Todos os formulários POST devem salvar TODOS os campos do template (bug recorrente!)
- Mobile first: toda interface do membro deve funcionar em celular
- **Logging**: usar `logging.getLogger(__name__)` — NUNCA `print()` ou `open('debug.log')`
- **Credenciais**: SEMPRE via `os.getenv()` — NUNCA hardcoded
- **Sanitização**: markdown → `bleach.clean()` no backend (entrada + saída), `DOMPurify.sanitize()` no frontend
- **Cache**: contexto IA cacheado 5min com invalidação via signals (`gestao/signals.py`)
- **CSRF**: NUNCA usar `@csrf_exempt` — templates já enviam `X-CSRFToken` nos headers AJAX

## Integrações

- **Hubsoft**: Webhook n8n (dados do cliente) + PostgreSQL read-only (cidade, recorrência, app). Credenciais no `.env` (`HUBSOFT_DB_*`). Cache de 1h via Django cache framework.
- **OTP WhatsApp**: Webhook n8n, rate limiting 60s, expiração 10min
- **OpenAI**: API key no `.env` (`OPENAI_API_KEY`), modelo configurável por agente (padrão `gpt-4o-mini`). Contexto limitado a 20 projetos + 30 tarefas/projeto. Contexto cacheado 5min (invalidado via signals).

## Variáveis de Ambiente (.env)

```
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*
DB_NAME=megasorteio
DB_USER=admin
DB_PASSWORD=...
DB_HOST=187.62.153.52
DB_PORT=5432
HUBSOFT_DB_USER=mega_leitura
HUBSOFT_DB_PASSWORD=...
HUBSOFT_DB_HOST=177.10.118.77
HUBSOFT_DB_PORT=9432
HUBSOFT_DB_NAME=hubsoft
OPENAI_API_KEY=sk-proj-...
```

## Observações de Segurança

- Dados sensíveis de clientes (CPF, telefone, endereço) — seguir LGPD
- Credenciais migradas para `.env` (DB principal, Hubsoft, OpenAI, SECRET_KEY) ✅
- DEBUG e ALLOWED_HOSTS controlados via `.env` ✅
- Parceiro só vê seus próprios dados (isolamento por FK)
- Logs debug removidos — sem exposição de CPF/telefone em logs ✅
- Markdown sanitizado (bleach + DOMPurify) contra XSS ✅
- Race conditions protegidas com `select_for_update()` + `F()` ✅
