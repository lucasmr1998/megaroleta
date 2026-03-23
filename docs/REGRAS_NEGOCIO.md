# Regras de Negocio

> Regras que DEVEM ser respeitadas em qualquer alteracao no sistema. Quebrar essas regras pode causar problemas financeiros, legais ou de experiencia do usuario.

---

## Geral

- **LGPD:** Dados pessoais (CPF, telefone, endereco) nunca devem ser expostos em logs ou respostas de API publica
- **Apenas pessoa fisica:** Somente assinantes pessoa fisica dos planos Megalink Telecom participam do clube
- **Mobile first:** Toda interface do membro deve funcionar bem em celular (maioria dos acessos)
- **Segmentacao por cidade:** Premios, cupons e parceiros sao filtrados por cidade. O membro so ve o que e relevante para sua localidade
- **Triangulo de valor:** Toda feature nova deve gerar valor para pelo menos 2 dos 3 eixos: parceiro B2B, cliente assinante, Megalink

---

## Saldo e Pontos

- **Saldo nunca negativo:** O saldo de pontos de um membro NUNCA pode ficar abaixo de zero
- **Debito atomico:** Toda operacao que debita saldo deve usar `F('saldo') - valor` com `@transaction.atomic` para evitar race conditions
- **XP so cresce:** XP total nunca e decrementado (diferente de saldo, que pode ser gasto)
- **Extrato imutavel:** Registros em `ExtratoPontuacao` sao de auditoria e nunca devem ser editados ou deletados

---

## Roleta

- **Custo antes do giro:** O saldo deve ser verificado ANTES de executar o sorteio
- **Estoque atomico:** Decremento de estoque do premio deve usar `F('quantidade') - 1` com guarda dupla (`WHERE quantidade > 0`)
- **Cidade obrigatoria:** Premio com `cidades_permitidas` so pode ser sorteado para membros da cidade correspondente. Se vazio, vale para todas
- **Limite de giros:** Respeitar `limite_giros_por_membro` e `periodo_limite` configurados
- **Premios com estoque zero:** Premios zerados NAO entram no sorteio

---

## Cupons

- **Aprovacao obrigatoria:** Cupons criados por parceiros nascem com `status_aprovacao='pendente'` e `ativo=False`. So ficam disponiveis apos aprovacao do admin
- **Validacao de resgate:** Antes de resgatar, verificar: saldo (se modalidade pontos), nivel (se modalidade nivel), estoque, limite por membro, cidade, validade
- **Codigo unico:** Cada resgate gera um codigo unico (uuid). Dois resgates nunca compartilham o mesmo codigo
- **Baixa pelo parceiro:** So o parceiro dono do cupom (ou o admin) pode dar baixa. Parceiro X nao ve cupons do parceiro Y
- **Valor da compra opcional:** O parceiro pode informar o valor da compra ao validar, mas nao e obrigatorio

---

## Indicacoes

- **Sem auto-indicacao:** Membro nao pode indicar a si mesmo (verificacao por telefone)
- **Sem duplicata:** O mesmo indicador nao pode indicar o mesmo telefone duas vezes (`unique_together`)
- **Pontos na conversao:** Pontos so sao creditados ao indicador quando o status muda para "convertido" (nao antes)
- **Pontos uma vez:** Flag `pontos_creditados` garante que pontos nao sao dados duas vezes para a mesma indicacao
- **Codigo permanente:** O `codigo_indicacao` do membro nunca muda apos ser gerado

---

## Niveis e Gamificacao

- **Niveis desbloqueiam valor:** Cada nivel (Bronze, Prata, Ouro) deve dar acesso a beneficios progressivos
- **Subir de nivel = comportamento desejado:** Os gatilhos de XP devem sempre incentivar acoes que interessam a Megalink (recorrencia, app, indicacao, adiantado)
- **Custo emocional de saida:** O acumulo de pontos, nivel e cupons deve criar retencao positiva — o cliente perde tudo se cancelar
- **XP nunca reseta:** O progresso do membro e permanente

## Parceiros

- **Parceiro nao e anunciante:** Parceiro e participante do ecossistema. Nao paga por midia, oferece desconto e recebe publico
- **Custo zero para o parceiro:** Nao cobrar mensalidade ou taxa. O modelo e ganha-ganha
- **Isolamento de dados:** Parceiro so ve dados dos seus proprios cupons e resgates
- **Login separado:** Painel do parceiro e completamente independente do admin
- **User vinculado:** Parceiro deve ter um User Django vinculado (OneToOne) para acessar o painel
- **Curadoria Megalink:** Todo cupom de parceiro passa por aprovacao antes de ser disponibilizado

---

## Hubsoft

- **Fonte de verdade para cidade:** A cidade de instalacao consultada via PostgreSQL Hubsoft prevalece sobre qualquer outra fonte
- **Sincronizacao no login:** Pontos extras (recorrencia, adiantado, app) sao sincronizados automaticamente quando o membro valida o OTP
- **Somente leitura:** O sistema NUNCA escreve no banco do Hubsoft. Apenas consultas SELECT

---

## OTP

- **Expiracao 10 minutos:** Codigo OTP expira apos 10 minutos
- **Rate limiting 60 segundos:** Minimo de 60 segundos entre solicitacoes de OTP por sessao
- **6 digitos:** Codigo sempre tem 6 digitos numericos

---

## Seguranca

- **Credenciais em variaveis de ambiente:** Senhas, SECRET_KEY e tokens NUNCA devem estar hardcoded — todas ja migradas para `.env` ✅
- **Logging seguro:** NUNCA usar `print()` ou gravar dados sensiveis em arquivo. Usar `logging.getLogger(__name__)`
- **Sanitizacao obrigatoria:** Markdown renderizado deve passar por `bleach.clean()` (backend) e `DOMPurify.sanitize()` (frontend)
- **Sem csrf_exempt:** NUNCA usar `@csrf_exempt` — templates enviam `X-CSRFToken` nos headers AJAX
- **Cache Hubsoft:** Dados do Hubsoft cacheados via Django cache framework (1 hora). NUNCA usar variaveis estaticas de classe como cache
- **CSRF obrigatorio:** Todos os formularios POST devem incluir `{% csrf_token %}`
- **Login required:** Todas as views do admin exigem `@login_required` + `@user_passes_test(is_staff)`
- **select_for_update:** Operacoes que modificam saldo ou estoque devem usar lock pessimista
