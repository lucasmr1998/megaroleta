# Roadmap do Projeto MegaRoleta

> Historico de entregas, plano de lancamento e proximos passos.

---

## Entregas Realizadas (Produto)

### Fase 1 — Roleta e Gamificacao (base)
- [x] Cadastro de membros via CPF + OTP WhatsApp
- [x] Integracao Hubsoft (dados cadastrais, cidade, pontuacoes)
- [x] Sistema de pontos (Saldo/Giros + XP)
- [x] Missoes com gatilhos automaticos (cadastro, recorrencia, app, adiantado)
- [x] Roleta com sorteio ponderado e animacao
- [x] Premios com estoque, probabilidade e restricao por cidade
- [x] Niveis do clube (Bronze, Prata, Ouro)
- [x] Dashboard admin com KPIs e graficos

### Fase 2 — Redesign e Modularizacao (marco/2026)
- [x] Redesign completo do dashboard admin
- [x] Topbar de modulos + sidebar contextual
- [x] Separacao em 4 apps Django (roleta, parceiros, indicacoes, carteirinha)
- [x] Limpeza de codigo legado (apps clientes e participacao removidos)

### Fase 3 — Parceiros e Cupons (marco/2026)
- [x] CRUD de parceiros com logo e contato
- [x] Cupons com 3 modalidades (gratuito, pontos, nivel)
- [x] Fluxo de resgate com codigo unico
- [x] Pagina publica de validacao de cupom
- [x] Painel do parceiro (dashboard, cupons, resgates, validar)
- [x] Solicitacao de cupom pelo parceiro com aprovacao do admin
- [x] Detalhes do cupom com historico de utilizacoes

### Fase 4 — Indicacoes (marco/2026)
- [x] Link de indicacao unico por membro
- [x] Pagina publica de indicacao com formulario
- [x] Gestao de indicacoes no admin (status, conversao, pontos)
- [x] Pagina de embaixadores com links copiaveis
- [x] Configuracao visual da pagina de indicacao
- [x] Credito automatico de pontos na conversao

### Fase 5 — Area do Membro (marco/2026)
- [x] Hub com 6 cards (Roleta, Cupons, Indicar, Perfil, Carteirinha, Missoes)
- [x] Pagina dedicada para cada funcionalidade
- [x] Design mobile-first com fundo #000b4a
- [x] Pagina da roleta padronizada no novo layout

### Fase 6 — Relatorios e Dashboards (marco/2026)
- [x] Relatorio da Roleta (funil, evolucao, cidades, premios, horarios)
- [x] Relatorio de Indicacoes (KPIs, embaixadores, por cidade)
- [x] Relatorio de Parceiros (resgates, cupons top, por parceiro)
- [x] Dashboard por modulo (Roleta, Parceiros, Indicacoes, Carteirinha)

### Fase 7 — Carteirinhas (marco/2026)
- [x] Modelos customizaveis (cores, gradiente, imagem, campos configuraveis)
- [x] Regras de atribuicao (por nivel, XP, cidade, todos)
- [x] Preview em tempo real no admin
- [x] Pagina do membro com download PNG
- [x] Renderizacao CSS (estilo Urbis) sem depender de imagem

### Fase 8 — Estrutura Estrategica (marco/2026)
- [x] Documentacao estrategica (ESTRATEGIA.md, ROADMAP.md, DECISOES.md, REGRAS_NEGOCIO.md)
- [x] Time de agentes IA (CTO, CPO, CFO, CMO, PMM, Comercial B2B, CS)
- [x] Tools reutilizaveis (analise dados, copy, ROI, code review, spec, prospector)
- [x] Base de conhecimento (brandbook, metas, financeiro, concorrentes, FAQ)
- [x] Sistema de sessoes e entregas

### Fase 9 — Gestao de Projetos e Sala de Agentes (marco/2026)
- [x] App `gestao` com models Projeto, Etapa, Tarefa, Nota, Reuniao, MensagemReuniao
- [x] Dashboard CEO com KPIs do sistema (membros, giros, parceiros, cupons, indicacoes)
- [x] Kanban board com 4 colunas (pendente, em andamento, concluida, bloqueada)
- [x] Projeto "Lancamento Floriano" populado com 25 tarefas em 4 etapas
- [x] Sala de agentes com chat individual integrado via OpenAI API (gpt-4o-mini)
- [x] Reunioes com nome, descricao e participantes selecionaveis
- [x] Moderador inteligente que direciona mensagens para agentes relevantes
- [x] Agentes respondem sequencialmente (um por vez, estilo conversa)
- [x] Historico de reunioes salvo no banco (persistente)
- [x] Acoes dos agentes: salvar entregas, sessoes, criar/atualizar tarefas, consultar outros agentes
- [x] Visualizacao de entregas e sessoes com markdown renderizado
- [x] Editor de entregas com preview em tempo real
- [x] Botao "Salvar Sessao" no chat individual

### Fase 10 — Hardening e Seguranca (marco/2026)
- [x] Migracao de credenciais hardcoded para .env (DB, Hubsoft, OpenAI, SECRET_KEY)
- [x] DEBUG e ALLOWED_HOSTS controlados via .env
- [x] Remocao de logs debug com dados sensiveis (CPF, telefone)
- [x] select_for_update + F() em atribuir_pontos e validar_cupom
- [x] @transaction.atomic em CRUD de parceiros, cupons e carteirinhas
- [x] Eliminacao de queries N+1 em roleta_init_dados, membro_missoes, membro_indicar, membro_perfil
- [x] 17 db_index adicionados em campos filtrados frequentemente
- [x] Cache Django para dados Hubsoft (1 hora, substituiu cache estatico)
- [x] Limite de contexto IA (20 projetos, 30 tarefas/projeto, textos truncados)
- [x] Sanitizacao markdown: bleach (backend) + DOMPurify (frontend)
- [x] Remocao de @csrf_exempt dos endpoints de chat
- [x] Logging estruturado (substituiu print por logging.getLogger)
- [x] Correcao URL duplicada roleta.urls no root (redirect para /roleta/)
- [x] requirements.txt atualizado (python-dotenv, openai, requests, bleach)

---

## Plano de Lancamento — Floriano (EM ANDAMENTO)

> Decisao do CEO em 19/03/2026. Detalhes em `docs/entregas/pmm/cronograma_floriano.md`

### Dados
- **Cidade-piloto**: Floriano (sede Megalink)
- **Base total Megalink**: 13.209 clientes
- **Membros no Clube**: 82 (0,6% penetracao)
- **Meta 4 semanas**: 500 membros (3,8%) + 8-10 parceiros

### Timeline

| Semana | Foco | Meta Principal | Status |
|--------|------|----------------|--------|
| **Semana 1** | Parceiros + avaliar WhatsApp | 5 parceiros ativos + decisao disparo | [ ] |
| **Semana 2** | Fechar parceiros + preparar lancamento | 8+ parceiros + equipe treinada + materiais | [ ] |
| **Semana 3** | Lancamento massivo (13 mil clientes) | 300+ novos membros | [ ] |
| **Semana 4** | Indicacoes + review | 20+ indicacoes + decisao escalar | [ ] |

### Prioridade CEO
1. **Parceiros PRIMEIRO** — sem parceiro, clube nao tem valor
2. **Dados financeiros** — fornecer ARPU, churn, CAC numa proxima sessao
3. **Ferramenta WhatsApp** — avaliar ate sexta da Semana 1

### Pendencias Criticas
- [ ] CEO: avaliar ferramenta de disparo WhatsApp em massa
- [ ] CEO: fornecer base total de clientes por cidade (para priorizar apos Floriano)
- [ ] CEO: fornecer dados financeiros (ARPU, churn) para sessao com CFO
- [ ] Comercial B2B: listar 20 comercios-alvo em Floriano
- [ ] PMM: criar one-pager "O que e o Clube"
- [ ] CMO: aprovar copy de lancamento

---

## Proximas Fases (Produto)

### Fase 11 — Loja de Pontos
- [ ] Criar app `loja` separado
- [ ] Modelo ItemLoja generico (cupom, brinde, produto)
- [ ] Categorias de itens
- [ ] Vitrine do membro (/membro/loja/) substituindo pagina de cupons
- [ ] Resgate unificado
- [ ] Dashboard admin da loja

### Fase 12 — Melhorias de UX
- [ ] Notificacoes (novo cupom disponivel, indicacao convertida)
- [ ] Historico de giros do membro na area do membro
- [ ] QR Code real na carteirinha (em vez de icone)
- [ ] Compartilhamento de premios ganhos

### Fase 13 — Inteligencia e Automacao
- [ ] Relatorio de ROI por parceiro
- [ ] Segmentacao de membros (por cidade, nivel, engajamento)
- [ ] Campanhas direcionadas (cupons por segmento)
- [ ] Automacao de expiracao de cupons
- [ ] Alertas automaticos de churn

---

## Plano de Escala por Cidade

> Apos Floriano validado, replicar playbook.

| Prioridade | Cidade | Membros Clube | Base Megalink | Penetracao | Status |
|-----------|--------|--------------|---------------|-----------|--------|
| 1 | **Floriano** | 82 | 13.209 | 0,6% | 🟡 Em lancamento |
| 2 | Timon | 35 | [verificar] | [calc] | Aguardando |
| 3 | Oeiras | 34 | [verificar] | [calc] | Aguardando |
| 4 | Picos | 33 | [verificar] | [calc] | Aguardando |
| 5 | Valenca do Piaui | 27 | [verificar] | [calc] | Aguardando |

**Criterio para escalar**: Floriano com 300+ membros, 8+ parceiros e indicacoes acontecendo.

---

## Backlog de Ideias

> Priorizar com base no triangulo de valor (parceiro B2B + cliente + Megalink).

### Aquisicao e Crescimento
- App mobile nativo (React Native / Flutter)
- Totem fisico em lojas da Megalink para girar a roleta
- QR Code para validacao de cupom (em vez de codigo digitado)
- Programa de member-get-member com recompensas escalonadas

### Engajamento e Retencao
- Ranking de membros por cidade (gamificacao social)
- Desafios semanais/mensais com premios especiais
- Compartilhamento de premios ganhos nas redes sociais
- Streak de acesso (bonus por dias consecutivos)

### Parceiros e Monetizacao
- Relatorio de ROI por parceiro (clientes novos gerados)
- Dashboard de prospeccao B2B (metricas para convencer novos parceiros)
- Programa de pontos entre parceiros (pontos universais)

### Inteligencia e Automacao
- Segmentacao de membros (por cidade, nivel, engajamento, churn risk)
- Automacao de expiracao de cupons
- Notificacoes push (novo cupom, indicacao convertida, nivel subiu)
- Integracao com sistema de cobranca (bonus automatico ao pagar)

### Escala
- Replicacao automatica por cidade (onboarding de cidade nova)
- Gamificacao entre cidades (ranking de engajamento por cidade)
