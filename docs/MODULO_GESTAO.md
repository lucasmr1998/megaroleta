# Modulo Gestao — Documentacao Completa

## O que e

Modulo Django para gestao de projetos com agentes IA autonomos. Os agentes trabalham em times (C-Level, Marketing, Customer Success, Parcerias, Produto & Tech), executam tarefas, delegam entre si e geram propostas que o CEO aprova.

Funciona como uma "empresa virtual" onde os agentes sao funcionarios com responsabilidades, backlog de tarefas, processos definidos e rotinas automaticas.

---

## Requisitos

- Python 3.10+
- Django 4.2+
- PostgreSQL
- API Key: Google AI (Gemini) ou OpenAI
- Pacotes: `google-genai`, `openai`, `bleach`, `python-dotenv`

## Variaveis de Ambiente

```
OPENAI_API_KEY=sk-...          # Opcional (se usar modelos OpenAI)
GOOGLE_AI_API_KEY=AIza...      # Para Gemini e geracao de imagens
```

---

## Arquitetura

```
gestao/
├── models.py                   # 17 models (Projeto, Tarefa, Agente, Documento, etc.)
├── ai_service.py               # Chat com IA (OpenAI + Gemini), contexto, processos
├── agent_actions.py            # 19 blocos de acao executaveis pelos agentes
├── consulta_dados_service.py   # 16 consultas de dados do sistema
├── signals.py                  # Invalidacao de cache ao salvar Projeto/Tarefa/Doc
├── context_processors.py       # Badges de propostas/alertas pendentes
├── faq_service.py              # Geracao de FAQ por IA
├── health_service.py           # Health check do sistema
├── apps.py                     # Registro de signals
├── urls.py                     # 50+ rotas
├── views/
│   ├── __init__.py             # Re-exporta tudo
│   ├── helpers.py              # Markdown render + sanitizacao
│   ├── dashboard.py            # Dashboard CEO + mapa
│   ├── projetos.py             # CRUD projetos, kanban, tarefas
│   ├── documentos.py           # CRUD documentos, sessoes, entregas
│   ├── agentes.py              # CRUD agentes + tools
│   ├── sala.py                 # Chat 1:1, reunioes, API chat
│   ├── api.py                  # Slash commands
│   ├── automacoes.py           # Automacoes, executores, rotinas de agentes
│   └── propostas_alertas.py    # Aprovacao de propostas, alertas
├── management/commands/
│   ├── testar_agentes.py       # 122+ testes estruturais + IA
│   └── executar_automacoes.py  # Scheduler de automacoes
├── templatetags/
│   └── gestao_tags.py          # Tags customizadas
└── templates/gestao/dashboard/ # 30 templates HTML
```

---

## Models Principais

### Projeto
Gestao de projetos com Kanban. Campos: nome, status, prioridade, objetivo, publico_alvo, criterios_sucesso, riscos, responsavel, orcamento.

### Tarefa
Unidade de trabalho dos agentes. Campos estruturados para execucao:

| Campo | Descricao |
|-------|-----------|
| `titulo` | Nome da tarefa |
| `objetivo` | O que deve alcancar |
| `contexto` | Inputs, referencias, restricoes |
| `passos` | Passo-a-passo numerado |
| `entregavel` | O que deve ser produzido |
| `criterios_aceite` | Como saber que esta concluida |
| `processo` | FK para Documento de processo |
| `pasta_destino` | FK para pasta onde salvar resultado |
| `criado_por_agente` | FK — None = humano, preenchido = agente delegou |
| `nivel_delegacao` | 0=humano, 1=agente, 2=sub-delegado (max 2) |
| `log_execucao` | Historico de execucao com timestamps |
| `status` | rascunho, pendente, em_andamento, concluida, bloqueada |

### Agente
Agente IA configuravel. Campos:
- `slug`, `nome`, `descricao`, `icone`, `cor`, `time`
- `prompt` — System prompt para chat interativo
- `prompt_autonomo` — System prompt para rotina autonoma (se vazio, usa `prompt`)
- `modelo` — Ex: `gemini-2.5-flash`, `gpt-4o-mini`, `gpt-4o`

### Documento
Modelo unificado. Categorias: estrategia, regras, roadmap, decisoes, entrega, sessao, contexto, relatorio, email, processo, imagem, outro.
- Campo `arquivo` (ImageField) para imagens geradas por IA
- Campo `visivel_agentes` controla se aparece no contexto dos agentes
- Organizado em `PastaDocumento` hierarquica (pai/filho)

### Automacao
Trigger periodico com dois modos:
- **modo=tool**: executa tool direto (ex: health_check). Se `encaminhar_para` configurado, agente analisa resultado.
- **modo=agente**: acorda agente para rotina. Fluxo: buscar backlog → executar tarefas 1 por vez → gerar propostas.

### Proposta
Acao proposta por agente aguardando aprovacao do CEO. Campo `dados_execucao` (JSON) armazena o bloco de acao para execucao diferida ao aprovar.

### Alerta
Gerado por monitoramento automatico. Tipos: health, estoque, churn, metrica, erro, sistema.

---

## Fluxo de Chat

```
CEO envia mensagem no chat
  ↓
ai_service.chat_agente()
  - Seleciona prompt (chat ou autonomo)
  - Carrega contexto do negocio (cache 5min)
  - Busca processo relevante (se modo=chat)
  - Envia para OpenAI ou Gemini
  ↓
Agente responde com blocos de acao
  ↓
agent_actions.processar_acoes()
  - Detecta 19 tipos de blocos via regex
  - Executa handlers (criar tarefa, salvar doc, consultar dados, gerar imagem)
  - Registra no LogTool
  ↓
Resposta limpa retorna ao CEO
```

## Fluxo de Automacao (modo=agente)

```
executar_automacoes (cron)
  ↓
Para cada tarefa do agente no backlog:
  Se PENDENTE → gera proposta para mover para em_andamento
  Se EM_ANDAMENTO → executa com 2 chamadas IA:
    1. "Execute esta tarefa" → agente pede dados (CONSULTAR_DADOS)
    2. Recebe dados → produz entregavel (SALVAR_EMAIL, CRIAR_TAREFA, etc.)
  ↓
Blocos viram Propostas (execucao diferida)
  ↓
CEO aprova → sistema executa bloco
```

## Travas de Seguranca

| Trava | Descricao |
|-------|-----------|
| Anti-loop | Agente nao pode criar tarefa para si mesmo |
| Nivel max | Delegacao max 2 niveis (humano → agente → sub-agente) |
| Campos obrigatorios | Tarefa criada por agente exige `objetivo` |
| Status rascunho | Tarefa de agente nasce como rascunho (precisa aprovacao) |
| Limite por ciclo | Max 3 tarefas criadas por agente / Max 10 propostas por ciclo |
| Alertas | Gera alerta quando limites sao atingidos |

---

## Blocos de Acao (19 tipos)

### Executaveis pelo agente

| Bloco | Funcao |
|-------|--------|
| `---SALVAR_DOCUMENTO---` | Salva documento (markdown) |
| `---SALVAR_EMAIL---` | Salva template de e-mail (HTML) |
| `---CRIAR_TAREFA---` | Cria tarefa no kanban |
| `---ATUALIZAR_TAREFA---` | Atualiza status de tarefa |
| `---CRIAR_PROJETO---` | Cria projeto |
| `---ATUALIZAR_PROJETO---` | Atualiza projeto |
| `---CRIAR_ETAPA---` | Cria etapa no projeto |
| `---CONSULTAR_DADOS---` | Executa 1 de 16 consultas de dados |
| `---CONSULTAR_DOCUMENTO---` | Le documento por slug |
| `---LISTAR_DOCUMENTOS---` | Lista documentos por categoria |
| `---EXPLORAR_CODIGO---` | Busca no codigo-fonte |
| `---VALIDAR_AGENTES---` | Testa todos os agentes |
| `---GERAR_BANNER---` | Gera banner via Gemini (imagem) |
| `---GERAR_IMAGEM_CUPOM---` | Gera imagem de cupom via Gemini |
| `---GERAR_ARTE_CAMPANHA---` | Gera arte de campanha via Gemini |

### Consultas de Dados Disponiveis

```
resumo_geral, membros_novos, membros_inativos, membros_por_cidade,
niveis_distribuicao, giros_periodo, premios_sorteados, estoque_premios,
cupons_status, resgates_por_parceiro, parceiros_resumo, indicacoes_periodo,
projetos_status, tarefas_pendentes, verificar_integridade, minhas_tarefas
```

---

## Agentes (17 ativos, 5 times)

| Time | Agentes |
|------|---------|
| C-Level | CEO, CTO, CPO, CFO |
| Marketing | CMO, PMM, Content, Customer Marketing, Growth |
| Customer Success | CS Manager, Support, Community |
| Parcerias | Comercial B2B |
| Produto & Tech | Product Manager, QA, DevOps, Analista de Dados |

Cada agente tem:
- Prompt de chat (conversacional)
- Prompt autonomo (executor de tarefas)
- Modelo IA configuravel (Gemini Flash, GPT-4o-mini, etc.)
- Tools disponiveis (69 no total)

---

## Geracao de Imagens

Usa **Gemini 2.5 Flash Image** para gerar:
- Banners para landing page/campanhas
- Imagens de cupons de parceiros
- Artes para campanhas de marketing

Imagens sao salvas como Documento (categoria `imagem`) com campo `arquivo` (ImageField).

Limite: 5 imagens por ciclo de automacao.

---

## Interface (Sidebar)

```
Gestao:
  Dashboard CEO        — Metricas, atividade dos agentes, propostas, alertas
  Propostas [N]        — Fila de aprovacao
  Alertas [N]          — Alertas do sistema
  Documentos           — Todos os documentos por categoria/pasta
  Projetos             — Lista + Kanban

Inteligencia:
  Sala de Agentes      — Chat 1:1 e reunioes
  Mapa                 — Visualizacao do sistema

Sistema:
  Agentes              — CRUD com prompts duplos (chat + autonomo)
  Ferramentas          — 69 tools (executaveis + conhecimento)
  Automacoes           — 10 automacoes com scheduler
  Logs                 — Historico de execucoes
```

---

## Como Instalar em Outro Projeto

### 1. Copiar o app

```bash
cp -r gestao/ seu_projeto/gestao/
```

### 2. Adicionar ao INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...
    'gestao',
]
```

### 3. Adicionar ao settings.py

```python
# Cache (necessario para contexto IA)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'gestao-cache',
        'TIMEOUT': 300,
    }
}

# Context processor (badges de propostas/alertas)
TEMPLATES[0]['OPTIONS']['context_processors'].append('gestao.context_processors.gestao_badges')
```

### 4. Adicionar URLs

```python
# urls.py raiz
urlpatterns = [
    path('roleta/', include('gestao.urls')),  # ou outro prefixo
]
```

### 5. Variaveis de ambiente

```
GOOGLE_AI_API_KEY=sua_chave_aqui
OPENAI_API_KEY=sua_chave_aqui  # opcional
```

### 6. Migrar

```bash
python manage.py migrate gestao
```

### 7. Criar agentes iniciais

Os agentes sao criados via painel (Dashboard > Sistema > Agentes) ou via management command.

### 8. Configurar automacoes

Via painel (Dashboard > Sistema > Automacoes) ou banco.

---

## Management Commands

```bash
# Testes estruturais (rapido, sem IA)
python manage.py testar_agentes --rapido

# Testes completos (com chamadas IA)
python manage.py testar_agentes

# Executar automacoes pendentes
python manage.py executar_automacoes
```

---

## Dependencias do Modulo

O modulo gestao depende de models de outros apps para consultas de dados:

- `roleta.models`: MembroClube, PremioRoleta, NivelClube, ParticipanteRoleta, Cidade
- `parceiros.models`: Parceiro, CupomDesconto, ResgateCupom
- `indicacoes.models`: Indicacao

Para usar em outro projeto, adapte o `consulta_dados_service.py` para seus models.

---

## Providers de IA Suportados

| Provider | Modelos | Uso |
|----------|---------|-----|
| Google Gemini | `gemini-2.5-flash` (chat), `gemini-2.5-flash-image` (imagens) | Padrao atual |
| OpenAI | `gpt-4o-mini`, `gpt-4o` | Alternativo |

O modelo e configuravel por agente. O sistema detecta automaticamente pelo prefixo (`gemini-` = Google, resto = OpenAI).
