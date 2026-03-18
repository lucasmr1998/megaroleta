# Documentacao — Sistema de Roleta (Megalink Clube)

> Documentacao tecnica e funcional do sistema de gamificacao com roleta para o Clube Megalink.

---

## Sumario

1. [Visao Geral](#1-visao-geral)
2. [Fluxo Principal do Usuario](#2-fluxo-principal-do-usuario)
3. [Regras de Pontuacao e Gamificacao](#3-regras-de-pontuacao-e-gamificacao)
4. [Integracao com o Hubsoft](#4-integracao-com-o-hubsoft)
5. [Premios e Sorteio](#5-premios-e-sorteio)
6. [Verificacao de Identidade (OTP)](#6-verificacao-de-identidade-otp)
7. [Entidades do Sistema](#7-entidades-do-sistema)
8. [Painel Administrativo (Dashboard)](#8-painel-administrativo-dashboard)
9. [Endpoints da API Interna](#9-endpoints-da-api-interna)
10. [Configuracoes Gerais](#10-configuracoes-gerais)
11. [Integracoes Externas](#11-integracoes-externas)
12. [Assets Visuais](#12-assets-visuais)
13. [Deploy e Infraestrutura](#13-deploy-e-infraestrutura)

---

## 1. Visao Geral

O sistema e uma plataforma de fidelidade gamificada. Clientes da Megalink acumulam pontos (chamados de **Giros**) ao completar missoes, e gastam esses pontos para **girar a roleta** e conquistar premios fisicos ou digitais.

**Tecnologias:**
- Backend: Django 4.2+ / Python 3.10+
- Frontend: HTML5, CSS3, JavaScript Vanilla (jQuery)
- Banco principal: PostgreSQL (producao) / SQLite3 (dev)
- Banco externo: PostgreSQL do Hubsoft (somente leitura)
- Integracao de dados do cliente: Webhook n8n + consulta direta ao banco Hubsoft
- Envio de OTP por WhatsApp: via webhook n8n
- Deploy: Gunicorn + Nginx
- Graficos: Chart.js

---

## 2. Fluxo Principal do Usuario

O fluxo abaixo cobre o caminho completo, do acesso a roleta ate o giro.

```
1. Usuario acessa /roleta/
2. Digita o CPF -> Sistema consulta Hubsoft (via webhook n8n)
   - Se cliente Hubsoft: dados preenchidos automaticamente
   - Se nao cliente: formulario manual de cadastro
3. Envio do OTP via WhatsApp (codigo de 6 digitos, expira em 10 min)
4. Validacao do OTP -> Sessao autenticada inicia + pontos Hubsoft sincronizados
5. Roleta exibida com saldo. Se saldo >= custo do giro: botao "Girar" ativo
6. Giro executado -> Saldo deduzido -> XP creditado -> Premio sorteado -> Estoque atualizado -> Animacao exibida
```

### Regras de Autenticacao de Sessao

- Apos validar o OTP com sucesso, o membro recebe uma **sessao autenticada** (`auth_membro_id` na session).
- Sessoes autenticadas saltam a tela de CPF e OTP em visitas futuras.
- Logout disponivel via `/roleta/logout/`.

---

## 3. Regras de Pontuacao e Gamificacao

### Sistema de Pontos

O sistema usa dois tipos de moeda:

| Tipo | Nome | Uso |
|------|------|-----|
| **Saldo** | Giros | Custo para girar a roleta |
| **XP** | Experiencia | Sobe o nivel do membro no clube |

### Missoes (RegraPontuacao)

Cada missao tem um **gatilho** (identificador unico), uma recompensa em Saldo e/ou XP, e um limite de vezes que pode ser concluida por membro.

| Gatilho | Descricao | Quando e acionado |
|---|---|---|
| `cadastro_inicial` | Bonus de boas-vindas | No primeiro cadastro do membro |
| `telefone_verificado` | Validou o WhatsApp | Na primeira validacao de OTP (1 vez por membro) |
| `hubsoft_recorrencia` | Ativou pagamento recorrente | Sincronizacao com Hubsoft (cartao de credito cadastrado) |
| `hubsoft_adiantado` | Pagou fatura adiantada | Sincronizacao mensal com Hubsoft |
| `hubsoft_app` | Usa o App do Cliente | Sincronizacao com Hubsoft (1 vez por membro) |
| `ajuste_manual_admin` | Ajuste pelo Admin | Quando um admin altera o saldo manualmente |

> Novas regras podem ser criadas livremente no Dashboard -> Gamificacao.

### XP e Niveis

- XP e acumulado com missoes e com os proprios giros (`xp_por_giro`, configuravel).
- O **nivel atual** do membro e calculado dinamicamente com base no XP total vs. a tabela de `NivelClube`.
- Exemplos de niveis: Bronze, Prata, Ouro — cada um com um `xp_necessario` minimo.
- O "proximo nivel" e o percentual de progresso sao exibidos em tempo real na interface.

---

## 4. Integracao com o Hubsoft

O sistema consulta o CRM Hubsoft em duas etapas distintas:

### 4.1 Webhook n8n — Dados cadastrais do cliente
- **Endpoint:** `https://automation-n8n.v4riem.easypanel.host/webhook/roletaconsultarcliente`
- **Acionamento:** Ao digitar o CPF na tela da roleta
- **Retorna:** Nome, e-mail, telefone (mascarado), endereco, ID do cliente Hubsoft

### 4.2 PostgreSQL Hubsoft (somente leitura) — Cidade e pontuacoes extras
- **Host:** `177.10.118.77:9432` | Banco: `hubsoft` | Usuario: `mega_leitura`
- **Consulta 1 – Cidade:** Busca a cidade de instalacao do cliente (fonte de verdade para elegibilidade de premios geograficos).
- **Consulta 2 – Pontuacoes:** Verifica se o cliente:
  - Tem cartao de credito cadastrado (recorrencia)
  - Pagou a fatura do mes atual antes do vencimento (adiantado)
  - Acessou o App Central do cliente

> **Nota:** A consulta de cidade via PostgreSQL prevalece sobre o webhook quando ha discrepancia.

### Prioridade de Cidade
```
1. PostgreSQL Hubsoft (endereco de instalacao) — maior prioridade
2. Webhook n8n
3. Dados digitados pelo usuario
```

---

## 5. Premios e Sorteio

### Configuracao de Premios

Cada premio (`PremioRoleta`) tem:

| Campo | Descricao |
|---|---|
| `nome` | Nome do premio exibido |
| `quantidade` | Estoque disponivel |
| `posicoes` | Posicoes na roda da roleta ocupadas por este premio (ex: `4,7`) |
| `probabilidade` | Peso de probabilidade (ex: `1` = raro, `10` = comum) |
| `mensagem_vitoria` | Mensagem personalizada exibida ao ganhar |
| `cidades_permitidas` | Relacionamento M2M com cidades elegiveis. Se vazio, vale para **todas** as cidades |

### Logica do Sorteio (`SorteioService`)

1. Filtra os premios com **estoque > 0** e que tenham a **cidade do membro** como elegivel (ou sem restricao de cidade).
2. O sorteio usa `random.choices()` com os **pesos de probabilidade** de cada premio — premios mais comuns tem mais chance.
3. Uma posicao aleatoria de `posicoes` e sorteada para a animacao da roleta.
4. O estoque e decrementado **atomicamente via `F()`** (protecao contra race conditions).
5. Se o estoque esgota entre o `SELECT` e o `UPDATE`, o giro e revertido via `@transaction.atomic`.

### Race Condition Protection

```
SELECT premios disponiveis (quantidade > 0)
    -> SorteioService calcula sorteio
    -> UPDATE SET quantidade = F('quantidade') - 1
       WHERE quantidade > 0  <- guarda dupla
    -> Se rows_updated == 0: rollback via IntegrityError
```

---

## 6. Verificacao de Identidade (OTP)

### Fluxo OTP

1. Usuario informa CPF e telefone.
2. Sistema gera um codigo de 6 digitos aleatorio.
3. Codigo salvo na session do Django com timestamp.
4. Codigo enviado via **webhook n8n** (`roletacodconfirmacao`) -> WhatsApp do usuario.
5. Usuario digita o codigo recebido.
6. Sistema valida comparando com a session.

### Regras de Validacao

- **Expiracao:** O codigo expira **10 minutos** apos a geracao.
- **Throttle:** Apenas **1 codigo por minuto** pode ser solicitado por session (rate limiting).
- **Seguranca:** Clientes identificados como Hubsoft (`perfil_cliente = 'sim'`) so podem prosseguir se OTP for validado.

### Eventos pos-validacao

- Sessao autenticada iniciada.
- Se for a primeira validacao do membro -> gatilho `telefone_verificado` disparado.
- Sincronizacao automatica com Hubsoft (recorrencia, adiantado, app).

---

## 7. Entidades do Sistema

### `MembroClube`
Representa um membro cadastrado no clube.

| Campo | Tipo | Descricao |
|---|---|---|
| `cpf` | CharField (unico) | Identificador principal |
| `nome`, `email`, `telefone` | CharField | Dados pessoais |
| `cidade`, `bairro`, `estado`, `cep`, `endereco` | CharField | Localizacao |
| `saldo` | IntegerField | Saldo de giros disponiveis |
| `xp_total` | IntegerField | XP total acumulado |
| `validado` | BooleanField | Se confirmou OTP ao menos uma vez |
| `id_cliente_hubsoft` | IntegerField | ID do cliente no sistema Hubsoft |
| `nivel_atual` | Property | Nome do nivel baseado no XP |
| `proximo_nivel` | Property | Proximo `NivelClube` a ser atingido |

### `ParticipanteRoleta`
Registro imutavel de cada giro executado.

| Campo | Tipo | Descricao |
|---|---|---|
| `membro` | FK MembroClube | Referencia ao membro |
| `premio` | CharField | Nome do premio ganho |
| `status` | CharField | `reservado`, `ganhou`, `inviavel_tec`, `inviavel_cani` |
| `canal_origem` | CharField | Ex: `Online`, `Totem`, `Operador` |
| `saldo` | IntegerField | Saldo restante apos o giro |
| `data_criacao` | DateTimeField | Data/hora do giro |

### `RegraPontuacao`
Define regras de ganho de pontos via gatilhos.

| Campo | Tipo | Descricao |
|---|---|---|
| `gatilho` | CharField (unico) | Identificador do evento |
| `nome_exibicao` | CharField | Nome legivel para o usuario |
| `pontos_saldo` | IntegerField | Giros concedidos |
| `pontos_xp` | IntegerField | XP concedido |
| `limite_por_membro` | IntegerField | `0` = ilimitado |
| `visivel_na_roleta` | BooleanField | Se aparece na lista de missoes |

### `ExtratoPontuacao`
Historico de cada vez que um membro ganhou pontos. Campos: `membro` (FK), `regra` (FK), `pontos_saldo_ganhos`, `pontos_xp_ganhos`, `descricao_extra`, `data_recebimento`.

### `PremioRoleta`
Configuracao de cada fatia da roleta.

### `NivelClube`
Tabela de niveis com XP minimo para alcancar cada um. Campos: `nome`, `xp_necessario`, `ordem`.

### `RoletaConfig`
Singleton de configuracoes globais do sistema.

### `RouletteAsset`
Imagens customizaveis da interface (frame, fundo, logo, ponteiro).

### `Cidade`
Cidades habilitadas para restricao geografica de premios.

---

## 8. Painel Administrativo (Dashboard)

Acessivel via `/roleta/dashboard/` — requer login de staff Django.

O dashboard foi redesenhado com layout moderno: sidebar full-height com navegacao por secoes, cards KPI com indicadores de variacao percentual, e design system consistente.

### Paginas do Dashboard

| Rota | Funcao |
|---|---|
| `/dashboard/` | Home com KPIs (leads, validacoes, jogadores, giros) com variacao % (7 dias vs anterior), grafico de evolucao diaria (7 dias), ultimos ganhadores |
| `/dashboard/premios/` | Tabela de premios com estoque, peso, chance %, cidades (badges). Adicionar e editar via modais |
| `/dashboard/participantes/` | Lista de membros paginada (50/pagina), busca por nome/CPF, filtro por cidade, ajuste manual de saldo. Query otimizada com `annotate` |
| `/dashboard/participantes/<id>/extrato/` | Historico detalhado de pontos de um membro com KPIs (saldo, giros, nivel) |
| `/dashboard/giros/` | Log de todos os giros paginado (50/pagina) com busca. Query otimizada com `select_related` |
| `/dashboard/relatorios/` | **Relatorios analiticos** com filtro de periodo (7/15/30/90 dias ou total). Inclui: funil de conversao com taxas %, evolucao temporal (diaria ou semanal conforme periodo), giros por horario, top 10 jogadores, status dos giros, visao detalhada por cidade com premios ganhos |
| `/dashboard/cidades/` | CRUD de cidades habilitadas |
| `/dashboard/assets/` | Upload/gerenciamento de imagens da roleta (frames, fundo, logo, ponteiro) |
| `/dashboard/config/` | Configuracoes globais: custo do giro, XP por giro, limite de giros por membro e periodo |
| `/dashboard/gamificacao/` | CRUD de niveis do clube e regras de pontuacao (missoes) |
| `/dashboard/exportar/` | Exporta todos os participantes em CSV (compativel com Excel, BOM UTF-8) |
| `/dashboard/docs/` | Renderiza esta documentacao como HTML estilizado |
| `/dashboard/login/` | Tela de login administrativo |

### Metricas do Dashboard Home

- **KPI Cards com Variacao:**
  - Leads (membros iniciados) com variacao % vs 7 dias anteriores
  - Validacoes WhatsApp com variacao %
  - Jogadores (realizaram ao menos 1 giro) com variacao %
  - Total de giros com variacao %
  - Indicadores visuais: seta verde (crescimento) ou vermelha (queda)
- **Grafico de Linha:** Evolucao diaria dos ultimos 7 dias (cadastros, validacoes, giros)
- **Tabela:** Ultimos 10 ganhadores (excluindo "Nao foi dessa vez")

### Pagina de Relatorios

A pagina de relatorios (`/dashboard/relatorios/`) oferece analise aprofundada com:

- **Filtro de periodo:** 7, 15, 30, 90 dias ou todo periodo
- **Funil de conversao:** Leads -> Validados -> Jogaram -> Ganharam, com taxas de conversao entre cada etapa
- **Evolucao temporal:** Grafico de linha com cadastros vs giros. Agrupamento diario para periodos <= 30 dias, semanal para periodos maiores
- **Giros por horario:** Grafico de barras mostrando distribuicao ao longo das 24 horas (identifica picos de uso)
- **Top 10 jogadores:** Ranking por quantidade de giros com XP
- **Status dos giros:** Distribuicao entre reservado, ganhou, inviavel_tec, inviavel_cani
- **Visao detalhada por cidade:** Tabela com membros, validados, taxa de validacao, giros, XP total e premios ganhos por cidade

### Otimizacoes de Performance

- **Participantes:** `annotate(total_giros=Count('giros'))` elimina N+1 queries
- **Giros:** `select_related('membro')` evita query extra por linha
- **Extrato:** `select_related('regra')` evita query extra por linha
- **Premios:** `prefetch_related('cidades_permitidas')` carrega cidades em 1 query
- **Paginacao:** 50 itens por pagina em membros e giros

---

## 9. Endpoints da API Interna

| Metodo | Endpoint | Descricao |
|---|---|---|
| `GET` | `/roleta/api/init-dados/` | Retorna todos os dados iniciais da interface (config, cidades, assets, saldo, missoes) |
| `POST` | `/roleta/verificar-cliente/` | Consulta dados do cliente pelo CPF no Hubsoft |
| `POST` | `/roleta/solicitar-otp/` | Gera e envia codigo OTP via WhatsApp |
| `POST` | `/roleta/validar-otp/` | Valida o codigo OTP inserido pelo usuario |
| `POST` | `/roleta/pre-cadastrar/` | Cria/atualiza o membro antes do OTP (salva dados do formulario) |
| `POST` | `/roleta/cadastrar/` | Executa o cadastro final + giro da roleta |
| `GET` | `/roleta/logout/` | Encerra a sessao autenticada |

---

## 10. Configuracoes Gerais

Todas as configuracoes ficam em `RoletaConfig` (singleton, editavel pelo Dashboard):

| Campo | Padrao | Descricao |
|---|---|---|
| `nome_clube` | "Clube MegaLink" | Nome exibido na interface |
| `custo_giro` | 10 | Pontos necessarios para girar |
| `xp_por_giro` | 5 | XP ganho a cada giro realizado |
| `limite_giros_por_membro` | 0 (sem limite) | Maximo de giros por periodo |
| `periodo_limite` | `total` | Janela de tempo: `total`, `diario`, `semanal`, `mensal` |

---

## 11. Integracoes Externas

| Integracao | Tipo | URL / Host | Finalidade |
|---|---|---|---|
| n8n – consulta cliente | Webhook POST | `automation-n8n.v4riem.easypanel.host/webhook/roletaconsultarcliente` | Buscar dados do cliente Hubsoft |
| n8n – envio OTP | Webhook POST | `automation-n8n.v4riem.easypanel.host/webhook/roletacodconfirmacao` | Enviar codigo OTP via WhatsApp |
| Hubsoft PostgreSQL | Leitura direta | `177.10.118.77:9432` banco `hubsoft` usuario `mega_leitura` | Cidade de instalacao, recorrencia, adiantado e uso do app |

---

## 12. Assets Visuais

A interface suporta customizacao visual por tipo via o Dashboard -> Visual:

| Tipo | Descricao | Uso |
|---|---|---|
| `frame` | Frames da roda da roleta | Um por posicao (ordem 0-12) |
| `background` | Fundo da pagina | Imagem de fundo da tela toda |
| `logo` | Logo central | Exibido no centro da roleta |
| `pointer` | Ponteiro/seta | Indica o premio sorteado |

Assets podem ser ativados/desativados individualmente. Apenas assets ativos sao carregados na interface publica.

Enquanto os assets carregam via API (`/roleta/api/init-dados/`), um spinner de loading e exibido no lugar da roleta.

---

## 13. Deploy e Infraestrutura

### Producao
- **Servidor web:** Gunicorn + Nginx
- **Dominio:** `roleta.megalinkpiaui.com.br`
- **Banco:** PostgreSQL (host: `187.62.153.52:5432`, banco: `megasorteio`)
- **Timezone:** America/Fortaleza
- **Locale:** pt-br

### Comandos uteis

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Rodar migrations
.venv/bin/python manage.py migrate

# Coletar arquivos estaticos
.venv/bin/python manage.py collectstatic --noinput

# Reiniciar servico
sudo systemctl restart megaroleta

# Ver logs
sudo journalctl -u megaroleta -n 50 -f

# Testar e recarregar Nginx
sudo nginx -t && sudo systemctl reload nginx
```

### Estrutura de Arquivos

```
roleta/
  models.py              # 9 modelos de dados
  admin.py               # Configuracao do Django Admin
  urls.py                # Rotas da aplicacao
  views/
    core_views.py        # Views principais (index, logout)
    api_views.py         # Endpoints JSON (sorteio, OTP, verificacao)
    dashboard_views.py   # Painel administrativo + relatorios
    docs_views.py        # Documentacao renderizada
  services/
    sorteio_service.py   # Algoritmo de sorteio ponderado
    hubsoft_service.py   # Integracao Hubsoft (webhook + PostgreSQL)
    otp_service.py       # Geracao e envio de OTP via WhatsApp
    gamification_service.py  # Sistema de pontos/XP
  templates/roleta/
    index_frontend.html  # Interface publica da roleta
    dashboard/           # 13 templates do painel admin
  static/roleta/
    css/dashboard.css    # Design system do dashboard
    js/                  # jQuery, Bootstrap, custom.js
    images/              # Frames da roleta (fallback)
```
