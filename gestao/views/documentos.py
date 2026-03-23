from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.db.models import Count, Q

from gestao.models import Documento, Agente, PastaDocumento
from gestao.views.helpers import _render_md_text, _sanitizar_markdown


@login_required(login_url='/roleta/dashboard/login/')
def gestao_sessoes(request):
    """Lista todas as sessoes com agentes."""
    sessoes = Documento.objects.filter(categoria='sessao').select_related('agente')
    return render(request, 'gestao/dashboard/sessoes.html', {
        'sessoes': sessoes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_sessao_detalhe(request, sessao_id):
    """Visualiza uma sessao especifica."""
    sessao = get_object_or_404(Documento, id=sessao_id, categoria='sessao')
    html = _render_md_text(sessao.conteudo)
    return render(request, 'gestao/dashboard/documento.html', {
        'titulo': sessao.titulo,
        'tipo': f'Sessão — {sessao.agente.nome if sessao.agente else "Sem agente"}',
        'html': html,
        'voltar_url': 'gestao_documentos',
        'documento_id': sessao.id,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_entregas(request):
    """Lista todas as entregas dos agentes."""
    entregas = Documento.objects.filter(categoria='entrega').select_related('agente')
    return render(request, 'gestao/dashboard/entregas.html', {
        'entregas': entregas,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_entrega_detalhe(request, entrega_id):
    """Visualiza uma entrega especifica."""
    entrega = get_object_or_404(Documento, id=entrega_id, categoria='entrega')
    html = _render_md_text(entrega.conteudo)
    return render(request, 'gestao/dashboard/documento.html', {
        'titulo': entrega.titulo,
        'tipo': f'Entrega — {entrega.agente.nome if entrega.agente else "Sem agente"}',
        'html': html,
        'voltar_url': 'gestao_entregas',
        'entrega_id': entrega.id,
        'documento_id': entrega.id,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_entrega_editar(request, entrega_id):
    """Editor de entregas — redireciona para editor de documentos."""
    return redirect('gestao_documento_editar', documento_id=entrega_id)


@login_required(login_url='/roleta/dashboard/login/')
def gestao_entrega_criar(request):
    """Criar nova entrega."""
    if request.method == 'POST':
        agente = Agente.objects.filter(id=request.POST.get('agente')).first()
        import uuid
        slug = f"entrega-{uuid.uuid4().hex[:8]}"
        Documento.objects.create(
            titulo=request.POST.get('titulo', '').strip(),
            slug=slug,
            categoria='entrega',
            agente=agente,
            conteudo=_sanitizar_markdown(request.POST.get('conteudo', '')),
            resumo=request.POST.get('resumo', '').strip(),
        )
        messages.success(request, 'Entrega criada.')
        return redirect('gestao_entregas')

    agentes = Agente.objects.filter(ativo=True)
    return render(request, 'gestao/dashboard/entrega_editar.html', {
        'entrega': None,
        'conteudo': '',
        'agentes': agentes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_entrega_excluir(request, entrega_id):
    """Excluir uma entrega."""
    entrega = get_object_or_404(Documento, id=entrega_id, categoria='entrega')
    if request.method == 'POST':
        entrega.delete()
        messages.success(request, 'Entrega excluída.')
        return redirect('gestao_entregas')
    return redirect('gestao_entrega_detalhe', entrega_id=entrega_id)


@login_required(login_url='/roleta/dashboard/login/')
def gestao_sessao_editar(request, sessao_id):
    """Redireciona para editor de documentos."""
    return redirect('gestao_documento_editar', documento_id=sessao_id)


@login_required(login_url='/roleta/dashboard/login/')
def gestao_sessao_criar(request):
    """Criar nova sessão como documento."""
    import uuid as _uuid

    if request.method == 'POST':
        agente = Agente.objects.filter(id=request.POST.get('agente')).first()
        Documento.objects.create(
            titulo=request.POST.get('titulo', '').strip(),
            slug=f"sessao-{_uuid.uuid4().hex[:8]}",
            categoria='sessao',
            agente=agente,
            conteudo=_sanitizar_markdown(request.POST.get('conteudo', '')),
            resumo=request.POST.get('resumo', '').strip(),
        )
        messages.success(request, 'Sessão criada.')
        return redirect('gestao_documentos')

    agentes = Agente.objects.filter(ativo=True)
    return render(request, 'gestao/dashboard/documento_editar.html', {
        'documento': None,
        'conteudo': '',
        'categorias': Documento.CATEGORIA_CHOICES,
        'agentes': agentes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_sessao_excluir(request, sessao_id):
    """Excluir uma sessão."""
    sessao = get_object_or_404(Documento, id=sessao_id, categoria='sessao')
    if request.method == 'POST':
        sessao.delete()
        messages.success(request, 'Sessão excluída.')
        return redirect('gestao_documentos')
    return redirect('gestao_documento_detalhe', documento_id=sessao_id)


@login_required(login_url='/roleta/dashboard/login/')
def gestao_documentos(request):
    """Lista todos os documentos com filtro por categoria e pasta."""
    categoria_filtro = request.GET.get('categoria', '')
    pasta_filtro = request.GET.get('pasta', '')
    busca = request.GET.get('q', '').strip()

    # CRUD de pastas
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'criar_pasta':
            nome = request.POST.get('nome', '').strip()
            pai_id = request.POST.get('pai') or None
            if nome:
                from django.utils.text import slugify
                slug = slugify(nome)
                PastaDocumento.objects.get_or_create(
                    slug=slug,
                    defaults={'nome': nome, 'pai_id': pai_id}
                )
                messages.success(request, f'Pasta "{nome}" criada.')
        elif action == 'excluir_pasta':
            pasta_id = request.POST.get('pasta_id')
            pasta = PastaDocumento.objects.filter(id=pasta_id).first()
            if pasta:
                # Mover docs da pasta para "sem pasta"
                Documento.objects.filter(pasta=pasta).update(pasta=None)
                pasta.delete()
                messages.success(request, 'Pasta excluída. Documentos movidos para raiz.')
        return redirect('gestao_documentos')

    qs = Documento.objects.select_related('agente', 'pasta').all()
    if categoria_filtro:
        qs = qs.filter(categoria=categoria_filtro)
    if pasta_filtro:
        if pasta_filtro == 'sem_pasta':
            qs = qs.filter(pasta__isnull=True)
        else:
            qs = qs.filter(pasta__slug=pasta_filtro)
    if busca:
        qs = qs.filter(Q(titulo__icontains=busca) | Q(conteudo__icontains=busca) | Q(descricao__icontains=busca))

    # Contadores por categoria
    from django.db.models import Count as _Count
    contadores_raw = dict(Documento.objects.values_list('categoria').annotate(c=_Count('id')).values_list('categoria', 'c'))
    total = sum(contadores_raw.values())

    filtros = []
    for valor, label in Documento.CATEGORIA_CHOICES:
        count = contadores_raw.get(valor, 0)
        if count > 0:
            filtros.append({'valor': valor, 'label': label, 'count': count})

    # Pastas
    pastas = PastaDocumento.objects.annotate(total_docs=_Count('documentos')).order_by('ordem', 'nome')

    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    documentos = paginator.get_page(page)

    return render(request, 'gestao/dashboard/documentos.html', {
        'documentos': documentos,
        'categorias': Documento.CATEGORIA_CHOICES,
        'categoria_filtro': categoria_filtro,
        'pasta_filtro': pasta_filtro,
        'busca': busca,
        'filtros': filtros,
        'total': total,
        'pastas': pastas,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_documento_detalhe(request, documento_id):
    """Visualiza um documento."""
    documento = get_object_or_404(Documento, id=documento_id)

    # E-mails: renderizar HTML bruto (sem bleach) dentro de iframe
    is_email = documento.categoria == 'email'
    if is_email:
        html = documento.conteudo
    else:
        html = _render_md_text(documento.conteudo)

    is_imagem = documento.categoria == 'imagem' and documento.arquivo

    return render(request, 'gestao/dashboard/documento.html', {
        'titulo': documento.titulo,
        'tipo': documento.get_categoria_display(),
        'html': html,
        'voltar_url': 'gestao_documentos',
        'documento_id': documento.id,
        'is_email': is_email,
        'is_imagem': is_imagem,
        'imagem_url': documento.arquivo.url if is_imagem else None,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_documento_editar(request, documento_id):
    """Editor de documentos."""
    documento = get_object_or_404(Documento, id=documento_id)

    if request.method == 'POST':
        documento.titulo = request.POST.get('titulo', documento.titulo).strip()
        documento.conteudo = _sanitizar_markdown(request.POST.get('conteudo', ''))
        documento.descricao = request.POST.get('descricao', '').strip()
        documento.categoria = request.POST.get('categoria', documento.categoria)
        documento.visivel_agentes = request.POST.get('visivel_agentes') == 'on'
        documento.ordem = int(request.POST.get('ordem', documento.ordem) or 0)
        agente_id = request.POST.get('agente')
        documento.agente = Agente.objects.filter(id=agente_id).first() if agente_id else None
        pasta_id = request.POST.get('pasta')
        documento.pasta_id = pasta_id if pasta_id else None
        documento.save()
        messages.success(request, f'Documento "{documento.titulo}" salvo.')
        if documento.categoria == 'entrega':
            return redirect('gestao_entrega_detalhe', entrega_id=documento.id)
        return redirect('gestao_documento_detalhe', documento_id=documento.id)

    agentes = Agente.objects.filter(ativo=True)
    pastas = PastaDocumento.objects.order_by('nome')
    return render(request, 'gestao/dashboard/documento_editar.html', {
        'documento': documento,
        'conteudo': documento.conteudo,
        'categorias': Documento.CATEGORIA_CHOICES,
        'agentes': agentes,
        'pastas': pastas,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_documento_criar(request):
    """Criar novo documento."""
    import uuid as _uuid

    if request.method == 'POST':
        slug = request.POST.get('slug', '').strip()
        if not slug:
            slug = f"doc-{_uuid.uuid4().hex[:8]}"
        agente_id = request.POST.get('agente')
        agente = Agente.objects.filter(id=agente_id).first() if agente_id else None
        Documento.objects.create(
            titulo=request.POST.get('titulo', '').strip(),
            slug=slug,
            categoria=request.POST.get('categoria', 'outro'),
            agente=agente,
            conteudo=_sanitizar_markdown(request.POST.get('conteudo', '')),
            descricao=request.POST.get('descricao', '').strip(),
            visivel_agentes=request.POST.get('visivel_agentes') == 'on',
            ordem=int(request.POST.get('ordem', 0) or 0),
        )
        messages.success(request, 'Documento criado.')
        return redirect('gestao_documentos')

    agentes = Agente.objects.filter(ativo=True)
    return render(request, 'gestao/dashboard/documento_editar.html', {
        'documento': None,
        'conteudo': '',
        'categorias': Documento.CATEGORIA_CHOICES,
        'agentes': agentes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_documento_excluir(request, documento_id):
    """Excluir documento."""
    documento = get_object_or_404(Documento, id=documento_id)
    if request.method == 'POST':
        documento.delete()
        messages.success(request, 'Documento excluído.')
        return redirect('gestao_documentos')
    return redirect('gestao_documento_detalhe', documento_id=documento_id)
