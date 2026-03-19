import os
import glob
from openai import OpenAI
from django.conf import settings


def get_client():
    """Retorna cliente OpenAI configurado."""
    api_key = os.environ.get('OPENAI_API_KEY', getattr(settings, 'OPENAI_API_KEY', ''))
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


DOCS_BASE = os.path.join(settings.BASE_DIR, 'docs')


def carregar_prompt_agente(agente_id):
    """Carrega o prompt do agente a partir do arquivo .md."""
    AGENTES_MAP = {
        'cto': 'docs/agentes/executivo/cto.md',
        'cpo': 'docs/agentes/executivo/cpo.md',
        'cfo': 'docs/agentes/executivo/cfo.md',
        'cmo': 'docs/agentes/comercial/cmo.md',
        'pmm': 'docs/agentes/comercial/pmm.md',
        'b2b': 'docs/agentes/comercial/comercial_b2b.md',
        'cs': 'docs/agentes/comercial/customer_success.md',
    }

    caminho = AGENTES_MAP.get(agente_id)
    if not caminho:
        return None

    filepath = os.path.join(settings.BASE_DIR, caminho)
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def _ler_arquivo(caminho, max_chars=None):
    """Le um arquivo com limite de caracteres."""
    if not os.path.exists(caminho):
        return ""
    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    if max_chars and len(conteudo) > max_chars:
        conteudo = conteudo[:max_chars] + "\n\n[... truncado por limite de tamanho ...]"
    return conteudo


def carregar_contexto_completo():
    """Carrega todo o contexto disponivel: docs estrategicos, entregas, sessoes, projetos."""

    contexto = ""

    # 1. Documentos estrategicos (sempre incluir)
    docs_estrategicos = [
        'docs/ESTRATEGIA.md',
        'docs/ROADMAP.md',
        'docs/REGRAS_NEGOCIO.md',
        'docs/DECISOES.md',
    ]
    for doc in docs_estrategicos:
        filepath = os.path.join(settings.BASE_DIR, doc)
        conteudo = _ler_arquivo(filepath, max_chars=8000)
        if conteudo:
            contexto += f"\n\n{'='*60}\n📄 {doc}\n{'='*60}\n\n{conteudo}"

    # 2. Entregas dos agentes (todas)
    pasta_entregas = os.path.join(DOCS_BASE, 'entregas')
    if os.path.exists(pasta_entregas):
        for agente_dir in sorted(os.listdir(pasta_entregas)):
            pasta_agente = os.path.join(pasta_entregas, agente_dir)
            if os.path.isdir(pasta_agente):
                for f in sorted(os.listdir(pasta_agente)):
                    if f.endswith('.md') and f != 'README.md':
                        filepath = os.path.join(pasta_agente, f)
                        conteudo = _ler_arquivo(filepath, max_chars=6000)
                        if conteudo:
                            contexto += f"\n\n{'='*60}\n📦 Entrega {agente_dir.upper()}: {f}\n{'='*60}\n\n{conteudo}"

    # 3. Sessoes recentes (ultimas 5)
    pasta_sessoes = os.path.join(DOCS_BASE, 'contexto', 'sessoes')
    if os.path.exists(pasta_sessoes):
        sessoes = sorted(
            [f for f in os.listdir(pasta_sessoes) if f.endswith('.md') and f not in ('README.md', 'TEMPLATE.md')],
            reverse=True
        )[:5]
        for f in sessoes:
            filepath = os.path.join(pasta_sessoes, f)
            conteudo = _ler_arquivo(filepath, max_chars=4000)
            if conteudo:
                contexto += f"\n\n{'='*60}\n💬 Sessao: {f}\n{'='*60}\n\n{conteudo}"

    # 4. Contexto do negocio (brandbook, metas, financeiro)
    docs_contexto = [
        'docs/contexto/brandbook/README.md',
        'docs/contexto/metas.md',
        'docs/contexto/dados_financeiros.md',
        'docs/contexto/concorrentes.md',
        'docs/contexto/faq_reclamacoes.md',
    ]
    for doc in docs_contexto:
        filepath = os.path.join(settings.BASE_DIR, doc)
        conteudo = _ler_arquivo(filepath, max_chars=3000)
        if conteudo:
            contexto += f"\n\n{'='*60}\n📋 {doc}\n{'='*60}\n\n{conteudo}"

    # 5. Projetos e tarefas (do banco de dados)
    try:
        from gestao.models import Projeto, Tarefa
        projetos = Projeto.objects.filter(ativo=True).prefetch_related('tarefas', 'etapas')
        if projetos:
            contexto += f"\n\n{'='*60}\n📊 PROJETOS ATIVOS (do sistema)\n{'='*60}\n\n"
            for p in projetos:
                tarefas = p.tarefas.all()
                total = tarefas.count()
                concluidas = tarefas.filter(status='concluida').count()
                pendentes = tarefas.filter(status='pendente').count()
                andamento = tarefas.filter(status='em_andamento').count()
                bloqueadas = tarefas.filter(status='bloqueada').count()

                contexto += f"### Projeto: {p.nome}\n"
                contexto += f"- Responsavel: {p.responsavel}\n"
                contexto += f"- Progresso: {concluidas}/{total} tarefas ({p.progresso}%)\n"
                contexto += f"- Pendentes: {pendentes} | Em andamento: {andamento} | Bloqueadas: {bloqueadas}\n"
                if p.descricao:
                    contexto += f"- Descricao: {p.descricao}\n"

                # Tarefas pendentes e em andamento (as mais relevantes)
                tarefas_ativas = tarefas.filter(status__in=['pendente', 'em_andamento', 'bloqueada']).order_by('prioridade', 'data_limite')
                if tarefas_ativas:
                    contexto += "\nTarefas ativas:\n"
                    for t in tarefas_ativas:
                        etapa_nome = t.etapa.nome if t.etapa else "Sem etapa"
                        prazo = t.data_limite.strftime('%d/%m') if t.data_limite else "Sem prazo"
                        contexto += f"  - [{t.get_status_display()}] [{t.get_prioridade_display()}] {t.titulo} | {t.responsavel} | {etapa_nome} | Prazo: {prazo}\n"
                contexto += "\n"
    except Exception:
        pass

    # 6. Dados do sistema (metricas reais)
    try:
        from roleta.models import MembroClube, ParticipanteRoleta
        from parceiros.models import Parceiro, CupomDesconto, ResgateCupom
        from indicacoes.models import Indicacao

        total_membros = MembroClube.objects.count()
        membros_validados = MembroClube.objects.filter(validado=True).count()
        total_giros = ParticipanteRoleta.objects.count()
        total_parceiros = Parceiro.objects.filter(ativo=True).count()
        total_cupons = CupomDesconto.objects.filter(ativo=True, status_aprovacao='aprovado').count()
        total_resgates = ResgateCupom.objects.count()
        total_indicacoes = Indicacao.objects.count()
        ind_convertidas = Indicacao.objects.filter(status='convertido').count()

        # Membros por cidade (top 5)
        from django.db.models import Count
        cidades = MembroClube.objects.exclude(cidade__isnull=True).exclude(cidade='').values('cidade').annotate(total=Count('id')).order_by('-total')[:5]

        contexto += f"\n\n{'='*60}\n📈 METRICAS REAIS DO SISTEMA (tempo real)\n{'='*60}\n\n"
        contexto += f"- Total de membros no Clube: {total_membros}\n"
        contexto += f"- Membros validados (OTP): {membros_validados}\n"
        contexto += f"- Total de giros realizados: {total_giros}\n"
        contexto += f"- Parceiros ativos: {total_parceiros}\n"
        contexto += f"- Cupons ativos: {total_cupons}\n"
        contexto += f"- Cupons resgatados: {total_resgates}\n"
        contexto += f"- Indicacoes totais: {total_indicacoes}\n"
        contexto += f"- Indicacoes convertidas: {ind_convertidas}\n"
        contexto += f"\nMembros por cidade (top 5):\n"
        for c in cidades:
            contexto += f"  - {c['cidade']}: {c['total']} membros\n"
    except Exception:
        pass

    return contexto


AGENTES_INFO = [
    {'id': 'cto', 'nome': 'CTO', 'descricao': 'Tecnologia e Arquitetura', 'icone': 'fas fa-code', 'cor': '#3b82f6', 'time': 'Executivo'},
    {'id': 'cpo', 'nome': 'CPO', 'descricao': 'Produto e Priorização', 'icone': 'fas fa-cube', 'cor': '#8b5cf6', 'time': 'Executivo'},
    {'id': 'cfo', 'nome': 'CFO', 'descricao': 'Finanças e ROI', 'icone': 'fas fa-chart-pie', 'cor': '#10b981', 'time': 'Executivo'},
    {'id': 'cmo', 'nome': 'CMO', 'descricao': 'Marketing e Growth', 'icone': 'fas fa-bullhorn', 'cor': '#f59e0b', 'time': 'Comercial'},
    {'id': 'pmm', 'nome': 'PMM', 'descricao': 'Posicionamento e Messaging', 'icone': 'fas fa-bullseye', 'cor': '#ec4899', 'time': 'Comercial'},
    {'id': 'b2b', 'nome': 'Comercial B2B', 'descricao': 'Prospecção de Parceiros', 'icone': 'fas fa-handshake', 'cor': '#6366f1', 'time': 'Comercial'},
    {'id': 'cs', 'nome': 'Customer Success', 'descricao': 'Onboarding e Retenção', 'icone': 'fas fa-heart', 'cor': '#ef4444', 'time': 'Comercial'},
]


def chat_agente(agente_id, mensagem, historico=None):
    """Envia mensagem para um agente e retorna resposta."""
    client = get_client()
    if not client:
        return "Erro: API key não configurada. Defina OPENAI_API_KEY nas variáveis de ambiente."

    prompt = carregar_prompt_agente(agente_id)
    if not prompt:
        return f"Erro: Agente '{agente_id}' não encontrado."

    contexto = carregar_contexto_completo()

    system_message = prompt + "\n\n" + "="*60 + "\nCONTEXTO COMPLETO DO NEGOCIO (use para embasar suas respostas)\n" + "="*60 + "\n" + contexto

    # Instrucoes adicionais
    system_message += "\n\n--- INSTRUCOES ADICIONAIS ---\n"
    system_message += """- Sempre responda em portugues brasileiro.
- Use os dados reais do sistema quando disponíveis.

REGRA CRITICA DE COMUNICACAO:
- Voce esta numa CONVERSA, nao numa apresentacao. Responda como um colega de trabalho.
- Perguntas casuais ("como esta?", "e ai?", "o que acha?", "review") = resposta CURTA (3-8 frases). SEM template, SEM readout, SEM headings ##.
- Perguntas rapidas ("quantos parceiros?", "qual o status?") = responda DIRETO em 1-3 frases.
- Pedido de acao ("crie tarefa", "salve isso") = execute e confirme em 1 frase.
- SOMENTE use readout completo com template quando o CEO pedir EXPLICITAMENTE ("me da um readout", "faz uma analise completa", "preciso de um plano detalhado").
- Na duvida, seja BREVE. O CEO pode pedir para aprofundar.
- Nao repita informacoes que o CEO ja sabe. Seja direto.

REGRA CRITICA DE IDENTIDADE:
- Voce e UM agente. Fale SOMENTE sobre SUA area.
- NUNCA fale pelos outros agentes. NUNCA inclua secoes como "### CTO:", "### CMO:" na sua resposta.
- Se o CEO perguntar algo que nao e da sua area, diga "isso e com o [agente X], posso falar sobre [sua area]".
- Cada agente fala por si. O CEO usa os botoes para pedir para outros agentes responderem.
"""

    # Acoes disponiveis
    system_message += "\n\n--- ACOES QUE VOCE PODE EXECUTAR ---\n"
    system_message += """
Voce pode executar acoes no sistema incluindo blocos especiais na sua resposta.
Use essas acoes quando o CEO pedir para salvar algo, criar tarefa ou atualizar status.

1. SALVAR ENTREGA (criar/atualizar documento):
---SALVAR_ENTREGA---
agente: """ + agente_id + """
arquivo: nome_do_arquivo.md
conteudo:
# Titulo do Documento
(conteudo markdown completo aqui)
---FIM_ENTREGA---

2. SALVAR SESSAO (registrar conversa):
---SALVAR_SESSAO---
arquivo: """ + f"{__import__('datetime').date.today().isoformat()}_{agente_id}_topico.md" + """
conteudo:
# Sessao: ...
(conteudo da sessao)
---FIM_SESSAO---

3. CRIAR TAREFA:
---CRIAR_TAREFA---
projeto: Nome do Projeto
titulo: Descricao da tarefa
responsavel: Quem faz
prioridade: critica/alta/media/baixa
---FIM_TAREFA---

4. ATUALIZAR TAREFA:
---ATUALIZAR_TAREFA---
titulo: Texto parcial do titulo da tarefa
status: pendente/em_andamento/concluida/bloqueada
---FIM_TAREFA---

5. CONSULTAR OUTRO AGENTE (pedir opiniao/validacao):
---CONSULTAR_AGENTE---
agente: cto
pergunta: (sua pergunta para o outro agente)
---FIM_CONSULTA---

Agentes disponiveis para consulta: cto, cpo, cfo, cmo, pmm, b2b, cs

IMPORTANTE:
- Use essas acoes apenas quando o CEO pedir explicitamente ("salve isso", "crie uma tarefa", "atualize o status", "consulte o CTO")
- OU quando voce precisa da opiniao de outro agente para completar sua resposta
- OU quando seu readout gerar um documento que deve ser persistido (planejamento, analise, spec)
- Sempre inclua a acao DENTRO da sua resposta normal, o sistema processa automaticamente
- O CEO vera uma confirmacao "✅ ..." ou a resposta do agente consultado no lugar do bloco
- Use a consulta com moderacao (maximo 1-2 por resposta) para nao demorar demais
"""

    messages = [{"role": "system", "content": system_message}]

    # Adicionar historico
    if historico:
        for msg in historico:
            messages.append({"role": msg['role'], "content": msg['content']})

    messages.append({"role": "user", "content": mensagem})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=4000,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erro na API: {str(e)}"


def moderador_decidir(mensagem, agentes_disponiveis, historico_reuniao=None):
    """
    Moderador DETERMINISTICO — sem IA, sem erro, sem custo.
    Analisa palavras-chave na mensagem e retorna lista com 1 agente.
    """
    msg = mensagem.lower().strip()

    # Regra 1: CEO mencionou agente pelo nome → só esse agente
    mencoes_diretas = {
        'cto': 'cto',
        'cpo': 'cpo',
        'cfo': 'cfo',
        'cmo': 'cmo',
        'pmm': 'pmm',
        'comercial': 'b2b',
        'b2b': 'b2b',
        'customer success': 'cs',
        'customer': 'cs',
        'success': 'cs',
    }
    for termo, agente_id in mencoes_diretas.items():
        if termo in msg and agente_id in agentes_disponiveis:
            return [agente_id]

    # Regra 2: Palavras-chave por tema → agente dono do tema
    temas = [
        (['go-to-market', 'gtm', 'posicionamento', 'messaging', 'battle card', 'one-pager'], 'pmm'),
        (['marketing', 'campanha', 'copy', 'growth', 'instagram', 'post'], 'cmo'),
        (['parceiro', 'prospeccao', 'abordagem', 'script', 'objecao'], 'b2b'),
        (['tecnologia', 'codigo', 'bug', 'performance', 'sistema', 'deploy', 'servidor'], 'cto'),
        (['financeiro', 'roi', 'custo', 'preco', 'investimento', 'payback', 'arpu', 'churn'], 'cfo'),
        (['onboarding', 'engajamento', 'reativacao', 'whatsapp', 'mensagem'], 'cs'),
        (['feature', 'roadmap', 'produto', 'priorizacao', 'backlog', 'spec'], 'cpo'),
    ]
    for palavras, agente_id in temas:
        for palavra in palavras:
            if palavra in msg and agente_id in agentes_disponiveis:
                return [agente_id]

    # Regra 3: CEO quer ouvir todos
    todos_keywords = ['todos', 'todo mundo', 'cada um', 'pessoal', 'equipe toda']
    for kw in todos_keywords:
        if kw in msg:
            return agentes_disponiveis[:3]  # maximo 3

    # Regra 4: Fallback → CPO (dono do roadmap/projeto)
    if 'cpo' in agentes_disponiveis:
        return ['cpo']

    return agentes_disponiveis[:1]


def reuniao_agentes(mensagem, agentes_ids=None):
    """Envia pergunta para multiplos agentes e coleta respostas."""
    if not agentes_ids:
        agentes_ids = [a['id'] for a in AGENTES_INFO]

    respostas = []
    for agente_id in agentes_ids:
        info = next((a for a in AGENTES_INFO if a['id'] == agente_id), None)
        if info:
            resposta = chat_agente(agente_id, mensagem)
            respostas.append({
                'agente': info,
                'resposta': resposta,
            })

    return respostas
