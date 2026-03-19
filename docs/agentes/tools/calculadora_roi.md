# Tool: Calculadora de ROI

## Funcao
Calcular retorno sobre investimento de acoes, features, premiacoes e expansoes.

## Input
Fornecer:
1. **Acao proposta**: O que estamos avaliando
2. **Custo**: Valor estimado (unico ou recorrente)
3. **Premissas**: ARPU, churn, taxa de conversao, etc.
4. **Periodo**: Em quantos meses avaliar

## Output Obrigatorio

```
## Calculadora ROI

### Acao Avaliada
[Descricao da acao]

### Custos
| Item | Tipo | Valor |
|------|------|-------|
| [item] | Unico/Mensal | R$ [valor] |
| **Total mensal** | | **R$ [valor]** |

### Beneficios Estimados
| Beneficio | Premissa | Valor Mensal |
|-----------|----------|-------------|
| Retencao incremental | [X] membros x R$[ARPU] | R$ [valor] |
| Aquisicao organica | [X] indicacoes x R$[CAC economizado] | R$ [valor] |
| [outro] | [premissa] | R$ [valor] |
| **Total mensal** | | **R$ [valor]** |

### ROI
| Cenario | Conversao | ROI | Payback |
|---------|-----------|-----|---------|
| Pessimista | [X]% | [X]:1 | [X] meses |
| Realista | [X]% | [X]:1 | [X] meses |
| Otimista | [X]% | [X]:1 | [X] meses |

### Premissas Criticas
- [Premissa 1]: Se errada, impacto [alto/medio/baixo]
- [Premissa 2]: Se errada, impacto [alto/medio/baixo]

### Veredicto
[Viavel / Condicional / Inviavel] — [justificativa em 1 frase]
```

## Formulas Usadas

```
ROI = (Beneficio Mensal - Custo Mensal) / Custo Mensal
Payback = Custo Total / Beneficio Mensal
LTV = ARPU x Tempo Medio de Permanencia (meses)
CAC Indicacao = Custo dos Pontos Concedidos / Indicacoes Convertidas
Valor do Churn Evitado = Membros Retidos x ARPU x Meses Incrementais
```
