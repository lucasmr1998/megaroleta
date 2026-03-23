from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
import json as json_lib

import re as _re

from gestao.models import Reuniao, MensagemReuniao, Agente, MensagemChat, Documento
from gestao.ai_service import AGENTES_INFO, chat_agente, moderador_decidir
from gestao.agent_actions import processar_acoes


def _extrair_passos_processo(processo_conteudo, mensagem_original):
    """Extrai passos numerados do conteudo de um processo e retorna lista estruturada."""
    passos = []
    # Buscar titulo do processo
    titulo = ''
    for linha in processo_conteudo.split('\n'):
        if linha.startswith('# '):
            titulo = linha.lstrip('#').strip()
            break

    # Buscar secao "## Passos" e extrair ### 1, ### 2, etc.
    in_passos = False
    passo_atual = None
    passo_conteudo = []

    for linha in processo_conteudo.split('\n'):
        if '## Passos' in linha or '## passos' in linha:
            in_passos = True
            continue
        if in_passos and linha.startswith('## ') and 'Passos' not in linha:
            # Saiu da secao de passos
            if passo_atual:
                passos.append({'titulo': passo_atual, 'instrucao': '\n'.join(passo_conteudo).strip()})
            break
        if in_passos and _re.match(r'^###\s+\d+', linha):
            # Novo passo
            if passo_atual:
                passos.append({'titulo': passo_atual, 'instrucao': '\n'.join(passo_conteudo).strip()})
            passo_atual = _re.sub(r'^###\s+', '', linha).strip()
            passo_conteudo = []
        elif in_passos and passo_atual:
            passo_conteudo.append(linha)

    # Ultimo passo
    if passo_atual:
        passos.append({'titulo': passo_atual, 'instrucao': '\n'.join(passo_conteudo).strip()})

    if not passos:
        return None

    return {
        'titulo': titulo,
        'mensagem_original': mensagem_original,
        'passos': [
            {
                'numero': i + 1,
                'titulo': p['titulo'],
                'instrucao': p['instrucao'],
                'status': 'pendente',
            }
            for i, p in enumerate(passos)
        ],
    }


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

    agente_obj = Agente.objects.filter(slug=agente_id).first()

    if request.method == 'POST' and request.POST.get('action') == 'limpar':
        if agente_obj:
            MensagemChat.objects.filter(agente=agente_obj).delete()
        return redirect('sala_chat', agente_id=agente_id)

    # Historico do banco
    historico = []
    if agente_obj:
        msgs = MensagemChat.objects.filter(agente=agente_obj).order_by('data_criacao')
        historico = [{'role': m.role, 'content': m.conteudo} for m in msgs]

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
                # Incluir mensagens de TODOS os participantes para contexto completo
                msgs_db = MensagemReuniao.objects.filter(
                    reuniao_id=reuniao_id
                ).order_by('-data_criacao')[:20]
                for m in reversed(msgs_db):
                    role = 'user' if m.tipo == 'ceo' else 'assistant'
                    prefixo = f"[{m.agente_nome}] " if m.tipo == 'agente' and m.agente_id != agente_id else ""
                    historico_reuniao.append({'role': role, 'content': f'{prefixo}{m.conteudo}'})

            agente_info = next((a for a in AGENTES_INFO if a['id'] == agente_id), None)
            nome = agente_info['nome'] if agente_info else agente_id

            try:
                resposta = chat_agente(agente_id, mensagem, historico_reuniao)
                resposta_limpa, acoes = processar_acoes(resposta, agente_id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception(f'Erro reuniao agente {agente_id}')
                resposta_limpa = f"Desculpe, tive um problema ao processar. Erro: {str(e)[:100]}"
                acoes = []

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
            # Chat individual — historico do banco
            agente_obj = Agente.objects.filter(slug=agente_id).first()
            historico = []
            if agente_obj:
                msgs = MensagemChat.objects.filter(agente=agente_obj).order_by('-data_criacao')[:20]
                historico = [{'role': m.role, 'content': m.conteudo} for m in reversed(msgs)]

            # Verificar se existe processo relevante para a mensagem
            from gestao.ai_service import _buscar_processo_relevante
            processo_info = _buscar_processo_relevante(mensagem)
            processo_passos = None

            if processo_info:
                # Extrair passos do processo para botoes
                processo_passos = _extrair_passos_processo(processo_info, mensagem)

            try:
                resposta = chat_agente(agente_id, mensagem, historico)
                resposta_limpa, acoes = processar_acoes(resposta, agente_id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception(f'Erro chat agente {agente_id}')
                resposta_limpa = f"Desculpe, tive um problema ao processar. Erro: {str(e)[:100]}"
                acoes = []

            # Salvar mensagens no banco (mesmo com erro, para manter historico)
            if agente_obj:
                MensagemChat.objects.create(agente=agente_obj, role='user', conteudo=mensagem)
                MensagemChat.objects.create(agente=agente_obj, role='assistant', conteudo=resposta_limpa)

            response_data = {
                'success': True,
                'resposta': resposta_limpa,
                'acoes': acoes,
            }
            if processo_passos:
                response_data['processo_passos'] = processo_passos

            return JsonResponse(response_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=200)


@login_required(login_url='/roleta/dashboard/login/')
def api_salvar_sessao(request):
    """Salva historico do chat como documento de sessao."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método inválido'}, status=405)

    try:
        data = json_lib.loads(request.body)
    except json_lib.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    agente_id = data.get('agente_id', '')
    from datetime import date
    import uuid as _uuid

    agente_obj = Agente.objects.filter(slug=agente_id).first()
    if not agente_obj:
        return JsonResponse({'error': 'Agente não encontrado'}, status=400)

    # Ler historico do banco
    msgs = MensagemChat.objects.filter(agente=agente_obj).order_by('data_criacao')
    if not msgs.exists():
        return JsonResponse({'error': 'Histórico vazio'}, status=400)

    agente_nome = agente_obj.nome
    hoje = date.today().isoformat()

    primeira_pergunta = ''
    for m in msgs:
        if m.role == 'user':
            primeira_pergunta = m.conteudo[:80]
            break

    conteudo = f"# Sessao: {agente_nome} — Conversa\n"
    conteudo += f"**Data:** {hoje}\n"
    conteudo += f"**Agente:** {agente_nome}\n"
    conteudo += f"**Participante:** CEO\n\n---\n\n"
    conteudo += f"## Resumo\nConversa com {agente_nome} sobre: {primeira_pergunta}\n\n"
    conteudo += "## Transcricao\n\n"

    for m in msgs:
        if m.role == 'user':
            conteudo += f"### CEO\n{m.conteudo}\n\n"
        else:
            conteudo += f"### {agente_nome}\n{m.conteudo}\n\n"

    sessao = Documento.objects.create(
        titulo=f"Conversa com {agente_nome}: {primeira_pergunta}" if primeira_pergunta else f"Conversa com {agente_nome}",
        slug=f"sessao-{_uuid.uuid4().hex[:8]}",
        categoria='sessao',
        agente=agente_obj,
        resumo=f"Conversa sobre: {primeira_pergunta}" if primeira_pergunta else "",
        conteudo=conteudo,
    )

    return JsonResponse({
        'success': True,
        'sessao_id': sessao.id,
        'message': f'Sessão salva: {sessao.titulo}',
    })
