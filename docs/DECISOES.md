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

## D009 — App Gestao Separado

**Data:** Marco/2026
**Contexto:** CEO precisa de visao executiva (projetos, tarefas, metricas) e sala para conversar com agentes IA.
**Decisao:** Criar app `gestao` separado com models proprios (Projeto, Tarefa, Reuniao, Mensagem).
**Alternativas:** Usar ferramenta externa (Trello, Notion) ou integrar no app roleta.
**Motivo:** Manter tudo dentro do sistema permite que agentes IA acessem dados de projetos/tarefas e que o CEO tenha visao unificada sem sair do dashboard.

---

## D010 — Moderador Inteligente nas Reunioes

**Data:** Marco/2026
**Contexto:** Nas reunioes com todos os agentes, o CEO falava algo especifico de comercial e todos respondiam, inclusive CTO e CFO que nao tinham relevancia.
**Decisao:** Criar moderador (chamada leve ao GPT) que analisa a mensagem do CEO e decide quais agentes devem responder.
**Alternativas:** Sempre todos respondem (barulhento), CEO seleciona manualmente quem responde (trabalhoso).
**Motivo:** Simula uma reuniao real onde o moderador direciona a conversa. Economiza tokens e tempo.

---

## D011 — Reunioes Persistentes no Banco

**Data:** Marco/2026
**Contexto:** Historico da reuniao era perdido ao recarregar a pagina (estava na sessao Django).
**Decisao:** Criar models Reuniao + MensagemReuniao no banco. Cada reuniao tem nome, descricao e participantes. Mensagens salvas automaticamente.
**Alternativas:** Manter na sessao (simples mas volatil), salvar como arquivo .md (nao permite continuar conversa).
**Motivo:** Permite continuar reunioes, revisitar historico e ter contexto acumulado para os agentes.

---

## D012 — Carteirinha Renderizada via CSS

**Data:** Marco/2026
**Contexto:** Inicialmente carteirinha dependia de imagem de fundo. CEO pediu modelo estilo Urbis (renderizado pelo sistema).
**Decisao:** Dois modos: cores/gradiente (CSS puro com circulos decorativos) ou imagem de fundo. Admin escolhe.
**Alternativas:** Apenas imagem (limitado), apenas CSS (sem flexibilidade de design complexo).
**Motivo:** CSS puro permite criar infinitos modelos sem designer. Imagem como opcao para casos especiais.

---

## D013 — Credenciais Migradas para .env

**Data:** Marco/2026
**Contexto:** Credenciais do banco principal, Hubsoft e OpenAI estavam hardcoded no settings.py e hubsoft_service.py, expostas no git.
**Decisao:** Migrar todas as credenciais para `.env` via `python-dotenv`. Criar helper `_get_hubsoft_connection()` centralizado. DEBUG e ALLOWED_HOSTS também via `.env`.
**Alternativas:** Manter hardcoded (inseguro), usar Django-environ (dependência extra).
**Motivo:** Segurança básica — credenciais nunca devem estar no código-fonte. python-dotenv já era dependência do projeto.

---

## D014 — select_for_update + F() em Operações Financeiras

**Data:** Marco/2026
**Contexto:** `atribuir_pontos()` e `validar_cupom()` tinham race conditions — requests concorrentes podiam duplicar pontos ou usar cupom duas vezes.
**Decisao:** Implementar `select_for_update()` para lock pessimista + `F()` expressions para updates atômicos. Todas as views de escrita receberam `@transaction.atomic`.
**Alternativas:** Usar `SERIALIZABLE` isolation level (impacto global), usar filas/Celery (complexo demais para o volume atual).
**Motivo:** Proteção pontual onde necessário, sem impactar performance das leituras.

---

## D015 — Sanitização de Markdown (bleach + DOMPurify)

**Data:** Marco/2026
**Contexto:** Documentos renderizados via `markdown.markdown()` + `|safe` no template e `marked.parse()` + `innerHTML` no JS permitiam XSS.
**Decisao:** Backend: sanitizar HTML com `bleach.clean()` (whitelist de tags). Frontend: envolver todo `marked.parse()` com `DOMPurify.sanitize()`.
**Alternativas:** Escapar todo HTML (perde formatação), usar iframe sandbox (complexo).
**Motivo:** Abordagem em camadas — sanitiza em ambos os lados. Tags de formatação permitidas, scripts bloqueados.

---

## D016 — Django Cache Framework para Dados Hubsoft

**Data:** Marco/2026
**Contexto:** Cache de clientes por cidade era variável estática na classe (`_cache_clientes_cidade`), não funcionava com múltiplos workers do Gunicorn.
**Decisao:** Migrar para `django.core.cache` (default LocMemCache, upgrade futuro para Redis). Cache de 1 hora.
**Alternativas:** Redis direto (overkill para agora), cache no banco (lento).
**Motivo:** Django cache framework é padrão, funciona com qualquer backend, e a migração para Redis no futuro é transparente.

---

## D017 — Eliminação de N+1 com Annotate em Dict

**Data:** Marco/2026
**Contexto:** Views de missões, cupons e indicações faziam N queries dentro de loops (1 query por regra/cupom/indicação).
**Decisao:** Padrão `dict(QuerySet.values_list(...).annotate(...).values_list(...))` para buscar contadores em 1 query e consultar via dict.get().
**Alternativas:** prefetch_related (não resolve contadores), Subquery (mais verboso).
**Motivo:** Reduz queries de N+1 para 2 (1 lista + 1 contadores). Simples e legível.

---

## D018 — Logging Estruturado (sem print)

**Data:** Marco/2026
**Contexto:** Erros eram logados via `print()` (invisível em produção com Gunicorn) e `open('roleta_debug.log')` (gravava CPF/telefone em arquivo no disco).
**Decisao:** Substituir todos os `print()` por `logging.getLogger(__name__).warning()`. Remover todos os `open('debug.log')`. Configurar loggers por app no settings.
**Alternativas:** Sentry (custo), ELK stack (complexo demais para o momento).
**Motivo:** logging stdlib é suficiente, integra com Gunicorn/systemd, sem exposição de dados sensíveis.
