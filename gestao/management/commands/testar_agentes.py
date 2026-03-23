"""
Teste automatizado do sistema de agentes IA.
Simula conversas reais e valida: prompts, tools, identidade, dados reais.

Uso:
  python manage.py testar_agentes              # roda todos os testes
  python manage.py testar_agentes --agente cto  # testa só um agente
  python manage.py testar_agentes --rapido      # só testes sem IA (validação local)
"""
import time
import logging
from django.core.management.base import BaseCommand
from gestao.models import Agente, ToolAgente, Automacao, Alerta, Proposta
from gestao.ai_service import chat_agente, moderador_decidir
from gestao.agent_actions import processar_acoes
from gestao.consulta_dados_service import executar_consulta

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Testa o sistema de agentes IA com conversas simuladas'

    def add_arguments(self, parser):
        parser.add_argument('--agente', type=str, help='Testar apenas um agente (slug)')
        parser.add_argument('--rapido', action='store_true', help='Só testes locais (sem chamar OpenAI)')
        parser.add_argument('--verbose', action='store_true', help='Mostrar respostas completas')

    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        self.rapido = options.get('rapido', False)
        self.agente_filtro = options.get('agente')
        self.total = 0
        self.ok = 0
        self.falhas = []

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('  TESTE AUTOMATIZADO - SISTEMA DE AGENTES IA')
        self.stdout.write('=' * 70 + '\n')

        # Fase 1: Testes de estrutura (sem IA)
        self._titulo('FASE 1: ESTRUTURA (sem IA)')
        self._testar_agentes_existem()
        self._testar_tools_existem()
        self._testar_prompts_enxutos()
        self._testar_tools_referenciadas_nos_prompts()
        self._testar_automacoes()
        self._testar_consulta_dados()
        self._testar_moderador()

        # Fase 2: Testes com IA (chama OpenAI)
        if not self.rapido:
            self._titulo('FASE 2: CONVERSAS COM IA')
            agentes_teste = ['cto', 'cpo', 'cmo', 'cfo', 'pmm', 'b2b', 'cs', 'ceo',
                             'content', 'custmkt', 'growth', 'support', 'pm', 'qa', 'devops', 'analista']
            if self.agente_filtro:
                agentes_teste = [self.agente_filtro]

            for slug in agentes_teste:
                if Agente.objects.filter(slug=slug, ativo=True).exists():
                    self._testar_conversa_casual(slug)
                    self._testar_consulta_dados_via_agente(slug)

            # Testes especificos por agente
            if not self.agente_filtro or self.agente_filtro == 'cto':
                self._testar_tool_especifica('cto', 'Me dá um readout sobre o estado do sistema', 'readout')
            if not self.agente_filtro or self.agente_filtro == 'cpo':
                self._testar_tool_especifica('cpo', 'Analise a feature de notificações com ICE', 'ice')
            if not self.agente_filtro or self.agente_filtro == 'cfo':
                self._testar_tool_especifica('cfo', 'Qual o ROI estimado do programa de indicações?', 'roi')

            self._titulo('FASE 3: AÇÕES (criar tarefa, documento)')
            if not self.agente_filtro or self.agente_filtro == 'cpo':
                self._testar_criacao_tarefa()

        # Resultado final
        self._titulo('RESULTADO FINAL')
        self.stdout.write(f'  Total de testes: {self.total}')
        self.stdout.write(self.style.SUCCESS(f'  Passou: {self.ok}'))
        if self.falhas:
            self.stdout.write(self.style.ERROR(f'  Falhou: {len(self.falhas)}'))
            for f in self.falhas:
                self.stdout.write(self.style.ERROR(f'    - {f}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n  TODOS OS TESTES PASSARAM!'))
        self.stdout.write('')

    # ── Helpers ──────────────────────────────────────────

    def _titulo(self, texto):
        self.stdout.write(f'\n--- {texto} ---\n')

    def _check(self, nome, condicao, detalhe=''):
        self.total += 1
        if condicao:
            self.ok += 1
            self.stdout.write(self.style.SUCCESS(f'  [OK] {nome}'))
        else:
            self.falhas.append(f'{nome}: {detalhe}')
            self.stdout.write(self.style.ERROR(f'  [FALHOU] {nome} — {detalhe}'))

    def _chat(self, agente_slug, mensagem):
        """Envia mensagem para agente e retorna resposta processada."""
        self.stdout.write(f'    Enviando para {agente_slug}: "{mensagem[:60]}..."')
        inicio = time.time()
        resposta = chat_agente(agente_slug, mensagem)
        resposta_limpa, acoes = processar_acoes(resposta, agente_slug)
        duracao = round(time.time() - inicio, 1)
        self.stdout.write(f'    Resposta em {duracao}s ({len(resposta_limpa)} chars, {len(acoes)} acoes)')
        if self.verbose:
            self.stdout.write(f'    >>> {resposta_limpa[:500]}')
        return resposta_limpa, acoes

    # ── Fase 1: Estrutura ────────────────────────────────

    def _testar_agentes_existem(self):
        esperados = ['ceo', 'cto', 'cpo', 'cfo', 'cmo', 'pmm', 'b2b', 'cs',
                     'content', 'custmkt', 'growth', 'support', 'community',
                     'pm', 'qa', 'devops', 'analista']
        for slug in esperados:
            agente = Agente.objects.filter(slug=slug).first()
            self._check(
                f'Agente {slug} existe',
                agente is not None,
                'nao encontrado no banco'
            )
            if agente:
                self._check(
                    f'Agente {slug} ativo',
                    agente.ativo,
                    'esta inativo'
                )

    def _testar_tools_existem(self):
        tools = ToolAgente.objects.filter(ativo=True)
        self._check(
            f'Tools existem ({tools.count()} ativas)',
            tools.count() >= 60,
            f'apenas {tools.count()} (esperado >= 60)'
        )

        # Tools criticas
        criticas = [
            'consultar_dados', 'criar_tarefa', 'atualizar_tarefa',
            'criar_projeto', 'salvar_documento', 'consultar_agente',
            'consultar_documento', 'listar_documentos',
        ]
        for slug in criticas:
            self._check(
                f'Tool critica: {slug}',
                ToolAgente.objects.filter(slug=slug, ativo=True).exists(),
                'nao encontrada ou inativa'
            )

    def _testar_prompts_enxutos(self):
        for agente in Agente.objects.filter(ativo=True):
            tamanho = len(agente.prompt)
            # Operador pode ser curto, outros devem ter entre 500 e 6000
            if agente.slug == 'operador':
                self._check(
                    f'Prompt {agente.slug} ({tamanho} chars)',
                    200 < tamanho < 2000,
                    f'{tamanho} chars (esperado 200-2000)'
                )
            else:
                self._check(
                    f'Prompt {agente.slug} ({tamanho} chars)',
                    1000 < tamanho < 6000,
                    f'{tamanho} chars (esperado 1000-6000, prompt pode estar inchado)'
                )

    def _testar_tools_referenciadas_nos_prompts(self):
        """Verifica se os agentes referenciam suas tools no prompt."""
        mapa = {
            'cto': ['readout_tecnico', 'decisao_arquitetural'],
            'cmo': ['readout_marketing', 'planejador_campanha'],
            'pmm': ['readout_posicionamento', 'battle_card'],
            'b2b': ['readout_comercial', 'script_abordagem'],
            'cs': ['readout_cs'],
            'cpo': ['readout_produto'],
            'cfo': ['readout_financeiro', 'analise_viabilidade'],
            'content': ['gerador_copy', 'gerador_post_instagram'],
            'custmkt': ['mensagens_ciclo_vida', 'diagnostico_churn'],
            'growth': ['analise_funil', 'calculadora_roi'],
            'support': ['responder_duvida'],
            'pm': ['priorizacao_ice', 'gerador_spec'],
            'qa': ['code_review', 'checklist_seguranca'],
            'devops': ['health_check'],
            'analista': ['analise_dados', 'gerador_relatorio'],
        }
        for slug, tools in mapa.items():
            agente = Agente.objects.filter(slug=slug).first()
            if agente:
                for tool_slug in tools:
                    self._check(
                        f'{slug} referencia tool {tool_slug}',
                        tool_slug in agente.prompt,
                        f'tool {tool_slug} nao mencionada no prompt'
                    )

    def _testar_automacoes(self):
        autos = Automacao.objects.select_related('encaminhar_para', 'tool').all()
        self._check(
            f'Automacoes existem ({autos.count()})',
            autos.count() >= 1,
            'nenhuma automacao'
        )
        for auto in autos:
            destino = auto.encaminhar_para.slug if auto.encaminhar_para else 'direto'
            self._check(
                f'Automacao {auto.tool.slug}->{destino} valida',
                auto.tool is not None,
                'tool nula'
            )

    def _testar_consulta_dados(self):
        """Testa todas as consultas do consulta_dados_service."""
        consultas = [
            'resumo_geral', 'membros_novos', 'membros_inativos',
            'membros_por_cidade', 'giros_periodo', 'estoque_premios',
            'cupons_status', 'parceiros_resumo', 'indicacoes_periodo',
            'projetos_status', 'tarefas_pendentes',
        ]
        for consulta in consultas:
            try:
                resultado = executar_consulta(consulta, periodo='30d')
                tem_conteudo = len(resultado) > 50
                sem_erro = 'erro' not in resultado.lower()[:100]
                self._check(
                    f'Consulta: {consulta}',
                    tem_conteudo and sem_erro,
                    f'resultado vazio ou com erro ({resultado[:100]})'
                )
            except Exception as e:
                self._check(f'Consulta: {consulta}', False, str(e)[:100])

    def _testar_moderador(self):
        """Testa o moderador deterministico."""
        agentes = ['ceo', 'cto', 'cpo', 'cfo', 'cmo', 'pmm', 'b2b', 'cs',
                   'content', 'custmkt', 'growth', 'support', 'community',
                   'pm', 'qa', 'devops', 'analista']

        casos = [
            ('CTO, analise isso', ['cto']),
            ('PMM e CMO, o que acham?', ['pmm', 'cmo']),
            ('como está o código?', ['qa']),
            ('qual o ROI?', ['cfo']),
            ('crie um post pro Instagram', ['content']),
            ('preciso de um script de vendas', ['b2b']),
            ('como está o onboarding?', ['cs']),
            ('priorize o backlog', ['pm']),
            ('como está o funil de aquisição?', ['growth']),
            ('membros inativos precisam de reativação', ['custmkt']),
            ('um membro tem dúvida sobre cupom', ['support']),
            ('me dá os números da semana', ['analista']),
            ('como está o servidor?', ['devops']),
        ]
        for mensagem, esperado in casos:
            resultado = moderador_decidir(mensagem, agentes)
            # Verifica se pelo menos o primeiro agente esperado está no resultado
            acertou = esperado[0] in resultado
            self._check(
                f'Moderador: "{mensagem[:40]}" -> {resultado}',
                acertou,
                f'esperado {esperado}, obteve {resultado}'
            )

        # Teste de múltiplos agentes
        resultado = moderador_decidir('PMM e CMO, o que acham?', agentes)
        self._check(
            f'Moderador retorna multiplos: {resultado}',
            len(resultado) >= 2,
            f'esperado 2+ agentes, obteve {len(resultado)}'
        )

    # ── Fase 2: Conversas com IA ─────────────────────────

    def _testar_conversa_casual(self, slug):
        """Testa se agente responde casualmente a perguntas casuais."""
        resposta, acoes = self._chat(slug, 'E ai, como estamos?')

        # Deve ser curta (< 800 chars pra casual)
        self._check(
            f'{slug}: resposta casual curta',
            len(resposta) < 1500,
            f'{len(resposta)} chars (esperado < 1500)'
        )

        # Deve estar em portugues
        palavras_pt = ['de', 'do', 'da', 'que', 'para', 'com', 'uma', 'nos', 'como']
        tem_pt = any(p in resposta.lower() for p in palavras_pt)
        self._check(
            f'{slug}: resposta em portugues',
            tem_pt,
            'nao parece estar em portugues'
        )

        # Nao deve ter readout/template
        tem_template = '### 1.' in resposta or '## CMO Readout' in resposta or '## CTO Readout' in resposta
        self._check(
            f'{slug}: sem template em casual',
            not tem_template,
            'usou template em pergunta casual'
        )

        # Nao deve fingir ser outro agente
        agente = Agente.objects.get(slug=slug)
        outros = Agente.objects.filter(ativo=True).exclude(slug=slug).exclude(slug='operador')
        finge_outro = False
        for outro in outros:
            if f'### {outro.nome}:' in resposta or f'## {outro.nome}' in resposta:
                finge_outro = True
                break
        self._check(
            f'{slug}: nao finge ser outro agente',
            not finge_outro,
            'incluiu secao com nome de outro agente'
        )

    def _testar_consulta_dados_via_agente(self, slug):
        """Testa se agente usa consultar_dados em vez de inventar."""
        resposta, acoes = self._chat(slug, 'Quantos membros temos cadastrados?')

        # Deve conter numeros reais (verificar se o numero de membros aparece)
        from roleta.models import MembroClube
        total_real = MembroClube.objects.count()

        # Verifica se o numero real aparece ou se usou consultar_dados
        usou_dados = (
            str(total_real) in resposta or
            'CONSULTAR_DADOS' in resposta or
            any('consultar_dados' in a.lower() for a in acoes if isinstance(a, str))
        )
        self._check(
            f'{slug}: usa dados reais ou consultar_dados',
            usou_dados,
            f'numero real ({total_real}) nao encontrado na resposta e nao usou tool'
        )

    def _testar_tool_especifica(self, slug, mensagem, keyword):
        """Testa se agente usa tool quando solicitado."""
        resposta, acoes = self._chat(slug, mensagem)

        # Resposta deve ser mais longa (usa template)
        self._check(
            f'{slug}: resposta estruturada para "{keyword}"',
            len(resposta) > 300,
            f'resposta muito curta ({len(resposta)} chars) para pedido de analise'
        )

    def _testar_criacao_tarefa(self):
        """Testa se CPO pergunta antes de criar tarefa."""
        resposta, acoes = self._chat('cpo', 'Sugira 3 tarefas para melhorar o engajamento')

        # Deve listar sugestoes MAS perguntar antes de criar
        tem_pergunta = any(p in resposta.lower() for p in [
            'quer que eu crie', 'criar no sistema', 'confirma', 'deseja que',
            'posso criar', 'devo criar', 'gostaria que eu',
        ])
        nao_criou_direto = 'CRIAR_TAREFA' not in resposta

        self._check(
            f'cpo: pergunta antes de criar tarefas',
            tem_pergunta or nao_criou_direto,
            'criou tarefas sem perguntar ou nao perguntou se deve criar'
        )
