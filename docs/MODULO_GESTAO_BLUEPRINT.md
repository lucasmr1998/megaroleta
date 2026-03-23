# Blueprint — Modulo de Gestao com Agentes IA

> Guia completo para replicar o sistema de gestao inteligente em qualquer projeto Django.
> Baseado na implementacao real do Clube Megalink (marco/2026).

---

## 1. Visao Geral

O modulo de gestao e um centro de comando que combina:
- **Gestao de projetos** (Kanban, tarefas, etapas)
- **Base de documentos** (estrategia, regras, entregas, contexto)
- **Time de agentes IA** que conversam, executam acoes e consultam uns aos outros
- **Ferramentas** (tools) que os agentes usam para agir no sistema
- **Automacoes** que disparam agente + ferramenta em intervalos

### Principio Central

```
Automacao (trigger) → Agente (cerebro) → Ferramenta (mao)
          cron              IA              acao no sistema
```

O mesmo agente pode ser chamado manualmente (Sala) ou automaticamente (Automacao).
A mesma ferramenta funciona nos dois caminhos. Log unificado.

---

## 2. Arquitetura

```
gestao/
├── models.py           # 14 models
├── views.py            # ~45 views
├── urls.py             # ~50 rotas
├── ai_service.py       # Integracao OpenAI, contexto, moderador
├── agent_actions.py    # Processa blocos de acao na resposta do agente
├── faq_service.py      # Gera FAQ automatica via IA
├── health_service.py   # Health check de servicos
└── templates/gestao/dashboard/
    ├── ceo.html             # Dashboard executivo
    ├── projetos.html        # Lista de projetos
    ├── projeto_editar.html  # Editor de projeto
    ├── kanban.html          # Kanban board
    ├── tarefa_editar.html   # Editor de tarefa
    ├── documentos.html      # Gestor de documentos (filtro, busca)
    ├── documento.html       # Visualizar markdown
    ├── documento_editar.html # Editor markdown com preview
    ├── agentes.html         # Lista de agentes
    ├── agente_editar.html   # Editor de agente
    ├── tools.html           # Lista de ferramentas (filtro, busca)
    ├── tool_editar.html     # Editor de ferramenta
    ├── sala.html            # Lobby — escolher agente
    ├── sala_chat.html       # Chat 1:1 com agente
    ├── sala_reuniao.html    # Reuniao com moderador
    ├── automacoes.html      # Dashboard de automacoes
    ├── automacao_faq.html   # Ver/editar FAQs geradas
    ├── automacao_health.html # Health check em tempo real
    └── mapa.html            # Documentacao viva do sistema
```

---

## 3. Models

### 3.1 Gestao de Projetos

```python
class Projeto(models.Model):
    nome = CharField(200)
    descricao = TextField(blank=True)
    status = CharField(choices: planejamento/em_andamento/pausado/concluido/cancelado)
    prioridade = CharField(choices: critica/alta/media/baixa)
    objetivo = TextField(blank=True)
    publico_alvo = TextField(blank=True)
    criterios_sucesso = TextField(blank=True)
    riscos = TextField(blank=True)
    premissas = TextField(blank=True)
    responsavel = CharField(100)
    stakeholders = TextField(blank=True)
    contexto_agentes = TextField(blank=True)  # info extra para IA
    orcamento = TextField(blank=True)
    data_inicio = DateField(null=True)
    data_fim_prevista = DateField(null=True)
    ativo = BooleanField(default=True)
    # @property progresso -> % de tarefas concluidas

class Etapa(models.Model):
    projeto = FK(Projeto)
    nome = CharField(200)
    descricao = TextField(blank=True)
    ordem = IntegerField(default=0)
    data_inicio = DateField(null=True)
    data_fim = DateField(null=True)

class Tarefa(models.Model):
    projeto = FK(Projeto)
    etapa = FK(Etapa, null=True)
    titulo = CharField(300)
    descricao = TextField(blank=True)
    responsavel = CharField(100)
    status = CharField(choices: pendente/em_andamento/concluida/bloqueada)
    prioridade = CharField(choices: critica/alta/media/baixa)
    data_limite = DateField(null=True)
    data_conclusao = DateTimeField(null=True)
    ordem = IntegerField(default=0)

class Nota(models.Model):
    tarefa = FK(Tarefa)
    autor = CharField(100)
    texto = TextField()
```

### 3.2 Documentos

```python
class Documento(models.Model):
    titulo = CharField(300)
    slug = SlugField(100, unique=True)
    categoria = CharField(choices: estrategia/regras/roadmap/decisoes/entrega/sessao/contexto/outro)
    agente = FK(Agente, null=True)       # autor IA
    conteudo = TextField()                # markdown
    resumo = TextField(blank=True)
    descricao = CharField(300, blank=True)
    visivel_agentes = BooleanField(True)  # se agentes recebem como contexto
    ordem = IntegerField(default=0)
```

### 3.3 Agentes IA

```python
class Agente(models.Model):
    slug = SlugField(20, unique=True)     # ex: cto, cmo, operador
    nome = CharField(100)                 # ex: CTO, Operador
    descricao = CharField(200)            # ex: Tecnologia e Arquitetura
    icone = CharField(50)                 # classe FontAwesome
    cor = CharField(10)                   # hex
    time = CharField(choices: executivo/comercial/tools)
    prompt = TextField()                  # system prompt completo
    modelo = CharField(50, default='gpt-4o-mini')
    ativo = BooleanField(True)
    ordem = IntegerField(default=0)

class MensagemChat(models.Model):
    agente = FK(Agente)
    role = CharField(choices: user/assistant)
    conteudo = TextField()
```

### 3.4 Ferramentas (Tools)

```python
class ToolAgente(models.Model):
    slug = SlugField(50, unique=True)     # ex: criar_tarefa, gerar_faq
    nome = CharField(100)
    descricao = CharField(300)
    icone = CharField(50)
    tipo = CharField(choices: executavel/conhecimento)
    prompt = TextField()                  # instrucoes de uso
    exemplo = TextField(blank=True)
    ativo = BooleanField(True)

class LogTool(models.Model):
    tool = FK(ToolAgente, null=True)
    tool_slug = CharField(50)
    agente = FK(Agente, null=True)
    resultado = TextField()
    sucesso = BooleanField(True)
```

### 3.5 Reunioes

```python
class Reuniao(models.Model):
    nome = CharField(200)
    descricao = TextField(blank=True)
    agentes = CharField(200)              # slugs separados por virgula
    ativa = BooleanField(True)

class MensagemReuniao(models.Model):
    reuniao = FK(Reuniao)
    tipo = CharField(choices: ceo/agente/moderador)
    agente_id = CharField(20)
    agente_nome = CharField(100)
    conteudo = TextField()
```

### 3.6 Automacoes

```python
class Automacao(models.Model):
    agente = FK(Agente)                   # quem executa
    tool = FK(ToolAgente)                 # o que executa
    intervalo_horas = IntegerField(24)    # a cada X horas
    status = CharField(choices: ativo/pausado/erro)
    ultima_execucao = DateTimeField(null=True)
    ultimo_resultado = TextField(blank=True)
    total_execucoes = IntegerField(0)
    total_erros = IntegerField(0)
    ativo = BooleanField(True)
    # unique_together: (agente, tool)
```

### 3.7 FAQ Automatica

```python
class FAQCategoria(models.Model):
    nome = CharField(100)
    slug = SlugField(50, unique=True)
    icone = CharField(50)
    cor = CharField(10)
    ordem = IntegerField(0)
    ativo = BooleanField(True)

class FAQItem(models.Model):
    categoria = FK(FAQCategoria)
    pergunta = CharField(500)
    resposta = TextField()
    ordem = IntegerField(0)
    ativo = BooleanField(True)
    gerado_por_ia = BooleanField(False)
    hash_dados_fonte = CharField(64)      # detecta quando dados mudam
```

---

## 4. Agentes — Time Padrao

### Executivo

| Slug | Nome | Foco | Modelo |
|------|------|------|--------|
| `ceo` | CEO | Visao Estrategica | gpt-4o-mini |
| `cto` | CTO | Tecnologia e Arquitetura | gpt-4o-mini |
| `cpo` | CPO | Produto e Priorizacao | gpt-4o-mini |
| `cfo` | CFO | Financas e ROI | gpt-4o-mini |

### Comercial

| Slug | Nome | Foco | Modelo |
|------|------|------|--------|
| `cmo` | CMO | Marketing e Growth | gpt-4o-mini |
| `pmm` | PMM | Posicionamento e Messaging | gpt-4o-mini |
| `b2b` | Comercial B2B | Prospeccao de Parceiros | gpt-4o-mini |
| `cs` | Customer Success | Onboarding e Retencao | gpt-4o-mini |

### Operacoes

| Slug | Nome | Foco | Modelo |
|------|------|------|--------|
| `operador` | Operador | Automacoes do sistema | gpt-4o-mini |

Cada agente tem um **prompt** completo que define sua identidade, area de atuacao e regras de comunicacao. Os prompts sao editaveis pelo painel.

---

## 5. Ferramentas — Inventario Completo

### Executaveis (acoes no sistema)

| Slug | Nome | O que faz |
|------|------|-----------|
| `salvar_documento` | Salvar Documento | Cria documento no banco |
| `criar_tarefa` | Criar Tarefa | Cria tarefa no Kanban |
| `atualizar_tarefa` | Atualizar Tarefa | Muda status de tarefa |
| `consultar_agente` | Consultar Agente | Chama outro agente com contexto |
| `criar_projeto` | Criar Projeto | Cria projeto completo |
| `atualizar_projeto` | Atualizar Projeto | Muda status/dados de projeto |
| `criar_etapa` | Criar Etapa | Cria fase/sprint no projeto |
| `resumo_projeto` | Resumo de Projeto | Gera resumo com progresso e riscos |
| `gerar_faq` | Gerar FAQ | Gera FAQs via IA com dados reais |
| `health_check` | Monitor de Saude | Verifica 6 servicos |
| `expirar_cupons` | Expirador de Cupons | Desativa cupons vencidos |
| `alerta_churn` | Alerta de Churn | Membros inativos ha 30+ dias |
| `relatorio_diario` | Relatorio Diario | Resumo executivo do dia |
| `sincronizar_hubsoft` | Sincronizar Hubsoft | Sync pontos extras |
| `ranking_engajamento` | Ranking de Engajamento | Top membros por cidade |
| `notificar_estoque` | Alerta de Estoque | Premios acabando |

### Conhecimento (prompts especializados)

| Slug | Nome | O que faz |
|------|------|-----------|
| `analise_dados` | Analise de Dados | Insights sobre metricas |
| `gerador_copy` | Gerador de Copy | Textos WhatsApp/Instagram |
| `calculadora_roi` | Calculadora ROI | ROI de acoes e features |
| `auditor_codigo` | Auditor de Codigo | Review de codigo |
| `gerador_spec` | Gerador de Spec | Spec completa de feature |
| `prospector_parceiro` | Prospector de Parceiro | Abordagem B2B |
| `planejador_campanha` | Planejador de Campanha | Plano de campanha completo |
| `analista_retencao` | Analista de Retencao | Analise de churn + acoes |
| `gerador_relatorio` | Gerador de Relatorio | Relatorios executivos |
| `consultor_onboarding` | Consultor de Onboarding | Fluxos de onboarding |
| `criador_missao` | Criador de Missao | Missoes de gamificacao |
| `escritor_proposta_b2b` | Escritor de Proposta B2B | Propostas comerciais |
| `planejar_projeto` | Planejar Projeto | Plano completo de projeto |
| `retrospectiva` | Retrospectiva | Licoes aprendidas |

---

## 6. Fluxo: Como Tudo se Conecta

### Caminho 1 — Sala (manual)

```
CEO abre a Sala
    |
    v
Escolhe agente (ex: PMM)
    |
    v
Digita: "Crie um plano de lancamento para Timon"
    |
    v
Sistema monta contexto automatico:
  - Prompt do PMM (identidade + regras)
  - Documentos visiveis (estrategia, regras, contexto)
  - Projetos ativos com tarefas
  - Metricas do sistema em tempo real
  - Ferramentas disponiveis (formato de uso)
  - Agentes disponiveis para consulta
    |
    v
OpenAI (gpt-4o-mini) gera resposta com blocos de acao:
  ---CRIAR_PROJETO---
  nome: Lancamento Timon
  objetivo: 300 membros + 8 parceiros em 4 semanas
  ---FIM_PROJETO---

  ---CRIAR_ETAPA---
  projeto: Lancamento Timon
  nome: Semana 1 — Prospeccao
  ---FIM_ETAPA---

  ---CRIAR_TAREFA---
  projeto: Lancamento Timon
  titulo: Listar 20 comercios-alvo
  responsavel: Comercial B2B
  ---FIM_TAREFA---
    |
    v
agent_actions.py processa cada bloco:
  - Detecta pattern via regex
  - Executa handler correspondente
  - Registra no LogTool
  - Substitui bloco por confirmacao no chat
    |
    v
CEO ve: resposta limpa + "Projeto criado" + "Etapa criada" + "Tarefa criada"
Tudo visivel no Kanban, Documentos e Dashboard
```

### Caminho 2 — Automacao (cron)

```
Trigger dispara (ex: a cada 24h)
    |
    v
Busca Automacao no banco:
  agente = Operador
  tool = gerar_faq
    |
    v
Executa handler da tool via TOOL_EXECUTORS registry
    |
    v
faq_service.py:
  1. Coleta dados reais (premios, cupons, niveis, regras)
  2. Gera hash SHA256 dos dados
  3. Se hash mudou → chama OpenAI → gera 5 FAQs por categoria
  4. Se hash igual → pula (economia de tokens)
    |
    v
Resultado salvo no LogTool + Automacao.ultimo_resultado atualizado
Mesma tool pode ser chamada na Sala: "Operador, roda o FAQ"
```

---

## 7. Blocos de Acao (agent_actions.py)

Os agentes executam acoes incluindo blocos especiais na resposta:

| Bloco | Ferramenta | Acao |
|-------|------------|------|
| `---SALVAR_DOCUMENTO---...---FIM_DOCUMENTO---` | salvar_documento | Cria Documento no banco |
| `---CRIAR_PROJETO---...---FIM_PROJETO---` | criar_projeto | Cria Projeto |
| `---ATUALIZAR_PROJETO---...---FIM_PROJETO---` | atualizar_projeto | Atualiza Projeto |
| `---CRIAR_ETAPA---...---FIM_ETAPA---` | criar_etapa | Cria Etapa |
| `---CRIAR_TAREFA---...---FIM_TAREFA---` | criar_tarefa | Cria Tarefa |
| `---ATUALIZAR_TAREFA---...---FIM_TAREFA---` | atualizar_tarefa | Atualiza Tarefa |
| `---RESUMO_PROJETO---...---FIM_RESUMO---` | resumo_projeto | Gera resumo |
| `---CONSULTAR_AGENTE---...---FIM_CONSULTA---` | consultar_agente | Consulta outro agente |

### Formato dos blocos

```
---CRIAR_TAREFA---
titulo: Abordar 10 restaurantes em Timon
projeto: Lancamento Timon
responsavel: Comercial B2B
prioridade: alta
---FIM_TAREFA---
```

O parser `_parse_bloco()` extrai campos `chave: valor`. Campo `conteudo:` captura tudo ate o fim do bloco (para documentos com markdown).

### Retrocompatibilidade

`SALVAR_ENTREGA` e `SALVAR_SESSAO` mapeiam para `salvar_documento` automaticamente.

---

## 8. Contexto Carregado para Agentes

Cada agente recebe como system message:

1. **Prompt do agente** (do banco, campo `Agente.prompt`)
2. **Documentos visiveis** (onde `visivel_agentes=True`) — truncados a 2000 chars, limite 20 docs
3. **Projetos ativos** com tarefas — limite 20 projetos, 30 tarefas/projeto
4. **Metricas do sistema** — contadores em tempo real
5. **Entregas dos agentes** (docs categoria `entrega`)
6. **Ferramentas ativas** — executaveis (formato de bloco) + conhecimento (prompts)
7. **Instrucoes de comunicacao** — modo conversa, identidade, assertividade
8. **Agentes disponiveis** para consulta (`---CONSULTAR_AGENTE---`)

---

## 9. Reunioes com Moderador

O moderador e **deterministico** (sem IA, sem custo de tokens):

1. CEO envia mensagem na reuniao
2. Moderador analisa por regras:
   - **Regra 1**: CEO mencionou nome/slug de agente? → direciona para ele
   - **Regra 2**: Palavras-chave (marketing→cmo, tecnologia→cto, parceiro→b2b)
   - **Regra 3**: "todos" → 3 primeiros agentes
   - **Fallback**: CPO
3. Agente(s) respondem sequencialmente
4. Cada agente recebe: msgs do CEO + suas proprias respostas (nao ve outros)
5. Botoes "Ouvir tambem" para pedir opiniao extra

---

## 10. Slash Commands

Comandos rapidos digitados no chat com `/`:

| Comando | O que faz | Autocomplete |
|---------|-----------|-------------|
| `/help` | Lista comandos | - |
| `/tools` | Ferramentas dos agentes | Busca por nome |
| `/tarefas` | Tarefas ativas | Busca por titulo |
| `/docs` | Documentos recentes | Busca por titulo |
| `/projetos` | Projetos com progresso | Busca por nome |
| `/agentes` | Agentes (invoca no chat) | Busca por nome |
| `/automacoes` | Status das automacoes | - |
| `/faq` | FAQs por categoria | Busca por categoria |
| `/health` | Health check em tempo real | - |
| `/limpar` | Limpa historico | - |

### Autocomplete interativo

1. Digitar `/` abre popup com todos os comandos
2. Filtrar enquanto digita (ex: `/pro` → projetos)
3. Selecionar com setas + Tab/Enter
4. Comandos com argumentos mostram sugestoes do banco

---

## 11. Automacoes — Modelo

Uma automacao e um **trigger**: agente + ferramenta + intervalo.

```
Automacao = Agente (Operador) + Tool (gerar_faq) + 24h
```

### Executores

Os executores sao registrados via decorator:

```python
TOOL_EXECUTORS = {}

def _registrar_executor(slug):
    def decorator(fn):
        TOOL_EXECUTORS[slug] = fn
        return fn
    return decorator

@_registrar_executor('gerar_faq')
def _exec_gerar_faq():
    from gestao.faq_service import FAQService
    FAQService.garantir_categorias()
    resultado = FAQService.atualizar_faqs(force=True)
    return '\n'.join(f'{k}: {v}' for k, v in resultado.items())
```

Para adicionar nova automacao:
1. Criar a tool no banco (tipo `executavel`)
2. Implementar o executor com `@_registrar_executor('slug')`
3. Criar a Automacao no painel (agente + tool + intervalo)

### Logs unificados

Automacoes logam no `LogTool` (mesmo modelo que acoes dos agentes no chat). Sem tabela separada.

---

## 12. FAQ Automatica

### Como funciona

1. `faq_service.coletar_dados_sistema()` busca dados reais (premios, cupons, niveis, regras, parceiros)
2. Gera hash SHA256 dos dados de cada categoria
3. Se hash mudou → chama OpenAI com prompt contextualizado → gera 5 FAQs
4. Se hash igual → pula (sem custo)
5. FAQs editadas manualmente (`gerado_por_ia=False`) nunca sao sobrescritas

### Categorias padrao

| Slug | Nome | Dados fonte |
|------|------|-------------|
| `roleta` | Roleta | Config, premios |
| `pontos-niveis` | Pontos e Niveis | Niveis, regras |
| `cupons` | Cupons | Parceiros, cupons ativos |
| `indicacoes` | Indicacoes | Config, regra de indicacao |
| `carteirinha` | Carteirinha | Descricao estatica |
| `conta` | Minha Conta | Fluxo OTP/cadastro |

### Custo

~$0.01 por ciclo completo com gpt-4o-mini (6 categorias x ~500 tokens).

---

## 13. Health Check

6 verificacoes:

| Check | O que verifica | Aviso se |
|-------|---------------|----------|
| Banco Principal | Conexao PostgreSQL + count membros | Falha |
| Hubsoft | Conexao read-only + latencia | > 3000ms |
| API OpenAI | Ping com gpt-4o-mini | > 5000ms |
| Membros | Total + validados | 0 membros |
| Estoque Premios | Com/sem estoque + acabando | < 5 unidades |
| Cupons | Ativos + pendentes + vencidos | Vencidos ainda ativos |

---

## 14. Sidebar — Organizacao

```
GESTAO
├── Dashboard         → KPIs executivos
├── Documentos        → Base de conhecimento
├── Projetos          → Kanban + tarefas

INTELIGENCIA
├── Sala              → Chat 1:1 e reunioes com agentes
├── Mapa              → Documentacao viva do sistema

SISTEMA
├── Agentes           → Configurar agentes IA
├── Ferramentas       → Tools executaveis + conhecimento
├── Automacoes        → Triggers periodicos (agente + tool)
```

---

## 15. Stack Tecnica

| Componente | Tecnologia |
|------------|-----------|
| Backend | Django 4.2+ / Python 3.10+ |
| IA | OpenAI API (gpt-4o-mini, configuravel por agente) |
| Frontend | HTML5, JavaScript Vanilla, CSS3 |
| Markdown render | `markdown` (backend, sanitizado com `bleach`) + `marked.js` (frontend, sanitizado com `DOMPurify`) |
| Banco | PostgreSQL |
| Cache | Django cache framework |
| Logging | `logging` module (sem `print()`) |
| Seguranca | `select_for_update` + `F()`, `@transaction.atomic`, CSRF em tudo, credenciais via `.env` |

---

## 16. Para Replicar em Outro Projeto

### Passo a passo

1. **Criar app `gestao`** no projeto Django
2. **Copiar models.py** com os 14 models acima
3. **Criar `ai_service.py`** com:
   - `get_client()` → cliente OpenAI
   - `carregar_contexto_leve()` → docs + projetos + metricas
   - `chat_agente()` → envia mensagem com contexto completo
   - `moderador_decidir()` → deterministico por palavras-chave
4. **Criar `agent_actions.py`** com:
   - `processar_acoes()` → detecta blocos na resposta
   - Handlers para cada bloco (criar tarefa, salvar doc, etc.)
   - `TOOL_EXECUTORS` registry para automacoes
5. **Criar views** seguindo o padrao CRUD + APIs AJAX para chat
6. **Criar templates** (base estende o template do projeto)
7. **Popular banco** com agentes, tools e categorias FAQ
8. **Configurar `.env`** com `OPENAI_API_KEY`

### Adaptacoes necessarias

- **Metricas**: mudar `coletar_dados_sistema()` para buscar dados do seu dominio
- **Agentes**: ajustar prompts para o contexto do seu negocio
- **Tools**: criar ferramentas especificas (ex: se for e-commerce, tool de estoque)
- **FAQ**: ajustar categorias e dados coletados
- **Health check**: ajustar servicos verificados

### O que NAO precisa mudar

- Estrutura de models (projetos, tarefas, documentos, agentes, tools, automacoes)
- Logica de chat (contexto + OpenAI + processar acoes)
- Moderador deterministico
- Sistema de slash commands
- Automacao (agente + tool + trigger)
- FAQ com hash de mudanca
- Mapa do sistema (documentacao viva)
