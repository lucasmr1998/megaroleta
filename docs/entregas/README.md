# Entregas dos Agentes — Clube Megalink

> Documentos de trabalho produzidos pelos agentes. Sao referencias permanentes, diferente das sessoes (que sao transcricoes de conversas).

## Diferenca entre Sessoes e Entregas

| | Sessoes | Entregas |
|---|---------|---------|
| **O que e** | Transcricao de conversa | Documento de trabalho final |
| **Exemplo** | "Discutimos X, decidimos Y" | Planejamento, battle card, spec, analise |
| **Vive em** | `docs/contexto/sessoes/` | `docs/entregas/` |
| **Formato nome** | `YYYY-MM-DD_agente_topico.md` | `nome_descritivo.md` |
| **Atualiza?** | Nao (e historico) | Sim (evolui com o negocio) |

## Estrutura

```
docs/entregas/
├── README.md
├── pmm/                    # Entregas do PMM
│   ├── planejamento_produto.md    # Posicionamento, messaging, GTM, battle cards
│   ├── battle_cards.md            # (futuro) Cards isolados para vendedores
│   └── one_pager.md               # (futuro) One-pager do Clube
├── cmo/                    # Entregas do CMO
│   └── estrategia_marketing.md    # (futuro) Plano de marketing detalhado
├── cfo/                    # Entregas do CFO
│   └── analise_roi.md             # (futuro) Analise financeira
├── cpo/                    # Entregas do CPO
│   └── roadmap_priorizado.md      # (futuro) Backlog priorizado com ICE
├── cto/                    # Entregas do CTO
│   └── plano_tecnico.md           # (futuro) Plano de implementacao
├── b2b/                    # Entregas do Comercial B2B
│   └── plano_prospeccao.md        # (futuro) Pipeline por cidade
└── cs/                     # Entregas do Customer Success
    └── plano_onboarding.md        # (futuro) Fluxo de onboarding
```

## Como Funciona

1. Agente produz entrega durante sessao
2. CEO pede: "salve isso como entrega"
3. Arquivo vai para `docs/entregas/[agente]/`
4. Documento pode ser atualizado conforme o negocio evolui
5. Outros agentes consultam as entregas como referencia
