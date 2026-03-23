# Documentacao — Modulo de Gestao

> Centro de comando do CEO. Gestao de projetos, documentos, agentes IA e ferramentas.

---

## 1. Visao Geral

O modulo de gestao centraliza:
- **Dashboard executivo** com metricas do sistema em tempo real
- **Gestao de projetos** completa (objetivo, stakeholders, riscos, Kanban)
- **Documentos unificados** (estrategia, regras, entregas, sessoes, contexto)
- **Agentes IA** configuraveis pelo painel (prompt, modelo, ativar/desativar)
- **Tools** dos agentes gerenciaveis (executaveis + conhecimento)
- **Sala de agentes** com chat persistente, slash commands e invocacao de agentes
- **Reunioes** com moderador deterministico

Acessivel via `/roleta/dashboard/gestao/` — requer login de staff Django.

---

## 2. Arquitetura

### App Django: `gestao`

```
gestao/
├── models.py              # Projeto, Etapa, Tarefa, Nota, Documento, Agente,
│                          # ToolAgente, MensagemChat, LogTool, Reuniao, MensagemReuniao
├── views.py               # Dashboard, Kanban, Documentos, Agentes, Tools, Sala, APIs
├── ai_service.py          # Integracao OpenAI, contexto dinamico, moderador
├── agent_actions.py       # Acoes executaveis dos agentes (salvar doc, criar tarefa, etc.)
├── urls.py                # ~30 rotas
└── templates/gestao/dashboard/
    ├── ceo.html                # Dashboard CEO
    ├── projetos.html           # Lista de projetos
    ├── projeto_editar.html     # Editor de projeto (4 abas)
    ├── kanban.html             # Kanban board
    ├── tarefa_editar.html      # Editor de tarefa individual
    ├── documentos.html         # Gestor de documentos (filtro, busca, tabela)
    ├── documento.html          # Visualizar markdown renderizado
    ├── documento_editar.html   # Editor markdown com preview
    ├── agentes.html            # Lista de agentes IA
    ├── agente_editar.html      # Editor de agente (dados + prompt)
    ├── tools.html              # Lista de tools + logs de execucao
    ├── tool_editar.html        # Editor de tool
    ├── sala.html               # Lobby da sala de agentes
    ├── sala_chat.html          # Chat individual com agente
    ├── sala_reuniao.html       # Reuniao com agentes
    └── sala_reuniao_criar.html # Criar nova reuniao
```

---

## 3. Models

### Projeto
Projeto completo com contexto estrategico para agentes IA.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| nome | CharField(200) | Nome do projeto |
| descricao | TextField | Descricao geral |
| status | CharField | `planejamento`, `em_andamento`, `pausado`, `concluido`, `cancelado` |
| prioridade | CharField | `critica`, `alta`, `media`, `baixa` |
| objetivo | TextField | O que deve alcancar, qual problema resolve |
| publico_alvo | TextField | Para quem (ex: membros Floriano) |
| criterios_sucesso | TextField | KPIs e metas concretas |
| riscos | TextField | O que pode dar errado, dependencias |
| premissas | TextField | Premissas assumidas |
| responsavel | CharField(100) | Dono do projeto |
| stakeholders | TextField | Envolvidos e papeis (1 por linha: Nome - Papel) |
| contexto_agentes | TextField | Info extra para os agentes IA |
| orcamento | TextField | Budget e custos previstos |
| data_inicio | DateField | Inicio |
| data_fim_prevista | DateField | Previsao de conclusao |
| ativo | BooleanField | Ativo/arquivado |

**Property:** `progresso` — % de tarefas concluidas.

### Etapa
Fase dentro de um projeto (ex: Semana 1, Semana 2).

| Campo | Tipo | Descricao |
|-------|------|-----------|
| projeto | FK Projeto | Projeto pai |
| nome | CharField(200) | Nome da etapa |
| ordem | IntegerField | Ordem de exibicao |

### Tarefa
Acao especifica dentro de um projeto.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| projeto | FK Projeto | Projeto pai |
| etapa | FK Etapa (nullable) | Etapa associada |
| titulo | CharField(300) | Descricao da tarefa |
| descricao | TextField | Detalhes opcionais |
| responsavel | CharField(100) | Quem faz (ex: CEO, B2B) |
| status | CharField | `pendente`, `em_andamento`, `concluida`, `bloqueada` |
| prioridade | CharField | `critica`, `alta`, `media`, `baixa` |
| data_limite | DateField | Prazo |
| data_conclusao | DateTimeField | Quando foi concluida |

### Nota
Comentario em uma tarefa.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| tarefa | FK Tarefa | Tarefa associada |
| autor | CharField(100) | Quem escreveu |
| texto | TextField | Conteudo |

### Documento
Modelo unificado para todos os documentos da empresa.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| titulo | CharField(300) | Titulo do documento |
| slug | SlugField(100) | ID unico |
| categoria | CharField | `estrategia`, `regras`, `roadmap`, `decisoes`, `entrega`, `sessao`, `contexto`, `outro` |
| agente | FK Agente (nullable) | Agente autor (para entregas/sessoes) |
| conteudo | TextField | Conteudo em markdown |
| resumo | TextField | Resumo curto |
| descricao | CharField(300) | Descricao curta |
| visivel_agentes | BooleanField | Se agentes IA recebem este doc como contexto |
| ordem | IntegerField | Ordem de exibicao |

**Categorias:**
- `estrategia` — Visao, modelo de negocio, diferenciais
- `regras` — Regras que nunca devem ser quebradas
- `roadmap` — Entregas realizadas, proximos passos
- `decisoes` — Registro de decisoes arquiteturais
- `entrega` — Documentos produzidos pelos agentes (planejamentos, specs)
- `sessao` — Resumos/transcricoes de conversas com agentes
- `contexto` — Base de conhecimento (metas, financeiro, concorrentes)
- `outro` — Qualquer outro

### Agente
Agente de IA configuravel pelo painel.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| slug | SlugField(20) | ID unico (ex: cto, cmo, b2b) |
| nome | CharField(100) | Nome de exibicao |
| descricao | CharField(200) | Descricao curta |
| icone | CharField(50) | Classe FontAwesome |
| cor | CharField(10) | Cor hex |
| time | CharField | `executivo`, `comercial`, `tools` |
| prompt | TextField | System prompt completo (markdown) |
| modelo | CharField(50) | Modelo OpenAI (ex: gpt-4o-mini) |
| ativo | BooleanField | Ativo/inativo |
| ordem | IntegerField | Ordem de exibicao |

### ToolAgente
Ferramenta disponivel para os agentes.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| slug | SlugField(50) | ID unico (ex: salvar_documento, calculadora_roi) |
| nome | CharField(100) | Nome de exibicao |
| descricao | CharField(300) | O que a tool faz |
| tipo | CharField | `executavel` ou `conhecimento` |
| prompt | TextField | Instrucoes/prompt da tool |
| exemplo | TextField | Exemplo de uso |
| ativo | BooleanField | Ativa/inativa |

**Tipos:**
- `executavel` — Executa acoes no sistema (salvar documento, criar tarefa, etc.)
- `conhecimento` — Prompt que ensina o agente a fazer algo (analise de dados, copy, ROI, etc.)

### MensagemChat
Mensagem persistente no chat 1:1 com agente.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| agente | FK Agente | Agente da conversa |
| role | CharField | `user` ou `assistant` |
| conteudo | TextField | Texto da mensagem |

### LogTool
Log de execucao de tools pelos agentes.

| Campo | Tipo | Descricao |
|-------|------|-----------|
| tool | FK ToolAgente (nullable) | Tool executada |
| tool_slug | CharField(50) | Slug no momento da execucao |
| agente | FK Agente (nullable) | Agente que executou |
| resultado | TextField | Resultado da execucao |
| sucesso | BooleanField | Se executou com sucesso |

### Reuniao / MensagemReuniao
Reuniao com multiplos agentes. Mensagens salvas no banco com tipo (ceo/agente/moderador).

---

## 4. Rotas

### Dashboard e Projetos
| Rota | View | Descricao |
|------|------|-----------|
| `/dashboard/gestao/` | `dashboard_ceo` | Dashboard com KPIs |
| `/dashboard/gestao/projetos/` | `gestao_projetos` | Lista e criacao de projetos |
| `/dashboard/gestao/projetos/<id>/editar/` | `gestao_projeto_editar` | Editor completo (4 abas) |
| `/dashboard/gestao/projetos/<id>/toggle/` | `gestao_projeto_toggle` | Ativar/arquivar |
| `/dashboard/gestao/projetos/<id>/excluir/` | `gestao_projeto_excluir` | Excluir |
| `/dashboard/gestao/kanban/<id>/` | `kanban` | Kanban board |
| `/dashboard/gestao/kanban/<id>/tarefa/<id>/editar/` | `gestao_tarefa_editar` | Editor de tarefa |

### Documentos
| Rota | View | Descricao |
|------|------|-----------|
| `/dashboard/gestao/documentos/` | `gestao_documentos` | Gestor com filtro/busca |
| `/dashboard/gestao/documentos/criar/` | `gestao_documento_criar` | Criar documento |
| `/dashboard/gestao/documentos/<id>/` | `gestao_documento_detalhe` | Visualizar |
| `/dashboard/gestao/documentos/<id>/editar/` | `gestao_documento_editar` | Editor markdown |
| `/dashboard/gestao/documentos/<id>/excluir/` | `gestao_documento_excluir` | Excluir |

### Agentes e Tools
| Rota | View | Descricao |
|------|------|-----------|
| `/dashboard/gestao/agentes/` | `gestao_agentes` | Lista de agentes |
| `/dashboard/gestao/agentes/criar/` | `gestao_agente_criar` | Criar agente |
| `/dashboard/gestao/agentes/<id>/editar/` | `gestao_agente_editar` | Editor (dados + prompt) |
| `/dashboard/gestao/agentes/<id>/toggle/` | `gestao_agente_toggle` | Ativar/desativar |
| `/dashboard/gestao/tools/` | `gestao_tools` | Lista + logs de execucao |
| `/dashboard/gestao/tools/criar/` | `gestao_tool_criar` | Criar tool |
| `/dashboard/gestao/tools/<id>/editar/` | `gestao_tool_editar` | Editor |
| `/dashboard/gestao/tools/<id>/toggle/` | `gestao_tool_toggle` | Ativar/desativar |
| `/dashboard/gestao/tools/<id>/excluir/` | `gestao_tool_excluir` | Excluir |

### Sala de Agentes
| Rota | View | Descricao |
|------|------|-----------|
| `/dashboard/gestao/sala/` | `sala_agentes` | Lobby |
| `/dashboard/gestao/sala/<agente_id>/` | `sala_chat` | Chat individual |
| `/dashboard/gestao/sala/reuniao/criar/` | `sala_reuniao_criar` | Criar reuniao |
| `/dashboard/gestao/sala/reuniao/<id>/` | `sala_reuniao` | Reuniao |
| `/dashboard/gestao/sala/api/chat/` | `api_chat` | API AJAX para chat |
| `/dashboard/gestao/sala/api/comando/` | `api_slash_command` | API para slash commands |
| `/dashboard/gestao/sala/api/salvar-sessao/` | `api_salvar_sessao` | Salvar sessao como documento |

> Todos os endpoints da API usam CSRF padrao do Django (sem @csrf_exempt). Templates enviam X-CSRFToken.

---

## 5. Sidebar

```
GESTAO
├── Dashboard
├── Projetos
├── Sala de Agentes
├── Documentos
├── Agentes IA
└── Tools
```

---

## 6. Sala de Agentes

### Chat Individual
- Historico **persistente no banco** (model `MensagemChat`)
- Markdown renderizado via `marked.js` + sanitizado com `DOMPurify`
- Agente convidado: `/agentes ceo` traz outro agente para responder no chat
- Consulta entre agentes inclui contexto da conversa atual
- Agente consultado recebe instrucao de ser direto e assertivo (nao perguntar de volta)

### Slash Commands
Comandos digitados no chat com `/`:

| Comando | Descricao |
|---------|-----------|
| `/help` | Lista de comandos |
| `/tools` | Ferramentas dos agentes |
| `/tarefas` | Tarefas ativas dos projetos |
| `/docs` | Documentos recentes |
| `/projetos` | Projetos ativos com progresso |
| `/agentes` | Agentes IA ativos |
| `/limpar` | Limpa historico do chat |

**Comportamento interativo:**
- Ao digitar `/` aparece popup de autocomplete
- Ao selecionar um comando com argumentos (ex: `/projetos`) mostra opcoes do banco
- Filtra conforme digita (ex: `/projetos flo` → Lancamento Floriano)
- Navegacao: setas cima/baixo, Tab/Enter para selecionar, Esc para fechar
- `/agentes <slug>` invoca o agente no chat (responde a proxima mensagem)
- `/projetos <nome>` mostra detalhes com tarefas

### Reunioes
- Moderador **deterministico** (sem IA, sem custo) — analisa palavras-chave
- Mensagens persistem no banco (`MensagemReuniao`)
- Cada agente recebe apenas: msgs do CEO + suas proprias respostas
- Botoes "Ouvir tambem" para pedir opiniao de outros agentes

---

## 7. Tools dos Agentes

### Executaveis (agent_actions.py)
Processadas via regex na resposta do agente:

| Tool | Formato | Acao |
|------|---------|------|
| Salvar Documento | `---SALVAR_DOCUMENTO---...---FIM_DOCUMENTO---` | Cria Documento no banco |
| Criar Tarefa | `---CRIAR_TAREFA---...---FIM_TAREFA---` | Cria Tarefa no Kanban |
| Atualizar Tarefa | `---ATUALIZAR_TAREFA---...---FIM_TAREFA---` | Muda status |
| Consultar Agente | `---CONSULTAR_AGENTE---...---FIM_CONSULTA---` | Chama outro agente com contexto |

Retrocompatibilidade: `SALVAR_ENTREGA` e `SALVAR_SESSAO` ainda funcionam (mapeados para `SALVAR_DOCUMENTO`).

### Conhecimento (prompts carregados do banco)
| Tool | Descricao |
|------|-----------|
| Analise de Dados | Consulta metricas e gera insights acionaveis |
| Gerador de Copy | Textos para WhatsApp, Instagram, impresso |
| Calculadora ROI | ROI de acoes e features (3 cenarios) |
| Auditor de Codigo | Checklist seguranca/performance/produto |
| Gerador de Spec | Spec completa de feature com user stories e ICE |
| Prospector de Parceiro | Abordagem personalizada B2B com scripts |

### Logging
Cada execucao de tool e registrada no `LogTool`:
- Tool, agente, resultado, sucesso/erro, timestamp
- Contadores visiveis na pagina de Tools
- Ultimas 15 execucoes listadas com detalhes

---

## 8. Contexto Carregado para Agentes

Cada agente recebe como system message:

1. **Prompt do agente** (do banco, model `Agente.prompt`)
2. **Documentos visiveis** (`Documento.visivel_agentes=True`) — estrategia, regras, contexto
3. **Projetos completos** — objetivo, stakeholders, riscos, criterios, tarefas ativas
   - **Limitado a 20 projetos** mais recentes, 30 tarefas/projeto, textos truncados a 2000 chars
4. **Metricas do sistema** — membros, giros, parceiros, cupons, indicacoes, cidades
5. **Entregas dos agentes** (Documentos categoria `entrega`)
6. **Tools ativas** — executaveis (formato e instrucoes) + conhecimento (prompts)
7. **Instrucoes de comunicacao** — modo conversa, identidade, assertividade
8. **Agentes disponiveis** para consulta

---

## 9. Regras de Comunicacao

### Modo Conversa
- Perguntas casuais → resposta curta (3-8 frases), SEM template
- Perguntas rapidas → 1-3 frases diretas
- Pedido de acao → executa e confirma em 1 frase
- Readout completo → SOMENTE quando CEO pede explicitamente

### Identidade
- Agente fala SOMENTE sobre sua area
- NUNCA fala pelos outros agentes
- Se perguntam algo fora da area: "isso e com o [agente X]"

### Consulta entre Agentes
- Agente consultado recebe as ultimas 10 mensagens da conversa como contexto
- Instrucao explicita de NAO perguntar de volta — ser direto e assertivo
- Se faltar info, assumir cenario mais provavel

---

## 10. Dependencias

| Pacote | Uso |
|--------|-----|
| openai | API OpenAI (modelo configuravel por agente) |
| python-dotenv | Carregar .env |
| markdown | Renderizar markdown no servidor |
| marked.js (CDN) | Renderizar markdown no browser |
| bleach | Sanitizar HTML de markdown contra XSS |
| DOMPurify (CDN) | Sanitizar HTML no browser contra XSS |

### Variavel de Ambiente
```
OPENAI_API_KEY=sk-proj-...
```
