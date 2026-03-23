from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Max

from gestao.models import (
    Projeto, Tarefa, Agente, Alerta, Proposta, LogTool, Automacao,
)


@login_required(login_url='/roleta/dashboard/login/')
def dashboard_ceo(request):
    """Dashboard executivo do CEO."""
    # KPIs gerais — query unica com annotate
    kpis = Tarefa.objects.filter(projeto__ativo=True).aggregate(
        total=Count('id'),
        pendentes=Count('id', filter=Q(status='pendente')),
        andamento=Count('id', filter=Q(status='em_andamento')),
        concluidas=Count('id', filter=Q(status='concluida')),
        bloqueadas=Count('id', filter=Q(status='bloqueada')),
    )
    total_tarefas = kpis['total']
    tarefas_pendentes = kpis['pendentes']
    tarefas_andamento = kpis['andamento']
    tarefas_concluidas = kpis['concluidas']
    tarefas_bloqueadas = kpis['bloqueadas']

    # Tarefas criticas/urgentes
    urgentes = Tarefa.objects.filter(
        projeto__ativo=True,
        status__in=['pendente', 'em_andamento'],
        prioridade__in=['critica', 'alta'],
    ).select_related('projeto', 'etapa').order_by('prioridade', 'data_limite')[:10]

    # Proximas tarefas (por data limite)
    proximas = Tarefa.objects.filter(
        projeto__ativo=True,
        status__in=['pendente', 'em_andamento'],
        data_limite__isnull=False,
    ).select_related('projeto').order_by('data_limite')[:10]

    # Propostas pendentes
    propostas_recentes = Proposta.objects.filter(
        status='pendente'
    ).select_related('agente', 'tool').order_by('-prioridade', '-data_criacao')[:3]

    # Alertas ativos
    alertas_recentes = Alerta.objects.filter(
        resolvido=False
    ).select_related('agente').order_by('-severidade', '-data_criacao')[:5]

    # Atividade dos agentes — otimizado com annotate (query unica)
    agentes_qs = Agente.objects.filter(ativo=True).exclude(time='executivo').annotate(
        propostas_count=Count('propostas'),
        propostas_pendentes=Count('propostas', filter=Q(propostas__status='pendente')),
        ultimo_log_data=Max('logs_tools__data_criacao'),
    ).order_by('time', 'ordem')

    # Tarefas por responsavel — nao da pra anotar (icontains), mas query unica + dict
    tarefas_por_resp = {}
    for t in Tarefa.objects.filter(
        projeto__ativo=True, status__in=['pendente', 'em_andamento']
    ).values_list('responsavel', flat=True):
        if t:
            tarefas_por_resp[t.lower()] = tarefas_por_resp.get(t.lower(), 0) + 1

    # Agentes com automacao — set de IDs
    auto_agente_ids = set(Automacao.objects.filter(
        Q(modo='agente', agente__isnull=False) | Q(encaminhar_para__isnull=False)
    ).values_list('agente_id', flat=True))
    auto_encaminhar_ids = set(Automacao.objects.filter(
        encaminhar_para__isnull=False
    ).values_list('encaminhar_para_id', flat=True))
    agentes_com_auto = auto_agente_ids | auto_encaminhar_ids

    # Ultimo log por agente — query unica
    ultimos_logs_qs = LogTool.objects.filter(
        id__in=LogTool.objects.filter(
            agente__in=agentes_qs
        ).values('agente').annotate(
            ultimo_id=Max('id')
        ).values('ultimo_id')
    ).select_related('agente')
    ultimos_logs = {log.agente_id: log for log in ultimos_logs_qs}

    atividade_agentes = []
    for ag in agentes_qs:
        tarefas_ag = tarefas_por_resp.get(ag.nome.lower(), 0)
        atividade_agentes.append({
            'agente': ag,
            'propostas': ag.propostas_count,
            'propostas_pendentes': ag.propostas_pendentes,
            'tarefas': tarefas_ag,
            'ultimo_log': ultimos_logs.get(ag.id),
            'tem_automacao': ag.id in agentes_com_auto,
        })

    return render(request, 'gestao/dashboard/ceo.html', {
        'total_tarefas': total_tarefas,
        'tarefas_pendentes': tarefas_pendentes,
        'tarefas_andamento': tarefas_andamento,
        'tarefas_concluidas': tarefas_concluidas,
        'tarefas_bloqueadas': tarefas_bloqueadas,
        'urgentes': urgentes,
        'proximas': proximas,
        'propostas_recentes': propostas_recentes,
        'alertas_recentes': alertas_recentes,
        'atividade_agentes': atividade_agentes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_mapa(request):
    """Mapa vivo do módulo de gestão — documentação que reflete o estado real."""
    from gestao.models import (
        Documento, ToolAgente, Reuniao, MensagemChat, MensagemReuniao,
    )
    from roleta.models import MembroClube, ParticipanteRoleta, PremioRoleta, RegraPontuacao, NivelClube
    from parceiros.models import Parceiro, CupomDesconto, ResgateCupom
    from indicacoes.models import Indicacao

    # Agentes por time
    agentes = Agente.objects.filter(ativo=True).order_by('time', 'ordem')
    agentes_executivo = [a for a in agentes if a.time == 'executivo']
    agentes_marketing = [a for a in agentes if a.time == 'marketing']
    agentes_sucesso = [a for a in agentes if a.time == 'sucesso']
    agentes_parcerias = [a for a in agentes if a.time == 'parcerias']
    agentes_tech = [a for a in agentes if a.time == 'tech']

    # Tools
    tools_exec = ToolAgente.objects.filter(tipo='executavel', ativo=True)
    tools_conhecimento = ToolAgente.objects.filter(tipo='conhecimento', ativo=True)

    # Automações
    automacoes = Automacao.objects.all()

    # Projetos
    projetos = Projeto.objects.filter(ativo=True).prefetch_related('tarefas')

    # Documentos por categoria
    from gestao.models import Documento as DocModel
    docs_por_cat = {}
    for doc in DocModel.objects.values('categoria').annotate(total=Count('id')):
        docs_por_cat[doc['categoria']] = doc['total']

    # Reuniões
    total_reunioes = Reuniao.objects.count()
    total_msgs_reuniao = MensagemReuniao.objects.count()
    total_msgs_chat = MensagemChat.objects.count()

    # Logs (unificado no LogTool)
    total_logs_tool = LogTool.objects.count()

    # FAQ
    from gestao.models import FAQCategoria, FAQItem
    total_faq = FAQItem.objects.filter(ativo=True).count()
    total_faq_cats = FAQCategoria.objects.filter(ativo=True).count()

    # Sistema
    sistema = {
        'membros': MembroClube.objects.count(),
        'validados': MembroClube.objects.filter(validado=True).count(),
        'giros': ParticipanteRoleta.objects.count(),
        'premios': PremioRoleta.objects.count(),
        'niveis': NivelClube.objects.count(),
        'regras': RegraPontuacao.objects.filter(ativo=True).count(),
        'parceiros': Parceiro.objects.filter(ativo=True).count(),
        'cupons': CupomDesconto.objects.filter(ativo=True).count(),
        'resgates': ResgateCupom.objects.count(),
        'indicacoes': Indicacao.objects.count(),
    }

    # Automacoes por modo
    auto_tool = automacoes.filter(modo='tool')
    auto_agente = automacoes.filter(modo='agente')

    # Propostas e Alertas
    propostas_pendentes = Proposta.objects.filter(status='pendente').count()
    alertas_ativos = Alerta.objects.filter(resolvido=False).count()

    return render(request, 'gestao/dashboard/mapa.html', {
        'agentes_executivo': agentes_executivo,
        'agentes_marketing': agentes_marketing,
        'agentes_sucesso': agentes_sucesso,
        'agentes_parcerias': agentes_parcerias,
        'agentes_tech': agentes_tech,
        'total_agentes': agentes.count(),
        'tools_exec': tools_exec,
        'tools_conhecimento': tools_conhecimento,
        'automacoes': automacoes,
        'auto_tool': auto_tool,
        'auto_agente': auto_agente,
        'projetos': projetos,
        'docs_por_cat': docs_por_cat,
        'total_docs': sum(docs_por_cat.values()),
        'total_reunioes': total_reunioes,
        'total_msgs_reuniao': total_msgs_reuniao,
        'total_msgs_chat': total_msgs_chat,
        'total_logs_tool': total_logs_tool,
        'total_logs_auto': total_logs_tool,
        'total_faq': total_faq,
        'total_faq_cats': total_faq_cats,
        'propostas_pendentes_count': propostas_pendentes,
        'alertas_ativos_count': alertas_ativos,
        'sistema': sistema,
    })
