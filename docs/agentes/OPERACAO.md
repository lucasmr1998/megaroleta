# Operacao do Time de IAs — Clube Megalink

> Como o CEO orquestra agentes de IA para gerir o negocio com minima intervencao manual.

---

## 1. Visao Geral

Voce (CEO) opera o Clube Megalink com um time virtual de agentes de IA. Cada agente tem um papel, um escopo de decisao e um formato de output padronizado. Voce nao precisa fazer o trabalho operacional — precisa fazer as perguntas certas, tomar decisoes estrategicas e aprovar recomendacoes.

### Seu Papel como CEO
- **Definir direcao**: Quais problemas resolver, quais oportunidades perseguir
- **Aprovar/rejeitar**: Recomendacoes dos agentes passam por voce
- **Alimentar contexto**: Dados reais do negocio (ARPU, churn, base por cidade)
- **Conectar agentes**: Pegar output de um e alimentar outro
- **Decidir prioridades**: Quando agentes discordam, voce decide

### O que Voce NAO Precisa Fazer
- Escrever copy (CMO faz)
- Priorizar backlog (CPO faz)
- Calcular ROI (CFO faz)
- Criar scripts de venda (Comercial B2B faz)
- Montar onboarding (CS faz)
- Tomar decisoes tecnicas (CTO faz)

---

## 2. Organograma do Time

```
                        ┌─────────┐
                        │   CEO   │ ← Voce
                        │ (Lucas) │
                        └────┬────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
       ┌────┴────┐     ┌────┴────┐     ┌─────┴─────┐
       │   CTO   │     │   CPO   │     │    CFO    │
       │  Tech   │     │ Produto │     │ Financas  │
       └────┬────┘     └────┬────┘     └───────────┘
            │               │
     ┌──────┴──────┐   ┌────┴─────────────┐
     │ Claude Code │   │      CMO         │
     │ (execucao)  │   │   Marketing      │
     └─────────────┘   └────┬─────────────┘
                            │
                   ┌────────┼────────┐
                   │                 │
            ┌──────┴──────┐  ┌──────┴──────┐
            │ Comercial   │  │  Customer   │
            │    B2B      │  │  Success    │
            └─────────────┘  └─────────────┘
```

---

## 3. Fluxos de Trabalho

### 3.1 Fluxo: Nova Feature

```
CEO: "Quero fazer X"
  → CPO: Avalia impacto, escreve spec, prioriza (ICE)
    → CTO: Avalia viabilidade tecnica, estima esforco
      → CFO: Avalia ROI e viabilidade financeira
        → CEO: Aprova ou ajusta
          → CTO: Define plano tecnico
            → Claude Code: Implementa
              → CTO: Revisa (code review)
                → CMO: Planeja comunicacao de lancamento
                  → CS: Prepara onboarding da feature
```

**Prompt para iniciar:**
> "Quero implementar [feature]. CPO, me da um readout com ICE score e criterios de aceitacao."

### 3.2 Fluxo: Lancar em Nova Cidade

```
CEO: "Vamos lancar em [cidade]"
  → CFO: Analise de viabilidade por cidade (base, custo, payback)
    → Comercial B2B: Plano de prospeccao de parceiros (metas, segmentos, scripts)
      → CMO: Campanha de lancamento (awareness + ativacao)
        → CS: Plano de onboarding para membros e parceiros
          → CTO: Ativar cidade no sistema
```

**Prompt para iniciar:**
> "Quero lancar o Clube em [cidade]. Temos [X] clientes la. CFO, me da viabilidade. Comercial B2B, me da plano de prospeccao."

### 3.3 Fluxo: Prospectar Parceiro

```
CEO: "Quero abordar [tipo de comercio] em [cidade]"
  → Comercial B2B: Script de abordagem + proposta
    → CEO: Envia/executa a abordagem
      → Comercial B2B: Follow-up template
        → CS: Onboarding do parceiro (primeiros 30 dias)
```

**Prompt para iniciar:**
> "Comercial B2B, crie um script para abordar [restaurantes] em [Floriano]. Temos [X] membros la."

### 3.4 Fluxo: Campanha de Engajamento

```
CEO: "Engajamento esta baixo" ou "Quero aumentar indicacoes"
  → CMO: Propoe campanha com metricas
    → CPO: Valida se features necessarias existem
      → CFO: Valida custo da campanha (se envolver premios)
        → CEO: Aprova
          → CS: Executa comunicacao (templates WhatsApp)
            → CMO: Mede resultado
```

**Prompt para iniciar:**
> "CMO, o engajamento caiu 20% no ultimo mes. Me propoe uma campanha de reativacao com foco em [cupons/indicacoes/roleta]."

### 3.5 Fluxo: Revisao Mensal

```
CEO: "Review mensal"
  → CFO: Unit economics do mes (custo premios, resgates, retencao)
  → CPO: Metricas de produto (ativacao, retencao, features usadas)
  → CMO: Metricas de growth (CAC, indicacoes, funil)
  → CS: Health check (membros ativos, parceiros saudaveis, churn signals)
  → CTO: Debito tecnico, performance, seguranca
  → CEO: Consolida e decide prioridades do proximo mes
```

**Prompt para iniciar:**
> "Time, review mensal. Cada um me traga um readout com metricas do mes, diagnostico e recomendacao top-1."

### 3.6 Fluxo: Bug ou Problema Tecnico

```
CEO: "Algo esta quebrado" ou "Usuario reclamou de X"
  → CTO: Diagnostico (CTO Readout com causa raiz)
    → CTO: Plano de correcao (max 5 passos)
      → Claude Code: Implementa fix
        → CTO: Verifica
          → CS: Comunica ao usuario/parceiro se necessario
```

**Prompt para iniciar:**
> "CTO, [descrever problema]. Me da um readout com causa raiz e plano de correcao."

---

## 4. Prompts Rapidos para o CEO

### Decisao Estrategica
> "CPO, temos essas opcoes no backlog: [A, B, C]. Me prioriza com ICE score considerando que queremos [objetivo]."

### Validacao Financeira
> "CFO, estou pensando em [acao]. Quanto custa, qual o ROI esperado e em quanto tempo se paga?"

### Conteudo / Copy
> "CMO, preciso de [tipo de conteudo] para [publico] pelo [canal]. Objetivo: [objetivo]."

### Abordagem Comercial
> "Comercial B2B, me crie script para abordar [segmento] em [cidade] por [canal]. Base local: [X] membros."

### Problema com Usuario
> "CS, membro [nome/situacao] esta [problema]. Me da plano de acao com mensagens prontas."

### Problema Tecnico
> "CTO, [erro/problema]. Me da readout com diagnostico e plano de correcao."

### Review Rapido
> "[Agente], me da um readout rapido sobre [topico] com base nos dados atuais."

---

## 5. Regras de Orquestracao

### 5.1 Cadeia de Aprovacao
| Tipo de Decisao | Quem Propoe | Quem Valida | Quem Aprova |
|----------------|-------------|-------------|-------------|
| Nova feature | CPO | CTO + CFO | CEO |
| Campanha de marketing | CMO | CPO + CFO | CEO |
| Novo parceiro | Comercial B2B | — | CEO |
| Mudanca tecnica | CTO | CPO | CEO |
| Premiacao nova | CPO | CFO | CEO |
| Comunicacao em massa | CS ou CMO | — | CEO |
| Bug fix urgente | CTO | — | CTO (autonomia) |

### 5.2 Quando Escalar para o CEO
Agentes devem escalar quando:
- Decisao envolve gasto > R$ [definir threshold]
- Decisao afeta 2+ modulos
- Agentes discordam entre si
- Informacao critica esta faltando (ex: ARPU, churn rate)
- Risco reputacional (comunicacao publica)

### 5.3 Quando Agentes Tem Autonomia
Agentes podem agir sem aprovacao do CEO:
- CTO: bug fixes urgentes em producao
- CS: mensagens de onboarding padrao (templates aprovados)
- Comercial B2B: follow-up usando scripts ja aprovados

---

## 6. Base de Conhecimento (`docs/contexto/`)

Alem dos docs estrategicos, os agentes se alimentam de contexto real do negocio:

```
docs/contexto/
├── brandbook/              # Identidade visual, logos, tom de voz, cores
│   ├── README.md           # Guia completo de marca
│   └── [logos, assets]     # Arquivos visuais
├── metas.md                # OKRs e metas atuais (atualizar mensalmente)
├── dados_financeiros.md    # ARPU, churn, CAC, custos (atualizar mensalmente)
├── concorrentes.md         # Analise de concorrentes da regiao
├── faq_reclamacoes.md      # Perguntas frequentes e reclamacoes recorrentes
└── reunioes/               # Atas de reuniao (1 arquivo por reuniao)
    ├── TEMPLATE.md         # Template padrao
    └── YYYY-MM-DD.md       # Atas por data
```

### O que Alimentar em Cada Agente

| Contexto | CTO | CMO | CPO | CFO | B2B | CS |
|----------|:---:|:---:|:---:|:---:|:---:|:--:|
| `brandbook/` | | ✅ | ✅ | | ✅ | ✅ |
| `metas.md` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `dados_financeiros.md` | | | ✅ | ✅ | | |
| `concorrentes.md` | | ✅ | ✅ | | ✅ | |
| `faq_reclamacoes.md` | ✅ | | ✅ | | | ✅ |
| `reunioes/` (ultima) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 7. Dados que o CEO Deve Alimentar (Resumo)

Para os agentes funcionarem bem, o CEO precisa fornecer periodicamente:

### Dados Criticos (Alimentar Mensalmente)
| Dado | Quem Usa | Onde Conseguir |
|------|----------|---------------|
| ARPU medio | CFO | Hubsoft / financeiro |
| Churn mensal (%) | CFO, CPO, CS | Hubsoft / financeiro |
| Base total de clientes | CMO, Comercial B2B | Hubsoft |
| Base por cidade | Todos | Dashboard > Relatorios > Cidades |
| CAC por canal | CFO, CMO | Financeiro / marketing |
| Custo dos premios | CFO | Compras |
| Metas do mes | Todos | CEO define |

### Dados Automaticos (Ja no Sistema)
| Dado | Onde Ver |
|------|---------|
| Membros cadastrados | Dashboard > Home |
| Taxa de validacao OTP | Dashboard > Home |
| Giros realizados | Dashboard > Home |
| Cupons resgatados | Dashboard Parceiros > Home |
| Indicacoes feitas | Dashboard Indicacoes > Home |
| Parceiros ativos | Dashboard Parceiros > Home |
| Relatorios detalhados | Modulo Relatorios (Roleta, Indicacoes, Parceiros) |

---

## 8. Evolucao: Niveis de Automacao

### Nivel 1 — Atual (Manual + IA Consultiva)
- CEO faz perguntas, agentes respondem
- CEO copia outputs e executa manualmente
- Claude Code implementa sob orientacao do CTO

### Nivel 2 — Proximo (Semi-Automatizado)
- Agentes no n8n com triggers automaticos
- Review mensal automatico (agentes geram readouts sozinhos)
- Alertas de churn automaticos (CS monitora dados + envia alerta)
- Scripts de WhatsApp pre-aprovados disparam automaticamente

### Nivel 3 — Futuro (Orquestrado)
- Orchestrator Agent coordena os outros agentes
- Fluxos multi-agente rodam sem intervencao (ex: CPO prioriza → CTO avalia → CFO valida → CEO so aprova)
- Dashboard do CEO com readouts consolidados de todos os agentes
- Decisoes de rotina delegadas (agente tem autonomia dentro de parametros)

### Nivel 4 — Visao (Autonomo)
- Time de IAs opera o Clube com supervisao minima
- CEO define OKRs trimestrais, agentes executam
- Agentes aprendem com resultados e ajustam estrategia
- Intervencao humana so para decisoes de alto impacto

---

## 9. Proximo Passo Recomendado

Para sair do Nivel 1 (atual) para o Nivel 2:

1. **Definir dados criticos**: ARPU, churn, CAC (alimentar CFO e CMO)
2. **Criar rotina de review mensal**: Rodar cada agente 1x/mes com dados atualizados
3. **Aprovar templates de CS**: Mensagens de onboarding e reativacao padrao
4. **Automatizar alertas de churn**: n8n monitora dados + dispara WhatsApp
5. **Montar pipeline B2B no n8n**: Lead identificado → mensagem automatica → follow-up agendado

---

## 10. Como Iniciar uma Sessao com Agente

### Template para Qualquer Agente
```
1. Abra uma conversa nova
2. Cole o conteudo de docs/agentes/[agente].md como primeira mensagem
3. Cole os documentos de contexto indicados no prompt do agente
4. Faca sua pergunta ou peca o readout

Exemplo:
- Mensagem 1: [conteudo de cto.md]
- Mensagem 2: [conteudo de DOCUMENTACAO.md]
- Mensagem 3: [conteudo de REGRAS_NEGOCIO.md]
- Mensagem 4: "CTO, quero implementar a loja de pontos. Me da um readout com viabilidade tecnica."
```

### Sessao Multi-Agente (Sequencial)
```
1. Comecar com CPO (spec + priorizacao)
2. Pegar output do CPO → alimentar CTO (viabilidade)
3. Pegar output do CTO → alimentar CFO (ROI)
4. Consolidar os 3 → decidir como CEO
```
