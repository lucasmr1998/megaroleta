# 🎡 Documentação — Sistema de Roleta (MegaLink Clube)

> Documentação técnica e funcional do sistema de gamificação com roleta para o Clube MegaLink.

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Fluxo Principal do Usuário](#2-fluxo-principal-do-usuário)
3. [Regras de Pontuação e Gamificação](#3-regras-de-pontuação-e-gamificação)
4. [Integração com o Hubsoft](#4-integração-com-o-hubsoft)
5. [Prêmios e Sorteio](#5-prêmios-e-sorteio)
6. [Verificação de Identidade (OTP)](#6-verificação-de-identidade-otp)
7. [Entidades do Sistema](#7-entidades-do-sistema)
8. [Painel Administrativo (Dashboard)](#8-painel-administrativo-dashboard)
9. [Endpoints da API Interna](#9-endpoints-da-api-interna)
10. [Configurações Gerais](#10-configurações-gerais)
11. [Integrações Externas](#11-integrações-externas)
12. [Assets Visuais](#12-assets-visuais)

---

## 1. Visão Geral

O sistema é uma plataforma de fidelidade gamificada. Clientes da MegaLink acumulam pontos (chamados de **Giros**) ao completar missões, e gastam esses pontos para **girar a roleta** e conquistar prêmios físicos ou digitais.

**Tecnologias:**
- Backend: Django (Python)
- Banco principal: PostgreSQL
- Banco externo: PostgreSQL do Hubsoft (somente leitura)
- Integração de dados do cliente: Webhook n8n + consulta direta ao banco Hubsoft
- Envio de OTP por WhatsApp: via webhook n8n

---

## 2. Fluxo Principal do Usuário

O fluxo abaixo cobre o caminho completo, do acesso à roleta até o giro.

```
┌─────────────────────────────────┐
│ 1. Usuário acessa /roleta/      │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ 2. Digita o CPF                 │
│    → Sistema consulta Hubsoft   │
│      (via webhook n8n)          │
└───────────────┬─────────────────┘
                │
        ┌───────┴───────┐
        │               │
    [Cliente]       [Não cliente]
    Hubsoft?            │
        │               ▼
        │       ┌───────────────────┐
        │       │ Formulário manual │
        │       │ de cadastro       │
        │       └────────┬──────────┘
        │                │
        ▼                ▼
┌─────────────────────────────────┐
│ 3. Envio do OTP via WhatsApp    │
│    Código de 6 dígitos,         │
│    expira em 10 minutos         │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ 4. Validação do OTP             │
│    → Sessão autenticada inicia  │
│    → Pontos Hubsoft sincronizados│
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ 5. Roleta exibida com saldo     │
│    Se saldo ≥ custo do giro:    │
│    botão "Girar" ativo          │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ 6. Giro executado               │
│    → Saldo deduzido             │
│    → XP creditado               │
│    → Prêmio sorteado            │
│    → Estoque atualizado         │
│    → Animação exibida           │
└─────────────────────────────────┘
```

### Regras de Autenticação de Sessão

- Após validar o OTP com sucesso, o membro recebe uma **sessão autenticada** (`auth_membro_id` na session).
- Sessões autenticadas saltam a tela de CPF e OTP em visitas futuras.
- Logout disponível via `/roleta/logout/`.

---

## 3. Regras de Pontuação e Gamificação

### Sistema de Pontos

O sistema usa dois tipos de moeda:

| Tipo | Nome | Uso |
|------|------|-----|
| **Saldo** | Giros | Custo para girar a roleta |
| **XP** | Experiência | Sobe o nível do membro no clube |

### Missões (RegraPontuacao)

Cada missão tem um **gatilho** (identificador único), uma recompensa em Saldo e/ou XP, e um limite de vezes que pode ser concluída por membro.

| Gatilho | Descrição | Quando é acionado |
|---|---|---|
| `cadastro_inicial` | Bônus de boas-vindas | No primeiro cadastro do membro |
| `telefone_verificado` | Validou o WhatsApp | Na primeira validação de OTP (1 vez por membro) |
| `hubsoft_recorrencia` | Ativou pagamento recorrente | Sincronização com Hubsoft (cartão de crédito cadastrado) |
| `hubsoft_adiantado` | Pagou fatura adiantada | Sincronização mensal com Hubsoft |
| `hubsoft_app` | Usa o App do Cliente | Sincronização com Hubsoft (1 vez por membro) |
| `ajuste_manual_admin` | Ajuste pelo Admin | Quando um admin altera o saldo manualmente |

> Novas regras podem ser criadas livremente no Dashboard → Gamificação.

### XP e Níveis

- XP é acumulado com missões e com os próprios giros (`xp_por_giro`, configurável).
- O **nível atual** do membro é calculado dinamicamente com base no XP total vs. a tabela de `NivelClube`.
- Exemplos de níveis: Bronze, Prata, Ouro — cada um com um `xp_necessario` mínimo.
- O "próximo nível" e o percentual de progresso são exibidos em tempo real na interface.

---

## 4. Integração com o Hubsoft

O sistema consulta o CRM Hubsoft em duas etapas distintas:

### 4.1 Webhook n8n — Dados cadastrais do cliente
- **Endpoint:** `https://automation-n8n.v4riem.easypanel.host/webhook/roletaconsultarcliente`
- **Acionamento:** Ao digitar o CPF na tela da roleta
- **Retorna:** Nome, e-mail, telefone (mascarado), endereço, ID do cliente Hubsoft

### 4.2 PostgreSQL Hubsoft (somente leitura) — Cidade e pontuações extras
- **Host:** `177.10.118.77:9432` | Banco: `hubsoft` | Usuário: `mega_leitura`
- **Consulta 1 – Cidade:** Busca a cidade de instalação do cliente (fonte de verdade para elegibilidade de prêmios geográficos).
- **Consulta 2 – Pontuações:** Verifica se o cliente:
  - Tem cartão de crédito cadastrado (recorrência)
  - Pagou a fatura do mês atual antes do vencimento (adiantado)
  - Acessou o App Central do cliente

> **Nota:** A consulta de cidade via PostgreSQL prevalece sobre o webhook quando há discrepância.

### Prioridade de Cidade
```
1. PostgreSQL Hubsoft (endereço de instalação) — maior prioridade
2. Webhook n8n
3. Dados digitados pelo usuário
```

---

## 5. Prêmios e Sorteio

### Configuração de Prêmios

Cada prêmio (`PremioRoleta`) tem:

| Campo | Descrição |
|---|---|
| `nome` | Nome do prêmio exibido |
| `quantidade` | Estoque disponível |
| `posicoes` | Posições na roda da roleta ocupadas por este prêmio (ex: `4,7`) |
| `probabilidade` | Peso de probabilidade (ex: `1` = raro, `10` = comum) |
| `mensagem_vitoria` | Mensagem personalizada exibida ao ganhar |
| `cidades_permitidas` | Relacionamento M2M com cidades elegíveis. Se vazio, vale para **todas** as cidades |

### Lógica do Sorteio (`SorteioService`)

1. Filtra os prêmios com **estoque > 0** e que tenham a **cidade do membro** como elegível (ou sem restrição de cidade).
2. O sorteio usa `random.choices()` com os **pesos de probabilidade** de cada prêmio — prêmios mais comuns têm mais chance.
3. Uma posição aleatória de `posicoes` é sorteada para a animação da roleta.
4. O estoque é decrementado **atomicamente via `F()`** (proteção contra race conditions).
5. Se o estoque esgota entre o `SELECT` e o `UPDATE`, o giro é revertido via `@transaction.atomic`.

### Race Condition Protection

```
SELECT prêmios disponíveis (quantidade > 0)
    → SorteioService calcula sorteio
    → UPDATE SET quantidade = F('quantidade') - 1
       WHERE quantidade > 0  ← guarda dupla
    → Se rows_updated == 0: rollback via IntegrityError
```

---

## 6. Verificação de Identidade (OTP)

### Fluxo OTP

1. Usuário informa CPF e telefone.
2. Sistema gera um código de 6 dígitos aleatório.
3. Código salvo na session do Django com timestamp.
4. Código enviado via **webhook n8n** (`roletacodconfirmacao`) → WhatsApp do usuário.
5. Usuário digita o código recebido.
6. Sistema valida comparando com a session.

### Regras de Validação

- **Expiração:** O código expira **10 minutos** após a geração.
- **Throttle:** Apenas **1 código por minuto** pode ser solicitado por session (rate limiting).
- **Segurança:** Clientes identificados como Hubsoft (`perfil_cliente = 'sim'`) só podem prosseguir se OTP for validado.

### Eventos pós-validação

- Sessão autenticada iniciada.
- Se for a primeira validação do membro → gatilho `telefone_verificado` disparado.
- Sincronização automática com Hubsoft (recorrência, adiantado, app).

---

## 7. Entidades do Sistema

### `MembroClube`
Representa um membro cadastrado no clube.

| Campo | Tipo | Descrição |
|---|---|---|
| `cpf` | CharField (único) | Identificador principal |
| `nome`, `email`, `telefone` | CharField | Dados pessoais |
| `cidade`, `bairro`, `estado`, `cep`, `endereco` | CharField | Localização |
| `saldo` | IntegerField | Saldo de giros disponíveis |
| `xp_total` | IntegerField | XP total acumulado |
| `validado` | BooleanField | Se confirmou OTP ao menos uma vez |
| `id_cliente_hubsoft` | IntegerField | ID do cliente no sistema Hubsoft |
| `nivel_atual` | Property | Nome do nível baseado no XP |
| `proximo_nivel` | Property | Próximo `NivelClube` a ser atingido |

### `ParticipanteRoleta`
Registro imutável de cada giro executado.

| Campo | Tipo | Descrição |
|---|---|---|
| `membro` | FK MembroClube | Referência ao membro |
| `premio` | CharField | Nome do prêmio ganho |
| `status` | CharField | `reservado`, `ganhou`, `inviavel_tec`, `inviavel_cani` |
| `canal_origem` | CharField | Ex: `Online`, `Totem`, `Operador` |
| `data_criacao` | DateTimeField | Data/hora do giro |

### `RegraPontuacao`
Define regras de ganho de pontos via gatilhos.

| Campo | Tipo | Descrição |
|---|---|---|
| `gatilho` | CharField (único) | Identificador do evento |
| `nome_exibicao` | CharField | Nome legível para o usuário |
| `pontos_saldo` | IntegerField | Giros concedidos |
| `pontos_xp` | IntegerField | XP concedido |
| `limite_por_membro` | IntegerField | `0` = ilimitado |
| `visivel_na_roleta` | BooleanField | Se aparece na lista de missões |

### `ExtratoPontuacao`
Histórico de cada vez que um membro ganhou pontos.

### `PremioRoleta`
Configuração de cada fatia da roleta.

### `NivelClube`
Tabela de níveis com XP mínimo para alcançar cada um.

### `RoletaConfig`
Singleton de configurações globais do sistema.

### `RouletteAsset`
Imagens customizáveis da interface (frame, fundo, logo, ponteiro).

### `Cidade`
Cidades habilitadas para restrição geográfica de prêmios.

---

## 8. Painel Administrativo (Dashboard)

Acessível via `/roleta/dashboard/` — requer login de staff Django.

| Rota | Função |
|---|---|
| `/dashboard/` | Home com métricas: total de giros, funil de conversão, gráfico de prêmios e giros por dia |
| `/dashboard/premios/` | CRUD completo de prêmios, probabilidades e restrições por cidade |
| `/dashboard/participantes/` | Lista de membros, busca por nome/CPF/cidade, ajuste manual de saldo |
| `/dashboard/participantes/<id>/extrato/` | Histórico detalhado de pontos de um membro |
| `/dashboard/giros/` | Log de todos os giros realizados com status |
| `/dashboard/cidades/` | CRUD de cidades habilitadas |
| `/dashboard/assets/` | Upload/gerenciamento de imagens da roleta |
| `/dashboard/config/` | Configurações globais: custo do giro, XP por giro, limite de giros, período |
| `/dashboard/gamificacao/` | CRUD de níveis do clube e regras de pontuação |
| `/dashboard/diagnostico-hubsoft/` | Ferramenta de diagnóstico: consulta completa via CPF nas 4 fontes de dados |
| `/dashboard/exportar/` | Exporta todos os participantes em CSV (compatível com Excel) |

### Métricas do Home Dashboard

- **Funil de Conversão:**
  - Membros iniciados (cadastrados)
  - Membros validados (confirmaram OTP)
  - Membros jogadores (realizaram ao menos 1 giro)
  - Taxa de validação (%)
  - Taxa de engajamento (%)
- **Gráfico de Pizza:** Distribuição de prêmios distribuídos
- **Gráfico de Linha:** Giros dos últimos 7 dias
- **Últimos 5 ganhadores**

---

## 9. Endpoints da API Interna

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/roleta/api/init-dados/` | Retorna todos os dados iniciais da interface (prêmios, missões, saldo, assets) |
| `POST` | `/roleta/verificar-cliente/` | Consulta dados do cliente pelo CPF no Hubsoft |
| `POST` | `/roleta/solicitar-otp/` | Gera e envia código OTP via WhatsApp |
| `POST` | `/roleta/validar-otp/` | Valida o código OTP inserido pelo usuário |
| `POST` | `/roleta/pre-cadastrar/` | Cria/atualiza o membro antes do OTP (salva dados do formulário) |
| `POST` | `/roleta/cadastrar/` | Executa o cadastro final + giro da roleta |
| `GET` | `/roleta/logout/` | Encerra a sessão autenticada |

---

## 10. Configurações Gerais

Todas as configurações ficam em `RoletaConfig` (singleton, editável pelo Dashboard):

| Campo | Padrão | Descrição |
|---|---|---|
| `nome_clube` | "Clube MegaLink" | Nome exibido na interface |
| `custo_giro` | 10 | Pontos necessários para girar |
| `xp_por_giro` | 5 | XP ganho a cada giro realizado |
| `limite_giros_por_membro` | 0 (sem limite) | Máximo de giros por período |
| `periodo_limite` | `total` | Janela de tempo: `total`, `diario`, `semanal`, `mensal` |

---

## 11. Integrações Externas

| Integração | Tipo | URL / Host | Finalidade |
|---|---|---|---|
| n8n – consulta cliente | Webhook POST | `automation-n8n.v4riem.easypanel.host/webhook/roletaconsultarcliente` | Buscar dados do cliente Hubsoft |
| n8n – envio OTP | Webhook POST | `automation-n8n.v4riem.easypanel.host/webhook/roletacodconfirmacao` | Enviar código OTP via WhatsApp |
| Hubsoft PostgreSQL | Leitura direta | `177.10.118.77:9432` banco `hubsoft` | Cidade de instalação, recorrência, adiantado e uso do app |

---

## 12. Assets Visuais

A interface suporta customização visual por tipo via o Dashboard → Assets:

| Tipo | Descrição | Uso |
|---|---|---|
| `frame` | Frames da roda da roleta | Um por posição (ordem 0–12) |
| `background` | Fundo da página | Imagem de fundo da tela toda |
| `logo` | Logo central | Exibido no centro da roleta |
| `pointer` | Ponteiro/seta | Indica o prêmio sorteado |

Assets podem ser ativados/desativados individualmente. Apenas assets ativos são carregados na interface pública.
