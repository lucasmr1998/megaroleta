import os
import logging
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


def _truncar(texto, limite=2000):
    """Trunca texto longo adicionando indicador."""
    if not texto:
        return texto
    if len(texto) <= limite:
        return texto
    return texto[:limite] + "\n[... truncado ...]"


def get_client():
    """Retorna cliente OpenAI configurado."""
    api_key = os.environ.get('OPENAI_API_KEY', getattr(settings, 'OPENAI_API_KEY', ''))
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _is_gemini_model(modelo):
    """Verifica se o modelo e do Google Gemini."""
    return modelo.startswith('gemini-')


def _chat_gemini(modelo, system_message, messages_openai_format, max_tokens=4000, temperature=0.7):
    """Envia mensagem via Google GenAI API (SDK novo)."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get('GOOGLE_AI_API_KEY', '')
    if not api_key:
        return "Erro: GOOGLE_AI_API_KEY nao configurada no .env"

    client = genai.Client(api_key=api_key)

    # Converter formato OpenAI → Gemini contents
    contents = []
    for msg in messages_openai_format:
        if msg['role'] == 'system':
            continue  # vai como system_instruction
        role = 'model' if msg['role'] == 'assistant' else 'user'
        contents.append(types.Content(role=role, parts=[types.Part(text=msg['content'])]))

    response = client.models.generate_content(
        model=modelo,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_message,
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return response.text


def get_agentes_info():
    """Retorna lista de agentes ativos do banco no formato dict."""
    from gestao.models import Agente
    return [
        {
            'id': a.slug,
            'nome': a.nome,
            'descricao': a.descricao,
            'icone': a.icone,
            'cor': a.cor,
            'time': a.get_time_display(),
        }
        for a in Agente.objects.filter(ativo=True)
    ]


# Compatibilidade: AGENTES_INFO como property-like que busca do banco
class _AgentesInfoProxy:
    """Proxy que busca agentes do banco quando iterado."""
    def __iter__(self):
        return iter(get_agentes_info())
    def __len__(self):
        from gestao.models import Agente
        return Agente.objects.filter(ativo=True).count()
    def __getitem__(self, index):
        return get_agentes_info()[index]
    def __bool__(self):
        return True

AGENTES_INFO = _AgentesInfoProxy()


def carregar_prompt_agente(agente_id):
    """Carrega o prompt do agente a partir do banco."""
    from gestao.models import Agente
    agente = Agente.objects.filter(slug=agente_id, ativo=True).first()
    if not agente:
        return None
    return agente.prompt


def _buscar_processo_relevante(mensagem):
    """Busca processo na pasta 'processos' que seja relevante para a mensagem do CEO."""
    from gestao.models import Documento
    from django.db.models import Q

    msg_lower = mensagem.lower()

    # So buscar processos se parece um pedido de acao
    palavras_acao = ['crie', 'cria', 'criar', 'faca', 'faz', 'faça', 'gere', 'gera', 'gerar',
                     'escreva', 'escreve', 'produza', 'monte', 'elabore', 'prepare', 'execute']
    tem_acao = any(p in msg_lower for p in palavras_acao)
    if not tem_acao:
        return None

    processos = Documento.objects.filter(categoria='processo')
    if not processos.exists():
        return None

    # Buscar por relevancia: palavras do titulo/conteudo do processo na mensagem
    for proc in processos:
        # Extrair palavras-chave do titulo (ex: "Processo: Criar E-mail" -> ["criar", "email", "e-mail"])
        palavras_titulo = proc.titulo.lower().replace('processo:', '').strip().split()
        # Verificar se pelo menos 1 palavra-chave do processo aparece na mensagem
        match = sum(1 for p in palavras_titulo if len(p) > 2 and p in msg_lower)
        if match >= 1:
            return f"## {proc.titulo}\n\n{proc.conteudo}"

    return None


def carregar_contexto_leve():
    """Contexto reduzido (~15KB) com estrategia + metricas + projetos. Cacheado por 5 min."""
    from django.core.cache import cache
    cache_key = 'gestao:contexto_leve'
    cached = cache.get(cache_key)
    if cached:
        return cached

    contexto = ""

    # 1. Documentos estrategicos do banco (visiveis para agentes) — max 20 mais recentes
    try:
        from gestao.models import Documento
        docs = Documento.objects.filter(visivel_agentes=True).order_by('-data_atualizacao')[:20]
        for doc in docs:
            conteudo = _truncar(doc.conteudo, 2000)
            contexto += f"\n--- {doc.titulo} ---\n{conteudo}\n"
    except Exception:
        pass

    # 2. Projetos ativos (max 20 mais recentes) — otimizado com prefetch
    try:
        from gestao.models import Projeto, Tarefa
        from django.db.models import Count, Q, Prefetch

        tarefas_ativas_qs = Tarefa.objects.filter(
            status__in=['pendente', 'em_andamento', 'bloqueada']
        ).order_by('prioridade', 'data_limite')[:30]

        projetos = Projeto.objects.filter(ativo=True).annotate(
            _total_tarefas=Count('tarefas'),
            _tarefas_concluidas=Count('tarefas', filter=Q(tarefas__status='concluida')),
        ).prefetch_related(
            Prefetch('tarefas', queryset=tarefas_ativas_qs, to_attr='_tarefas_ativas')
        ).order_by('-data_atualizacao')[:20]

        if projetos:
            contexto += "\n--- PROJETOS ATIVOS ---\n"
            for p in projetos:
                total = p._total_tarefas
                concluidas = p._tarefas_concluidas

                contexto += f"\n## Projeto: {p.nome}\n"
                contexto += f"Status: {p.get_status_display()} | Prioridade: {p.get_prioridade_display()} | Progresso: {concluidas}/{total}\n"
                if p.responsavel:
                    contexto += f"Responsavel: {p.responsavel}\n"
                if p.objetivo:
                    contexto += f"Objetivo: {_truncar(p.objetivo, 500)}\n"
                if p.publico_alvo:
                    contexto += f"Publico-alvo: {_truncar(p.publico_alvo, 300)}\n"
                if p.criterios_sucesso:
                    contexto += f"Criterios de sucesso: {_truncar(p.criterios_sucesso, 500)}\n"
                if p.stakeholders:
                    contexto += f"Stakeholders:\n{_truncar(p.stakeholders, 500)}\n"
                if p.riscos:
                    contexto += f"Riscos: {_truncar(p.riscos, 500)}\n"
                if p.orcamento:
                    contexto += f"Orcamento: {p.orcamento}\n"
                if p.contexto_agentes:
                    contexto += f"Contexto extra: {_truncar(p.contexto_agentes, 1000)}\n"
                if p.data_inicio:
                    contexto += f"Inicio: {p.data_inicio.strftime('%d/%m/%Y')}"
                    if p.data_fim_prevista:
                        contexto += f" | Fim previsto: {p.data_fim_prevista.strftime('%d/%m/%Y')}"
                    contexto += "\n"

                if p._tarefas_ativas:
                    contexto += "Tarefas:\n"
                    for t in p._tarefas_ativas:
                        prazo = t.data_limite.strftime('%d/%m') if t.data_limite else "-"
                        contexto += f"  [{t.status}] {t.titulo} | {t.responsavel} | Prazo: {prazo}\n"
    except Exception:
        pass

    # 3. Metricas do sistema
    try:
        from roleta.models import MembroClube, ParticipanteRoleta
        from parceiros.models import Parceiro, CupomDesconto, ResgateCupom
        from indicacoes.models import Indicacao
        from django.db.models import Count

        contexto += "\n--- METRICAS DO SISTEMA ---\n"
        contexto += f"Membros: {MembroClube.objects.count()} ({MembroClube.objects.filter(validado=True).count()} validados)\n"
        contexto += f"Giros: {ParticipanteRoleta.objects.count()}\n"
        contexto += f"Parceiros ativos: {Parceiro.objects.filter(ativo=True).count()}\n"
        contexto += f"Cupons ativos: {CupomDesconto.objects.filter(ativo=True, status_aprovacao='aprovado').count()}\n"
        contexto += f"Resgates: {ResgateCupom.objects.count()} ({ResgateCupom.objects.filter(status='utilizado').count()} utilizados)\n"
        contexto += f"Indicacoes: {Indicacao.objects.count()} ({Indicacao.objects.filter(status='convertido').count()} convertidas)\n"

        cidades = MembroClube.objects.exclude(cidade__isnull=True).exclude(cidade='').values('cidade').annotate(total=Count('id')).order_by('-total')[:5]
        contexto += "Top cidades: " + ", ".join([f"{c['cidade']}({c['total']})" for c in cidades]) + "\n"
    except Exception:
        pass

    cache.set(cache_key, contexto, 300)  # 5 min
    return contexto


def carregar_contexto_completo():
    """Contexto completo incluindo entregas do banco."""
    contexto = carregar_contexto_leve()

    try:
        from gestao.models import Documento
        entregas = Documento.objects.filter(categoria='entrega').select_related('agente').order_by('-data_atualizacao')[:20]
        if entregas:
            contexto += "\n--- ENTREGAS DOS AGENTES ---\n"
            for e in entregas:
                conteudo = _truncar(e.conteudo, 2000)
                nome_agente = e.agente.nome if e.agente else 'Sem agente'
                contexto += f"\n--- Entrega {nome_agente}: {e.titulo} ---\n{conteudo}\n"
    except Exception:
        pass

    return contexto


def chat_agente(agente_id, mensagem, historico=None, modo='chat'):
    """Envia mensagem para um agente e retorna resposta.

    Args:
        modo: 'chat' (interativo com CEO) ou 'autonomo' (rotina de automacao)
    """
    from gestao.models import Agente

    agente = Agente.objects.filter(slug=agente_id, ativo=True).first()
    if not agente:
        return f"Erro: Agente '{agente_id}' não encontrado ou inativo."

    # Validar API key conforme provider
    if _is_gemini_model(agente.modelo):
        if not os.environ.get('GOOGLE_AI_API_KEY', ''):
            return "Erro: GOOGLE_AI_API_KEY nao configurada. Defina no .env."
        client = None  # Gemini nao usa client OpenAI
    else:
        client = get_client()
        if not client:
            return "Erro: API key não configurada. Defina OPENAI_API_KEY nas variáveis de ambiente."

    contexto = carregar_contexto_completo()

    # Selecionar prompt baseado no modo
    if modo == 'autonomo' and agente.prompt_autonomo:
        prompt_base = agente.prompt_autonomo
    else:
        prompt_base = agente.prompt

    system_message = prompt_base + "\n\n" + "="*60 + "\nCONTEXTO COMPLETO DO NEGOCIO (use para embasar suas respostas)\n" + "="*60 + "\n" + contexto

    # Processos so se aplicam no modo chat (no autonomo, vem vinculado a tarefa)
    if modo == 'chat':
        processo_contexto = _buscar_processo_relevante(mensagem)
        if processo_contexto:
            system_message += "\n\n" + "="*60 + "\nPROCESSO ENCONTRADO\n" + "="*60 + "\n"
            system_message += processo_contexto
            system_message += "\n\nIMPORTANTE: Existe um processo definido acima para esta acao. "
            system_message += "NAO execute os passos agora. O sistema vai mostrar botoes para o CEO executar passo a passo. "
            system_message += "Voce deve apenas responder com uma mensagem CURTA (2-3 frases) confirmando que encontrou o processo e o que ele faz. "
            system_message += "Exemplo: 'Encontrei o processo de criacao de e-mail. Ele tem 4 passos: coletar dados, redigir, gerar HTML e concluir. Use os botoes abaixo para executar cada etapa.'\n"

    # Instrucoes adicionais
    system_message += "\n\n--- INSTRUCOES ADICIONAIS ---\n"
    system_message += """- Sempre responda em portugues brasileiro.
- Use os dados reais do sistema quando disponíveis.

REGRA DE PROCESSOS:
- Se voce recebeu um bloco "PROCESSO ENCONTRADO" acima, NAO execute os passos. Apenas confirme que encontrou o processo em 2-3 frases. O sistema mostra botoes para execucao passo a passo.
- Se o CEO enviar uma mensagem que comeca com "Estou executando o passo", ai sim execute SOMENTE aquele passo especifico seguindo as instrucoes fornecidas.
- Se nao recebeu processo mas o CEO pediu uma acao, execute normalmente e sugira: "Nao encontrei processo definido para isso. Quer que eu crie um?"

REGRA CRITICA DE COMUNICACAO:
- Voce esta numa CONVERSA, nao numa apresentacao. Responda como um colega de trabalho.
- Perguntas casuais ("como esta?", "e ai?", "o que acha?", "review") = resposta CURTA (3-8 frases). SEM template, SEM readout, SEM headings ##.
- Perguntas rapidas ("quantos parceiros?", "qual o status?") = responda DIRETO em 1-3 frases.
- Pedido de acao ("crie tarefa", "salve isso") = execute e confirme em 1 frase.
- SOMENTE use readout completo com template quando o CEO pedir EXPLICITAMENTE ("me da um readout", "faz uma analise completa", "preciso de um plano detalhado").
- Na duvida, seja BREVE. O CEO pode pedir para aprofundar.
- Nao repita informacoes que o CEO ja sabe. Seja direto.

REGRA CRITICA DE IDENTIDADE:
- Voce e UM agente. Fale SOMENTE sobre SUA area.
- NUNCA fale pelos outros agentes. NUNCA inclua secoes como "### CTO:", "### CMO:" na sua resposta.
- Se o CEO perguntar algo que nao e da sua area, diga "isso e com o [agente X], posso falar sobre [sua area]".
- Cada agente fala por si. O CEO usa os botoes para pedir para outros agentes responderem.

REGRA CRITICA DE PROJETOS E TAREFAS:
- Antes de criar tarefas, SEMPRE siga este fluxo:
  1. Analise o contexto da conversa para entender o tema
  2. Verifique nos projetos ativos se existe um relacionado ao assunto
  3. Se encontrou um projeto que PARECE ser o certo, CONFIRME com o CEO: "Vou criar as tarefas no projeto [nome]. Confirma?"
  4. Se NAO existe projeto relacionado, CRIE o projeto primeiro com ---CRIAR_PROJETO--- e depois as tarefas dentro dele
  5. Se tiver duvida, PERGUNTE ao CEO em qual projeto criar
- NUNCA crie tarefas no primeiro projeto que encontrar sem confirmar
- NUNCA invente dados ou metricas. Use a tool consultar_dados para obter numeros reais do sistema.

REGRA CRITICA DE TOOLS NO CHAT:
- No chat, voce so pode usar blocos de acao que existem: CRIAR_TAREFA, CRIAR_PROJETO, ATUALIZAR_PROJETO, CRIAR_ETAPA, ATUALIZAR_TAREFA, SALVAR_DOCUMENTO, CONSULTAR_AGENTE, CONSULTAR_DOCUMENTO, LISTAR_DOCUMENTOS, CONSULTAR_DADOS, RESUMO_PROJETO.
- Tools como detectar_anomalia, validar_fluxos, consistencia_dados, health_check, rotina_customer_marketing sao AUTOMATICAS e rodam via automacao. NUNCA gere blocos com esses nomes no chat.
- Para buscar dados, SEMPRE use ---CONSULTAR_DADOS--- com a consulta desejada.
- Para salvar template de e-mail HTML, use ---SALVAR_EMAIL--- com assunto e conteudo HTML.

"""

    # Carregar tools do banco
    from gestao.models import ToolAgente
    tools = ToolAgente.objects.filter(ativo=True)

    tools_exec = tools.filter(tipo='executavel')
    tools_conhecimento = tools.filter(tipo='conhecimento')

    if tools_exec.exists():
        system_message += "\n\n--- ACOES QUE VOCE PODE EXECUTAR ---\n"
        system_message += """IMPORTANTE — REGRA DE EXECUCAO DE ACOES:
- Quando voce SUGERIR tarefas, etapas ou acoes, PRIMEIRO liste as sugestoes e PERGUNTE ao CEO: "Quer que eu crie essas tarefas no sistema?"
- SOMENTE inclua os blocos de acao (---CRIAR_TAREFA---, etc.) quando o CEO CONFIRMAR explicitamente ("sim", "crie", "pode criar", "faz isso").
- Quando o CEO PEDIR DIRETAMENTE para criar ("crie uma tarefa", "salve isso"), ai sim execute imediatamente com os blocos.
- Voce pode incluir MULTIPLOS blocos na mesma resposta (ex: criar projeto + criar etapas + criar tarefas).
- O sistema processa os blocos automaticamente. NAO descreva o que faria — EXECUTE com o bloco.

"""
        for i, tool in enumerate(tools_exec, 1):
            system_message += f"{i}. **{tool.nome}** — {tool.descricao}\n"
            system_message += f"{tool.prompt}\n"
            if tool.exemplo:
                system_message += f"\nExemplo:\n{tool.exemplo}\n"
            system_message += "\n"

    if tools_conhecimento.exists():
        system_message += "\n--- FERRAMENTAS DE CONHECIMENTO ---\n"
        system_message += "Use estas ferramentas quando o CEO pedir analises, copies, specs, etc.\n\n"
        for tool in tools_conhecimento:
            system_message += f"### {tool.nome}\n{tool.descricao}\n\n{tool.prompt}\n\n"

    # Listar agentes disponiveis para consulta
    outros = Agente.objects.filter(ativo=True).exclude(slug=agente_id).values_list('slug', flat=True)
    system_message += f"\nAgentes disponiveis para consulta: {', '.join(outros)}\n"

    messages = [{"role": "system", "content": system_message}]

    if historico:
        for msg in historico:
            messages.append({"role": msg['role'], "content": msg['content']})

    messages.append({"role": "user", "content": mensagem})

    try:
        if _is_gemini_model(agente.modelo):
            return _chat_gemini(
                modelo=agente.modelo,
                system_message=system_message,
                messages_openai_format=messages,
                max_tokens=4000,
                temperature=0.7,
            )
        else:
            response = client.chat.completions.create(
                model=agente.modelo,
                messages=messages,
                max_tokens=4000,
                temperature=0.7,
                timeout=60,
            )
            return response.choices[0].message.content
    except Exception as e:
        logger.exception(f'Erro API agente {agente_id}')
        return f"Erro na API: {str(e)}"


def moderador_decidir(mensagem, agentes_disponiveis, historico_reuniao=None):
    """
    Moderador DETERMINISTICO — sem IA, sem erro, sem custo.
    Analisa palavras-chave na mensagem e retorna lista com 1 agente.
    """
    import unicodedata
    def _normalizar(texto):
        nfkd = unicodedata.normalize('NFKD', texto.lower().strip())
        return ''.join(c for c in nfkd if not unicodedata.combining(c))

    msg = _normalizar(mensagem)

    # Regra 1: CEO mencionou agentes pelo nome (max 3)
    from gestao.models import Agente
    mencionados = []
    for agente in Agente.objects.filter(ativo=True):
        if agente.slug in msg or _normalizar(agente.nome) in msg:
            if agente.slug in agentes_disponiveis and agente.slug not in mencionados:
                mencionados.append(agente.slug)
    if mencionados:
        return mencionados[:3]

    # Regra 2: Palavras-chave por tema
    temas = [
        # Marketing
        (['go-to-market', 'gtm', 'posicionamento', 'messaging', 'battle card', 'one-pager'], 'pmm'),
        (['campanha', 'branding', 'estrategia de growth'], 'cmo'),
        (['conteudo', 'instagram', 'post', 'stories', 'reels', 'calendario editorial'], 'content'),
        (['lifecycle', 'reativacao', 'regua', 'membro inativo', 'comunicacao base'], 'custmkt'),
        (['funil', 'cac', 'cpa', 'midia paga', 'ads', 'aquisicao', 'conversao'], 'growth'),
        # Parcerias
        (['parceiro', 'prospeccao', 'abordagem', 'script', 'objecao'], 'b2b'),
        # Customer Success
        (['onboarding', 'jornada', 'health score', 'satisfacao'], 'cs'),
        (['suporte', 'duvida', 'ajuda', 'faq', 'atendimento', 'problema'], 'support'),
        (['comunidade', 'grupo', 'feedback', 'advocacy'], 'community'),
        # Tech
        (['tecnologia', 'arquitetura', 'decisao tecnica'], 'cto'),
        (['spec', 'feature', 'priorizacao', 'backlog', 'discovery', 'missao'], 'pm'),
        (['codigo', 'bug', 'review', 'teste', 'qualidade', 'seguranca'], 'qa'),
        (['deploy', 'servidor', 'infra', 'health check', 'monitoramento', 'uptime'], 'devops'),
        (['dados', 'relatorio', 'metricas', 'analise', 'cohort', 'anomalia', 'numeros'], 'analista'),
        # Executivo
        (['roadmap', 'produto', 'ux', 'mobile'], 'cpo'),
        (['financeiro', 'roi', 'custo', 'preco', 'investimento', 'payback', 'arpu'], 'cfo'),
    ]
    for palavras, agente_id in temas:
        for palavra in palavras:
            if palavra in msg and agente_id in agentes_disponiveis:
                return [agente_id]

    # Regra 3: CEO quer ouvir todos
    todos_keywords = ['todos', 'todo mundo', 'cada um', 'pessoal', 'equipe toda']
    for kw in todos_keywords:
        if kw in msg:
            return agentes_disponiveis[:3]

    # Regra 4: Fallback → CPO
    if 'cpo' in agentes_disponiveis:
        return ['cpo']

    return agentes_disponiveis[:1]
