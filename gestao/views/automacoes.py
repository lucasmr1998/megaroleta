from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q, Prefetch

from gestao.models import (
    Projeto, Tarefa, Agente, ToolAgente, LogTool, Automacao,
    Alerta, Proposta, Documento, FAQCategoria, FAQItem,
)
from gestao.agent_actions import processar_acoes


# ── Automações ────────────────────────────────────────────────────

def _seed_operador():
    """Cria o agente Operador e suas tools se não existirem."""
    from gestao.models import Agente, ToolAgente, Automacao

    operador, _ = Agente.objects.get_or_create(
        slug='operador',
        defaults={
            'nome': 'Operador',
            'descricao': 'Operações automáticas do sistema',
            'icone': 'fas fa-cog',
            'cor': '#f59e0b',
            'time': 'tools',
            'prompt': """Você é o Operador do Clube Megalink — responsável pelas tarefas operacionais automatizadas do sistema.

Suas responsabilidades:
- Gerar e atualizar FAQs baseadas em dados reais do sistema
- Monitorar a saúde dos serviços (banco, Hubsoft, OpenAI)
- Expirar cupons vencidos
- Identificar membros em risco de churn

Você é objetivo e técnico. Reporta resultados de forma clara e concisa.
Quando executar uma tool, descreva o que fez e o resultado.""",
            'modelo': 'gpt-4o-mini',
            'ativo': True,
            'ordem': 99,
        }
    )

    tools_config = [
        {
            'slug': 'gerar_faq',
            'nome': 'Gerar FAQ',
            'descricao': 'Analisa dados reais do sistema e gera perguntas frequentes via IA. Atualiza apenas quando dados mudam.',
            'icone': 'fas fa-question-circle',
            'tipo': 'executavel',
            'prompt': 'Coleta dados de prêmios, cupons, níveis, regras e gera 5 FAQs por categoria usando OpenAI.',
            'intervalo': 24,
            'ativo_auto': True,
        },
        {
            'slug': 'health_check',
            'nome': 'Monitor de Saúde',
            'descricao': 'Verifica conectividade com banco principal, Hubsoft e API OpenAI. Alerta se algum serviço estiver fora.',
            'icone': 'fas fa-heartbeat',
            'tipo': 'executavel',
            'prompt': 'Verifica 6 serviços: banco principal, Hubsoft, OpenAI, membros, estoque prêmios, cupons ativos.',
            'intervalo': 1,
            'ativo_auto': True,
        },
        {
            'slug': 'expirar_cupons',
            'nome': 'Expirador de Cupons',
            'descricao': 'Desativa cupons vencidos e resgates expirados automaticamente.',
            'icone': 'fas fa-clock',
            'tipo': 'executavel',
            'prompt': 'Busca cupons com data_fim no passado e marca como inativos.',
            'intervalo': 6,
            'ativo_auto': False,
        },
        {
            'slug': 'alerta_churn',
            'nome': 'Alerta de Churn',
            'descricao': 'Identifica membros sem atividade há mais de 30 dias e gera relatório de risco.',
            'icone': 'fas fa-exclamation-triangle',
            'tipo': 'executavel',
            'prompt': 'Busca membros que não giraram a roleta nos últimos 30 dias e gera relatório.',
            'intervalo': 24,
            'ativo_auto': False,
        },
    ]

    for tc in tools_config:
        tool, _ = ToolAgente.objects.get_or_create(
            slug=tc['slug'],
            defaults={
                'nome': tc['nome'],
                'descricao': tc['descricao'],
                'icone': tc['icone'],
                'tipo': tc['tipo'],
                'prompt': tc['prompt'],
            }
        )
        # Criar automacao (trigger) se nao existir
        encaminhar = {
            'health_check': 'cto',
            'alerta_churn': 'cs',
        }
        encaminhar_agente = None
        if tc['slug'] in encaminhar:
            encaminhar_agente = Agente.objects.filter(slug=encaminhar[tc['slug']]).first()
        Automacao.objects.get_or_create(
            tool=tool,
            defaults={
                'encaminhar_para': encaminhar_agente,
                'intervalo_horas': tc['intervalo'],
                'ativo': tc['ativo_auto'],
            }
        )


# Registry de tools executáveis por slug
TOOL_EXECUTORS = {}


def _registrar_executor(slug):
    """Decorator para registrar executores de tools."""
    def decorator(fn):
        TOOL_EXECUTORS[slug] = fn
        return fn
    return decorator


@_registrar_executor('gerar_faq')
def _exec_gerar_faq():
    from gestao.faq_service import FAQService
    FAQService.garantir_categorias()
    resultado = FAQService.atualizar_faqs(force=True)
    resultado_texto = '\n'.join(f'{k}: {v}' for k, v in resultado.items())
    return resultado_texto


@_registrar_executor('health_check')
def _exec_health_check():
    from gestao.health_service import HealthService
    relatorio = HealthService.verificar_tudo()
    linhas = []
    for c in relatorio['checks']:
        emoji = 'OK' if c['status'] == 'ok' else ('AVISO' if c['status'] == 'aviso' else 'ERRO')
        linhas.append(f"[{emoji}] {c['nome']}: {c['detalhe']} ({c['ms']}ms)")
    resultado_texto = '\n'.join(linhas)
    if relatorio['erros'] > 0:
        resultado_texto = f"ALERTA: {relatorio['erros']} servico(s) com problema\n\n{resultado_texto}"
    return resultado_texto


@_registrar_executor('rotina_customer_marketing')
def _exec_rotina_custmkt():
    from gestao.consulta_dados_service import executar_consulta
    partes = []
    partes.append(executar_consulta('membros_novos', periodo='1d'))
    partes.append(executar_consulta('membros_inativos', periodo='30d'))
    partes.append(executar_consulta('estoque_premios'))
    partes.append(executar_consulta('cupons_status'))
    partes.append(executar_consulta('resgates_por_parceiro', periodo='7d'))
    return '\n\n---\n\n'.join(partes)


@_registrar_executor('validar_fluxos')
def _exec_validar_fluxos():
    from roleta.models import MembroClube, ParticipanteRoleta, PremioRoleta
    from parceiros.models import CupomDesconto, ResgateCupom
    from indicacoes.models import Indicacao
    from django.utils import timezone

    checks = []

    # 1. Membros sem CPF
    sem_cpf = MembroClube.objects.filter(cpf='').count()
    checks.append(f"[{'OK' if sem_cpf == 0 else 'ERRO'}] Membros sem CPF: {sem_cpf}")

    # 2. Premios com probabilidade total != ~100%
    from django.db.models import Sum
    prob_total = PremioRoleta.objects.aggregate(total=Sum('probabilidade'))['total'] or 0
    checks.append(f"[{'OK' if 95 <= prob_total <= 105 else 'AVISO'}] Probabilidade total premios: {prob_total}%")

    # 3. Cupons vencidos ainda ativos
    vencidos_ativos = CupomDesconto.objects.filter(ativo=True, data_fim__lt=timezone.now()).count()
    checks.append(f"[{'OK' if vencidos_ativos == 0 else 'ALERTA'}] Cupons vencidos ativos: {vencidos_ativos}")

    # 4. Resgates sem membro
    resgates_orfaos = ResgateCupom.objects.filter(membro__isnull=True).count()
    checks.append(f"[{'OK' if resgates_orfaos == 0 else 'ERRO'}] Resgates sem membro: {resgates_orfaos}")

    return '\n'.join(checks)


@_registrar_executor('consistencia_dados')
def _exec_consistencia_dados():
    from roleta.models import MembroClube, PremioRoleta
    from parceiros.models import CupomDesconto
    from django.utils import timezone

    problemas = []

    # Saldo negativo
    saldo_neg = MembroClube.objects.filter(saldo__lt=0).count()
    if saldo_neg:
        problemas.append(f"ERRO: {saldo_neg} membros com saldo negativo")

    # XP negativo
    xp_neg = MembroClube.objects.filter(xp_total__lt=0).count()
    if xp_neg:
        problemas.append(f"ERRO: {xp_neg} membros com XP negativo")

    # Estoque negativo
    estoque_neg = PremioRoleta.objects.filter(quantidade__lt=0).count()
    if estoque_neg:
        problemas.append(f"ERRO: {estoque_neg} premios com estoque negativo")

    # Cupom com quantidade_resgatada > quantidade_total
    from django.db.models import F
    cupom_excesso = CupomDesconto.objects.filter(
        quantidade_total__gt=0, quantidade_resgatada__gt=F('quantidade_total')
    ).count()
    if cupom_excesso:
        problemas.append(f"ERRO: {cupom_excesso} cupons com resgates acima do limite")

    if not problemas:
        return "[OK] Nenhuma inconsistencia encontrada nos dados."
    return "ALERTA: Inconsistencias encontradas\n\n" + '\n'.join(problemas)


@_registrar_executor('detectar_anomalia')
def _exec_detectar_anomalia():
    from gestao.consulta_dados_service import executar_consulta
    from roleta.models import ParticipanteRoleta, MembroClube
    from parceiros.models import ResgateCupom
    from django.utils import timezone
    from datetime import timedelta

    agora = timezone.now()
    semana = agora - timedelta(days=7)
    mes = agora - timedelta(days=30)

    anomalias = []

    # Giros: comparar semana vs media mensal
    giros_semana = ParticipanteRoleta.objects.filter(data_criacao__gte=semana).count()
    giros_mes = ParticipanteRoleta.objects.filter(data_criacao__gte=mes).count()
    media_semanal = giros_mes / 4 if giros_mes else 0

    if media_semanal > 0:
        variacao = ((giros_semana - media_semanal) / media_semanal) * 100
        if abs(variacao) > 20:
            direcao = "ACIMA" if variacao > 0 else "ABAIXO"
            anomalias.append(f"ALERTA: Giros {direcao} da media ({giros_semana} vs {round(media_semanal)} media) — {round(variacao)}%")

    # Cadastros: comparar semana vs media
    cadastros_semana = MembroClube.objects.filter(data_cadastro__gte=semana).count()
    cadastros_mes = MembroClube.objects.filter(data_cadastro__gte=mes).count()
    media_cad = cadastros_mes / 4 if cadastros_mes else 0

    if media_cad > 0:
        var_cad = ((cadastros_semana - media_cad) / media_cad) * 100
        if abs(var_cad) > 20:
            direcao = "ACIMA" if var_cad > 0 else "ABAIXO"
            anomalias.append(f"ALERTA: Cadastros {direcao} da media ({cadastros_semana} vs {round(media_cad)} media) — {round(var_cad)}%")

    if not anomalias:
        return "[OK] Nenhuma anomalia detectada. Metricas dentro da media."
    return '\n'.join(anomalias)


@_registrar_executor('monitorar_performance')
def _exec_monitorar_performance():
    import time as _time

    checks = []

    # Banco principal
    try:
        from django.db import connection
        inicio = _time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        ms = int((_time.time() - inicio) * 1000)
        status = 'OK' if ms < 100 else ('AVISO' if ms < 500 else 'ERRO')
        checks.append(f"[{status}] Banco principal: {ms}ms")
    except Exception as e:
        checks.append(f"[ERRO] Banco principal: {str(e)[:80]}")

    # Hubsoft
    try:
        from django.db import connections
        inicio = _time.time()
        with connections['hubsoft'].cursor() as cursor:
            cursor.execute("SELECT 1")
        ms = int((_time.time() - inicio) * 1000)
        status = 'OK' if ms < 1000 else ('AVISO' if ms < 3000 else 'ERRO')
        checks.append(f"[{status}] Hubsoft: {ms}ms")
    except Exception as e:
        checks.append(f"[AVISO] Hubsoft: {str(e)[:80]}")

    return '\n'.join(checks)


@_registrar_executor('segmentar_base')
def _exec_segmentar_base():
    from gestao.consulta_dados_service import executar_consulta
    partes = []
    partes.append(executar_consulta('membros_inativos', periodo='30d'))
    partes.append(executar_consulta('membros_por_cidade'))
    partes.append(executar_consulta('niveis_distribuicao'))
    return '\n\n---\n\n'.join(partes)


@_registrar_executor('validar_agentes')
def _exec_validar_agentes():
    """Testa todos os agentes e retorna relatorio de qualidade."""
    import time as _time
    from gestao.ai_service import chat_agente
    from gestao.models import Agente as AgenteModel

    agentes = AgenteModel.objects.filter(ativo=True).exclude(slug='operador').order_by('time', 'ordem')
    resultados = []
    total_ok = 0
    total_falhas = 0

    perguntas_por_time = {
        'executivo': 'Como estamos hoje? Me da um resumo rapido.',
        'marketing': 'Como esta a comunicacao com a base?',
        'sucesso': 'Como esta a experiencia dos membros?',
        'parcerias': 'Como estamos com os parceiros?',
        'tech': 'Como esta o sistema hoje?',
    }

    for agente in agentes:
        pergunta = perguntas_por_time.get(agente.time, 'Como estamos?')
        problemas = []

        try:
            inicio = _time.time()
            resposta = chat_agente(agente.slug, pergunta)
            duracao = round(_time.time() - inicio, 1)

            # Verificacoes
            # 1. Resposta em portugues
            palavras_pt = ['de', 'do', 'da', 'que', 'para', 'com', 'uma']
            tem_pt = sum(1 for p in palavras_pt if f' {p} ' in resposta.lower()) >= 2
            if not tem_pt:
                problemas.append('Nao respondeu em portugues')

            # 2. Resposta curta (casual)
            if len(resposta) > 1500:
                problemas.append(f'Resposta muito longa para casual ({len(resposta)} chars)')

            # 3. Nao usa template sem pedir
            if '### 1.' in resposta and '### 2.' in resposta:
                problemas.append('Usou template/readout sem ser pedido')

            # 4. Nao finge ser outro agente
            outros = AgenteModel.objects.filter(ativo=True).exclude(slug=agente.slug).exclude(slug='operador')
            for outro in outros:
                if f'### {outro.nome}:' in resposta or f'## {outro.nome}' in resposta:
                    problemas.append(f'Fingiu ser {outro.nome}')
                    break

            # 5. Nao inventa dados absurdos
            if 'mil membros' in resposta.lower() or '10.000' in resposta or '50.000' in resposta:
                problemas.append('Possivelmente inventou dados (numeros altos demais)')

            if problemas:
                total_falhas += 1
                status = 'FALHOU'
                detalhes = '; '.join(problemas)
            else:
                total_ok += 1
                status = 'OK'
                detalhes = f'{len(resposta)} chars, {duracao}s'

            resultados.append(f"[{status}] {agente.nome} ({agente.time}) — {detalhes}")

        except Exception as e:
            total_falhas += 1
            resultados.append(f"[ERRO] {agente.nome} ({agente.time}) — {str(e)[:80]}")

    # Montar relatorio
    relatorio = f"# Validacao de Agentes\n\n"
    relatorio += f"**Total: {len(agentes)} agentes | OK: {total_ok} | Falhas: {total_falhas}**\n\n"

    for r in resultados:
        relatorio += f"- {r}\n"

    if total_falhas > 0:
        relatorio += f"\nALERTA: {total_falhas} agente(s) com problemas"
    else:
        relatorio += "\nTodos os agentes responderam corretamente."

    return relatorio


@login_required(login_url='/roleta/dashboard/login/')
def gestao_automacoes(request):
    """Dashboard de automações — agente + tool + trigger."""
    from gestao.models import Automacao, Agente, ToolAgente, LogTool

    # Seed do agente Operador + tools se necessário
    _seed_operador()

    # CRUD
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'criar':
            modo = request.POST.get('modo', 'tool')
            intervalo = int(request.POST.get('intervalo_horas', 24) or 24)

            if modo == 'agente':
                agente_id = request.POST.get('agente_id')
                if agente_id:
                    auto, created = Automacao.objects.get_or_create(
                        modo='agente', agente_id=agente_id,
                        defaults={'intervalo_horas': intervalo, 'ativo': True},
                    )
                    if created:
                        messages.success(request, f'Rotina criada: {auto.agente.nome}')
                    else:
                        messages.warning(request, 'Ja existe rotina para esse agente.')
            else:
                tool_id = request.POST.get('tool_id')
                encaminhar_id = request.POST.get('encaminhar_para') or None
                if tool_id:
                    auto, created = Automacao.objects.get_or_create(
                        modo='tool', tool_id=tool_id,
                        defaults={
                            'encaminhar_para_id': encaminhar_id,
                            'intervalo_horas': intervalo,
                            'ativo': True,
                        },
                    )
                    if created:
                        destino = f' -> {auto.encaminhar_para.nome}' if auto.encaminhar_para else ''
                        messages.success(request, f'Automacao criada: {auto.tool.nome}{destino}')
                    else:
                        messages.warning(request, 'Ja existe automacao para essa tool.')

        elif action == 'excluir':
            auto_id = request.POST.get('automacao_id')
            auto = get_object_or_404(Automacao, id=auto_id)
            auto.delete()
            messages.success(request, 'Automação excluída.')

        return redirect('gestao_automacoes')

    # Filtros
    modo_filtro = request.GET.get('modo')
    busca = request.GET.get('q', '').strip()
    automacoes = Automacao.objects.select_related('encaminhar_para', 'tool', 'agente').all()
    total_todas = automacoes.count()
    total_tool = automacoes.filter(modo='tool').count()
    total_agente = automacoes.filter(modo='agente').count()

    if modo_filtro in ('tool', 'agente'):
        automacoes = automacoes.filter(modo=modo_filtro)
    if busca:
        automacoes = automacoes.filter(
            Q(nome__icontains=busca) |
            Q(tool__nome__icontains=busca) |
            Q(agente__nome__icontains=busca) |
            Q(descricao__icontains=busca)
        )

    paginator = Paginator(automacoes, 10)
    page = request.GET.get('page')
    automacoes_page = paginator.get_page(page)

    # Logs recentes das tools de automação
    logs_recentes = LogTool.objects.select_related('tool', 'agente').order_by('-data_criacao')[:20]

    # Para o modal de criação
    agentes = Agente.objects.filter(ativo=True).order_by('nome')
    tools = ToolAgente.objects.filter(ativo=True, tipo='executavel').order_by('nome')

    return render(request, 'gestao/dashboard/automacoes.html', {
        'automacoes': automacoes_page,
        'logs_recentes': logs_recentes,
        'modo_filtro': modo_filtro,
        'busca': busca,
        'total_todas': total_todas,
        'total_tool': total_tool,
        'total_agente': total_agente,
        'agentes': agentes,
        'tools': tools,
    })


def _executar_modo_agente(request, automacao, logger):
    """Acorda agente para trabalhar. Duas etapas: coleta dados + analisa e age."""
    import time
    from gestao.ai_service import chat_agente
    from gestao.agent_actions import processar_acoes, _parse_bloco
    from gestao.models import LogTool, Alerta
    import re

    agente = automacao.agente
    inicio = time.time()

    try:
        from gestao.consulta_dados_service import executar_consulta
        from gestao.models import Tarefa
        from django.db.models import Q

        # ETAPA 1: Buscar backlog via codigo (zero tokens)
        tarefas = list(Tarefa.objects.filter(
            projeto__ativo=True,
            status__in=['pendente', 'em_andamento'],
        ).filter(
            Q(responsavel__iexact=agente.nome) | Q(responsavel__icontains=agente.nome)
        ).select_related('projeto', 'processo').order_by(
            # critica=0, alta=1, media=2, baixa=3
            'prioridade', 'data_criacao'
        )[:5])  # Max 5 tarefas por ciclo

        # Patterns para capturar blocos de acao
        _TOOL_MAP_PATTERNS = {
            r'---SALVAR_DOCUMENTO---\s+(.*?)---FIM_DOCUMENTO---': 'salvar_documento',
            r'---SALVAR_EMAIL---\s+(.*?)---FIM_EMAIL---': 'salvar_email',
            r'---CRIAR_TAREFA---\s+(.*?)---FIM_TAREFA---': 'criar_tarefa',
            r'---ATUALIZAR_TAREFA---\s+(.*?)---FIM_(?:ATUALIZAR_)?TAREFA---': 'atualizar_tarefa',
            r'---CRIAR_PROJETO---\s+(.*?)---FIM_PROJETO---': 'criar_projeto',
            r'---ATUALIZAR_PROJETO---\s+(.*?)---FIM_PROJETO---': 'atualizar_projeto',
            r'---CRIAR_ETAPA---\s+(.*?)---FIM_ETAPA---': 'criar_etapa',
        }

        propostas_criadas = 0
        tarefas_criadas_ciclo = 0
        MAX_TAREFAS_POR_AGENTE = 3
        MAX_PROPOSTAS_POR_CICLO = 10
        analise_partes = []

        # ETAPA 2: Processar cada tarefa individualmente
        for tarefa in tarefas:
            if propostas_criadas >= MAX_PROPOSTAS_POR_CICLO:
                Alerta.objects.create(
                    tipo='sistema', severidade='alta',
                    titulo=f'Ciclo interrompido: limite de propostas ({MAX_PROPOSTAS_POR_CICLO})',
                    descricao=f'Agente {agente.nome} atingiu limite de propostas por ciclo.',
                    agente=agente,
                )
                break

            if tarefa.status == 'pendente':
                # Tarefas pendentes: mover pra em_andamento (sem IA)
                tarefa.registrar_log(f'Rotina {agente.nome}: proposta para mover para em_andamento')
                Proposta.objects.create(
                    agente=agente,
                    titulo=f'{agente.nome}: Mover "{tarefa.titulo[:80]}" \u2192 Em Andamento',
                    descricao=f"**Acao:** Atualizar tarefa\n**Titulo:** {tarefa.titulo}\n**Novo status:** Em Andamento\n\n*Proposta gerada automaticamente pela rotina diaria do {agente.nome}.*",
                    prioridade=tarefa.prioridade,
                    tool=ToolAgente.objects.filter(slug='atualizar_tarefa').first(),
                    dados_execucao={'bloco': f'---ATUALIZAR_TAREFA---\ntitulo: {tarefa.titulo}\nstatus: em_andamento\n---FIM_TAREFA---', 'tool_slug': 'atualizar_tarefa'},
                )
                propostas_criadas += 1
                analise_partes.append(f"- Tarefa '{tarefa.titulo}': proposta mover para em_andamento")

            elif tarefa.status == 'em_andamento':
                # Tarefas em_andamento: executar com IA (2 chamadas)
                tarefa.registrar_log(f'Rotina {agente.nome}: iniciando execucao')

                # Montar contexto da tarefa
                tarefa_info = f"TAREFA: {tarefa.titulo}\n"
                tarefa_info += f"Objetivo: {tarefa.objetivo}\n" if tarefa.objetivo else ""
                tarefa_info += f"Contexto: {tarefa.contexto}\n" if tarefa.contexto else ""
                tarefa_info += f"Passos:\n{tarefa.passos}\n" if tarefa.passos else ""
                tarefa_info += f"Entregavel: {tarefa.entregavel}\n" if tarefa.entregavel else ""
                tarefa_info += f"Criterios: {tarefa.criterios_aceite}\n" if tarefa.criterios_aceite else ""

                # Chamada 2a: agente pede dados
                prompt_2a = (
                    f"Voce deve executar esta tarefa:\n\n{tarefa_info}\n\n"
                    f"Primeiro, consulte os dados que voce precisa usando ---CONSULTAR_DADOS---. "
                    f"Consultas disponiveis: membros_inativos, membros_novos, estoque_premios, cupons_status, membros_por_cidade.\n"
                    f"Use APENAS blocos de acao."
                )
                resp_2a = chat_agente(agente.slug, prompt_2a, modo='autonomo')
                resp_2a_processada, acoes_2a = processar_acoes(resp_2a, agente.slug)

                # Registrar dados consultados
                for acao in acoes_2a:
                    tarefa.registrar_log(f'Dados: {acao}')

                # Chamada 2b: agente recebe dados e produz entregavel
                prompt_2b = (
                    f"Voce esta executando a tarefa: {tarefa.titulo}\n\n"
                    f"Passos:\n{tarefa.passos}\n\n"
                    f"Dados coletados:\n{resp_2a_processada[:2000]}\n\n"
                    f"Agora produza o entregavel usando os dados acima.\n\n"
                    f"BLOCOS DE ACAO VALIDOS (use EXATAMENTE estes nomes):\n\n"
                    f"Para salvar e-mail — escreva o HTML completo do e-mail:\n"
                    f"---SALVAR_EMAIL---\n"
                    f"assunto: [assunto]\n"
                    f"conteudo:\n"
                    f"[HTML completo]\n"
                    f"---FIM_EMAIL---\n\n"
                    f"Para salvar documento:\n"
                    f"---SALVAR_DOCUMENTO---\n"
                    f"titulo: [titulo]\n"
                    f"categoria: [relatorio/entrega/outro]\n"
                    f"conteudo:\n"
                    f"[conteudo markdown]\n"
                    f"---FIM_DOCUMENTO---\n\n"
                    f"Para delegar tarefa a outro agente:\n"
                    f"---CRIAR_TAREFA---\n"
                    f"titulo: [titulo]\n"
                    f"projeto: [nome projeto]\n"
                    f"responsavel: [Content Marketing / CMO / CS Manager — NUNCA voce mesmo]\n"
                    f"prioridade: [critica/alta/media/baixa]\n"
                    f"objetivo: [OBRIGATORIO]\n"
                    f"contexto: [dados relevantes]\n"
                    f"---FIM_TAREFA---\n\n"
                    f"IMPORTANTE: NAO use blocos inventados como REDATOR_EMAIL ou GERADOR_HTML. "
                    f"Use APENAS os blocos listados acima. Produza o conteudo COMPLETO dentro do bloco."
                )
                resp_2b = chat_agente(agente.slug, prompt_2b, modo='autonomo')

                # Capturar blocos como propostas
                for pattern, tool_slug in _TOOL_MAP_PATTERNS.items():
                    for match in re.finditer(pattern, resp_2b, re.DOTALL | re.IGNORECASE):
                        if propostas_criadas >= MAX_PROPOSTAS_POR_CICLO:
                            break
                        if tool_slug == 'criar_tarefa':
                            tarefas_criadas_ciclo += 1
                            if tarefas_criadas_ciclo > MAX_TAREFAS_POR_AGENTE:
                                Alerta.objects.create(
                                    tipo='sistema', severidade='media',
                                    titulo=f'Limite de tarefas por agente ({MAX_TAREFAS_POR_AGENTE})',
                                    descricao=f'Agente {agente.nome} atingiu limite de tarefas criadas.',
                                    agente=agente,
                                )
                                continue

                        campos = _parse_bloco(match.group(1))
                        titulo_proposta = campos.get('titulo', campos.get('nome', tool_slug))

                        # Descricao legivel
                        acoes_labels = {
                            'criar_tarefa': 'Criar tarefa', 'atualizar_tarefa': 'Atualizar tarefa',
                            'salvar_documento': 'Salvar documento', 'salvar_email': 'Salvar e-mail',
                            'criar_projeto': 'Criar projeto', 'atualizar_projeto': 'Atualizar projeto',
                            'criar_etapa': 'Criar etapa',
                        }
                        descricao_partes = [f"**Acao:** {acoes_labels.get(tool_slug, tool_slug)}"]
                        if campos.get('titulo') or campos.get('nome'):
                            descricao_partes.append(f"**Titulo:** {campos.get('titulo', campos.get('nome', ''))}")
                        if campos.get('assunto'):
                            descricao_partes.append(f"**Assunto:** {campos.get('assunto', '')}")
                        if campos.get('status'):
                            status_labels = {'em_andamento': 'Em Andamento', 'concluida': 'Conclu\u00edda', 'pendente': 'Pendente'}
                            descricao_partes.append(f"**Novo status:** {status_labels.get(campos['status'], campos['status'])}")
                        if campos.get('projeto'):
                            descricao_partes.append(f"**Projeto:** {campos.get('projeto')}")
                        if campos.get('responsavel'):
                            descricao_partes.append(f"**Responsavel:** {campos.get('responsavel')}")
                        if campos.get('objetivo'):
                            descricao_partes.append(f"**Objetivo:** {campos.get('objetivo')[:300]}")
                        descricao_partes.append(f"\n*Gerado ao executar tarefa: {tarefa.titulo}*")

                        prio = campos.get('prioridade', tarefa.prioridade)
                        if prio not in ('critica', 'alta', 'media', 'baixa'):
                            prio = 'media'

                        # Titulo descritivo
                        if tool_slug == 'salvar_email':
                            titulo_final = f'{agente.nome}: Salvar e-mail "{campos.get("assunto", titulo_proposta)[:60]}"'
                        elif tool_slug == 'salvar_documento':
                            titulo_final = f'{agente.nome}: Salvar documento "{titulo_proposta[:60]}"'
                        elif tool_slug == 'criar_tarefa':
                            titulo_final = f'{agente.nome}: Criar tarefa "{titulo_proposta[:60]}"'
                        elif tool_slug == 'atualizar_tarefa' and campos.get('status'):
                            sl = {'em_andamento': 'Em Andamento', 'concluida': 'Conclu\u00edda'}.get(campos['status'], campos['status'])
                            titulo_final = f'{agente.nome}: Mover "{titulo_proposta[:60]}" \u2192 {sl}'
                        else:
                            titulo_final = f'{agente.nome}: {titulo_proposta[:80]}'

                        Proposta.objects.create(
                            agente=agente,
                            titulo=titulo_final,
                            descricao='\n'.join(descricao_partes),
                            prioridade=prio,
                            tool=ToolAgente.objects.filter(slug=tool_slug).first(),
                            dados_execucao={'bloco': match.group(0), 'tool_slug': tool_slug, 'tarefa_id': tarefa.id},
                        )
                        propostas_criadas += 1

                        # Registrar no log da tarefa
                        acoes_labels_log = {
                            'salvar_email': f'Proposta: salvar e-mail "{campos.get("assunto", titulo_proposta)[:60]}"',
                            'salvar_documento': f'Proposta: salvar documento "{titulo_proposta[:60]}"',
                            'criar_tarefa': f'Proposta: delegar "{titulo_proposta[:60]}" para {campos.get("responsavel", "?")}',
                            'atualizar_tarefa': f'Proposta: mover "{titulo_proposta[:60]}" para {campos.get("status", "?")}',
                        }
                        tarefa.registrar_log(acoes_labels_log.get(tool_slug, f'Proposta: {tool_slug} "{titulo_proposta[:60]}"'))

                # Executar blocos de consulta que sobraram na resp_2b
                processar_acoes(resp_2b, agente.slug)

                analise_partes.append(f"- Tarefa '{tarefa.titulo}': executada ({propostas_criadas} propostas)")

        duracao = int((time.time() - inicio) * 1000)

        # Salvar resultado
        analise_completa = f"## Rotina {agente.nome}\n\n" + "\n".join(analise_partes)
        resumo = f'{propostas_criadas} propostas criadas em {duracao}ms'

        automacao.ultima_execucao = timezone.now()
        automacao.total_execucoes += 1
        automacao.ultimo_resultado = resumo
        automacao.ultima_analise = analise_completa[:3000]
        automacao.status = 'ativo'
        automacao.save()

        LogTool.objects.create(
            tool_slug=f'rotina_{agente.slug}',
            agente=agente,
            resultado=f'{resumo}\n\n{analise_completa}',
            sucesso=True,
            tempo_ms=duracao,
        )

        if request:
            messages.success(request, f'{agente.nome} trabalhou: {propostas_criadas} propostas criadas ({duracao}ms)')

    except Exception as e:
        logger.exception(f'Erro ao acordar agente {agente.slug}')
        automacao.total_erros += 1
        automacao.total_execucoes += 1
        automacao.status = 'erro'
        automacao.ultimo_resultado = str(e)[:500]
        automacao.ultima_execucao = timezone.now()
        automacao.save()

        Alerta.objects.create(
            tipo='erro', severidade='critico',
            titulo=f'Erro na rotina de {agente.nome}',
            descricao=str(e),
            agente=agente,
        )
        if request:
            messages.error(request, f'Erro ao acordar {agente.nome}: {e}')

    return redirect('gestao_automacoes')


@login_required(login_url='/roleta/dashboard/login/')
def gestao_automacao_executar(request, automacao_id):
    """Executa automacao: modo tool (executa direto) ou modo agente (acorda agente)."""
    import logging
    import time
    from gestao.models import Automacao, LogTool

    logger = logging.getLogger(__name__)
    automacao = get_object_or_404(Automacao, id=automacao_id)

    if request.method == 'POST':
        # Modo agente: acorda o agente para trabalhar
        if automacao.modo == 'agente' and automacao.agente:
            return _executar_modo_agente(request, automacao, logger)

        # Modo tool: executa tool direto
        inicio = time.time()
        tool_slug = automacao.tool.slug if automacao.tool else ''
        executor = TOOL_EXECUTORS.get(tool_slug) if tool_slug else None

        try:
            # 1. Executar tool direto (sem IA)
            if executor:
                resultado_texto = executor()
            else:
                resultado_texto = f'Tool "{tool_slug}" sem executor implementado'

            duracao = int((time.time() - inicio) * 1000)

            # 2. Logar execucao
            LogTool.objects.create(
                tool=automacao.tool, tool_slug=tool_slug,
                agente=automacao.encaminhar_para,
                resultado=resultado_texto, sucesso=True,
            )
            automacao.ultima_execucao = timezone.now()
            automacao.total_execucoes += 1
            automacao.ultimo_resultado = resultado_texto
            automacao.status = 'ativo'
            automacao.save()

            # 3. Gerar alerta se detectou problema
            tem_problema = 'ERRO' in resultado_texto or 'ALERTA' in resultado_texto or 'risco' in resultado_texto.lower()
            if tem_problema:
                Alerta.objects.create(
                    tipo=_tipo_alerta_para_tool(tool_slug),
                    severidade='aviso' if 'AVISO' in resultado_texto else 'critico',
                    titulo=f'{automacao.tool.nome}: problemas detectados',
                    descricao=resultado_texto,
                    agente=automacao.encaminhar_para,
                    tool=automacao.tool,
                )

            # 4. Encaminhar para agente analisar (se configurado)
            if automacao.encaminhar_para:
                agente = automacao.encaminhar_para
                prompt_analise = (
                    f"A automacao '{automacao.tool.nome}' acabou de executar.\n\n"
                    f"## Resultado:\n{resultado_texto}\n\n"
                    f"Analise o resultado acima. Se identificar algo que precisa de acao, "
                    f"crie uma proposta ou alerta. Se estiver tudo normal, apenas confirme."
                )
                try:
                    from gestao.ai_service import chat_agente
                    resposta_agente = chat_agente(agente.slug, prompt_analise, modo='autonomo')
                    resposta_limpa, acoes = processar_acoes(resposta_agente, agente.slug)

                    # Salvar analise na automacao
                    automacao.ultima_analise = resposta_limpa
                    automacao.save(update_fields=['ultima_analise'])

                    # Salvar analise como proposta se o agente sugeriu acao
                    tem_acao = any(bloco in resposta_agente for bloco in ['---CRIAR_TAREFA', '---CRIAR_PROJETO', '---SALVAR_DOCUMENTO'])
                    if tem_acao:
                        # Acoes ja foram processadas pelo processar_acoes
                        pass
                    elif len(resposta_limpa) > 100 and not all(p in resposta_limpa.lower() for p in ['tudo normal', 'ok', 'sem problemas']):
                        # Agente tem algo a dizer -> criar proposta
                        Proposta.objects.create(
                            agente=agente,
                            titulo=f'Analise: {automacao.tool.nome}',
                            descricao=resposta_limpa[:1000],
                            prioridade='media' if not tem_problema else 'alta',
                            tool=automacao.tool,
                        )

                    messages.success(request, f'{automacao.tool.nome} executada ({duracao}ms) — {agente.nome} analisou')
                except Exception as e:
                    logger.exception(f'Erro ao encaminhar para {agente.slug}')
                    automacao.ultima_analise = f'Erro: {str(e)[:200]}'
                    automacao.save(update_fields=['ultima_analise'])
                    messages.warning(request, f'{automacao.tool.nome} executada ({duracao}ms) — erro ao encaminhar para {agente.nome}: {e}')
            else:
                messages.success(request, f'{automacao.tool.nome} executada ({duracao}ms)')

        except Exception as e:
            logger.exception(f'Erro na automacao {automacao_id}')
            LogTool.objects.create(
                tool=automacao.tool, tool_slug=tool_slug,
                agente=automacao.encaminhar_para,
                resultado=str(e), sucesso=False,
            )
            automacao.total_erros += 1
            automacao.total_execucoes += 1
            automacao.status = 'erro'
            automacao.ultimo_resultado = str(e)
            automacao.ultima_execucao = timezone.now()
            automacao.save()

            Alerta.objects.create(
                tipo='erro', severidade='critico',
                titulo=f'Erro ao executar {automacao.tool.nome}',
                descricao=str(e),
                agente=automacao.encaminhar_para, tool=automacao.tool,
            )
            messages.error(request, f'Erro ao executar "{automacao.tool.nome}": {e}')

    return redirect('gestao_automacoes')


def _tipo_alerta_para_tool(tool_slug):
    """Mapeia slug da tool para tipo de alerta."""
    mapa = {
        'health_check': 'health',
        'alerta_churn': 'churn',
        'notificar_estoque': 'estoque',
        'relatorio_diario': 'metrica',
        'ranking_engajamento': 'metrica',
        'sincronizar_hubsoft': 'health',
    }
    return mapa.get(tool_slug, 'outro')

    return redirect('gestao_automacoes')


@login_required(login_url='/roleta/dashboard/login/')
def gestao_automacao_editar(request, automacao_id):
    """Editar/visualizar uma automacao."""
    from gestao.models import Automacao, LogTool
    automacao = get_object_or_404(Automacao.objects.select_related('tool', 'encaminhar_para'), id=automacao_id)

    if request.method == 'POST':
        automacao.intervalo_horas = int(request.POST.get('intervalo_horas', 24) or 24)
        encaminhar_id = request.POST.get('encaminhar_para')
        automacao.encaminhar_para_id = encaminhar_id if encaminhar_id else None
        automacao.save()
        messages.success(request, f'Automacao "{automacao.tool.nome}" atualizada.')
        return redirect('gestao_automacao_editar', automacao_id=automacao.id)

    # Logs, alertas e propostas desta automacao
    if automacao.modo == 'agente' and automacao.agente:
        logs = LogTool.objects.filter(agente=automacao.agente).select_related('tool', 'agente').order_by('-data_criacao')[:20]
        alertas = Alerta.objects.filter(agente=automacao.agente).order_by('-data_criacao')[:10]
        propostas = Proposta.objects.filter(agente=automacao.agente).order_by('-data_criacao')[:10]
    else:
        logs = LogTool.objects.filter(tool=automacao.tool).select_related('tool', 'agente').order_by('-data_criacao')[:20]
        alertas = Alerta.objects.filter(tool=automacao.tool).order_by('-data_criacao')[:10]
        propostas = Proposta.objects.filter(tool=automacao.tool).order_by('-data_criacao')[:10]

    agentes = Agente.objects.filter(ativo=True).order_by('nome')

    return render(request, 'gestao/dashboard/automacao_editar.html', {
        'automacao': automacao,
        'logs': logs,
        'alertas': alertas,
        'propostas': propostas,
        'agentes': agentes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_automacao_toggle(request, automacao_id):
    """Ativa/desativa uma automação."""
    from gestao.models import Automacao
    automacao = get_object_or_404(Automacao, id=automacao_id)
    automacao.ativo = not automacao.ativo
    if automacao.ativo:
        automacao.status = 'ativo'
    else:
        automacao.status = 'pausado'
    automacao.save()
    return redirect('gestao_automacoes')


@login_required(login_url='/roleta/dashboard/login/')
def gestao_automacao_health(request):
    """Executa health check em tempo real e mostra resultado."""
    from gestao.health_service import HealthService
    relatorio = HealthService.verificar_tudo()
    return render(request, 'gestao/dashboard/automacao_health.html', {
        'relatorio': relatorio,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_logs(request):
    """Logs de execucao unificados — todas as tools e agentes."""
    from gestao.models import LogTool, Agente, ToolAgente

    busca = request.GET.get('q', '').strip()
    agente_filtro = request.GET.get('agente', '')
    sucesso_filtro = request.GET.get('sucesso', '')

    logs = LogTool.objects.select_related('tool', 'agente').order_by('-data_criacao')

    if agente_filtro:
        logs = logs.filter(agente__slug=agente_filtro)
    if sucesso_filtro == '1':
        logs = logs.filter(sucesso=True)
    elif sucesso_filtro == '0':
        logs = logs.filter(sucesso=False)
    if busca:
        logs = logs.filter(
            Q(resultado__icontains=busca) |
            Q(tool__nome__icontains=busca) |
            Q(agente__nome__icontains=busca)
        )

    total = logs.count()

    paginator = Paginator(logs, 10)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)

    agentes = Agente.objects.filter(ativo=True).order_by('nome')

    return render(request, 'gestao/dashboard/logs.html', {
        'logs': logs_page,
        'total': total,
        'busca': busca,
        'agente_filtro': agente_filtro,
        'sucesso_filtro': sucesso_filtro,
        'agentes': agentes,
    })


@login_required(login_url='/roleta/dashboard/login/')
def gestao_automacao_faq(request):
    """Visualizar e gerenciar FAQs geradas pela automação."""
    from gestao.models import FAQCategoria, FAQItem

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'toggle':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(FAQItem, id=item_id)
            item.ativo = not item.ativo
            item.save(update_fields=['ativo'])

        elif action == 'excluir':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(FAQItem, id=item_id)
            item.delete()

        elif action == 'editar':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(FAQItem, id=item_id)
            item.pergunta = request.POST.get('pergunta', '').strip()
            item.resposta = request.POST.get('resposta', '').strip()
            item.gerado_por_ia = False  # marcou como editado manualmente
            item.save()

        return redirect('gestao_automacao_faq')

    categorias = FAQCategoria.objects.filter(ativo=True).prefetch_related(
        Prefetch('itens', queryset=FAQItem.objects.all().order_by('ordem'))
    )
    total_itens = FAQItem.objects.count()
    total_ativos = FAQItem.objects.filter(ativo=True).count()
    total_ia = FAQItem.objects.filter(gerado_por_ia=True).count()

    return render(request, 'gestao/dashboard/automacao_faq.html', {
        'categorias': categorias,
        'total_itens': total_itens,
        'total_ativos': total_ativos,
        'total_ia': total_ia,
    })
