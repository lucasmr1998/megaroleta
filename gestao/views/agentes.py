from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q

from gestao.models import Agente, ToolAgente, LogTool, MensagemChat


@login_required(login_url='/roleta/dashboard/login/')
def gestao_agentes(request):
    """Lista todos os agentes com busca e filtro por time."""
    from gestao.models import Agente as AgenteModel

    time_filtro = request.GET.get('time', '')
    busca = request.GET.get('q', '').strip()
    todos = AgenteModel.objects.all()
    total_agentes = todos.filter(ativo=True).count()

    agentes = todos.order_by('time', 'ordem', 'nome')
    if time_filtro:
        agentes = agentes.filter(time=time_filtro)
    if busca:
        agentes = agentes.filter(
            Q(nome__icontains=busca) |
            Q(slug__icontains=busca) |
            Q(descricao__icontains=busca)
        )

    # Contadores por time
    times = []
    for k, v in AgenteModel.TIME_CHOICES:
        times.append({'valor': k, 'label': v, 'count': todos.filter(time=k, ativo=True).count()})

    paginator = Paginator(agentes, 10)
    page = request.GET.get('page')
    agentes_lista = paginator.get_page(page)

    return render(request, 'gestao/dashboard/agentes.html', {
        'agentes_lista': agentes_lista,
        'time_filtro': time_filtro,
        'busca': busca,
        'times': times,
        'total_agentes': total_agentes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_agente_editar(request, agente_id):
    """Editar agente (nome, prompt, modelo, etc)."""
    from gestao.models import Agente as AgenteModel
    agente = get_object_or_404(AgenteModel, id=agente_id)

    if request.method == 'POST':
        agente.nome = request.POST.get('nome', agente.nome).strip()
        agente.slug = request.POST.get('slug', agente.slug).strip()
        agente.descricao = request.POST.get('descricao', agente.descricao).strip()
        agente.icone = request.POST.get('icone', agente.icone).strip()
        agente.cor = request.POST.get('cor', agente.cor).strip()
        agente.time = request.POST.get('time', agente.time)
        agente.modelo = request.POST.get('modelo', agente.modelo).strip()
        agente.prompt = request.POST.get('prompt', agente.prompt)
        agente.prompt_autonomo = request.POST.get('prompt_autonomo', agente.prompt_autonomo)
        agente.ativo = request.POST.get('ativo') == 'on'
        agente.ordem = int(request.POST.get('ordem', agente.ordem) or 0)
        agente.save()
        messages.success(request, f'Agente "{agente.nome}" salvo.')
        return redirect('gestao_agentes')

    return render(request, 'gestao/dashboard/agente_editar.html', {
        'agente': agente,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_agente_criar(request):
    """Criar novo agente."""
    from gestao.models import Agente as AgenteModel

    if request.method == 'POST':
        AgenteModel.objects.create(
            nome=request.POST.get('nome', '').strip(),
            slug=request.POST.get('slug', '').strip(),
            descricao=request.POST.get('descricao', '').strip(),
            icone=request.POST.get('icone', 'fas fa-robot').strip(),
            cor=request.POST.get('cor', '#3b82f6').strip(),
            time=request.POST.get('time', 'executivo'),
            modelo=request.POST.get('modelo', 'gpt-4o-mini').strip(),
            prompt=request.POST.get('prompt', ''),
            prompt_autonomo=request.POST.get('prompt_autonomo', ''),
            ativo=request.POST.get('ativo') == 'on',
            ordem=int(request.POST.get('ordem', 0) or 0),
        )
        messages.success(request, 'Agente criado.')
        return redirect('gestao_agentes')

    return render(request, 'gestao/dashboard/agente_editar.html', {
        'agente': None,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_agente_toggle(request, agente_id):
    """Ativar/desativar agente."""
    from gestao.models import Agente as AgenteModel
    agente = get_object_or_404(AgenteModel, id=agente_id)
    if request.method == 'POST':
        agente.ativo = not agente.ativo
        agente.save()
        status = 'ativado' if agente.ativo else 'desativado'
        messages.success(request, f'Agente "{agente.nome}" {status}.')
    return redirect('gestao_agentes')


@login_required(login_url='/roleta/dashboard/login/')
def gestao_tools(request):
    """Lista todas as tools dos agentes com busca e filtro."""
    tools = ToolAgente.objects.annotate(
        total_execucoes=Count('logs'),
        execucoes_ok=Count('logs', filter=Q(logs__sucesso=True)),
    )

    # Contadores por tipo
    total = tools.count()
    total_exec = tools.filter(tipo='executavel').count()
    total_conhecimento = tools.filter(tipo='conhecimento').count()

    # Filtro por tipo
    tipo_filtro = request.GET.get('tipo', '')
    if tipo_filtro:
        tools = tools.filter(tipo=tipo_filtro)

    # Busca
    busca = request.GET.get('q', '').strip()
    if busca:
        tools = tools.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca) | Q(slug__icontains=busca))

    tools = tools.order_by('tipo', 'ordem', 'nome')

    paginator = Paginator(tools, 10)
    page = request.GET.get('page')
    tools_page = paginator.get_page(page)

    total_logs = LogTool.objects.count()
    logs_recentes = LogTool.objects.select_related('tool', 'agente')[:15]
    return render(request, 'gestao/dashboard/tools.html', {
        'tools': tools_page,
        'total': total,
        'total_exec': total_exec,
        'total_conhecimento': total_conhecimento,
        'tipo_filtro': tipo_filtro,
        'busca': busca,
        'total_logs': total_logs,
        'logs_recentes': logs_recentes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_tool_editar(request, tool_id):
    """Editar tool."""
    tool = get_object_or_404(ToolAgente, id=tool_id)

    if request.method == 'POST':
        tool.nome = request.POST.get('nome', tool.nome).strip()
        tool.slug = request.POST.get('slug', tool.slug).strip()
        tool.descricao = request.POST.get('descricao', tool.descricao).strip()
        tool.tipo = request.POST.get('tipo', tool.tipo)
        tool.prompt = request.POST.get('prompt', tool.prompt)
        tool.exemplo = request.POST.get('exemplo', '')
        tool.ativo = request.POST.get('ativo') == 'on'
        tool.ordem = int(request.POST.get('ordem', tool.ordem) or 0)
        tool.save()
        messages.success(request, f'Tool "{tool.nome}" salva.')
        return redirect('gestao_tools')

    return render(request, 'gestao/dashboard/tool_editar.html', {
        'tool': tool,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_tool_criar(request):
    """Criar nova tool."""
    if request.method == 'POST':
        ToolAgente.objects.create(
            nome=request.POST.get('nome', '').strip(),
            slug=request.POST.get('slug', '').strip(),
            descricao=request.POST.get('descricao', '').strip(),
            tipo=request.POST.get('tipo', 'conhecimento'),
            prompt=request.POST.get('prompt', ''),
            exemplo=request.POST.get('exemplo', ''),
            ativo=request.POST.get('ativo') == 'on',
            ordem=int(request.POST.get('ordem', 0) or 0),
        )
        messages.success(request, 'Tool criada.')
        return redirect('gestao_tools')

    return render(request, 'gestao/dashboard/tool_editar.html', {
        'tool': None,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_tool_toggle(request, tool_id):
    """Ativar/desativar tool."""
    tool = get_object_or_404(ToolAgente, id=tool_id)
    if request.method == 'POST':
        tool.ativo = not tool.ativo
        tool.save()
        status = 'ativada' if tool.ativo else 'desativada'
        messages.success(request, f'Tool "{tool.nome}" {status}.')
    return redirect('gestao_tools')


@login_required(login_url='/roleta/dashboard/login/')
def gestao_tool_excluir(request, tool_id):
    """Excluir tool."""
    tool = get_object_or_404(ToolAgente, id=tool_id)
    if request.method == 'POST':
        tool.delete()
        messages.success(request, 'Tool excluída.')
    return redirect('gestao_tools')
