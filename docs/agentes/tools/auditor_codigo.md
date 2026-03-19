# Tool: Auditor de Codigo

## Funcao
Revisar codigo do projeto Clube Megalink usando checklist padronizado.

## Input
Fornecer:
1. **Codigo**: Arquivo, diff ou trecho a revisar
2. **Contexto**: O que o codigo deveria fazer
3. **Tipo**: Feature nova, bug fix, refatoracao, migration

## Output Obrigatorio

```
## Auditoria de Codigo

### Arquivo(s) Revisado(s)
[Lista de arquivos]

### Checklist

#### Correcao
- [✅/⚠️/❌] Edge cases (nulls, vazios, dados faltantes)
- [✅/⚠️/❌] Concorrencia (race conditions em saldo/estoque)
- [✅/⚠️/❌] Tratamento de erro
- [✅/⚠️/❌] Validacao de input

#### Seguranca
- [✅/⚠️/❌] Autorizacao (admin vs parceiro vs membro)
- [✅/⚠️/❌] Sem injecao (SQL, XSS)
- [✅/⚠️/❌] Credenciais nao expostas
- [✅/⚠️/❌] PII nao logada (LGPD)
- [✅/⚠️/❌] Isolamento de dados entre parceiros

#### Integridade de Dados
- [✅/⚠️/❌] @transaction.atomic em operacoes criticas
- [✅/⚠️/❌] F() expressions para updates atomicos
- [✅/⚠️/❌] select_for_update() para locks
- [✅/⚠️/❌] Migrations presentes se schema mudou

#### Performance
- [✅/⚠️/❌] Sem N+1 queries
- [✅/⚠️/❌] Paginacao em listagens
- [✅/⚠️/❌] select_related/prefetch_related
- [✅/⚠️/❌] Timeout em consultas externas (Hubsoft)

#### Produto
- [✅/⚠️/❌] Campos do formulario salvos na view
- [✅/⚠️/❌] Segmentacao por cidade respeitada
- [✅/⚠️/❌] Mobile-first
- [✅/⚠️/❌] Sem regressao

### Problemas Encontrados
| # | Severidade | Descricao | Arquivo:Linha | Sugestao |
|---|-----------|-----------|---------------|----------|
| 1 | [Alta/Media/Baixa] | [problema] | [arquivo:linha] | [como corrigir] |

### Veredicto
[Aprovado / Aprovado com ressalvas / Requer correcoes]
```
