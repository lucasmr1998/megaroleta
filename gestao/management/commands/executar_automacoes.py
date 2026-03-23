"""
Scheduler de automacoes. Verifica quais estao no horario e executa.

Uso:
  python manage.py executar_automacoes           # executa as que estao no horario
  python manage.py executar_automacoes --force    # executa todas independente do horario
  python manage.py executar_automacoes --dry-run  # mostra o que executaria sem executar

Cron:
  # Roda a cada 30 minutos
  */30 * * * * cd /path/to/megaroleta && python manage.py executar_automacoes
"""
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from gestao.models import Automacao

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Executa automacoes que estao no horario'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Executar todas, ignorando intervalo')
        parser.add_argument('--dry-run', action='store_true', help='Mostrar o que executaria sem executar')

    def handle(self, *args, **options):
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)

        agora = timezone.now()
        automacoes = Automacao.objects.filter(ativo=True).select_related('tool', 'agente', 'encaminhar_para')

        self.stdout.write(f'\n[{agora.strftime("%d/%m/%Y %H:%M")}] Verificando {automacoes.count()} automacoes ativas...\n')

        executadas = 0
        puladas = 0

        for auto in automacoes:
            # Verificar se esta no horario
            if not force and auto.ultima_execucao:
                proxima = auto.ultima_execucao + timedelta(hours=auto.intervalo_horas)
                if agora < proxima:
                    restante = proxima - agora
                    horas = int(restante.total_seconds() // 3600)
                    minutos = int((restante.total_seconds() % 3600) // 60)
                    self.stdout.write(f'  [PULAR] {auto.nome} — proxima em {horas}h{minutos}m')
                    puladas += 1
                    continue

            # Executar
            nome = auto.nome
            modo = auto.modo

            if dry_run:
                self.stdout.write(self.style.WARNING(f'  [DRY-RUN] {nome} (modo={modo})'))
                executadas += 1
                continue

            self.stdout.write(f'  [EXECUTANDO] {nome} (modo={modo})...')

            try:
                if modo == 'agente' and auto.agente:
                    self._executar_agente(auto)
                elif modo == 'tool' and auto.tool:
                    self._executar_tool(auto)
                else:
                    self.stdout.write(self.style.ERROR(f'    Configuracao invalida: modo={modo}, tool={auto.tool}, agente={auto.agente}'))
                    continue

                executadas += 1
                self.stdout.write(self.style.SUCCESS(f'    OK: {auto.ultimo_resultado[:100]}'))

            except Exception as e:
                logger.exception(f'Erro na automacao {auto.id}')
                self.stdout.write(self.style.ERROR(f'    ERRO: {str(e)[:100]}'))

        self.stdout.write(f'\nResultado: {executadas} executadas, {puladas} puladas\n')

    def _executar_agente(self, automacao):
        """Modo agente: acorda o agente para trabalhar."""
        from gestao.views import _executar_modo_agente
        _executar_modo_agente(None, automacao, logger)

    def _executar_tool(self, automacao):
        """Modo tool: executa tool direto."""
        import time
        from gestao.views import TOOL_EXECUTORS, _tipo_alerta_para_tool
        from gestao.models import LogTool, Alerta, Proposta
        from gestao.ai_service import chat_agente
        from gestao.agent_actions import processar_acoes

        tool_slug = automacao.tool.slug
        executor = TOOL_EXECUTORS.get(tool_slug)

        inicio = time.time()

        try:
            if executor:
                resultado_texto = executor()
            else:
                resultado_texto = f'Tool "{tool_slug}" sem executor implementado'

            duracao = int((time.time() - inicio) * 1000)

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

            # Gerar alerta se problema
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

            # Encaminhar para agente se configurado
            if automacao.encaminhar_para:
                agente = automacao.encaminhar_para
                prompt_analise = (
                    f"A automacao '{automacao.tool.nome}' acabou de executar.\n\n"
                    f"## Resultado:\n{resultado_texto}\n\n"
                    f"Analise o resultado. Se identificar algo que precisa de acao, "
                    f"crie uma proposta ou alerta. Se estiver tudo normal, confirme."
                )
                try:
                    resposta_agente = chat_agente(agente.slug, prompt_analise)
                    resposta_limpa, acoes = processar_acoes(resposta_agente, agente.slug)
                    automacao.ultima_analise = resposta_limpa
                    automacao.save(update_fields=['ultima_analise'])

                    tem_acao = any(bloco in resposta_agente for bloco in ['---CRIAR_TAREFA', '---CRIAR_PROJETO', '---SALVAR_DOCUMENTO'])
                    if not tem_acao and len(resposta_limpa) > 100:
                        Proposta.objects.create(
                            agente=agente,
                            titulo=f'Analise: {automacao.tool.nome}',
                            descricao=resposta_limpa[:1000],
                            prioridade='media' if not tem_problema else 'alta',
                            tool=automacao.tool,
                        )
                except Exception as e:
                    logger.exception(f'Erro ao encaminhar para {agente.slug}')
                    automacao.ultima_analise = f'Erro: {str(e)[:200]}'
                    automacao.save(update_fields=['ultima_analise'])

        except Exception as e:
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
            raise
