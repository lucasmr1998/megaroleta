import os
import markdown
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.conf import settings
from django.db.models import Count, Q
from .models import Projeto, Etapa, Tarefa, Nota

DOCS_BASE = os.path.join(settings.BASE_DIR, 'docs')


@login_required(login_url='/roleta/dashboard/login/')
def dashboard_ceo(request):
    """Dashboard executivo do CEO."""
    projetos = Projeto.objects.filter(ativo=True).prefetch_related('tarefas', 'etapas')

    # KPIs gerais
    total_tarefas = Tarefa.objects.filter(projeto__ativo=True).count()
    tarefas_pendentes = Tarefa.objects.filter(projeto__ativo=True, status='pendente').count()
    tarefas_andamento = Tarefa.objects.filter(projeto__ativo=True, status='em_andamento').count()
    tarefas_concluidas = Tarefa.objects.filter(projeto__ativo=True, status='concluida').count()
    tarefas_bloqueadas = Tarefa.objects.filter(projeto__ativo=True, status='bloqueada').count()

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

    # Tarefas por responsavel
    por_responsavel = (
        Tarefa.objects.filter(projeto__ativo=True, status__in=['pendente', 'em_andamento'])
        .exclude(responsavel='')
        .values('responsavel')
        .annotate(
            total=Count('id'),
            criticas=Count('id', filter=Q(prioridade='critica')),
        )
        .order_by('-total')
    )

    # KPIs do sistema (metricas reais)
    sistema = {}
    try:
        from roleta.models import MembroClube, ParticipanteRoleta
        from parceiros.models import Parceiro, CupomDesconto, ResgateCupom
        from indicacoes.models import Indicacao

        sistema = {
            'membros': MembroClube.objects.count(),
            'membros_validados': MembroClube.objects.filter(validado=True).count(),
            'giros': ParticipanteRoleta.objects.count(),
            'parceiros': Parceiro.objects.filter(ativo=True).count(),
            'cupons': CupomDesconto.objects.filter(ativo=True, status_aprovacao='aprovado').count(),
            'resgates': ResgateCupom.objects.count(),
            'resgates_utilizados': ResgateCupom.objects.filter(status='utilizado').count(),
            'indicacoes': Indicacao.objects.count(),
            'indicacoes_convertidas': Indicacao.objects.filter(status='convertido').count(),
        }
    except Exception:
        pass

    return render(request, 'gestao/dashboard/ceo.html', {
        'projetos': projetos,
        'total_tarefas': total_tarefas,
        'tarefas_pendentes': tarefas_pendentes,
        'tarefas_andamento': tarefas_andamento,
        'tarefas_concluidas': tarefas_concluidas,
        'tarefas_bloqueadas': tarefas_bloqueadas,
        'urgentes': urgentes,
        'proximas': proximas,
        'por_responsavel': por_responsavel,
        'sistema': sistema,
    })


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


def _listar_md(pasta):
    """Lista arquivos .md numa pasta, retornando nome e metadata."""
    resultado = []
    if not os.path.exists(pasta):
        return resultado
    for f in sorted(os.listdir(pasta), reverse=True):
        if f.endswith('.md') and f not in ('README.md', 'TEMPLATE.md'):
            caminho = os.path.join(pasta, f)
            # Ler primeira linha como titulo
            with open(caminho, 'r', encoding='utf-8') as arq:
                primeira_linha = arq.readline().strip().lstrip('#').strip()
            resultado.append({
                'arquivo': f,
                'nome': f.replace('.md', '').replace('_', ' '),
                'titulo': primeira_linha,
                'tamanho': os.path.getsize(caminho),
                'modificado': os.path.getmtime(caminho),
            })
    return resultado


def _render_md(caminho):
    """Le um arquivo .md e retorna HTML renderizado."""
    if not os.path.exists(caminho):
        raise Http404("Arquivo não encontrado.")
    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    html = markdown.markdown(conteudo, extensions=['tables', 'fenced_code', 'toc'])
    return html


@login_required(login_url='/roleta/dashboard/login/')
def gestao_sessoes(request):
    """Lista todas as sessoes com agentes."""
    pasta = os.path.join(DOCS_BASE, 'contexto', 'sessoes')
    sessoes = _listar_md(pasta)
    return render(request, 'gestao/dashboard/sessoes.html', {
        'sessoes': sessoes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_sessao_detalhe(request, arquivo):
    """Visualiza uma sessao especifica."""
    caminho = os.path.join(DOCS_BASE, 'contexto', 'sessoes', arquivo)
    html = _render_md(caminho)
    nome = arquivo.replace('.md', '').replace('_', ' ')
    return render(request, 'gestao/dashboard/documento.html', {
        'titulo': nome,
        'tipo': 'Sessão',
        'html': html,
        'voltar_url': 'gestao_sessoes',
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_entregas(request):
    """Lista todas as entregas dos agentes."""
    pasta_entregas = os.path.join(DOCS_BASE, 'entregas')
    entregas = []
    if os.path.exists(pasta_entregas):
        for agente in sorted(os.listdir(pasta_entregas)):
            pasta_agente = os.path.join(pasta_entregas, agente)
            if os.path.isdir(pasta_agente):
                for f in sorted(os.listdir(pasta_agente)):
                    if f.endswith('.md') and f != 'README.md':
                        caminho = os.path.join(pasta_agente, f)
                        with open(caminho, 'r', encoding='utf-8') as arq:
                            primeira_linha = arq.readline().strip().lstrip('#').strip()
                        entregas.append({
                            'agente': agente.upper(),
                            'arquivo': f,
                            'nome': f.replace('.md', '').replace('_', ' '),
                            'titulo': primeira_linha,
                            'agente_pasta': agente,
                        })
    return render(request, 'gestao/dashboard/entregas.html', {
        'entregas': entregas,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_entrega_detalhe(request, agente, arquivo):
    """Visualiza uma entrega especifica."""
    caminho = os.path.join(DOCS_BASE, 'entregas', agente, arquivo)
    html = _render_md(caminho)
    nome = arquivo.replace('.md', '').replace('_', ' ')
    return render(request, 'gestao/dashboard/documento.html', {
        'titulo': nome,
        'tipo': f'Entrega — {agente.upper()}',
        'html': html,
        'voltar_url': 'gestao_entregas',
        'editar_url': True,
        'agente': agente,
        'arquivo': arquivo,
    })


# ── Sala de Agentes ──────────────────────────────────────────────────

from .ai_service import AGENTES_INFO, chat_agente, reuniao_agentes, moderador_decidir
from .agent_actions import processar_acoes
from .models import Reuniao, MensagemReuniao
import json as json_lib


@login_required(login_url='/roleta/dashboard/login/')
def sala_agentes(request):
    """Lobby da sala — escolher agente ou reuniao."""
    reunioes = Reuniao.objects.filter(ativa=True)[:10]
    return render(request, 'gestao/dashboard/sala.html', {
        'agentes': AGENTES_INFO,
        'reunioes': reunioes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def sala_chat(request, agente_id):
    """Chat individual com um agente."""
    agente = next((a for a in AGENTES_INFO if a['id'] == agente_id), None)
    if not agente:
        raise Http404("Agente não encontrado.")

    # Historico na sessao
    session_key = f'chat_{agente_id}'
    historico = request.session.get(session_key, [])

    if request.method == 'POST' and request.POST.get('action') == 'limpar':
        request.session[session_key] = []
        return redirect('sala_chat', agente_id=agente_id)

    return render(request, 'gestao/dashboard/sala_chat.html', {
        'agente': agente,
        'historico': historico,
    })


@login_required(login_url='/roleta/dashboard/login/')
def sala_reuniao_criar(request):
    """Criar nova reuniao."""
    if request.method == 'POST':
        agentes_ids = request.POST.getlist('agentes')
        reuniao = Reuniao.objects.create(
            nome=request.POST.get('nome', '').strip(),
            descricao=request.POST.get('descricao', '').strip(),
            agentes=','.join(agentes_ids),
        )
        return redirect('sala_reuniao', reuniao_id=reuniao.id)

    return render(request, 'gestao/dashboard/sala_reuniao_criar.html', {
        'agentes': AGENTES_INFO,
    })


@login_required(login_url='/roleta/dashboard/login/')
def sala_reuniao(request, reuniao_id):
    """Reuniao com agentes — carrega historico do banco."""
    reuniao = get_object_or_404(Reuniao, id=reuniao_id)
    mensagens = reuniao.mensagens.all()

    agentes_da_reuniao = [a for a in AGENTES_INFO if a['id'] in reuniao.agentes_lista]

    return render(request, 'gestao/dashboard/sala_reuniao.html', {
        'reuniao': reuniao,
        'mensagens': mensagens,
        'agentes': agentes_da_reuniao,
        'agentes_todos': AGENTES_INFO,
    })


from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@login_required(login_url='/roleta/dashboard/login/')
def api_chat(request):
    """API endpoint para chat AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método inválido'}, status=405)

    try:
        data = json_lib.loads(request.body)
    except json_lib.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    agente_id = data.get('agente_id')
    mensagem = data.get('mensagem', '').strip()
    modo = data.get('modo', 'chat')
    reuniao_id = data.get('reuniao_id')

    if not mensagem:
        return JsonResponse({'error': 'Mensagem vazia'}, status=400)

    try:
        if modo == 'reuniao':
            agentes_ids = data.get('agentes_ids', [a['id'] for a in AGENTES_INFO])

            historico_reuniao = []
            if reuniao_id:
                msgs_db = MensagemReuniao.objects.filter(reuniao_id=reuniao_id).order_by('-data_criacao')[:20]
                for m in reversed(msgs_db):
                    role = 'user' if m.tipo == 'ceo' else 'assistant'
                    historico_reuniao.append({'role': role, 'content': f'{m.agente_nome or "CEO"}: {m.conteudo}'})

                MensagemReuniao.objects.create(
                    reuniao_id=reuniao_id,
                    tipo='ceo',
                    agente_nome='CEO',
                    conteudo=mensagem,
                )

            agentes_selecionados = moderador_decidir(mensagem, agentes_ids, historico_reuniao)

            return JsonResponse({
                'success': True,
                'agentes_selecionados': agentes_selecionados,
            })

        elif modo == 'reuniao_agente':
            historico_reuniao = []
            if reuniao_id:
                msgs_db = MensagemReuniao.objects.filter(
                    reuniao_id=reuniao_id
                ).filter(
                    Q(tipo='ceo') | Q(agente_id=agente_id)
                ).order_by('-data_criacao')[:10]
                for m in reversed(msgs_db):
                    role = 'user' if m.tipo == 'ceo' else 'assistant'
                    historico_reuniao.append({'role': role, 'content': m.conteudo})

            resposta = chat_agente(agente_id, mensagem, historico_reuniao)
            resposta_limpa, acoes = processar_acoes(resposta, agente_id)

            agente_info = next((a for a in AGENTES_INFO if a['id'] == agente_id), None)
            nome = agente_info['nome'] if agente_info else agente_id

            if reuniao_id:
                MensagemReuniao.objects.create(
                    reuniao_id=reuniao_id,
                    tipo='agente',
                    agente_id=agente_id,
                    agente_nome=nome,
                    conteudo=resposta_limpa,
                )

            return JsonResponse({
                'success': True,
                'resposta': resposta_limpa,
                'acoes': acoes,
            })

        elif modo == 'limpar_reuniao':
            request.session['reuniao_historico'] = []
            return JsonResponse({'success': True})

        else:
            session_key = f'chat_{agente_id}'
            historico = request.session.get(session_key, [])

            resposta = chat_agente(agente_id, mensagem, historico)
            resposta_limpa, acoes = processar_acoes(resposta, agente_id)

            historico.append({'role': 'user', 'content': mensagem})
            historico.append({'role': 'assistant', 'content': resposta_limpa})
            if len(historico) > 20:
                historico = historico[-20:]
            request.session[session_key] = historico

            return JsonResponse({
                'success': True,
                'resposta': resposta_limpa,
                'acoes': acoes,
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=200)


@login_required(login_url='/roleta/dashboard/login/')
def api_salvar_sessao(request):
    """Salva historico do chat como sessao .md automaticamente."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método inválido'}, status=405)

    try:
        data = json_lib.loads(request.body)
    except json_lib.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    agente_id = data.get('agente_id', '')
    historico = data.get('historico', [])

    if not historico:
        return JsonResponse({'error': 'Histórico vazio'}, status=400)

    agente_info = next((a for a in AGENTES_INFO if a['id'] == agente_id), None)
    agente_nome = agente_info['nome'] if agente_info else agente_id.upper()

    # Gerar conteudo da sessao
    from datetime import date
    hoje = date.today().isoformat()

    # Resumo: primeira pergunta
    primeira_pergunta = ''
    for msg in historico:
        if msg['role'] == 'user':
            primeira_pergunta = msg['content'][:80]
            break

    topico = primeira_pergunta.replace(' ', '_').replace('/', '_')[:30] if primeira_pergunta else 'conversa'
    arquivo = f"{hoje}_{agente_id}_{topico}.md"

    conteudo = f"# Sessao: {agente_nome} — Conversa\n"
    conteudo += f"**Data:** {hoje}\n"
    conteudo += f"**Agente:** {agente_nome}\n"
    conteudo += f"**Participante:** CEO\n\n---\n\n"
    conteudo += f"## Resumo\nConversa com {agente_nome} sobre: {primeira_pergunta}\n\n"
    conteudo += "## Transcricao\n\n"

    for msg in historico:
        if msg['role'] == 'user':
            conteudo += f"### CEO\n{msg['content']}\n\n"
        else:
            conteudo += f"### {agente_nome}\n{msg['content']}\n\n"

    pasta = os.path.join(DOCS_BASE, 'contexto', 'sessoes')
    os.makedirs(pasta, exist_ok=True)
    filepath = os.path.join(pasta, arquivo)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    return JsonResponse({
        'success': True,
        'arquivo': arquivo,
        'message': f'Sessão salva: {arquivo}',
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_entrega_editar(request, agente, arquivo):
    """Editor de entregas com preview markdown."""
    caminho = os.path.join(DOCS_BASE, 'entregas', agente, arquivo)

    if not os.path.exists(caminho):
        raise Http404("Arquivo não encontrado.")

    if request.method == 'POST':
        conteudo = request.POST.get('conteudo', '')
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        messages.success(request, f'Entrega "{arquivo}" salva.')
        return redirect('gestao_entrega_detalhe', agente=agente, arquivo=arquivo)

    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    nome = arquivo.replace('.md', '').replace('_', ' ')

    return render(request, 'gestao/dashboard/entrega_editar.html', {
        'agente': agente,
        'arquivo': arquivo,
        'nome': nome,
        'conteudo': conteudo,
    })
