# Documentacao — Modulo de Gestao

> Documentacao tecnica e funcional do modulo de gestao de projetos e sala de agentes IA.

---

## 1. Visao Geral

O modulo de gestao e o centro de comando do CEO. Ele consolida:
- **Dashboard executivo** com metricas do sistema em tempo real
- **Gestao de projetos** com Kanban visual
- **Sala de agentes IA** com chat individual e reunioes
- **Entregas e sessoes** dos agentes renderizadas como documentos

Acessivel via `/roleta/dashboard/gestao/` — requer login de staff Django.

---

## 2. Arquitetura

### App Django: `gestao`

```
gestao/
├── models.py              # Projeto, Etapa, Tarefa, Nota, Reuniao, MensagemReuniao
├── views.py               # Dashboard CEO, Kanban, Sala, Entregas, Sessoes
├── ai_service.py          # Integracao OpenAI, carregamento de contexto, moderador
├── agent_actions.py       # Acoes dos agentes (salvar entrega, criar tarefa, etc.)
├── urls.py                # Rotas do modulo
├── admin.py               # Django Admin
└── templates/gestao/dashboard/
    ├── ceo.html                # Dashboard CEO
    ├── projetos.html           # Lista de projetos
    ├── kanban.html             # Kanban board
    ├── sala.html               # Lobby da sala de agentes
    ├── sala_chat.html          # Chat individual com agente
    ├── sala_reuniao.html       # Reuniao com agentes
    ├── sala_reuniao_criar.html # Criar nova reuniao
    ├── entregas.html           # Lista de entregas
    ├── sessoes.html            # Lista de sessoes
    ├── documento.html          # Visualizar markdown renderizado
    └── entrega_editar.html     # Editor markdown com preview
```

---

## 3. Models

### Projeto
Projeto de alto nivel (ex: Lancamento Floriano).

| Campo | Tipo | Descricao |
|-------|------|-----------|
| nome | CharField(200) | Nome do projeto |
| descricao | TextField | Descricao opcional |
| responsavel | CharField(100) | Nome ou papel (ex: CEO) |
| data_inicio | DateField | Data de inicio |
| data_fim_prevista | DateField | Previsao de conclusao |
| ativo | BooleanField | Se o projeto esta ativo |

**Property:** `progresso` — calcula % de tarefas concluidas.

### Etapa
Fase dentro de um projeto (ex: Semana 1, Semana 2).

| Campo | Tipo | Descricao |
|-------|------|-----------|
| projeto | FK Projeto | Projeto pai |
| nome | CharField(200) | Nome da etapa |
| ordem | IntegerField | Ordem de exibicao |
| data_inicio | DateField | Inicio da etapa |
| data_fim | DateField | Fim da etapa |

### Tarefa
Acao especifica dentro de um projeto.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| projeto | FK Projeto | Projeto pai |
| etapa | FK Etapa (nullable) | Etapa associada |
| titulo | CharField(300) | Descricao da tarefa |
| descricao | TextField | Detalhes opcionais |
| responsavel | CharField(100) | Quem faz (ex: CEO, Comercial B2B) |
| status | CharField | `pendente`, `em_andamento`, `concluida`, `bloqueada` |
| prioridade | CharField | `critica`, `alta`, `media`, `baixa` |
| data_limite | DateField | Prazo |
| data_conclusao | DateTimeField | Quando foi concluida |
| ordem | IntegerField | Ordem de exibicao |

### Nota
Comentario em uma tarefa.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| tarefa | FK Tarefa | Tarefa associada |
| autor | CharField(100) | Quem escreveu |
| texto | TextField | Conteudo |

### Reuniao
Reuniao com agentes de IA.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| nome | CharField(200) | Nome da reuniao (ex: Review Semanal) |
| descricao | TextField | Objetivo da reuniao |
| agentes | CharField(200) | IDs dos agentes separados por virgula |
| ativa | BooleanField | Se a reuniao esta ativa |

**Properties:** `agentes_lista` (lista de IDs), `total_mensagens` (count).

### MensagemReuniao
Mensagem dentro de uma reuniao.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| reuniao | FK Reuniao | Reuniao associada |
| tipo | CharField | `ceo`, `agente`, `moderador` |
| agente_id | CharField(20) | ID do agente (se tipo=agente) |
| agente_nome | CharField(100) | Nome do agente |
| conteudo | TextField | Conteudo da mensagem (markdown) |

---

## 4. Rotas

| Rota | View | Descricao |
|------|------|-----------|
| `/dashboard/gestao/` | `dashboard_ceo` | Dashboard CEO com KPIs |
| `/dashboard/gestao/projetos/` | `gestao_projetos` | Lista e criacao de projetos |
| `/dashboard/gestao/kanban/<id>/` | `kanban` | Kanban board de um projeto |
| `/dashboard/gestao/sessoes/` | `gestao_sessoes` | Lista de sessoes com agentes |
| `/dashboard/gestao/sessoes/<arquivo>/` | `gestao_sessao_detalhe` | Visualizar sessao |
| `/dashboard/gestao/entregas/` | `gestao_entregas` | Lista de entregas dos agentes |
| `/dashboard/gestao/entregas/<agente>/<arquivo>/` | `gestao_entrega_detalhe` | Visualizar entrega |
| `/dashboard/gestao/entregas/<agente>/<arquivo>/editar/` | `gestao_entrega_editar` | Editor markdown |
| `/dashboard/gestao/sala/` | `sala_agentes` | Lobby da sala de agentes |
| `/dashboard/gestao/sala/reuniao/criar/` | `sala_reuniao_criar` | Criar nova reuniao |
| `/dashboard/gestao/sala/reuniao/<id>/` | `sala_reuniao` | Reuniao com agentes |
| `/dashboard/gestao/sala/api/chat/` | `api_chat` | API AJAX para chat |
| `/dashboard/gestao/sala/api/salvar-sessao/` | `api_salvar_sessao` | Salvar sessao do chat |
| `/dashboard/gestao/sala/<agente_id>/` | `sala_chat` | Chat individual |

---

## 5. Dashboard CEO

### Metricas do Sistema (tempo real)
Dados lidos diretamente do banco:
- Membros (total + validados)
- Giros realizados
- Parceiros ativos + cupons ativos
- Resgates (total + utilizados)
- Indicacoes (total + convertidas)

### Metricas de Tarefas
- Total, pendentes, em andamento, concluidas, bloqueadas
- Projetos ativos com barra de progresso
- Carga por responsavel (quem tem mais tarefas)
- Tarefas urgentes (criticas + altas)
- Proximos prazos

---

## 6. Kanban

Board visual com 4 colunas:

| Coluna | Cor | Acoes |
|--------|-----|-------|
| Pendente | Cinza | Botao "Iniciar →" |
| Em Andamento | Azul | Botao "← Voltar" + "Concluir ✓" |
| Concluida | Verde | Texto riscado |
| Bloqueada | Vermelho | Botao "Desbloquear" |

### Funcionalidades
- Cards com borda colorida por prioridade (vermelha = critica, amarela = alta)
- Responsavel e prazo visiveis no card
- Modal para criar nova tarefa (titulo, descricao, responsavel, prioridade, etapa, prazo)
- Barra de progresso do projeto no topo

---

## 7. Sala de Agentes IA

### Integracao OpenAI
- **Modelo:** `gpt-4o-mini`
- **API Key:** Variavel de ambiente `OPENAI_API_KEY` (arquivo `.env`)
- **Biblioteca:** `openai` (Python SDK)

### Contexto Carregado Automaticamente
Cada agente recebe como system message:
1. **Prompt do agente** (arquivo `.md` da pasta `docs/agentes/`)
2. **Documentos estrategicos** (ESTRATEGIA.md, ROADMAP.md, REGRAS_NEGOCIO.md, DECISOES.md)
3. **Entregas dos agentes** (todos os `.md` de `docs/entregas/`)
4. **Sessoes recentes** (ultimas 5 de `docs/contexto/sessoes/`)
5. **Contexto do negocio** (brandbook, metas, financeiro, concorrentes, FAQ)
6. **Projetos e tarefas** (do banco, em tempo real)
7. **Metricas do sistema** (membros, giros, parceiros, cupons, indicacoes, por cidade)
8. **Instrucoes adicionais** (modo conversa, identidade, acoes disponiveis)

### Agentes Disponiveis

| ID | Nome | Time | Arquivo |
|----|------|------|---------|
| cto | CTO | Executivo | `docs/agentes/executivo/cto.md` |
| cpo | CPO | Executivo | `docs/agentes/executivo/cpo.md` |
| cfo | CFO | Executivo | `docs/agentes/executivo/cfo.md` |
| cmo | CMO | Comercial | `docs/agentes/comercial/cmo.md` |
| pmm | PMM | Comercial | `docs/agentes/comercial/pmm.md` |
| b2b | Comercial B2B | Comercial | `docs/agentes/comercial/comercial_b2b.md` |
| cs | Customer Success | Comercial | `docs/agentes/comercial/customer_success.md` |

---

## 8. Chat Individual

### Fluxo
1. CEO escolhe agente no lobby
2. Digita mensagem → envia via AJAX para `/api/chat/` (modo `chat`)
3. Servidor carrega prompt + contexto completo + historico da sessao
4. Chama OpenAI API
5. Processa acoes embutidas na resposta
6. Salva no historico da sessao Django (ultimas 20 mensagens)
7. Retorna resposta renderizada em markdown (via `marked.js`)

### Funcionalidades
- Historico mantido na sessao (persiste entre mensagens)
- Botao "Salvar Sessao" gera arquivo `.md` em `docs/contexto/sessoes/`
- Botao "Limpar Chat" reseta historico
- Markdown renderizado (tabelas, codigo, headings, listas)
- Animacao "pensando..." enquanto aguarda

---

## 9. Reunioes

### Criar Reuniao
- Nome (obrigatorio)
- Descricao (opcional)
- Participantes (checkboxes dos 7 agentes)

### Moderador Deterministico
O moderador NAO usa IA — e logica Python pura que analisa palavras-chave:

```
"CMO como esta?" → ['cmo']
"Comercial, update" → ['b2b']
"go-to-market" → ['pmm']
"como estamos?" → ['cpo']
"todos, review" → ['cpo', 'cmo', 'b2b'] (max 3)
```

Regras de priorizacao:
1. Mencao direta pelo nome → so esse agente
2. Palavra-chave do tema → agente dono do tema
3. "todos" / "cada um" → maximo 3
4. Fallback → CPO

### Fluxo da Reuniao
1. CEO digita mensagem
2. Moderador deterministico decide qual agente responde
3. Mensagem do CEO salva no banco (`MensagemReuniao tipo=ceo`)
4. Agente selecionado recebe a mensagem + historico (so msgs do CEO + suas proprias respostas)
5. Agente responde → resposta salva no banco (`MensagemReuniao tipo=agente`)
6. Botoes "Ouvir tambem: [CTO] [PMM] ..." aparecem
7. CEO pode clicar num botao para pedir a outro agente → gera nova mensagem do CEO + resposta

### Historico Persistente
- Todas as mensagens salvas no banco (modelo `MensagemReuniao`)
- Ao recarregar a pagina, historico completo e carregado
- Markdown renderizado via `marked.js` no carregamento

### Isolamento de Contexto
Cada agente recebe no historico SOMENTE:
- Mensagens do CEO
- Suas proprias respostas anteriores

NAO ve respostas de outros agentes. Isso evita roleplay (agente falando como se fosse outro).

---

## 10. Acoes dos Agentes

Os agentes podem executar acoes no sistema incluindo blocos especiais na resposta:

### Salvar Entrega
```
---SALVAR_ENTREGA---
agente: pmm
arquivo: nome.md
conteudo: (markdown)
---FIM_ENTREGA---
```
Salva em `docs/entregas/[agente]/[arquivo]`.

### Salvar Sessao
```
---SALVAR_SESSAO---
arquivo: 2026-03-19_agente_topico.md
conteudo: (markdown)
---FIM_SESSAO---
```
Salva em `docs/contexto/sessoes/`.

### Criar Tarefa
```
---CRIAR_TAREFA---
projeto: Lancamento Floriano
titulo: Fazer X
responsavel: CEO
prioridade: alta
---FIM_TAREFA---
```
Cria tarefa no projeto ativo mais relevante.

### Atualizar Tarefa
```
---ATUALIZAR_TAREFA---
titulo: Texto parcial do titulo
status: concluida
---FIM_TAREFA---
```

### Consultar Outro Agente
```
---CONSULTAR_AGENTE---
agente: cto
pergunta: Isso e viavel tecnicamente?
---FIM_CONSULTA---
```
Chama outro agente e inclui a resposta na mensagem.

### Processamento
O `agent_actions.py` processa os blocos na resposta:
1. Detecta blocos via regex
2. Executa a acao (salvar arquivo, criar no banco, etc.)
3. Substitui o bloco por confirmacao: `> ✅ Entrega salva: entregas/pmm/...`

---

## 11. Entregas e Sessoes

### Entregas (`docs/entregas/`)
- Documentos de trabalho produzidos pelos agentes
- Organizados por agente: `docs/entregas/pmm/`, `docs/entregas/cmo/`, etc.
- Visualizacao com markdown renderizado
- Editor com preview em tempo real (lado a lado)
- Botao "Editar" na pagina de visualizacao

### Sessoes (`docs/contexto/sessoes/`)
- Transcricoes de conversas com agentes
- Nomeadas por data + agente + topico
- Botao "Salvar Sessao" no chat individual gera automaticamente
- Visualizacao com markdown renderizado

---

## 12. Regras de Comunicacao dos Agentes

### Modo Conversa
- Perguntas casuais ("como esta?") → resposta curta (3-8 frases), SEM template
- Perguntas rapidas ("quantos parceiros?") → 1-3 frases diretas
- Pedido de acao ("crie tarefa") → executa e confirma em 1 frase
- Readout completo → SOMENTE quando CEO pede explicitamente

### Identidade
- Agente fala SOMENTE sobre sua area
- NUNCA fala pelos outros agentes
- NUNCA inclui secoes como "### CTO:", "### CMO:" na resposta
- Se perguntam algo fora da area: "isso e com o [agente X]"

---

## 13. Integracao no Admin

### Topbar
Modulo "Gestao" na topbar do dashboard admin.

### Sidebar
```
GESTAO
├── Dashboard CEO
├── Projetos (Kanban)
├── Sala de Agentes
├── Entregas
└── Sessoes
```

---

## 14. Dependencias

| Pacote | Versao | Uso |
|--------|--------|-----|
| openai | latest | API do GPT-4o-mini |
| python-dotenv | latest | Carregar .env |
| markdown | latest | Renderizar .md no servidor (entregas/sessoes) |
| marked.js | CDN | Renderizar markdown no browser (chat) |

### Variavel de Ambiente
```
OPENAI_API_KEY=sk-proj-...
```
Arquivo `.env` na raiz do projeto (no `.gitignore`).
