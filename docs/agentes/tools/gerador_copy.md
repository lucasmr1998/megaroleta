# Tool: Gerador de Copy

## Funcao
Gerar textos de comunicacao prontos para usar em diferentes canais.

## Input
Fornecer:
1. **Objetivo**: O que a mensagem deve gerar (cadastro, resgate, indicacao, etc.)
2. **Publico**: Quem recebe (membros Bronze, parceiros novos, inativos, etc.)
3. **Canal**: WhatsApp, Instagram, impresso, email
4. **Tom**: Urgente, casual, informativo, comemorativo
5. **Contexto** (opcional): Dados relevantes (nome do parceiro, desconto, etc.)

## Output Obrigatorio

```
## Copy Gerado

### Contexto
- Objetivo: [objetivo]
- Publico: [publico]
- Canal: [canal]

### Versao A
---
[Mensagem completa pronta para copiar]
---

### Versao B (variante)
---
[Mensagem alternativa]
---

### Regras Aplicadas
- [ ] Max 160 chars na primeira linha (preview WhatsApp)
- [ ] Emoji no inicio
- [ ] CTA claro na ultima linha
- [ ] Tom adequado ao publico
- [ ] Nao promete feature inexistente
- [ ] Nao expoe dados pessoais
```

## Templates por Canal

### WhatsApp
- Primeira linha: emoji + gancho (max 160 chars)
- Corpo: max 3 linhas
- CTA: link ou instrucao clara
- Total: max 300 chars

### Instagram (Post)
- Titulo: 1 linha impactante
- Corpo: 3-5 linhas
- Hashtags: 3-5 relevantes
- CTA: no final

### Instagram (Stories)
- Texto principal: max 2 linhas (fonte grande)
- CTA: swipe up ou "link na bio"

### Material Impresso
- Titulo: grande e direto
- Subtitulo: beneficio principal
- CTA: QR code ou URL curta
