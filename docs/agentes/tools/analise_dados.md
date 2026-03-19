# Tool: Analise de Dados

## Funcao
Consultar metricas do Clube Megalink e gerar insights acionaveis.

## Input
Fornecer:
1. **Pergunta**: O que quer saber (ex: "Quantos membros ativos em Floriano?")
2. **Periodo**: Ultimos 7/15/30/90 dias ou total
3. **Segmento** (opcional): Cidade, nivel, parceiro especifico

## Fontes de Dados
- Dashboard Admin: `/roleta/dashboard/` (KPIs gerais)
- Relatorio Roleta: `/roleta/dashboard/relatorios/` (funil, evolucao, cidades, premios)
- Relatorio Indicacoes: `/roleta/dashboard/relatorios/indicacoes/` (embaixadores, conversao)
- Relatorio Parceiros: `/roleta/dashboard/relatorios/parceiros/` (resgates, cupons top)
- Dashboard Parceiros: `/roleta/dashboard/parceiros/` (KPIs parceiros)
- Dashboard Indicacoes: `/roleta/dashboard/indicacoes/` (KPIs indicacoes)

## Output Obrigatorio

```
## Analise de Dados

### Pergunta
[A pergunta original]

### Dados
| Metrica | Valor | Periodo | Fonte |
|---------|-------|---------|-------|
| [metrica] | [valor] | [periodo] | [dashboard/relatorio] |

### Tendencia
- [Subindo/Descendo/Estavel] comparado com periodo anterior
- Variacao: [X]%

### Insight
- [1 insight principal baseado nos dados]

### Acao Sugerida
- [1 acao concreta baseada no insight]
```

## Metricas Disponiveis

### Roleta
- Membros cadastrados (total, por cidade)
- Validacoes OTP (total, taxa)
- Giros realizados (total, media por membro)
- Premios distribuidos (por tipo, por cidade)
- Funil: cadastro → validacao → giro → premio

### Indicacoes
- Total de indicacoes
- Taxa de conversao (pendente → convertido)
- Top embaixadores
- Indicacoes por cidade

### Parceiros
- Parceiros ativos
- Cupons ativos / resgatados / utilizados
- Valor em compras
- Resgates por parceiro

### Membros
- Distribuicao por nivel (Bronze/Prata/Ouro)
- Engajamento (giros nos ultimos 7/30 dias)
- Saldo medio
- XP medio
