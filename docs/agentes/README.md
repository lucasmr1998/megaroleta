# Agentes Estrategicos — Clube Megalink

> Time virtual de IAs organizado em times com ferramentas especializadas.

## Estrutura

```
docs/agentes/
├── README.md                    # Este arquivo
├── OPERACAO.md                  # Como o CEO orquestra o time
├── ARQUITETURA.md               # Arquitetura tecnica dos agentes e tools
│
├── executivo/                   # Time Executivo (decisao estrategica)
│   ├── cto.md                   # CTO — Tecnologia e arquitetura
│   ├── cpo.md                   # CPO — Produto e priorizacao
│   └── cfo.md                   # CFO — Financas e viabilidade
│
├── comercial/                   # Time Comercial (growth e retencao)
│   ├── cmo.md                   # CMO — Marketing e growth
│   ├── pmm.md                   # PMM — Posicionamento, messaging, enablement
│   ├── comercial_b2b.md         # Prospeccao de parceiros
│   └── customer_success.md      # Onboarding e engajamento
│
└── tools/                       # Ferramentas reutilizaveis
    ├── README.md                # Catalogo completo
    ├── analise_dados.md         # Consultar metricas do sistema
    ├── gerador_copy.md          # Gerar copy WhatsApp/redes/impresso
    ├── calculadora_roi.md       # ROI, payback, cenarios financeiros
    ├── auditor_codigo.md        # Code review com checklist
    ├── gerador_spec.md          # Spec de feature com ICE
    └── prospector_parceiro.md   # Abordagem personalizada B2B
```

## Quick Start

1. Leia `OPERACAO.md` — como o time funciona
2. Leia `ARQUITETURA.md` — estrutura tecnica
3. Escolha o agente + tools necessarias
4. Cole prompt + contexto em uma conversa nova

## Qual Agente Usar?

| Preciso de... | Time | Agente | Tools que Usa |
|---------------|------|--------|---------------|
| Implementar feature | Executivo | **CPO** → **CTO** | gerador_spec, auditor_codigo |
| Calcular viabilidade | Executivo | **CFO** | calculadora_roi, analise_dados |
| Campanha de marketing | Comercial | **CMO** | gerador_copy, analise_dados |
| Abordar parceiro | Comercial | **Comercial B2B** | prospector_parceiro, gerador_copy |
| Problema de usuario | Comercial | **CS** | gerador_copy, analise_dados |
| Bug ou problema tecnico | Executivo | **CTO** | auditor_codigo, analise_dados |
| Review mensal | Todos | Cada um | analise_dados |

## Documentos de Contexto

| Documento | Obrigatorio Para |
|-----------|-----------------|
| `docs/ESTRATEGIA.md` | Todos |
| `docs/ROADMAP.md` | CPO, CTO, CMO |
| `docs/DECISOES.md` | CTO, CPO |
| `docs/REGRAS_NEGOCIO.md` | Todos |
| `DOCUMENTACAO.md` | CTO |
| `docs/contexto/brandbook/` | CMO, CS, B2B |
| `docs/contexto/metas.md` | Todos |
| `docs/contexto/dados_financeiros.md` | CFO, CPO |
