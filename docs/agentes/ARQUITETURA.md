# Arquitetura do Time de IAs — Clube Megalink

> Como os agentes estao organizados, quais ferramentas tem e como se comunicam.

---

## 1. Estrutura de Pastas

```
docs/agentes/
├── README.md                    # Indice e quick start
├── OPERACAO.md                  # Como o CEO orquestra tudo
├── ARQUITETURA.md               # Este arquivo
│
├── executivo/                   # Time Executivo (decisao estrategica)
│   ├── ceo.md                   # CEO — orquestrador, decisor final
│   ├── cto.md                   # CTO — tecnologia e arquitetura
│   ├── cpo.md                   # CPO — produto e priorizacao
│   └── cfo.md                   # CFO — financas e viabilidade
│
├── comercial/                   # Time Comercial (aquisicao e retencao)
│   ├── cmo.md                   # CMO — marketing e growth
│   ├── comercial_b2b.md         # Prospeccao de parceiros
│   └── customer_success.md      # Onboarding, engajamento, churn
│
└── tools/                       # Ferramentas que os agentes usam
    ├── README.md                # Catalogo de tools
    ├── analise_dados.md         # Consultar metricas do sistema
    ├── gerador_copy.md          # Gerar copy para WhatsApp/redes
    ├── calculadora_roi.md       # Calcular ROI de acoes
    ├── auditor_codigo.md        # Revisar codigo e detectar problemas
    ├── gerador_spec.md          # Gerar spec de feature
    └── prospector_parceiro.md   # Gerar abordagem para parceiro
```

---

## 2. Times

### Time Executivo
Decisoes estrategicas que definem o rumo do negocio.

| Agente | Papel | Decide Sobre |
|--------|-------|-------------|
| **CEO** | Orquestrador | Direcao, prioridades, aprovacoes finais |
| **CTO** | Tecnologia | Arquitetura, codigo, seguranca, performance |
| **CPO** | Produto | Roadmap, features, UX, metricas de produto |
| **CFO** | Financas | ROI, viabilidade, pricing, unit economics |

### Time Comercial
Execucao de growth, vendas e sucesso do cliente.

| Agente | Papel | Executa |
|--------|-------|---------|
| **CMO** | Marketing | Campanhas, copy, funil, posicionamento |
| **Comercial B2B** | Vendas | Prospeccao de parceiros, scripts, objecoes |
| **Customer Success** | Retencao | Onboarding, reativacao, churn prevention |

---

## 3. Tools (Ferramentas)

Tools sao prompts especializados que os agentes CHAMAM durante seu trabalho.
A diferenca entre agente e tool:

- **Agente** = tem papel, contexto, personalidade, template de output
- **Tool** = faz UMA coisa especifica e retorna resultado estruturado

### Como Funciona

Quando um agente precisa de algo, ele "chama" a tool:

```
CEO: "CPO, quero lancar a loja de pontos."

CPO (internamente):
  1. Usa [gerador_spec] para escrever a spec
  2. Usa [calculadora_roi] para estimar impacto
  3. Usa [analise_dados] para ver metricas atuais
  4. Gera o CPO Readout com tudo consolidado
```

### Na Pratica (Manual)
1. Abra conversa com o agente (CPO)
2. CPO responde e menciona: "Preciso analisar dados. Usando a tool analise_dados..."
3. CPO incorpora o resultado da tool no readout

### Na Pratica (Automacao)
1. Agente CPO recebe task
2. Chama tool `analise_dados` via API/funcao
3. Chama tool `calculadora_roi` via API/funcao
4. Consolida e retorna readout

---

## 4. Catalogo de Tools

### analise_dados
**Input:** Pergunta sobre metricas do sistema
**Output:** Dados estruturados (tabela/numeros)
**Quem usa:** Todos os agentes
**Fonte:** Dashboards do sistema, relatorios, banco de dados
```
Exemplos:
- "Quantos membros ativos temos em Floriano?"
- "Qual a taxa de conversao OTP nos ultimos 30 dias?"
- "Quantos cupons foram resgatados no ultimo mes?"
```

### gerador_copy
**Input:** Objetivo + publico + canal
**Output:** Mensagens prontas com variantes A/B
**Quem usa:** CMO, CS, Comercial B2B
```
Exemplos:
- "Copy de reativacao para membros inativos 15+ dias via WhatsApp"
- "Post Instagram sobre novo parceiro restaurante"
- "Mensagem de boas-vindas para parceiro recem cadastrado"
```

### calculadora_roi
**Input:** Acao proposta + custos + premissas
**Output:** ROI, payback, cenarios (otimista/realista/pessimista)
**Quem usa:** CFO, CPO, CMO
```
Exemplos:
- "ROI de adicionar Air Fryer como premio (custo R$200, estoque 10)"
- "Viabilidade de lancar em cidade com 200 clientes"
- "Custo-beneficio de campanha de indicacoes com 5 giros de bonus"
```

### auditor_codigo
**Input:** Arquivo ou diff de codigo
**Output:** Checklist de review com OK/Atencao/Problema
**Quem usa:** CTO
```
Exemplos:
- "Revisar a view de resgate de cupom"
- "Verificar se a migration e segura"
- "Checar N+1 queries na dashboard"
```

### gerador_spec
**Input:** Descricao da feature + contexto
**Output:** Spec completa (problema, solucao, user stories, criterios, metricas)
**Quem usa:** CPO, CTO
```
Exemplos:
- "Spec para loja de pontos"
- "Spec para notificacoes de nivel"
- "Spec para QR code na carteirinha"
```

### prospector_parceiro
**Input:** Segmento + cidade + dados da base
**Output:** Lista de prospectos + scripts personalizados
**Quem usa:** Comercial B2B
```
Exemplos:
- "Prospectar restaurantes em Floriano (base: 229 membros)"
- "Script para academias em Teresina"
- "Follow-up para parceiro que nao respondeu"
```

---

## 5. Comunicacao Entre Agentes

### Padrao de Handoff
Quando um agente precisa de outro, o CEO faz o handoff:

```
[CEO] → [CPO]: "Spec para feature X"
[CPO] → [CEO]: CPO Readout com spec + ICE
[CEO] → [CTO]: "CPO aprovou, viabilidade tecnica?"
[CTO] → [CEO]: CTO Readout com plano
[CEO] → [CFO]: "CTO ok, ROI?"
[CFO] → [CEO]: CFO Readout com numeros
[CEO] → Decisao final
```

### Padrao de Cadeia (sem CEO no meio)
Para fluxos rotineiros, agentes podem referenciar outputs anteriores:

```
"CTO, o CPO fez esta spec: [colar spec]. Me da viabilidade tecnica."
"CFO, o CTO estimou 8h de dev. Me da o ROI considerando [premissas]."
```

---

## 6. Evolucao Futura

### Fase 1 — Atual
- Agentes como prompts manuais
- Tools como instrucoes embutidas no agente
- CEO faz handoff manual

### Fase 2 — Tools Separadas
- Cada tool e um prompt independente
- Agente chama tool explicitamente
- Resultado da tool e incorporado ao readout

### Fase 3 — Automacao (n8n/CrewAI)
- Agentes como nodes no n8n
- Tools como funcoes chamadas via API
- Fluxos automaticos (CPO → CTO → CFO sem CEO no meio)
- Estado persistido entre execucoes

### Fase 4 — Agentes Autonomos
- Agentes monitoram metricas e agem proativamente
- CS detecta churn e envia mensagem sem pedir
- CFO alerta quando custo de premio ultrapassa threshold
- CMO lanca campanha quando engajamento cai
