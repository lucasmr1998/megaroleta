"""
Service para consulta de dados reais do sistema.
Usado pelos agentes IA via tool consultar_dados.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F

logger = logging.getLogger(__name__)


def _periodo(dias_str):
    """Converte string de periodo em timedelta. Ex: '7d', '30d', '1d'."""
    try:
        dias = int(dias_str.replace('d', '').strip())
    except (ValueError, AttributeError):
        dias = 7
    return timezone.now() - timedelta(days=dias)


def executar_consulta(consulta, periodo='7d', cidade=None, limite=20):
    """Executa uma consulta e retorna resultado formatado em markdown."""
    consulta = consulta.strip().lower().replace(' ', '_')
    desde = _periodo(periodo)

    handler = CONSULTAS.get(consulta)
    if not handler:
        disponiveis = ', '.join(sorted(CONSULTAS.keys()))
        return f"Consulta '{consulta}' nao encontrada.\n\nConsultas disponiveis:\n{disponiveis}"

    try:
        return handler(desde=desde, cidade=cidade, limite=limite)
    except Exception as e:
        logger.exception(f'Erro na consulta {consulta}')
        return f"Erro ao executar consulta '{consulta}': {str(e)}"


# ── Consultas de Membros ─────────────────────────────────────────

def _resumo_geral(desde, cidade, limite):
    from roleta.models import MembroClube, ParticipanteRoleta, PremioRoleta, NivelClube
    from parceiros.models import Parceiro, CupomDesconto, ResgateCupom
    from indicacoes.models import Indicacao
    from gestao.models import Projeto, Tarefa, Proposta, Alerta

    membros = MembroClube.objects.all()
    giros = ParticipanteRoleta.objects.all()
    resgates = ResgateCupom.objects.all()
    indicacoes = Indicacao.objects.all()

    resultado = "# Resumo Geral do Sistema\n\n"
    resultado += "## Membros\n"
    resultado += f"- Total: **{membros.count()}**\n"
    resultado += f"- Validados: **{membros.filter(validado=True).count()}**\n"
    resultado += f"- Novos (periodo): **{membros.filter(data_cadastro__gte=desde).count()}**\n\n"

    resultado += "## Engajamento\n"
    resultado += f"- Total giros: **{giros.count()}**\n"
    resultado += f"- Giros no periodo: **{giros.filter(data_criacao__gte=desde).count()}**\n"
    membros_ativos = giros.filter(data_criacao__gte=desde).values('membro').distinct().count()
    resultado += f"- Membros ativos no periodo: **{membros_ativos}**\n\n"

    resultado += "## Parceiros e Cupons\n"
    resultado += f"- Parceiros ativos: **{Parceiro.objects.filter(ativo=True).count()}**\n"
    resultado += f"- Cupons ativos: **{CupomDesconto.objects.filter(ativo=True, status_aprovacao='aprovado').count()}**\n"
    resultado += f"- Total resgates: **{resgates.count()}**\n"
    resultado += f"- Resgates no periodo: **{resgates.filter(data_resgate__gte=desde).count()}**\n"
    resultado += f"- Resgates utilizados: **{resgates.filter(status='utilizado').count()}**\n\n"

    resultado += "## Indicacoes\n"
    resultado += f"- Total: **{indicacoes.count()}**\n"
    resultado += f"- No periodo: **{indicacoes.filter(data_indicacao__gte=desde).count()}**\n"
    resultado += f"- Convertidas: **{indicacoes.filter(status='convertido').count()}**\n\n"

    resultado += "## Premios\n"
    premios = PremioRoleta.objects.all()
    resultado += f"- Total cadastrados: **{premios.count()}**\n"
    resultado += f"- Com estoque: **{premios.filter(quantidade__gt=0).count()}**\n"
    sem_estoque = premios.filter(quantidade=0).exclude(nome__icontains='nao foi')
    if sem_estoque.exists():
        resultado += f"- **SEM ESTOQUE**: {', '.join(sem_estoque.values_list('nome', flat=True))}\n"
    resultado += "\n"

    resultado += "## Gestao\n"
    resultado += f"- Projetos ativos: **{Projeto.objects.filter(ativo=True).count()}**\n"
    resultado += f"- Tarefas pendentes: **{Tarefa.objects.filter(status='pendente').count()}**\n"
    resultado += f"- Propostas pendentes: **{Proposta.objects.filter(status='pendente').count()}**\n"
    resultado += f"- Alertas ativos: **{Alerta.objects.filter(resolvido=False).count()}**\n"

    return resultado


def _membros_novos(desde, cidade, limite):
    from roleta.models import MembroClube
    qs = MembroClube.objects.filter(data_cadastro__gte=desde)
    if cidade:
        qs = qs.filter(cidade__icontains=cidade)

    total = qs.count()
    resultado = f"# Membros Novos no Periodo\n\n"
    resultado += f"**Total: {total}**\n\n"

    if total == 0:
        return resultado + "Nenhum novo membro no periodo."

    # Por cidade
    por_cidade = qs.values('cidade').annotate(total=Count('id')).order_by('-total')[:limite]
    if por_cidade:
        resultado += "## Por Cidade\n| Cidade | Total |\n|--------|-------|\n"
        for c in por_cidade:
            resultado += f"| {c['cidade'] or 'Sem cidade'} | {c['total']} |\n"

    # Validados vs nao
    validados = qs.filter(validado=True).count()
    resultado += f"\n- Validados: **{validados}** ({round(validados/total*100) if total else 0}%)\n"
    resultado += f"- Nao validados: **{total - validados}**\n"

    return resultado


def _membros_inativos(desde, cidade, limite):
    from roleta.models import MembroClube, ParticipanteRoleta

    # Membros que NAO giraram desde a data
    membros_ativos_ids = ParticipanteRoleta.objects.filter(
        data_criacao__gte=desde, membro__isnull=False
    ).values_list('membro_id', flat=True).distinct()

    qs = MembroClube.objects.filter(validado=True).exclude(id__in=membros_ativos_ids)
    if cidade:
        qs = qs.filter(cidade__icontains=cidade)

    total = qs.count()
    resultado = f"# Membros Inativos (sem giro no periodo)\n\n"
    resultado += f"**Total: {total}** membros validados sem atividade\n\n"

    # Por cidade
    por_cidade = qs.values('cidade').annotate(total=Count('id')).order_by('-total')[:limite]
    if por_cidade:
        resultado += "## Por Cidade\n| Cidade | Inativos |\n|--------|----------|\n"
        for c in por_cidade:
            resultado += f"| {c['cidade'] or 'Sem cidade'} | {c['total']} |\n"

    # Top inativos por saldo (tem saldo mas nao usa)
    com_saldo = qs.filter(saldo__gt=0).order_by('-saldo')[:10]
    if com_saldo:
        resultado += "\n## Com Saldo Parado (oportunidade)\n| Membro | Cidade | Saldo | XP |\n|--------|--------|-------|----|\n"
        for m in com_saldo:
            resultado += f"| {m.nome.split()[0]} | {m.cidade or '-'} | {m.saldo} | {m.xp_total} |\n"

    return resultado


def _membros_por_cidade(desde, cidade, limite):
    from roleta.models import MembroClube
    qs = MembroClube.objects.all()

    resultado = "# Membros por Cidade\n\n"
    por_cidade = qs.values('cidade').annotate(
        total=Count('id'),
        validados=Count('id', filter=Q(validado=True)),
        saldo_total=Sum('saldo'),
        xp_medio=Avg('xp_total'),
    ).order_by('-total')[:limite]

    resultado += "| Cidade | Total | Validados | Saldo Total | XP Medio |\n"
    resultado += "|--------|-------|-----------|-------------|----------|\n"
    for c in por_cidade:
        resultado += f"| {c['cidade'] or 'Sem cidade'} | {c['total']} | {c['validados']} | {c['saldo_total'] or 0} | {round(c['xp_medio'] or 0)} |\n"

    return resultado


def _niveis_distribuicao(desde, cidade, limite):
    from roleta.models import MembroClube, NivelClube

    niveis = NivelClube.objects.all().order_by('xp_necessario')
    membros = MembroClube.objects.filter(validado=True)
    if cidade:
        membros = membros.filter(cidade__icontains=cidade)

    total = membros.count()
    resultado = "# Distribuicao de Niveis\n\n"
    resultado += f"**Total membros validados: {total}**\n\n"
    resultado += "| Nivel | XP Necessario | Membros | % |\n|-------|---------------|---------|---|\n"

    niveis_list = list(niveis)
    # Query unica com Case/When para contar membros por faixa de nivel
    from django.db.models import Case, When, Value, CharField
    if niveis_list and total:
        whens = []
        for i, nivel in enumerate(niveis_list):
            xp_min = nivel.xp_necessario
            xp_max = niveis_list[i + 1].xp_necessario if i + 1 < len(niveis_list) else 999999
            whens.append(When(xp_total__gte=xp_min, xp_total__lt=xp_max, then=Value(nivel.nome)))

        dist = membros.annotate(
            nivel_nome=Case(*whens, default=Value('Sem nivel'), output_field=CharField())
        ).values('nivel_nome').annotate(count=Count('id'))
        dist_dict = {d['nivel_nome']: d['count'] for d in dist}

        for nivel in niveis_list:
            count = dist_dict.get(nivel.nome, 0)
            pct = round(count / total * 100) if total else 0
            resultado += f"| {nivel.nome} | {nivel.xp_necessario} | {count} | {pct}% |\n"
    else:
        for nivel in niveis_list:
            resultado += f"| {nivel.nome} | {nivel.xp_necessario} | 0 | 0% |\n"

    return resultado


# ── Consultas de Engajamento ─────────────────────────────────────

def _giros_periodo(desde, cidade, limite):
    from roleta.models import ParticipanteRoleta
    qs = ParticipanteRoleta.objects.filter(data_criacao__gte=desde)
    if cidade:
        qs = qs.filter(cidade__icontains=cidade)

    total = qs.count()
    resultado = f"# Giros no Periodo\n\n**Total: {total}**\n\n"

    # Por premio
    por_premio = qs.values('premio').annotate(total=Count('id')).order_by('-total')[:limite]
    if por_premio:
        resultado += "## Premios Sorteados\n| Premio | Quantidade |\n|--------|------------|\n"
        for p in por_premio:
            resultado += f"| {p['premio']} | {p['total']} |\n"

    # Por cidade
    por_cidade = qs.values('cidade').annotate(total=Count('id')).order_by('-total')[:10]
    if por_cidade:
        resultado += "\n## Por Cidade\n| Cidade | Giros |\n|--------|-------|\n"
        for c in por_cidade:
            resultado += f"| {c['cidade'] or 'Sem cidade'} | {c['total']} |\n"

    # Por status
    por_status = qs.values('status').annotate(total=Count('id')).order_by('-total')
    if por_status:
        resultado += "\n## Por Status\n"
        for s in por_status:
            resultado += f"- {s['status']}: **{s['total']}**\n"

    return resultado


def _premios_sorteados(desde, cidade, limite):
    from roleta.models import ParticipanteRoleta
    qs = ParticipanteRoleta.objects.filter(data_criacao__gte=desde)
    if cidade:
        qs = qs.filter(cidade__icontains=cidade)

    resultado = "# Premios Mais Sorteados\n\n"
    por_premio = qs.values('premio').annotate(
        total=Count('id')
    ).order_by('-total')[:limite]

    resultado += "| Premio | Quantidade | % |\n|--------|------------|---|\n"
    total_giros = qs.count() or 1
    for p in por_premio:
        pct = round(p['total'] / total_giros * 100, 1)
        resultado += f"| {p['premio']} | {p['total']} | {pct}% |\n"

    return resultado


def _estoque_premios(desde, cidade, limite):
    from roleta.models import PremioRoleta

    premios = PremioRoleta.objects.all().order_by('quantidade')
    resultado = "# Estoque de Premios\n\n"
    resultado += "| Premio | Estoque | Probabilidade | Status |\n"
    resultado += "|--------|---------|---------------|--------|\n"

    for p in premios:
        if 'nao foi' in p.nome.lower():
            continue
        status = "OK" if p.quantidade > 5 else ("BAIXO" if p.quantidade > 0 else "ZERADO")
        resultado += f"| {p.nome} | {p.quantidade} | {p.probabilidade}% | {status} |\n"

    return resultado


# ── Consultas de Parceiros e Cupons ──────────────────────────────

def _cupons_status(desde, cidade, limite):
    from parceiros.models import CupomDesconto, ResgateCupom

    cupons = CupomDesconto.objects.all()
    agora = timezone.now()

    resultado = "# Status dos Cupons\n\n"
    resultado += f"- Total cadastrados: **{cupons.count()}**\n"
    resultado += f"- Ativos e aprovados: **{cupons.filter(ativo=True, status_aprovacao='aprovado').count()}**\n"
    resultado += f"- Pendentes aprovacao: **{cupons.filter(status_aprovacao='pendente').count()}**\n"
    resultado += f"- Vencidos ainda ativos: **{cupons.filter(ativo=True, data_fim__lt=agora).count()}**\n\n"

    # Mais resgatados no periodo
    resgates = ResgateCupom.objects.filter(data_resgate__gte=desde)
    top = resgates.values('cupom__titulo', 'cupom__parceiro__nome').annotate(
        total=Count('id')
    ).order_by('-total')[:limite]

    if top:
        resultado += "## Mais Resgatados (periodo)\n| Cupom | Parceiro | Resgates |\n|-------|----------|----------|\n"
        for t in top:
            resultado += f"| {t['cupom__titulo']} | {t['cupom__parceiro__nome']} | {t['total']} |\n"

    return resultado


def _resgates_por_parceiro(desde, cidade, limite):
    from parceiros.models import ResgateCupom

    qs = ResgateCupom.objects.filter(data_resgate__gte=desde)

    resultado = "# Resgates por Parceiro\n\n"
    por_parceiro = qs.values('cupom__parceiro__nome').annotate(
        total=Count('id'),
        utilizados=Count('id', filter=Q(status='utilizado')),
    ).order_by('-total')[:limite]

    if not por_parceiro:
        return resultado + "Nenhum resgate no periodo."

    resultado += "| Parceiro | Resgates | Utilizados | Taxa Uso |\n"
    resultado += "|----------|----------|------------|----------|\n"
    for p in por_parceiro:
        taxa = round(p['utilizados'] / p['total'] * 100) if p['total'] else 0
        resultado += f"| {p['cupom__parceiro__nome']} | {p['total']} | {p['utilizados']} | {taxa}% |\n"

    return resultado


def _parceiros_resumo(desde, cidade, limite):
    from parceiros.models import Parceiro, CupomDesconto, ResgateCupom

    parceiros = Parceiro.objects.filter(ativo=True)
    resultado = "# Resumo de Parceiros\n\n"
    resultado += f"**Total ativos: {parceiros.count()}**\n\n"

    resultado += "| Parceiro | Cupons Ativos | Resgates Total | Resgates Periodo |\n"
    resultado += "|----------|---------------|----------------|------------------|\n"
    for p in parceiros[:limite]:
        cupons_ativos = CupomDesconto.objects.filter(parceiro=p, ativo=True, status_aprovacao='aprovado').count()
        resgates_total = ResgateCupom.objects.filter(cupom__parceiro=p).count()
        resgates_periodo = ResgateCupom.objects.filter(cupom__parceiro=p, data_resgate__gte=desde).count()
        resultado += f"| {p.nome} | {cupons_ativos} | {resgates_total} | {resgates_periodo} |\n"

    return resultado


# ── Consultas de Indicacoes ──────────────────────────────────────

def _indicacoes_periodo(desde, cidade, limite):
    from indicacoes.models import Indicacao

    qs = Indicacao.objects.filter(data_indicacao__gte=desde)
    total = qs.count()

    resultado = "# Indicacoes no Periodo\n\n"
    resultado += f"- Total: **{total}**\n"
    resultado += f"- Convertidas: **{qs.filter(status='convertido').count()}**\n"
    resultado += f"- Pendentes: **{qs.filter(status='pendente').count()}**\n\n"

    # Top indicadores
    top = qs.values('membro_indicador__nome', 'membro_indicador__cidade').annotate(
        total=Count('id'),
        convertidas=Count('id', filter=Q(status='convertido')),
    ).order_by('-total')[:limite]

    if top:
        resultado += "## Top Indicadores\n| Membro | Cidade | Indicacoes | Convertidas |\n|--------|--------|------------|-------------|\n"
        for t in top:
            resultado += f"| {t['membro_indicador__nome'].split()[0] if t['membro_indicador__nome'] else '-'} | {t['membro_indicador__cidade'] or '-'} | {t['total']} | {t['convertidas']} |\n"

    return resultado


# ── Consultas de Projetos/Gestao ─────────────────────────────────

def _projetos_status(desde, cidade, limite):
    from gestao.models import Projeto, Tarefa

    projetos = Projeto.objects.filter(ativo=True).prefetch_related('tarefas')
    resultado = "# Status dos Projetos\n\n"

    for p in projetos[:limite]:
        tarefas = p.tarefas.all()
        total = tarefas.count()
        pendentes = tarefas.filter(status='pendente').count()
        andamento = tarefas.filter(status='em_andamento').count()
        concluidas = tarefas.filter(status='concluida').count()
        bloqueadas = tarefas.filter(status='bloqueada').count()

        resultado += f"## {p.nome}\n"
        resultado += f"- Status: **{p.get_status_display()}** | Prioridade: **{p.get_prioridade_display()}**\n"
        resultado += f"- Progresso: **{p.progresso}%** ({concluidas}/{total} tarefas)\n"
        resultado += f"- Pendentes: {pendentes} | Andamento: {andamento} | Bloqueadas: {bloqueadas}\n"
        if p.responsavel:
            resultado += f"- Responsavel: {p.responsavel}\n"
        if p.data_fim_prevista:
            resultado += f"- Prazo: {p.data_fim_prevista.strftime('%d/%m/%Y')}\n"
        resultado += "\n"

    return resultado


def _tarefas_pendentes(desde, cidade, limite):
    from gestao.models import Tarefa

    qs = Tarefa.objects.filter(
        projeto__ativo=True, status__in=['pendente', 'em_andamento', 'bloqueada']
    ).select_related('projeto').order_by('prioridade', 'data_limite')[:limite]

    resultado = "# Tarefas Pendentes\n\n"
    resultado += f"**Total: {qs.count()}**\n\n"
    resultado += "| Tarefa | Projeto | Responsavel | Prioridade | Status | Prazo |\n"
    resultado += "|--------|---------|-------------|------------|--------|-------|\n"
    for t in qs:
        prazo = t.data_limite.strftime('%d/%m/%Y') if t.data_limite else '-'
        resultado += f"| {t.titulo[:40]} | {t.projeto.nome[:20]} | {t.responsavel or '-'} | {t.prioridade} | {t.status} | {prazo} |\n"

    return resultado


# ── Consulta de Integridade ───────────────────────────────────────

def _verificar_integridade(desde, cidade, limite):
    from roleta.models import MembroClube, PremioRoleta
    from parceiros.models import CupomDesconto, ResgateCupom
    from django.db.models import F

    resultado = "# Verificacao de Integridade\n\n"
    problemas = 0

    # 1. Membros com saldo negativo
    saldo_neg = MembroClube.objects.filter(saldo__lt=0)
    if saldo_neg.exists():
        problemas += saldo_neg.count()
        resultado += f"## [CRITICO] {saldo_neg.count()} membros com saldo negativo\n"
        for m in saldo_neg[:10]:
            resultado += f"- {m.nome} (ID {m.id}): saldo = {m.saldo}\n"
        resultado += "\n"

    # 2. Membros com XP negativo
    xp_neg = MembroClube.objects.filter(xp_total__lt=0)
    if xp_neg.exists():
        problemas += xp_neg.count()
        resultado += f"## [CRITICO] {xp_neg.count()} membros com XP negativo\n"
        for m in xp_neg[:10]:
            resultado += f"- {m.nome} (ID {m.id}): xp_total = {m.xp_total}\n"
        resultado += "\n"

    # 3. Premios com estoque negativo
    estoque_neg = PremioRoleta.objects.filter(quantidade__lt=0)
    if estoque_neg.exists():
        problemas += estoque_neg.count()
        resultado += f"## [CRITICO] {estoque_neg.count()} premios com estoque negativo\n"
        for p in estoque_neg[:10]:
            resultado += f"- {p.nome} (ID {p.id}): quantidade = {p.quantidade}\n"
        resultado += "\n"

    # 4. Cupons vencidos ainda ativos
    from django.utils import timezone as tz
    agora = tz.now()
    vencidos = CupomDesconto.objects.filter(ativo=True, data_fim__lt=agora)
    if vencidos.exists():
        problemas += vencidos.count()
        resultado += f"## [ALTO] {vencidos.count()} cupons vencidos ainda ativos\n"
        for c in vencidos[:10]:
            resultado += f"- {c.titulo} (ID {c.id}): venceu em {c.data_fim.strftime('%d/%m/%Y')}\n"
        resultado += "\n"

    # 5. Cupons com resgates acima do limite
    cupom_excesso = CupomDesconto.objects.filter(
        quantidade_total__gt=0, quantidade_resgatada__gt=F('quantidade_total')
    )
    if cupom_excesso.exists():
        problemas += cupom_excesso.count()
        resultado += f"## [CRITICO] {cupom_excesso.count()} cupons com resgates acima do limite\n"
        for c in cupom_excesso[:10]:
            resultado += f"- {c.titulo}: {c.quantidade_resgatada}/{c.quantidade_total}\n"
        resultado += "\n"

    # 6. Resgates sem membro
    resgates_orfaos = ResgateCupom.objects.filter(membro__isnull=True).count()
    if resgates_orfaos:
        problemas += resgates_orfaos
        resultado += f"## [ALTO] {resgates_orfaos} resgates sem membro vinculado\n\n"

    # 7. Probabilidade dos premios
    from django.db.models import Sum
    prob_total = PremioRoleta.objects.aggregate(total=Sum('probabilidade'))['total'] or 0
    if prob_total < 95 or prob_total > 105:
        problemas += 1
        resultado += f"## [MEDIO] Probabilidade total dos premios: {prob_total}% (esperado ~100%)\n\n"

    if problemas == 0:
        resultado += "**Nenhuma inconsistencia encontrada. Todos os dados estao integros.**\n"
    else:
        resultado += f"\n---\n**Total: {problemas} problemas encontrados.**\n"

    return resultado


# ── Consulta de Backlog ───────────────────────────────────────────

def _minhas_tarefas(desde, cidade, limite):
    """Busca tarefas pendentes para um responsavel especifico.
    O parametro 'cidade' e usado como nome do responsavel neste contexto."""
    from gestao.models import Tarefa
    from django.db.models import Q

    responsavel = cidade  # reutilizamos o parametro cidade como responsavel

    if not responsavel:
        return "Informe o responsavel. Use: consulta: minhas_tarefas, cidade: QA"

    # Buscar por nome exato ou parcial (case insensitive)
    qs = Tarefa.objects.filter(
        projeto__ativo=True,
        status__in=['rascunho', 'pendente', 'em_andamento', 'bloqueada'],
    ).filter(
        Q(responsavel__iexact=responsavel) |
        Q(responsavel__icontains=responsavel)
    ).select_related('projeto').order_by('prioridade', 'data_limite')[:limite]

    total = qs.count()
    resultado = f"# Backlog de Tarefas para {responsavel}\n\n"
    resultado += f"**Total: {total}**\n\n"

    if total == 0:
        resultado += "Nenhuma tarefa pendente.\n"
        return resultado

    for t in qs:
        prazo = t.data_limite.strftime('%d/%m/%Y') if t.data_limite else '-'
        resultado += f"\n## {t.titulo}\n"
        resultado += f"- **Projeto:** {t.projeto.nome}\n"
        resultado += f"- **Prioridade:** {t.prioridade} | **Status:** {t.status} | **Prazo:** {prazo}\n"
        if t.objetivo:
            resultado += f"- **Objetivo:** {t.objetivo}\n"
        if t.contexto:
            resultado += f"- **Contexto:** {t.contexto}\n"
        if t.passos:
            resultado += f"- **Passos:**\n{t.passos}\n"
        if t.entregavel:
            resultado += f"- **Entregavel:** {t.entregavel}\n"
        if t.criterios_aceite:
            resultado += f"- **Criterios de aceite:** {t.criterios_aceite}\n"
        if t.pasta_destino:
            resultado += f"- **Salvar em:** pasta '{t.pasta_destino.caminho}'\n"
        if t.processo:
            resultado += f"- **Processo:** {t.processo.titulo}\n"

    return resultado


# ── Registry ─────────────────────────────────────────────────────

CONSULTAS = {
    # Geral
    'resumo_geral': _resumo_geral,
    'resumo': _resumo_geral,

    # Membros
    'membros_novos': _membros_novos,
    'membros_inativos': _membros_inativos,
    'membros_por_cidade': _membros_por_cidade,
    'niveis_distribuicao': _niveis_distribuicao,
    'niveis': _niveis_distribuicao,

    # Engajamento
    'giros_periodo': _giros_periodo,
    'giros': _giros_periodo,
    'premios_sorteados': _premios_sorteados,
    'premios': _premios_sorteados,
    'estoque_premios': _estoque_premios,
    'estoque': _estoque_premios,

    # Parceiros e Cupons
    'cupons_status': _cupons_status,
    'cupons': _cupons_status,
    'resgates_por_parceiro': _resgates_por_parceiro,
    'resgates': _resgates_por_parceiro,
    'parceiros_resumo': _parceiros_resumo,
    'parceiros': _parceiros_resumo,

    # Indicacoes
    'indicacoes_periodo': _indicacoes_periodo,
    'indicacoes': _indicacoes_periodo,

    # Gestao
    'projetos_status': _projetos_status,
    'projetos': _projetos_status,
    'tarefas_pendentes': _tarefas_pendentes,
    'tarefas': _tarefas_pendentes,

    # Integridade
    'verificar_integridade': _verificar_integridade,
    'integridade': _verificar_integridade,

    # Backlog
    'minhas_tarefas': _minhas_tarefas,
}
