# Sessoes com Agentes — Clube Megalink

> Transcricoes de conversas com agentes de IA. Servem como memoria de longo prazo para decisoes, insights e contexto.

## Estrutura

```
docs/contexto/sessoes/
├── README.md                           # Este arquivo
├── 2026-03-19_cmo_estrategia.md        # Exemplo
├── 2026-03-19_pmm_planejamento.md      # Exemplo
└── ...
```

## Convencao de Nomes

```
YYYY-MM-DD_agente_topico.md
```

Exemplos:
- `2026-03-19_cmo_estrategia_marketing.md`
- `2026-03-20_cto_loja_de_pontos.md`
- `2026-03-21_cfo_roi_premiacao.md`
- `2026-03-22_b2b_prospeccao_floriano.md`

## Template de Sessao

Toda sessao salva deve seguir o formato em `TEMPLATE.md`.

## Como Usar em Conversas Futuras

Ao iniciar uma sessao com um agente, voce pode alimentar com sessoes anteriores:

```
"Agente, na sessao de 19/03 discutimos X. [colar resumo da sessao]
Hoje quero continuar a partir de Y."
```

## Quem Consome

| Agente | Sessoes Relevantes |
|--------|-------------------|
| Todos | Sessoes do CEO (decisoes estrategicas) |
| CPO | Sessoes do CMO e PMM (demandas de produto) |
| CTO | Sessoes do CPO (specs e features) |
| CMO | Sessoes do PMM (posicionamento) |
| B2B | Sessoes do PMM (battle cards) e CMO (campanhas) |
| CS | Sessoes do CMO (campanhas) e CPO (features novas) |
