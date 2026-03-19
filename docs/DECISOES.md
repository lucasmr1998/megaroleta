# Registro de Decisoes

> Decisoes arquiteturais e de produto tomadas ao longo do projeto. Cada decisao inclui contexto, alternativas e motivo da escolha.

---

## D001 — Separacao em 3 Apps Django

**Data:** Marco/2026
**Contexto:** O projeto comecou como um app unico (`roleta`). Com a adicao de parceiros/cupons e indicacoes, ficou grande demais.
**Decisao:** Separar em 3 apps independentes: `roleta`, `parceiros`, `indicacoes`.
**Alternativas:** Manter tudo no app `roleta` (mais simples, mas menos organizado).
**Motivo:** Cada dominio tem models, views e templates proprios. Facilita manutencao, testes e futuras migracoes.

---

## D002 — Cupons com 3 Modalidades

**Data:** Marco/2026
**Contexto:** Inicialmente cupons seriam pagos em pontos. O usuario pediu flexibilidade.
**Decisao:** 3 modalidades: gratuito, custo em pontos, bonus de nivel.
**Alternativas:** Apenas custo em pontos (mais simples).
**Motivo:** Permite estrategias diferentes — cupons gratuitos atraem, pagos incentivam acumulo, por nivel incentivam engajamento.

---

## D003 — Indicacao via URL Publica (nao API)

**Data:** Marco/2026
**Contexto:** Membro precisa indicar amigos que NAO sao clientes ainda (nao tem login no sistema).
**Decisao:** Cada membro tem uma URL publica (`/indicar/<codigo>/`) com formulario simples.
**Alternativas:** API + formulario no front-end da roleta (mais complexo, exigiria que o indicado acessasse a roleta).
**Motivo:** O indicado so precisa preencher nome e telefone. Sem fricao. Link compartilhavel via WhatsApp.

---

## D004 — Painel do Parceiro Separado do Admin

**Data:** Marco/2026
**Contexto:** Parceiros precisam validar cupons e ver seus dados, mas nao devem acessar o admin.
**Decisao:** Painel proprio em `/parceiro/` com login Django (User vinculado ao Parceiro via OneToOne).
**Alternativas:** Usar o Django Admin com permissoes restritas (menos controle sobre UX).
**Motivo:** UX dedicada para o parceiro, sem risco de acesso a dados de outros modulos. Parceiro so ve seus proprios cupons/resgates.

---

## D005 — Fluxo de Aprovacao de Cupons

**Data:** Marco/2026
**Contexto:** Parceiros solicitam cupons mas a Megalink precisa aprovar antes de disponibilizar.
**Decisao:** Campo `status_aprovacao` no CupomDesconto (pendente/aprovado/rejeitado). Cupom criado pelo parceiro nasce como `pendente` + `ativo=False`.
**Alternativas:** Parceiro nao cria cupons (so o admin). Mais seguro mas menos autonomia.
**Motivo:** Equilibrio entre autonomia do parceiro e controle da Megalink.

---

## D006 — Area do Membro como Hub com Cards

**Data:** Marco/2026
**Contexto:** Inicialmente o membro logava e ia direto pra roleta. Com cupons, indicacoes e perfil, ficou apertado.
**Decisao:** Apos login, membro vai para um hub (`/membro/`) com cards: Roleta, Cupons, Indicar, Perfil, Missoes. Cada um abre pagina dedicada.
**Alternativas:** Abas no painel da roleta (tentado antes, ruim em mobile). Tela unica com scroll (poluido).
**Motivo:** Cards grandes sao otimos em mobile, cada pagina carrega so o que precisa (performance), e e facil adicionar novos cards futuros (ex: Loja).

---

## D007 — Topbar de Modulos no Admin

**Data:** Marco/2026
**Contexto:** Sidebar ficou longa demais com todos os modulos (Roleta + Parceiros + Indicacoes + Operacao + Suporte).
**Decisao:** Topbar horizontal com modulos e sidebar lateral que muda conforme o modulo selecionado.
**Alternativas:** Sidebar unica com secoes (ficava muito longa). Menu hamburger (esconde demais).
**Motivo:** Padrao usado em ferramentas SaaS modernas. Cada modulo tem seu proprio "mini-sidebar" com paginas relevantes.

---

## D008 — Loja como App Separado (futuro)

**Data:** Marco/2026
**Contexto:** A pagina de cupons do membro deveria virar uma "loja" com cupons, brindes e futuros produtos.
**Decisao:** Criar app `loja` separado do `parceiros`. O app `parceiros` cuida da gestao de parceiros; a `loja` cuida da vitrine do membro.
**Alternativas:** Expandir o app `parceiros` (mistura responsabilidades).
**Motivo:** Separacao de responsabilidades. A loja e voltada para o membro; parceiros e voltado para gestao B2B.

---

## Template para Novas Decisoes

```
## DXXX — Titulo

**Data:**
**Contexto:**
**Decisao:**
**Alternativas:**
**Motivo:**
```
