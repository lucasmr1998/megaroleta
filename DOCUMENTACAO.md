# Documentacao — Sistema MegaRoleta (Megalink Clube)

> Documentacao tecnica e funcional da plataforma de gamificacao, cupons de parceiros e indicacoes para o Clube Megalink.

---

## Sumario

1. [Visao Geral](#1-visao-geral)
2. [Arquitetura de Apps Django](#2-arquitetura-de-apps-django)
3. [Fluxo Principal do Usuario](#3-fluxo-principal-do-usuario)
4. [Area do Membro (Hub)](#4-area-do-membro-hub)
5. [Regras de Pontuacao e Gamificacao](#5-regras-de-pontuacao-e-gamificacao)
6. [Integracao com o Hubsoft](#6-integracao-com-o-hubsoft)
7. [Premios e Sorteio](#7-premios-e-sorteio)
8. [Verificacao de Identidade (OTP)](#8-verificacao-de-identidade-otp)
9. [Modulo de Parceiros e Cupons](#9-modulo-de-parceiros-e-cupons)
10. [Modulo de Indicacoes](#10-modulo-de-indicacoes)
11. [Painel do Parceiro](#11-painel-do-parceiro)
12. [Painel Administrativo (Dashboard)](#12-painel-administrativo-dashboard)
13. [Endpoints da API](#13-endpoints-da-api)
14. [Entidades do Sistema](#14-entidades-do-sistema)
15. [Configuracoes Gerais](#15-configuracoes-gerais)
16. [Integracoes Externas](#16-integracoes-externas)
17. [Deploy e Infraestrutura](#17-deploy-e-infraestrutura)

---

## 1. Visao Geral

O sistema e uma plataforma de fidelidade gamificada. Clientes da Megalink acumulam pontos (chamados de **Giros**) ao completar missoes, e gastam esses pontos para **girar a roleta** e conquistar premios fisicos ou digitais. Alem da roleta, o sistema oferece **cupons de desconto de parceiros** e um **programa de indicacoes**.

**Tecnologias:**
- Backend: Django 4.2+ / Python 3.10+
- Frontend: HTML5, CSS3, JavaScript Vanilla (jQuery)
- Banco principal: PostgreSQL (producao) / SQLite3 (dev)
- Banco externo: PostgreSQL do Hubsoft (somente leitura)
- Integracao: Webhook n8n + consulta direta ao banco Hubsoft
- Envio de OTP: WhatsApp via webhook n8n
- Deploy: Gunicorn + Nginx
- Graficos: Chart.js

---

## 2. Arquitetura de Apps Django

O projeto esta separado em **3 apps Django** independentes:

```
megaroleta/
├── roleta/           # App principal: roleta, membros, premios, gamificacao
├── parceiros/        # Gestao de parceiros, cupons e resgates
├── indicacoes/       # Sistema de indicacoes e embaixadores
└── sorteio/          # Projeto Django (settings, urls raiz)
```

### App `roleta`
- Models: MembroClube, PremioRoleta, ParticipanteRoleta, RegraPontuacao, ExtratoPontuacao, NivelClube, RoletaConfig, RouletteAsset, Cidade
- Views: core (index, logout), api (init-dados, cadastrar, OTP), dashboard, membro (hub, jogar, cupons, indicar, perfil, missoes), docs
- Services: SorteioService, HubsoftService, OTPService, GamificationService

### App `parceiros`
- Models: Parceiro (com FK User), CupomDesconto (3 modalidades + status de aprovacao), ResgateCupom
- Views: dashboard admin (home, parceiros, cupons, resgates, detalhe, validar) + painel do parceiro (home, cupons, resgates, validar)
- Services: CupomService

### App `indicacoes`
- Models: Indicacao, IndicacaoConfig (visual da pagina publica)
- Views: dashboard admin (home, indicacoes, membros/embaixadores, visual) + pagina publica de indicacao
- Services: IndicacaoService

---

## 3. Fluxo Principal do Usuario

```
1. Usuario acessa /roleta/
2. Digita o CPF -> Sistema consulta Hubsoft (via webhook n8n)
   - Se cliente Hubsoft: dados preenchidos automaticamente
   - Se nao cliente: formulario manual de cadastro
3. Envio do OTP via WhatsApp (codigo de 6 digitos, expira em 10 min)
4. Validacao do OTP -> Sessao autenticada + pontos Hubsoft sincronizados
5. Redirecionado para /roleta/membro/ (Hub)
6. Membro escolhe: Roleta, Cupons, Indicar, Perfil ou Missoes
```

---

## 4. Area do Membro (Hub)

Apos login, o membro acessa `/roleta/membro/` — um hub com cards:

| Card | Rota | Descricao |
|------|------|-----------|
| Roleta | `/membro/jogar/` | Girar a roleta (fundo branco, animacao) |
| Cupons | `/membro/cupons/` | Ver e resgatar cupons de parceiros |
| Indicar | `/membro/indicar/` | Link de indicacao, compartilhar WhatsApp, historico |
| Perfil | `/membro/perfil/` | Saldo, XP, nivel, barra de progresso, extrato |
| Missoes | `/membro/missoes/` | Lista de missoes com progresso geral |

### Design
- Fundo `#000b4a` (azul marinho da identidade visual)
- Cards brancos com icones coloridos
- Header compacto: nome + saldo + botao sair
- Responsivo: 2 colunas mobile, 4 colunas desktop

---

## 5. Regras de Pontuacao e Gamificacao

### Sistema de Pontos

| Tipo | Nome | Uso |
|------|------|-----|
| **Saldo** | Giros | Custo para girar a roleta |
| **XP** | Experiencia | Sobe o nivel do membro no clube |

### Missoes (RegraPontuacao)

| Gatilho | Descricao | Quando e acionado |
|---|---|---|
| `cadastro_inicial` | Bonus de boas-vindas | No primeiro cadastro |
| `telefone_verificado` | Validou o WhatsApp | Na primeira validacao de OTP |
| `hubsoft_recorrencia` | Ativou pagamento recorrente | Sincronizacao com Hubsoft |
| `hubsoft_adiantado` | Pagou fatura adiantada | Sincronizacao mensal com Hubsoft |
| `hubsoft_app` | Usa o App do Cliente | Sincronizacao com Hubsoft |
| `indicacao_convertida` | Indicacao convertida | Quando indicado vira cliente |
| `resgate_cupom` | Resgatou cupom | Ao resgatar um cupom |
| `ajuste_manual_admin` | Ajuste pelo Admin | Quando admin altera saldo |

### XP e Niveis
- XP acumulado com missoes e giros (`xp_por_giro` configuravel)
- Nivel calculado dinamicamente vs. tabela `NivelClube`
- Exemplos: Bronze, Prata, Ouro

---

## 6. Integracao com o Hubsoft

### Webhook n8n — Dados cadastrais
- **Endpoint:** `automation-n8n.v4riem.easypanel.host/webhook/roletaconsultarcliente`
- **Retorna:** Nome, e-mail, telefone (mascarado), endereco, ID cliente

### PostgreSQL Hubsoft (somente leitura)
- **Host:** `177.10.118.77:9432` | Banco: `hubsoft` | Usuario: `mega_leitura`
- Consulta cidade de instalacao
- Verifica recorrencia, pagamento adiantado e uso do app
- Consulta quantidade de clientes por cidade (para relatorios)

---

## 7. Premios e Sorteio

### Logica do Sorteio (`SorteioService`)
1. Filtra premios com estoque > 0 e cidade elegivel
2. Sorteio ponderado via `random.choices()` com pesos de probabilidade
3. Posicao aleatoria sorteada para animacao
4. Estoque decrementado atomicamente via `F()` + `@transaction.atomic`
5. Race condition protegida com guarda dupla no UPDATE

---

## 8. Verificacao de Identidade (OTP)

- Codigo de 6 digitos, expira em 10 minutos
- Rate limiting: 1 codigo por minuto por sessao
- Enviado via webhook n8n -> WhatsApp
- Pos-validacao: sessao autenticada + sincronizacao Hubsoft

---

## 9. Modulo de Parceiros e Cupons

### Parceiros
Empresas parceiras da Megalink que oferecem cupons aos membros do clube.

| Campo | Descricao |
|---|---|
| `nome`, `logo`, `descricao` | Dados do parceiro |
| `contato_nome`, `contato_telefone`, `contato_email` | Contato |
| `usuario` | FK User Django (para acesso ao painel do parceiro) |
| `cidades` | M2M com Cidade |

### Cupons de Desconto
3 modalidades:
- **Gratuito** — qualquer membro pode resgatar
- **Pontos** — gasta saldo de pontos para resgatar
- **Nivel** — disponivel a partir de certo nivel (NivelClube)

### Fluxo de Aprovacao
1. Parceiro solicita novo cupom via painel (`status_aprovacao='pendente'`)
2. Admin ve cupom pendente no dashboard de Cupons (aparecem no topo)
3. Admin aprova (ativa o cupom) ou rejeita (com motivo)
4. Parceiro ve o status no seu painel

### Validacao de Cupom
1. Membro resgata cupom -> recebe codigo unico (ex: `A3F8B2C1D4E5`)
2. Membro apresenta codigo no estabelecimento
3. Parceiro acessa pagina de validacao -> digita codigo -> ve detalhes
4. Parceiro informa valor da compra e confirma utilizacao
5. Status muda de "resgatado" para "utilizado"

### Paginas publicas
- `/roleta/cupom/validar/` — Validacao publica (sem login)
- `/roleta/parceiro/validar/` — Validacao no painel do parceiro (com login)

---

## 10. Modulo de Indicacoes

### Fluxo
1. Membro recebe link unico: `/roleta/indicar/<codigo>/`
2. Membro compartilha link (botao WhatsApp disponivel)
3. Indicado acessa link -> preenche formulario (nome, telefone, CPF opcional, cidade)
4. Indicacao registrada com status "pendente"
5. Equipe Megalink gerencia no admin: contato feito -> convertido -> pontos creditados

### Codigo de Indicacao
- Campo `codigo_indicacao` no MembroClube (CharField, unique)
- Auto-gerado via `uuid4().hex[:8].upper()` no primeiro save

### Configuracao Visual
- Pagina publica personalizavel: titulo, subtitulo, cores, logo, imagem de fundo
- Campos do formulario configuraveis (mostrar/ocultar CPF e Cidade)
- Configuracao via admin: Indicacoes > Configuracoes

---

## 11. Painel do Parceiro

Acesso via `/roleta/parceiro/login/` — requer User Django vinculado ao Parceiro.

### Paginas

| Pagina | Descricao |
|---|---|
| Dashboard | KPIs (cupons ativos, resgates, utilizados, valor compras), grafico 7 dias, acoes rapidas |
| Cupons | Lista dos cupons do parceiro com status de aprovacao. Botao "Solicitar Cupom" (modal 2 etapas) |
| Resgates | Historico completo de resgates com filtros e paginacao |
| Validar | Digitar codigo, ver detalhes, informar valor da compra, confirmar utilizacao |

### Seguranca
- Parceiro so ve dados dos seus proprios cupons (filtro `cupom__parceiro=parceiro`)
- Nao impacta o admin — sistemas completamente separados
- `@login_required` + verificacao de `User.parceiro` (OneToOne)

---

## 12. Painel Administrativo (Dashboard)

Acessivel via `/roleta/dashboard/` — requer login de staff Django.

### Navegacao
- **Topbar:** Modulos (Roleta, Parceiros, Indicacoes, Operacao, Relatorios) + icones (Suporte, Configuracoes, Ver Roleta)
- **Sidebar:** Paginas do modulo ativo (muda conforme o modulo selecionado)

### Modulo Roleta
| Pagina | Rota |
|---|---|
| Dashboard | `/dashboard/` — KPIs com variacao %, grafico evolucao, ultimos ganhadores |
| Premios | `/dashboard/premios/` — CRUD via modais, peso/chance, cidades |
| Membros | `/dashboard/participantes/` — Paginado, busca, ajuste de saldo |
| Cidades | `/dashboard/cidades/` — CRUD de cidades habilitadas |

### Modulo Parceiros
| Pagina | Rota |
|---|---|
| Dashboard | `/dashboard/parceiros/` — KPIs, grafico resgates, top cupons |
| Parceiros | `/dashboard/parceiros/lista/` — CRUD parceiros |
| Cupons | `/dashboard/cupons/` — CRUD cupons, aprovar/rejeitar solicitacoes |
| Resgates | `/dashboard/cupons/resgates/` — Historico global |
| Detalhe Cupom | `/dashboard/cupons/<id>/` — Resumo + historico do cupom |

### Modulo Indicacoes
| Pagina | Rota |
|---|---|
| Dashboard | `/dashboard/indicacoes/` — KPIs, grafico, top embaixadores |
| Indicacoes | `/dashboard/indicacoes/lista/` — Listagem, alterar status |
| Embaixadores | `/dashboard/indicacoes/membros/` — Membros com links de indicacao |
| Configuracoes | `/dashboard/indicacoes/visual/` — Visual da pagina publica |

### Modulo Operacao
| Pagina | Rota |
|---|---|
| Historico | `/dashboard/giros/` — Log de todos os giros |
| Visual | `/dashboard/assets/` — Upload imagens da roleta |
| Gamificacao | `/dashboard/gamificacao/` — Niveis e regras de pontuacao |

### Modulo Relatorios
| Pagina | Rota |
|---|---|
| Roleta | `/dashboard/relatorios/` — Funil, evolucao, cidades, premios, horarios, top jogadores |
| Indicacoes | `/dashboard/relatorios/indicacoes/` — KPIs, evolucao, embaixadores, por cidade |
| Parceiros | `/dashboard/relatorios/parceiros/` — KPIs, cupons top, resgates por parceiro |

---

## 13. Endpoints da API

| Metodo | Endpoint | Descricao |
|---|---|---|
| `GET` | `/roleta/api/init-dados/` | Dados iniciais (config, assets, saldo, missoes, cupons, indicacoes) |
| `POST` | `/roleta/verificar-cliente/` | Consulta CPF no Hubsoft |
| `POST` | `/roleta/solicitar-otp/` | Gera e envia OTP via WhatsApp |
| `POST` | `/roleta/validar-otp/` | Valida codigo OTP |
| `POST` | `/roleta/pre-cadastrar/` | Cria/atualiza membro antes do OTP |
| `POST` | `/roleta/cadastrar/` | Executa giro da roleta |
| `POST` | `/roleta/api/cupons/resgatar/` | Resgata cupom pelo membro |
| `POST` | `/roleta/api/indicacao/criar/` | Cria indicacao pelo membro |
| `GET` | `/roleta/logout/` | Encerra sessao |

---

## 14. Entidades do Sistema

### App `roleta`
- **MembroClube** — CPF (unico), nome, saldo, xp_total, nivel_atual, codigo_indicacao, validado
- **ParticipanteRoleta** — Registro de cada giro (membro FK, premio, status, saldo, data)
- **PremioRoleta** — nome, quantidade, posicoes, probabilidade, mensagem_vitoria, cidades_permitidas M2M
- **RegraPontuacao** — gatilho (unico), nome_exibicao, pontos_saldo, pontos_xp, limite_por_membro
- **ExtratoPontuacao** — membro FK, regra FK, pontos ganhos, descricao_extra, data
- **NivelClube** — nome, xp_necessario, ordem
- **RoletaConfig** — custo_giro, xp_por_giro, nome_clube, limite_giros, periodo_limite
- **RouletteAsset** — tipo (frame/background/logo/pointer), ordem, imagem, ativo
- **Cidade** — nome (unico), ativo

### App `parceiros`
- **Parceiro** — nome, logo, descricao, contato, usuario FK User, cidades M2M, ativo
- **CupomDesconto** — parceiro FK, titulo, codigo, tipo_desconto, valor, modalidade, custo_pontos, nivel_minimo FK, imagem, quantidade, limite, validade, status_aprovacao, motivo_rejeicao
- **ResgateCupom** — membro FK, cupom FK, codigo_unico, pontos_gastos, valor_compra, status, datas

### App `indicacoes`
- **Indicacao** — membro_indicador FK, nome/telefone/cpf/cidade indicado, status, pontos_creditados, datas, observacoes. unique_together: [indicador, telefone]
- **IndicacaoConfig** — titulo, subtitulo, textos, cores, logo, imagem_fundo, campos visiveis (singleton)

### App `carteirinha`
- **ModeloCarteirinha** — nome, tipo_fundo (cor/imagem), cores (fundo, texto, destaque), logo, campos visiveis (9 toggles), texto_marca, texto_rodape
- **RegraAtribuicao** — modelo FK, tipo (nivel/pontuacao_minima/cidade/todos/manual), prioridade
- **CarteirinhaMembro** — membro FK, modelo FK, foto, data_emissao, data_validade

### App `gestao`
- **Projeto** — nome, descricao, responsavel, datas, progresso calculado
- **Etapa** — projeto FK, nome, ordem, datas
- **Tarefa** — projeto FK, etapa FK, titulo, responsavel, status (pendente/em_andamento/concluida/bloqueada), prioridade (critica/alta/media/baixa), data_limite
- **Nota** — tarefa FK, autor, texto
- **Reuniao** — nome, descricao, agentes (comma-separated IDs), ativa
- **MensagemReuniao** — reuniao FK, tipo (ceo/agente/moderador), agente_id, agente_nome, conteudo

---

## 15. Configuracoes Gerais

| Campo | Padrao | Descricao |
|---|---|---|
| `nome_clube` | "Clube Megalink" | Nome exibido na interface |
| `custo_giro` | 10 | Pontos para girar |
| `xp_por_giro` | 5 | XP ganho por giro |
| `limite_giros_por_membro` | 0 (sem limite) | Maximo de giros por periodo |
| `periodo_limite` | `total` | Janela: total, diario, semanal, mensal |

---

## 16. Integracoes Externas

| Integracao | Tipo | Finalidade |
|---|---|---|
| n8n – consulta cliente | Webhook POST | Dados do cliente Hubsoft |
| n8n – envio OTP | Webhook POST | Codigo OTP via WhatsApp |
| Hubsoft PostgreSQL | Leitura direta | Cidade, recorrencia, adiantado, app, clientes por cidade |
| OpenAI API | REST API | Sala de agentes IA (gpt-4o-mini) |

---

## 17. Deploy e Infraestrutura

### Producao
- **Servidor:** Gunicorn + Nginx
- **Dominio:** `roleta.megalinkpiaui.com.br`
- **Banco:** PostgreSQL (`187.62.153.52:5432`, banco `megasorteio`)
- **Timezone:** America/Fortaleza

### Comandos uteis
```bash
source .venv/bin/activate
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart megaroleta
sudo journalctl -u megaroleta -n 50 -f
sudo nginx -t && sudo systemctl reload nginx
```

### Estrutura de Arquivos
```
megaroleta/
├── roleta/
│   ├── models.py                  # 9 modelos
│   ├── urls.py                    # Rotas da roleta + membro + API
│   ├── views/
│   │   ├── core_views.py          # index, logout
│   │   ├── api_views.py           # init-dados, cadastrar, OTP, cupons, indicacoes
│   │   ├── dashboard_views.py     # Painel admin + relatorios
│   │   ├── membro_views.py        # Hub, jogar, cupons, indicar, perfil, missoes
│   │   └── docs_views.py          # Documentacao renderizada
│   ├── services/
│   │   ├── sorteio_service.py     # Sorteio ponderado
│   │   ├── hubsoft_service.py     # Integracao Hubsoft
│   │   ├── otp_service.py         # OTP via WhatsApp
│   │   └── gamification_service.py # Pontos/XP
│   └── templates/roleta/
│       ├── index_frontend.html    # Tela de login/cadastro
│       ├── membro/                # Hub, jogar, cupons, indicar, perfil, missoes
│       └── dashboard/             # Templates do admin
├── parceiros/
│   ├── models.py                  # Parceiro, CupomDesconto, ResgateCupom
│   ├── views.py                   # Dashboard admin parceiros
│   ├── views_painel.py            # Painel do parceiro
│   ├── services.py                # CupomService
│   └── templates/parceiros/
│       ├── dashboard/             # Admin: home, parceiros, cupons, resgates, detalhe
│       └── painel/                # Parceiro: home, cupons, resgates, validar, login
├── indicacoes/
│   ├── models.py                  # Indicacao, IndicacaoConfig
│   ├── views.py                   # Dashboard admin + pagina publica
│   ├── services.py                # IndicacaoService
│   └── templates/indicacoes/
│       ├── dashboard/             # Admin: home, indicacoes, membros, visual
│       └── indicar.html           # Pagina publica de indicacao
├── carteirinha/
│   ├── models.py                  # ModeloCarteirinha, RegraAtribuicao, CarteirinhaMembro
│   ├── views.py                   # Admin: modelos, regras, preview + membro
│   ├── services.py                # CarteirinhaService
│   └── templates/carteirinha/
│       ├── dashboard/             # Admin: home, modelos, criar, editar, regras, preview
│       └── partials/cartao.html   # Template reutilizavel do cartao
├── gestao/
│   ├── models.py                  # Projeto, Etapa, Tarefa, Nota, Reuniao, MensagemReuniao
│   ├── views.py                   # Dashboard CEO, kanban, sala agentes, entregas, sessoes
│   ├── ai_service.py              # Integracao OpenAI, prompts, moderador
│   ├── agent_actions.py           # Acoes: salvar entrega/sessao, criar/atualizar tarefa, consultar agente
│   └── templates/gestao/dashboard/
│       ├── ceo.html               # Dashboard CEO com KPIs
│       ├── kanban.html            # Kanban board
│       ├── sala.html              # Lobby da sala de agentes
│       ├── sala_chat.html         # Chat individual com agente
│       ├── sala_reuniao.html      # Reuniao com moderador
│       ├── sala_reuniao_criar.html # Criar reuniao
│       ├── entregas.html          # Lista de entregas
│       ├── sessoes.html           # Lista de sessoes
│       ├── documento.html         # Visualizar markdown renderizado
│       └── entrega_editar.html    # Editor markdown com preview
├── docs/
│   ├── ESTRATEGIA.md              # Visao, triangulo de valor, diferenciais
│   ├── ROADMAP.md                 # Entregas + plano lancamento + backlog
│   ├── DECISOES.md                # Registro de decisoes
│   ├── REGRAS_NEGOCIO.md          # Regras inviolaveis
│   ├── agentes/                   # Prompts dos agentes IA (executivo/, comercial/, tools/)
│   ├── entregas/                  # Documentos produzidos pelos agentes
│   └── contexto/                  # Brandbook, metas, financeiro, sessoes
└── sorteio/
    ├── settings.py                # Configuracoes Django (dotenv)
    └── urls.py                    # URLs raiz
```
