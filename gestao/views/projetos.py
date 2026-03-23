from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q

from gestao.models import Projeto, Etapa, Tarefa, Nota, Documento, PastaDocumento
from gestao.views.helpers import _sanitizar_markdown


@login_required(login_url='/roleta/dashboard/login/')
def kanban(request, projeto_id):
    """Kanban board de um projeto."""
    projeto = get_object_or_404(Projeto, id=projeto_id)
    etapas = projeto.etapas.prefetch_related('tarefas').all()

    # Tarefas sem etapa
    sem_etapa = projeto.tarefas.filter(etapa__isnull=True)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'criar_tarefa':
            Tarefa.objects.create(
                projeto=projeto,
                etapa_id=request.POST.get('etapa_id') or None,
                titulo=request.POST.get('titulo', '').strip(),
                descricao=request.POST.get('descricao', '').strip(),
                responsavel=request.POST.get('responsavel', '').strip(),
                prioridade=request.POST.get('prioridade', 'media'),
                data_limite=request.POST.get('data_limite') or None,
            )
            messages.success(request, 'Tarefa criada.')

        elif action == 'mover':
            tarefa_id = request.POST.get('tarefa_id')
            novo_status = request.POST.get('novo_status')
            tarefa = get_object_or_404(Tarefa, id=tarefa_id, projeto=projeto)
            tarefa.status = novo_status
            if novo_status == 'concluida':
                tarefa.data_conclusao = timezone.now()
            tarefa.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, f'Tarefa movida para {tarefa.get_status_display()}.')

        elif action == 'criar_etapa':
            ultima_ordem = projeto.etapas.count()
            Etapa.objects.create(
                projeto=projeto,
                nome=request.POST.get('nome', '').strip(),
                ordem=ultima_ordem,
            )
            messages.success(request, 'Etapa criada.')

        elif action == 'adicionar_nota':
            tarefa_id = request.POST.get('tarefa_id')
            tarefa = get_object_or_404(Tarefa, id=tarefa_id, projeto=projeto)
            Nota.objects.create(
                tarefa=tarefa,
                texto=request.POST.get('texto', '').strip(),
            )
            messages.success(request, 'Nota adicionada.')

        elif action == 'excluir_tarefa':
            tarefa_id = request.POST.get('tarefa_id')
            tarefa = get_object_or_404(Tarefa, id=tarefa_id, projeto=projeto)
            tarefa.delete()
            messages.success(request, 'Tarefa excluída.')

        return redirect('kanban', projeto_id=projeto.id)

    status_list = [
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em Andamento'),
        ('concluida', 'Concluída'),
        ('bloqueada', 'Bloqueada'),
    ]
    status_counts = {}
    for code, _ in status_list:
        status_counts[code] = projeto.tarefas.filter(status=code).count()

    return render(request, 'gestao/dashboard/kanban.html', {
        'projeto': projeto,
        'etapas': etapas,
        'sem_etapa': sem_etapa,
        'status_list': status_list,
        'status_counts': status_counts,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_projetos(request):
    """Lista e criacao de projetos."""
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'criar':
            Projeto.objects.create(
                nome=request.POST.get('nome', '').strip(),
                descricao=request.POST.get('descricao', '').strip(),
                responsavel=request.POST.get('responsavel', '').strip(),
                data_inicio=request.POST.get('data_inicio') or None,
                data_fim_prevista=request.POST.get('data_fim_prevista') or None,
            )
            messages.success(request, 'Projeto criado.')
        return redirect('gestao_projetos')

    projetos = Projeto.objects.annotate(
        total_tarefas=Count('tarefas'),
        tarefas_ok=Count('tarefas', filter=Q(tarefas__status='concluida')),
    )
    return render(request, 'gestao/dashboard/projetos.html', {
        'projetos': projetos,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_projeto_editar(request, projeto_id):
    """Editar projeto."""
    projeto = get_object_or_404(Projeto, id=projeto_id)

    if request.method == 'POST':
        projeto.nome = request.POST.get('nome', projeto.nome).strip()
        projeto.descricao = _sanitizar_markdown(request.POST.get('descricao', '').strip())
        projeto.status = request.POST.get('status', projeto.status)
        projeto.prioridade = request.POST.get('prioridade', projeto.prioridade)
        projeto.objetivo = _sanitizar_markdown(request.POST.get('objetivo', '').strip())
        projeto.publico_alvo = request.POST.get('publico_alvo', '').strip()
        projeto.criterios_sucesso = request.POST.get('criterios_sucesso', '').strip()
        projeto.riscos = _sanitizar_markdown(request.POST.get('riscos', '').strip())
        projeto.premissas = _sanitizar_markdown(request.POST.get('premissas', '').strip())
        projeto.responsavel = request.POST.get('responsavel', '').strip()
        projeto.stakeholders = request.POST.get('stakeholders', '').strip()
        projeto.orcamento = request.POST.get('orcamento', '').strip()
        projeto.contexto_agentes = _sanitizar_markdown(request.POST.get('contexto_agentes', '').strip())
        projeto.data_inicio = request.POST.get('data_inicio') or None
        projeto.data_fim_prevista = request.POST.get('data_fim_prevista') or None
        projeto.save()
        messages.success(request, f'Projeto "{projeto.nome}" salvo.')
        return redirect('gestao_projeto_editar', projeto_id=projeto.id)

    return render(request, 'gestao/dashboard/projeto_editar.html', {
        'projeto': projeto,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_projeto_toggle(request, projeto_id):
    """Ativar/desativar projeto."""
    projeto = get_object_or_404(Projeto, id=projeto_id)
    if request.method == 'POST':
        projeto.ativo = not projeto.ativo
        projeto.save()
        status = 'ativado' if projeto.ativo else 'arquivado'
        messages.success(request, f'Projeto "{projeto.nome}" {status}.')
    return redirect('gestao_projetos')


@login_required(login_url='/roleta/dashboard/login/')
def gestao_projeto_excluir(request, projeto_id):
    """Excluir projeto."""
    projeto = get_object_or_404(Projeto, id=projeto_id)
    if request.method == 'POST':
        nome = projeto.nome
        projeto.delete()
        messages.success(request, f'Projeto "{nome}" excluído.')
    return redirect('gestao_projetos')


@login_required(login_url='/roleta/dashboard/login/')
def gestao_tarefa_detalhe(request, projeto_id, tarefa_id):
    """Visualizar detalhes de uma tarefa."""
    projeto = get_object_or_404(Projeto, id=projeto_id)
    tarefa = get_object_or_404(
        Tarefa.objects.select_related('projeto', 'etapa', 'processo', 'pasta_destino', 'criado_por_agente'),
        id=tarefa_id, projeto=projeto
    )

    # Acao rapida: aprovar rascunho
    if request.method == 'POST':
        acao = request.POST.get('acao', '')
        if acao == 'aprovar' and tarefa.status == 'rascunho':
            tarefa.status = 'pendente'
            tarefa.save(update_fields=['status'])
            messages.success(request, f'Tarefa "{tarefa.titulo}" aprovada e movida para Pendente.')
        elif acao == 'iniciar' and tarefa.status == 'pendente':
            tarefa.status = 'em_andamento'
            tarefa.save(update_fields=['status'])
            messages.success(request, f'Tarefa "{tarefa.titulo}" movida para Em Andamento.')
        elif acao == 'concluir' and tarefa.status == 'em_andamento':
            tarefa.status = 'concluida'
            tarefa.data_conclusao = timezone.now()
            tarefa.save(update_fields=['status', 'data_conclusao'])
            messages.success(request, f'Tarefa "{tarefa.titulo}" concluida.')
        return redirect('gestao_tarefa_detalhe', projeto_id=projeto_id, tarefa_id=tarefa_id)

    notas = tarefa.notas.all().order_by('-data_criacao') if hasattr(tarefa, 'notas') else []

    return render(request, 'gestao/dashboard/tarefa_detalhe.html', {
        'projeto': projeto,
        'tarefa': tarefa,
        'notas': notas,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_tarefa_editar(request, projeto_id, tarefa_id):
    """Editar tarefa individual."""
    projeto = get_object_or_404(Projeto, id=projeto_id)
    tarefa = get_object_or_404(Tarefa, id=tarefa_id, projeto=projeto)

    if request.method == 'POST':
        tarefa.titulo = request.POST.get('titulo', tarefa.titulo).strip()
        tarefa.descricao = request.POST.get('descricao', '').strip()
        tarefa.responsavel = request.POST.get('responsavel', '').strip()
        tarefa.prioridade = request.POST.get('prioridade', tarefa.prioridade)
        tarefa.status = request.POST.get('status', tarefa.status)
        tarefa.data_limite = request.POST.get('data_limite') or None
        etapa_id = request.POST.get('etapa_id')
        tarefa.etapa_id = etapa_id if etapa_id else None
        # Campos estruturados
        tarefa.objetivo = request.POST.get('objetivo', '').strip()
        tarefa.contexto = request.POST.get('contexto', '').strip()
        tarefa.passos = request.POST.get('passos', '').strip()
        tarefa.entregavel = request.POST.get('entregavel', '').strip()
        tarefa.criterios_aceite = request.POST.get('criterios_aceite', '').strip()
        pasta_id = request.POST.get('pasta_destino')
        tarefa.pasta_destino_id = pasta_id if pasta_id else None
        processo_id = request.POST.get('processo')
        tarefa.processo_id = processo_id if processo_id else None
        if tarefa.status == 'concluida' and not tarefa.data_conclusao:
            tarefa.data_conclusao = timezone.now()
        tarefa.save()
        messages.success(request, f'Tarefa "{tarefa.titulo}" salva.')
        return redirect('kanban', projeto_id=projeto.id)

    from gestao.models import PastaDocumento, Documento
    etapas = projeto.etapas.all()
    pastas = PastaDocumento.objects.order_by('ordem', 'nome')
    processos = Documento.objects.filter(categoria='processo').order_by('titulo')
    return render(request, 'gestao/dashboard/tarefa_editar.html', {
        'projeto': projeto,
        'tarefa': tarefa,
        'etapas': etapas,
        'pastas': pastas,
        'processos': processos,
    })
