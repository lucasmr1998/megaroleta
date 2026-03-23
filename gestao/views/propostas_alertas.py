import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone

from gestao.models import Proposta, Alerta, LogTool
from gestao.agent_actions import processar_acoes
from gestao.views.automacoes import TOOL_EXECUTORS


# ── Propostas (fila de aprovação) ────────────────────────────────

@login_required(login_url='/roleta/dashboard/login/')
def gestao_propostas(request):
    """Fila de propostas dos agentes aguardando aprovação do CEO."""
    import logging
    logger = logging.getLogger(__name__)

    filtro = request.GET.get('filtro', 'pendentes')

    if filtro == 'todas':
        propostas = Proposta.objects.select_related('agente', 'tool', 'alerta', 'reuniao').all()
    elif filtro == 'aprovadas':
        propostas = Proposta.objects.select_related('agente', 'tool').filter(status='aprovada')
    elif filtro == 'executadas':
        propostas = Proposta.objects.select_related('agente', 'tool').filter(status='executada')
    elif filtro == 'rejeitadas':
        propostas = Proposta.objects.select_related('agente', 'tool').filter(status='rejeitada')
    else:
        propostas = Proposta.objects.select_related('agente', 'tool', 'alerta').filter(status='pendente')

    # KPIs
    pendentes = Proposta.objects.filter(status='pendente').count()
    aprovadas = Proposta.objects.filter(status='aprovada').count()
    executadas = Proposta.objects.filter(status='executada').count()
    rejeitadas = Proposta.objects.filter(status='rejeitada').count()

    paginator = Paginator(propostas, 10)
    page = request.GET.get('page')
    propostas_page = paginator.get_page(page)

    return render(request, 'gestao/dashboard/propostas.html', {
        'propostas': propostas_page,
        'filtro': filtro,
        'pendentes': pendentes,
        'aprovadas': aprovadas,
        'executadas': executadas,
        'rejeitadas': rejeitadas,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_proposta_detalhe(request, proposta_id):
    """Detalhe completo de uma proposta."""
    proposta = get_object_or_404(
        Proposta.objects.select_related('agente', 'tool', 'alerta', 'reuniao'),
        id=proposta_id
    )

    # Logs relacionados (da tool + agente)
    from gestao.models import LogTool
    logs = []
    if proposta.tool:
        logs = LogTool.objects.filter(
            tool=proposta.tool, agente=proposta.agente
        ).order_by('-data_criacao')[:10]

    return render(request, 'gestao/dashboard/proposta_detalhe.html', {
        'proposta': proposta,
        'logs': logs,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_proposta_aprovar(request, proposta_id):
    """Aprova uma proposta e executa a tool associada."""
    import logging
    logger = logging.getLogger(__name__)

    proposta = get_object_or_404(Proposta, id=proposta_id)

    if request.method == 'POST' and proposta.status == 'pendente':
        proposta.status = 'aprovada'
        proposta.data_decisao = timezone.now()
        proposta.save()

        from gestao.models import LogTool

        try:
            # 1. Se tem bloco de acao nos dados_execucao (veio de modo=agente)
            if proposta.dados_execucao and proposta.dados_execucao.get('bloco'):
                bloco = proposta.dados_execucao['bloco']
                resposta_limpa, acoes = processar_acoes(bloco, proposta.agente.slug if proposta.agente else 'ceo')
                resultado = f'Bloco executado: {", ".join(acoes) if acoes else resposta_limpa[:200]}'

            # 2. Se tem tool com executor (modo=tool)
            elif proposta.tool:
                tool_slug = proposta.tool.slug
                executor = TOOL_EXECUTORS.get(tool_slug)
                if executor:
                    resultado = executor()
                else:
                    resultado = f'Proposta aprovada (tool {tool_slug} sem executor)'

            # 3. Sem tool nem bloco — so aprova
            else:
                resultado = 'Proposta aprovada'

            if proposta.tool:
                LogTool.objects.create(
                    tool=proposta.tool,
                    tool_slug=proposta.tool.slug,
                    agente=proposta.agente,
                    resultado=resultado,
                    sucesso=True,
                )
            proposta.status = 'executada'
            proposta.resultado_execucao = resultado
            proposta.data_execucao = timezone.now()
            proposta.save()
            messages.success(request, f'Proposta aprovada e executada: {proposta.titulo}')

        except Exception as e:
            logger.exception(f'Erro ao executar proposta {proposta_id}')
            if proposta.tool:
                LogTool.objects.create(
                    tool=proposta.tool,
                    tool_slug=proposta.tool.slug,
                    agente=proposta.agente,
                    resultado=str(e),
                    sucesso=False,
                )
            proposta.status = 'erro'
            proposta.resultado_execucao = str(e)
            proposta.save()
            messages.error(request, f'Proposta aprovada mas erro na execucao: {e}')

    return redirect('gestao_propostas')


@login_required(login_url='/roleta/dashboard/login/')
def gestao_proposta_rejeitar(request, proposta_id):
    """Rejeita uma proposta com motivo."""
    proposta = get_object_or_404(Proposta, id=proposta_id)

    if request.method == 'POST' and proposta.status == 'pendente':
        proposta.status = 'rejeitada'
        proposta.motivo_rejeicao = request.POST.get('motivo', '').strip()
        proposta.data_decisao = timezone.now()
        proposta.save()
        messages.success(request, f'Proposta rejeitada: {proposta.titulo}')

    return redirect('gestao_propostas')


# ── Alertas ──────────────────────────────────────────────────────

@login_required(login_url='/roleta/dashboard/login/')
def gestao_alertas(request):
    """Dashboard de alertas do sistema."""
    filtro = request.GET.get('filtro', 'ativos')

    if filtro == 'todos':
        alertas = Alerta.objects.select_related('agente', 'tool').all()
    elif filtro == 'resolvidos':
        alertas = Alerta.objects.select_related('agente', 'tool').filter(resolvido=True)
    else:
        alertas = Alerta.objects.select_related('agente', 'tool').filter(resolvido=False)

    # KPIs
    total_ativos = Alerta.objects.filter(resolvido=False).count()
    total_criticos = Alerta.objects.filter(resolvido=False, severidade='critico').count()
    total_avisos = Alerta.objects.filter(resolvido=False, severidade='aviso').count()
    total_info = Alerta.objects.filter(resolvido=False, severidade='info').count()

    paginator = Paginator(alertas, 10)
    page = request.GET.get('page')
    alertas_page = paginator.get_page(page)

    return render(request, 'gestao/dashboard/alertas.html', {
        'alertas': alertas_page,
        'filtro': filtro,
        'total_ativos': total_ativos,
        'total_criticos': total_criticos,
        'total_avisos': total_avisos,
        'total_info': total_info,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_alerta_resolver(request, alerta_id):
    """Marca um alerta como resolvido."""
    alerta = get_object_or_404(Alerta, id=alerta_id)
    if request.method == 'POST':
        alerta.resolvido = True
        alerta.save()
        messages.success(request, f'Alerta resolvido: {alerta.titulo}')
    return redirect('gestao_alertas')


@login_required(login_url='/roleta/dashboard/login/')
def gestao_alerta_ler(request, alerta_id):
    """Marca um alerta como lido."""
    alerta = get_object_or_404(Alerta, id=alerta_id)
    if request.method == 'POST':
        alerta.lido = True
        alerta.save()
    return redirect('gestao_alertas')
