from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
import json as json_lib

from gestao.models import Projeto, Tarefa, Documento, Agente, ToolAgente, MensagemChat, Proposta
from gestao.ai_service import AGENTES_INFO


@login_required(login_url='/roleta/dashboard/login/')
def api_slash_command(request):
    """Processa comandos / do chat."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método inválido'}, status=405)

    try:
        data = json_lib.loads(request.body)
    except json_lib.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    comando = data.get('comando', '').strip().lower()
    agente_id = data.get('agente_id', '')

    if comando == 'tools':
        arg = data.get('arg', '').strip()
        if arg:
            tool = ToolAgente.objects.filter(Q(slug=arg) | Q(nome__icontains=arg)).first()
            if tool:
                from gestao.models import LogTool
                total = LogTool.objects.filter(tool=tool).count()
                linhas = [f"**{tool.nome}** ({tool.get_tipo_display()})\n",
                          f"{tool.descricao}\n",
                          f"- Status: {'Ativa' if tool.ativo else 'Inativa'}",
                          f"- Execuções: {total}",
                          f"- Prompt: {len(tool.prompt)} chars"]
                if tool.exemplo:
                    linhas.append(f"\n**Exemplo:**\n```\n{tool.exemplo}\n```")
                return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})
            return JsonResponse({'success': True, 'resposta': f'Tool `{arg}` não encontrada.'})
        tools = ToolAgente.objects.filter(ativo=True)
        linhas = ['**Tools disponíveis:**\n']
        for t in tools:
            tipo_icon = '⚡' if t.tipo == 'executavel' else '🧠'
            linhas.append(f"- {tipo_icon} **{t.nome}** — {t.descricao}")
        return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})

    elif comando == 'tarefas':
        arg = data.get('arg', '').strip()
        if arg:
            tarefa = Tarefa.objects.filter(id=arg).first() if arg.isdigit() else Tarefa.objects.filter(titulo__icontains=arg).first()
            if tarefa:
                linhas = [f"**{tarefa.titulo}**\n",
                          f"- Projeto: {tarefa.projeto.nome}",
                          f"- Status: {tarefa.get_status_display()}",
                          f"- Prioridade: {tarefa.get_prioridade_display()}",
                          f"- Responsável: {tarefa.responsavel or '-'}"]
                if tarefa.data_limite:
                    linhas.append(f"- Prazo: {tarefa.data_limite.strftime('%d/%m/%Y')}")
                if tarefa.descricao:
                    linhas.append(f"\n{tarefa.descricao}")
                return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})
        tarefas = Tarefa.objects.filter(
            projeto__ativo=True,
            status__in=['pendente', 'em_andamento', 'bloqueada']
        ).select_related('projeto').order_by('prioridade', 'data_limite')[:15]
        if not tarefas:
            return JsonResponse({'success': True, 'resposta': 'Nenhuma tarefa ativa encontrada.'})
        linhas = ['**Tarefas ativas:**\n']
        status_emoji = {'pendente': '⏳', 'em_andamento': '🔄', 'bloqueada': '🚫'}
        for t in tarefas:
            emoji = status_emoji.get(t.status, '📋')
            prazo = t.data_limite.strftime('%d/%m') if t.data_limite else ''
            linhas.append(f"- {emoji} **{t.titulo}** | {t.responsavel or '-'} | {prazo}")
        return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})

    elif comando == 'docs':
        arg = data.get('arg', '').strip()
        if arg:
            doc = Documento.objects.filter(Q(slug=arg) | Q(titulo__icontains=arg)).first()
            if doc:
                agente_nome = doc.agente.nome if doc.agente else '-'
                linhas = [f"**{doc.titulo}**\n",
                          f"- Categoria: {doc.get_categoria_display()}",
                          f"- Agente: {agente_nome}",
                          f"- Atualizado: {doc.data_atualizacao.strftime('%d/%m/%Y %H:%M')}",
                          f"- Tamanho: {len(doc.conteudo)} chars",
                          f"- Visível para agentes: {'Sim' if doc.visivel_agentes else 'Não'}"]
                if doc.resumo:
                    linhas.append(f"\n**Resumo:** {doc.resumo[:200]}")
                return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})
        docs = Documento.objects.order_by('-data_atualizacao')[:10]
        if not docs:
            return JsonResponse({'success': True, 'resposta': 'Nenhum documento encontrado.'})
        linhas = ['**Documentos recentes:**\n']
        for d in docs:
            cat = d.get_categoria_display()
            linhas.append(f"- [{cat}] **{d.titulo}** — {d.data_atualizacao.strftime('%d/%m %H:%M')}")
        return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})

    elif comando == 'projetos':
        arg = data.get('arg', '').strip()
        if arg:
            projeto = Projeto.objects.filter(Q(nome__icontains=arg), ativo=True).prefetch_related('tarefas').first()
            if projeto:
                tarefas = projeto.tarefas.all()
                total = tarefas.count()
                ok = tarefas.filter(status='concluida').count()
                pend = tarefas.filter(status='pendente').count()
                andamento = tarefas.filter(status='em_andamento').count()
                bloq = tarefas.filter(status='bloqueada').count()
                linhas = [f"**{projeto.nome}** — {projeto.progresso}%\n",
                          f"- Total: {total} tarefas ({ok} concluídas)",
                          f"- Pendentes: {pend} | Em andamento: {andamento} | Bloqueadas: {bloq}"]
                if projeto.responsavel:
                    linhas.append(f"- Responsável: {projeto.responsavel}")
                # Listar tarefas ativas
                ativas = tarefas.exclude(status='concluida').order_by('prioridade')[:10]
                if ativas:
                    linhas.append('\n**Tarefas:**')
                    for t in ativas:
                        emoji = {'pendente': '⏳', 'em_andamento': '🔄', 'bloqueada': '🚫'}.get(t.status, '')
                        linhas.append(f"- {emoji} {t.titulo} | {t.responsavel or '-'}")
                return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})
        projetos = Projeto.objects.filter(ativo=True).prefetch_related('tarefas')
        if not projetos:
            return JsonResponse({'success': True, 'resposta': 'Nenhum projeto ativo.'})
        linhas = ['**Projetos ativos:**\n']
        for p in projetos:
            total = p.tarefas.count()
            ok = p.tarefas.filter(status='concluida').count()
            linhas.append(f"- **{p.nome}** — {ok}/{total} tarefas ({p.progresso}%)")
        return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})

    elif comando == 'agentes':
        arg = data.get('arg', '').strip()
        if arg:
            a = Agente.objects.filter(Q(slug=arg) | Q(nome__icontains=arg), ativo=True).first()
            if a:
                return JsonResponse({
                    'success': True,
                    'invoke_agent': {
                        'slug': a.slug,
                        'nome': a.nome,
                        'icone': a.icone,
                        'cor': a.cor,
                    },
                    'resposta': f'**{a.nome}** entrou no chat. Envie sua próxima mensagem para ele responder.',
                })
            return JsonResponse({'success': True, 'resposta': f'Agente `{arg}` não encontrado.'})
        agentes_qs = Agente.objects.filter(ativo=True)
        linhas = ['**Agentes ativos:**\n']
        for a in agentes_qs:
            msgs = MensagemChat.objects.filter(agente=a).count()
            linhas.append(f"- **{a.nome}** ({a.slug}) — {a.descricao} | {msgs} msgs")
        linhas.append('\n*Use `/agentes <nome>` para chamar um agente para o chat.*')
        return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})

    elif comando == 'criar_projeto':
        # Preenche template no chat para o agente criar o projeto
        resposta = ("Crie um projeto com os seguintes dados:\n\n"
                    "**Nome:** [descreva o nome]\n"
                    "**Objetivo:** [o que deve alcançar]\n"
                    "**Responsável:** [quem lidera]\n"
                    "**Prioridade:** [critica/alta/media/baixa]\n"
                    "**Prazo:** [data prevista]\n\n"
                    "*Edite os campos acima e envie para o agente criar o projeto.*")
        return JsonResponse({'success': True, 'resposta': resposta, 'fill_input': True})

    elif comando == 'criar_tarefa':
        arg = data.get('arg', '').strip()
        if not arg:
            return JsonResponse({'success': True, 'resposta': 'Use `/criar_tarefa Nome do Projeto` para selecionar o projeto.'})
        resposta = (f"Crie uma tarefa no projeto **{arg}**:\n\n"
                    f"**Título:** [descreva a tarefa]\n"
                    f"**Responsável:** [quem faz]\n"
                    f"**Prioridade:** [critica/alta/media/baixa]\n"
                    f"**Prazo:** [data limite]\n\n"
                    f"*Edite e envie para o agente criar a tarefa.*")
        return JsonResponse({'success': True, 'resposta': resposta, 'fill_input': True})

    elif comando == 'criar_etapa':
        arg = data.get('arg', '').strip()
        if not arg:
            return JsonResponse({'success': True, 'resposta': 'Use `/criar_etapa Nome do Projeto` para selecionar o projeto.'})
        resposta = (f"Crie uma etapa no projeto **{arg}**:\n\n"
                    f"**Nome da etapa:** [ex: Semana 1, Sprint 3]\n"
                    f"**Data início:** [YYYY-MM-DD]\n"
                    f"**Data fim:** [YYYY-MM-DD]\n\n"
                    f"*Edite e envie para o agente criar a etapa.*")
        return JsonResponse({'success': True, 'resposta': resposta, 'fill_input': True})

    elif comando == 'resumo':
        arg = data.get('arg', '').strip()
        if not arg:
            return JsonResponse({'success': True, 'resposta': 'Use `/resumo Nome do Projeto` para selecionar o projeto.'})
        # Gera o resumo direto
        projeto = Projeto.objects.filter(Q(nome__icontains=arg), ativo=True).prefetch_related('tarefas').first()
        if not projeto:
            return JsonResponse({'success': True, 'resposta': f'Projeto "{arg}" não encontrado.'})
        tarefas = projeto.tarefas.all()
        total = tarefas.count()
        ok = tarefas.filter(status='concluida').count()
        pend = tarefas.filter(status='pendente').count()
        andamento = tarefas.filter(status='em_andamento').count()
        bloq = tarefas.filter(status='bloqueada').count()
        linhas = [
            f'**{projeto.nome}** — {projeto.progresso}%\n',
            f'**Status:** {projeto.get_status_display()}',
            f'**Tarefas:** {total} ({ok} concluídas, {andamento} em andamento, {pend} pendentes, {bloq} bloqueadas)',
        ]
        if projeto.responsavel:
            linhas.append(f'**Responsável:** {projeto.responsavel}')
        if projeto.data_fim_prevista:
            linhas.append(f'**Prazo:** {projeto.data_fim_prevista.strftime("%d/%m/%Y")}')
        if projeto.objetivo:
            linhas.append(f'\n**Objetivo:** {projeto.objetivo[:300]}')
        if projeto.riscos:
            linhas.append(f'\n**Riscos:** {projeto.riscos[:200]}')
        ativas = tarefas.exclude(status='concluida').order_by('prioridade')[:10]
        if ativas:
            linhas.append('\n**Tarefas pendentes:**')
            for t in ativas:
                emoji = {'pendente': '⏳', 'em_andamento': '🔄', 'bloqueada': '🚫'}.get(t.status, '')
                linhas.append(f'- {emoji} {t.titulo} | {t.responsavel or "-"}')
        return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})

    elif comando == 'automacoes':
        from gestao.models import Automacao
        autos = Automacao.objects.select_related('encaminhar_para', 'tool').all()
        if not autos:
            return JsonResponse({'success': True, 'resposta': 'Nenhuma automação configurada.'})
        linhas = ['**Automações:**\n']
        for a in autos:
            status = '✅' if a.ativo and a.status == 'ativo' else ('❌' if a.status == 'erro' else '⏸')
            exec_info = f'{a.total_execucoes}x' if a.total_execucoes > 0 else 'nunca'
            destino = f" → {a.encaminhar_para.nome}" if a.encaminhar_para else ""
            linhas.append(f"- {status} **{a.tool.nome}**{destino} | a cada {a.intervalo_horas}h | {exec_info}")
        return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})

    elif comando == 'faq':
        from gestao.models import FAQCategoria, FAQItem
        arg = data.get('arg', '').strip()
        if arg:
            cat = FAQCategoria.objects.filter(Q(slug__icontains=arg) | Q(nome__icontains=arg)).first()
            if cat:
                itens = FAQItem.objects.filter(categoria=cat, ativo=True)
                if not itens:
                    return JsonResponse({'success': True, 'resposta': f'Nenhuma FAQ em "{cat.nome}".'})
                linhas = [f'**{cat.nome}** ({itens.count()} perguntas)\n']
                for faq in itens:
                    linhas.append(f'**P:** {faq.pergunta}\n**R:** {faq.resposta}\n')
                return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})
            return JsonResponse({'success': True, 'resposta': f'Categoria `{arg}` não encontrada.'})
        cats = FAQCategoria.objects.filter(ativo=True)
        total = FAQItem.objects.filter(ativo=True).count()
        linhas = [f'**FAQ Automática** ({total} perguntas)\n']
        for cat in cats:
            n = FAQItem.objects.filter(categoria=cat, ativo=True).count()
            linhas.append(f'- **{cat.nome}** — {n} perguntas')
        linhas.append('\n*Use `/faq <categoria>` para ver as perguntas.*')
        return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})

    elif comando == 'health':
        from gestao.health_service import HealthService
        relatorio = HealthService.verificar_tudo()
        linhas = [f'**Monitor de Saúde** — {"✅ Saudável" if relatorio["saudavel"] else "❌ Problemas"}\n']
        for c in relatorio['checks']:
            emoji = '✅' if c['status'] == 'ok' else ('⚠️' if c['status'] == 'aviso' else '❌')
            linhas.append(f'- {emoji} **{c["nome"]}** — {c["detalhe"]} ({c["ms"]}ms)')
        return JsonResponse({'success': True, 'resposta': '\n'.join(linhas)})

    elif comando == 'help' or comando == 'ajuda':
        resposta = """**Comandos disponíveis:**

- `/tools` — Ferramentas dos agentes
- `/tarefas` — Tarefas ativas dos projetos
- `/docs` — Documentos recentes
- `/projetos` — Projetos ativos com progresso
- `/agentes` — Agentes IA ativos
- `/automacoes` — Automações ativas e status
- `/faq` — FAQs geradas por categoria
- `/health` — Verificar saúde do sistema
- `/limpar` — Limpa o histórico do chat
- `/help` — Esta mensagem"""
        return JsonResponse({'success': True, 'resposta': resposta})

    elif comando == 'suggest':
        # Autocomplete interativo — retorna opcoes para o hint popup
        tipo = data.get('tipo', '')
        busca = data.get('busca', '').strip()
        items = []

        if tipo == 'projetos':
            qs = Projeto.objects.filter(ativo=True)
            if busca:
                qs = qs.filter(nome__icontains=busca)
            for p in qs[:8]:
                items.append({'label': p.nome, 'sublabel': f'{p.progresso}% concluído', 'value': f'/projetos {p.nome}'})

        elif tipo == 'agentes':
            qs = Agente.objects.filter(ativo=True)
            if busca:
                qs = qs.filter(Q(nome__icontains=busca) | Q(slug__icontains=busca))
            for a in qs[:8]:
                msgs = MensagemChat.objects.filter(agente=a).count()
                items.append({'label': a.nome, 'sublabel': f'{a.descricao} | {msgs} msgs', 'value': f'/agentes {a.slug}', 'icon': a.icone, 'cor': a.cor})

        elif tipo == 'docs':
            qs = Documento.objects.all()
            if busca:
                qs = qs.filter(Q(titulo__icontains=busca) | Q(categoria__icontains=busca))
            for d in qs.order_by('-data_atualizacao')[:8]:
                items.append({'label': d.titulo, 'sublabel': d.get_categoria_display(), 'value': f'/docs {d.slug}'})

        elif tipo == 'tarefas':
            qs = Tarefa.objects.filter(projeto__ativo=True, status__in=['pendente', 'em_andamento', 'bloqueada'])
            if busca:
                qs = qs.filter(titulo__icontains=busca)
            status_emoji = {'pendente': '⏳', 'em_andamento': '🔄', 'bloqueada': '🚫'}
            for t in qs.order_by('prioridade', 'data_limite')[:8]:
                emoji = status_emoji.get(t.status, '')
                items.append({'label': f'{emoji} {t.titulo}', 'sublabel': f'{t.responsavel or "-"} | {t.projeto.nome}', 'value': f'/tarefas {t.id}'})

        elif tipo == 'tools':
            qs = ToolAgente.objects.filter(ativo=True)
            if busca:
                qs = qs.filter(Q(nome__icontains=busca) | Q(slug__icontains=busca))
            for t in qs[:8]:
                tipo_icon = '⚡' if t.tipo == 'executavel' else '🧠'
                items.append({'label': f'{tipo_icon} {t.nome}', 'sublabel': t.descricao, 'value': f'/tools {t.slug}'})

        elif tipo == 'faq':
            from gestao.models import FAQCategoria
            qs = FAQCategoria.objects.filter(ativo=True)
            if busca:
                qs = qs.filter(Q(nome__icontains=busca) | Q(slug__icontains=busca))
            for cat in qs[:8]:
                from gestao.models import FAQItem
                n = FAQItem.objects.filter(categoria=cat, ativo=True).count()
                items.append({'label': cat.nome, 'sublabel': f'{n} perguntas', 'value': f'/faq {cat.slug}'})

        return JsonResponse({'success': True, 'items': items})

    else:
        return JsonResponse({'success': True, 'resposta': f'Comando `/{comando}` não reconhecido. Use `/help` para ver os comandos disponíveis.'})
