def gestao_badges(request):
    """Injeta contadores de propostas e alertas pendentes em todas as páginas."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}

    from gestao.models import Proposta, Alerta
    return {
        'propostas_pendentes': Proposta.objects.filter(status='pendente').count(),
        'alertas_ativos': Alerta.objects.filter(resolvido=False).count(),
    }
