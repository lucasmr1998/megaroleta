# Tool: Gerador de Spec

## Funcao
Gerar especificacao completa de feature pronta para implementacao.

## Input
Fornecer:
1. **Nome da feature**: O que construir
2. **Problema**: O que esta errado ou faltando hoje
3. **Publico**: Quem vai usar (membro, parceiro, admin)
4. **Contexto**: Informacoes relevantes sobre o estado atual

## Output Obrigatorio

```
## Spec: [Nome da Feature]

### Problema
[O que esta errado ou faltando — com dados se possivel]

### Solucao
[Descricao clara do que sera construido]

### User Stories
- Como [persona], quero [acao] para [beneficio]
- Como [persona], quero [acao] para [beneficio]

### Impacto no Triangulo
- Parceiro B2B: [como impacta — positivo/neutro/negativo]
- Cliente Assinante: [como impacta]
- Megalink: [como impacta]
- Score: [1/3, 2/3 ou 3/3 eixos beneficiados]

### Criterios de Aceitacao
- [ ] [Criterio verificavel 1]
- [ ] [Criterio verificavel 2]
- [ ] [Criterio verificavel N]

### Fluxo do Usuario
```
Passo 1: [acao do usuario]
Passo 2: [resposta do sistema]
Passo 3: [acao do usuario]
...
```

### Modelo de Dados (se aplicavel)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| [campo] | [tipo] | [descricao] |

### Endpoints/Views (se aplicavel)
| Rota | Metodo | Descricao |
|------|--------|-----------|
| [rota] | [GET/POST] | [descricao] |

### Fora de Escopo
- [O que NAO faz parte desta feature]
- [O que fica para uma fase futura]

### Metricas de Sucesso
- KPI primario: [metrica + meta]
- KPI secundario: [metrica + meta]
- Prazo para avaliar: [X dias apos lancamento]

### Dependencias
- Tecnicas: [migrations, APIs, libs]
- Negocio: [conteudo, parceiros, dados]

### ICE Score
- Impact: [1-10] — [justificativa]
- Confidence: [1-10] — [justificativa]
- Ease: [1-10] — [justificativa]
- Score: [I x C x E / 10]
```
