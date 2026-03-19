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

## Stack Tecnológica

- Backend: Django 4.2+ / Python 3.10+
- Frontend: HTML5, CSS3, JavaScript Vanilla (jQuery)
- Banco de Dados: PostgreSQL (produção)
- Integrações: Hubsoft (PostgreSQL direto + webhook n8n), OpenAI API (sala de agentes)
- Deploy: Gunicorn + Nginx
- Variáveis de ambiente: python-dotenv (`.env`)

## Arquitetura de Apps Django

```
megaroleta/
├── roleta/          # Core: roleta, membros, prêmios, gamificação, área do membro
├── parceiros/       # B2B: parceiros, cupons, resgates, painel do parceiro
├── indicacoes/      # Indicações, embaixadores, página pública
├── carteirinha/     # Carteirinhas virtuais, modelos, regras de atribuição
├── gestao/          # Gestão de projetos, Kanban, sala de agentes IA, entregas, sessões
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
- `gestao/views.py` — Dashboard CEO, projetos, Kanban, sala de agentes, entregas, sessões

### Modelos Principais

**roleta**: MembroClube, PremioRoleta, ParticipanteRoleta, RegraPontuacao, ExtratoPontuacao, NivelClube, RoletaConfig, RouletteAsset, Cidade
**parceiros**: Parceiro (com FK User), CupomDesconto, ResgateCupom
**indicacoes**: Indicacao, IndicacaoConfig
**carteirinha**: ModeloCarteirinha, RegraAtribuicao, CarteirinhaMembro
**gestao**: Projeto, Etapa, Tarefa, Nota, Reuniao, MensagemReuniao

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

## Sala de Agentes IA

Integrada com OpenAI API (`gpt-4o-mini`). Localizada em `/roleta/dashboard/gestao/sala/`.

- **Chat individual**: Conversa 1:1 com qualquer agente
- **Reunião**: Cria reunião com nome/descrição, moderador inteligente direciona, agentes respondem sequencialmente, histórico salvo no banco
- **Ações dos agentes**: Salvar entregas, sessões, criar/atualizar tarefas
- **Consulta entre agentes**: Um agente pode consultar outro

### Agentes Disponíveis

```
docs/agentes/
├── executivo/: CTO, CPO, CFO
├── comercial/: CMO, PMM, Comercial B2B, Customer Success
└── tools/: analise_dados, gerador_copy, calculadora_roi, auditor_codigo, gerador_spec, prospector_parceiro
```

## Padrões de Código

- Use `@transaction.atomic` para operações que modificam saldo/estoque
- Proteção contra race condition: `select_for_update()` + `F()` expressions
- Performance: `annotate`, `select_related`, `prefetch_related`, paginação 50/pg
- Serviços stateless (métodos estáticos)
- Todos os formulários POST devem salvar TODOS os campos do template (bug recorrente!)
- Mobile first: toda interface do membro deve funcionar em celular

## Integrações

- **Hubsoft**: Webhook n8n (dados do cliente) + PostgreSQL read-only (cidade, recorrência, app)
- **OTP WhatsApp**: Webhook n8n, rate limiting 60s, expiração 10min
- **OpenAI**: API key no `.env`, modelo `gpt-4o-mini`, usado na sala de agentes

## Observações de Segurança

⚠️ Dados sensíveis de clientes (CPF, telefone, endereço) — seguir LGPD.
⚠️ Credenciais do banco ainda hardcoded no settings.py — meta: migrar para .env.
⚠️ Parceiro só vê seus próprios dados (isolamento por FK).
