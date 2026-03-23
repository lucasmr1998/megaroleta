from functools import cached_property
from django.db import models
from django.contrib.auth.models import User


class Projeto(models.Model):
    """Projeto completo com contexto para agentes IA trabalharem."""
    STATUS_CHOICES = [
        ('planejamento', 'Planejamento'),
        ('em_andamento', 'Em Andamento'),
        ('pausado', 'Pausado'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]
    PRIORIDADE_CHOICES = [
        ('critica', 'Crítica'),
        ('alta', 'Alta'),
        ('media', 'Média'),
        ('baixa', 'Baixa'),
    ]

    # Basico
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, help_text="Descricao geral do projeto")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planejamento', db_index=True)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default='media')

    # Estrategia
    objetivo = models.TextField(blank=True, help_text="O que este projeto deve alcancar? Qual problema resolve?")
    publico_alvo = models.TextField(blank=True, help_text="Para quem? (ex: membros Floriano, parceiros restaurantes)")
    criterios_sucesso = models.TextField(blank=True, help_text="Como sabemos que deu certo? KPIs e metas concretas")
    riscos = models.TextField(blank=True, help_text="O que pode dar errado? Dependencias externas?")
    premissas = models.TextField(blank=True, help_text="Premissas assumidas (ex: parceiro X vai aceitar, budget aprovado)")

    # Pessoas
    responsavel = models.CharField(max_length=100, blank=True, help_text="Dono do projeto (ex: CEO, PMM)")
    stakeholders = models.TextField(blank=True, help_text="Quem esta envolvido e qual o papel de cada um (1 por linha: Nome - Papel)")

    # Datas
    data_inicio = models.DateField(null=True, blank=True)
    data_fim_prevista = models.DateField(null=True, blank=True)

    # Contexto para agentes
    contexto_agentes = models.TextField(blank=True, help_text="Informacoes extras que os agentes IA devem saber sobre este projeto")
    orcamento = models.TextField(blank=True, help_text="Budget disponivel, custos previstos")

    # Controle
    ativo = models.BooleanField(default=True, db_index=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    @cached_property
    def progresso(self):
        tarefas = self.tarefas.all()
        if not tarefas:
            return 0
        concluidas = tarefas.filter(status='concluida').count()
        return round((concluidas / tarefas.count()) * 100)

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ['-data_criacao']


class Etapa(models.Model):
    """Etapa/fase de um projeto (ex: Semana 1, Semana 2)."""
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='etapas')
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    ordem = models.IntegerField(default=0)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.projeto.nome} → {self.nome}"

    @cached_property
    def progresso(self):
        tarefas = self.tarefas.all()
        if not tarefas:
            return 0
        concluidas = tarefas.filter(status='concluida').count()
        return round((concluidas / tarefas.count()) * 100)

    class Meta:
        verbose_name = "Etapa"
        verbose_name_plural = "Etapas"
        ordering = ['ordem']


class Tarefa(models.Model):
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em Andamento'),
        ('concluida', 'Concluída'),
        ('bloqueada', 'Bloqueada'),
    ]
    PRIORIDADE_CHOICES = [
        ('critica', 'Crítica'),
        ('alta', 'Alta'),
        ('media', 'Média'),
        ('baixa', 'Baixa'),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='tarefas')
    etapa = models.ForeignKey(Etapa, on_delete=models.SET_NULL, null=True, blank=True, related_name='tarefas')
    titulo = models.CharField(max_length=300)
    descricao = models.TextField(blank=True)
    responsavel = models.CharField(max_length=100, blank=True, help_text="Ex: CEO, Comercial B2B, CTO")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', db_index=True)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default='media')
    data_limite = models.DateField(null=True, blank=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    ordem = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)

    # Campos estruturados para execucao por agentes
    objetivo = models.TextField(blank=True, help_text="O que esta tarefa deve alcancar")
    contexto = models.TextField(blank=True, help_text="Inputs, referencias, publico-alvo, tom, restricoes")
    passos = models.TextField(blank=True, help_text="Passo-a-passo numerado que o agente deve seguir")
    entregavel = models.CharField(max_length=300, blank=True, help_text="O que deve ser produzido (ex: documento de e-mail)")
    criterios_aceite = models.TextField(blank=True, help_text="Como saber que a tarefa esta concluida corretamente")
    pasta_destino = models.ForeignKey(
        'PastaDocumento', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tarefas_destino', help_text="Pasta onde o entregavel deve ser salvo"
    )
    processo = models.ForeignKey(
        'Documento', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tarefas_processo', help_text="Documento de processo/receita que originou esta tarefa"
    )

    # Delegacao entre agentes
    criado_por_agente = models.ForeignKey(
        'Agente', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tarefas_criadas',
        help_text="Agente que criou/delegou esta tarefa (None = criada por humano)"
    )
    nivel_delegacao = models.IntegerField(
        default=0,
        help_text="0=humano, 1=delegada por agente, 2=sub-delegada. Max 2."
    )
    log_execucao = models.TextField(
        blank=True, default='',
        help_text="Historico de execucao da tarefa (preenchido automaticamente)"
    )

    def registrar_log(self, mensagem):
        """Adiciona entrada no log de execucao com timestamp."""
        from django.utils import timezone
        ts = timezone.now().strftime('%d/%m %H:%M')
        self.log_execucao += f"[{ts}] {mensagem}\n"
        self.save(update_fields=['log_execucao'])

    def __str__(self):
        return self.titulo

    class Meta:
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"
        ordering = ['ordem', '-prioridade', 'data_limite']


class Nota(models.Model):
    """Notas/comentarios em tarefas (historico)."""
    tarefa = models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name='notas')
    autor = models.CharField(max_length=100, default='CEO')
    texto = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.autor}: {self.texto[:50]}"

    class Meta:
        ordering = ['-data_criacao']


class PastaDocumento(models.Model):
    """Pasta para organizar documentos. Pode ter subpastas (pai)."""
    nome = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subpastas')
    icone = models.CharField(max_length=50, default='fas fa-folder', blank=True)
    cor = models.CharField(max_length=20, default='#3b82f6', blank=True)
    ordem = models.IntegerField(default=0)

    def __str__(self):
        if self.pai:
            return f"{self.pai.nome} / {self.nome}"
        return self.nome

    @property
    def caminho(self):
        """Retorna caminho completo: Pai / Filho / Neto."""
        partes = [self.nome]
        atual = self.pai
        while atual:
            partes.insert(0, atual.nome)
            atual = atual.pai
        return ' / '.join(partes)

    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name_plural = 'Pastas de Documentos'


class Documento(models.Model):
    """Documento unificado: estrategia, regras, entregas dos agentes, contexto, etc."""
    CATEGORIA_CHOICES = [
        ('estrategia', 'Estratégia'),
        ('regras', 'Regras de Negócio'),
        ('roadmap', 'Roadmap'),
        ('decisoes', 'Decisões'),
        ('entrega', 'Entrega de Agente'),
        ('sessao', 'Sessão com Agente'),
        ('contexto', 'Base de Conhecimento'),
        ('relatorio', 'Relatório'),
        ('email', 'Template de E-mail'),
        ('processo', 'Processo'),
        ('imagem', 'Imagem Gerada'),
        ('outro', 'Outro'),
    ]
    titulo = models.CharField(max_length=300)
    slug = models.SlugField(max_length=100, unique=True, help_text="Identificador unico (ex: estrategia, regras-negocio)")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='outro', db_index=True)
    pasta = models.ForeignKey(PastaDocumento, on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos', help_text="Pasta de organizacao (opcional)")
    agente = models.ForeignKey('Agente', on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos', help_text="Agente autor (para entregas)")
    conteudo = models.TextField(help_text="Conteudo em markdown", blank=True)
    arquivo = models.ImageField(upload_to='geradas/', blank=True, null=True, help_text="Imagem gerada por IA")
    resumo = models.TextField(blank=True, help_text="Resumo curto para contexto dos agentes")
    descricao = models.CharField(max_length=300, blank=True, help_text="Descricao curta do documento")
    visivel_agentes = models.BooleanField(default=True, help_text="Se True, agentes IA recebem este doc como contexto")
    ordem = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.agente:
            return f"{self.agente.nome}: {self.titulo}"
        return self.titulo

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['ordem', 'categoria', 'titulo']


class Agente(models.Model):
    """Agente de IA configuravel pelo painel."""
    TIME_CHOICES = [
        ('executivo', 'C-Level'),
        ('marketing', 'Marketing'),
        ('sucesso', 'Customer Success'),
        ('parcerias', 'Parcerias'),
        ('tech', 'Produto & Tech'),
    ]
    slug = models.SlugField(max_length=20, unique=True, help_text="ID unico (ex: cto, cmo, b2b)")
    nome = models.CharField(max_length=100, help_text="Nome de exibicao (ex: CTO, Comercial B2B)")
    descricao = models.CharField(max_length=200, help_text="Descricao curta (ex: Tecnologia e Arquitetura)")
    icone = models.CharField(max_length=50, default='fas fa-robot', help_text="Classe FontAwesome")
    cor = models.CharField(max_length=10, default='#3b82f6', help_text="Cor hex")
    time = models.CharField(max_length=20, choices=TIME_CHOICES, default='executivo')
    prompt = models.TextField(help_text="System prompt para chat interativo (markdown)")
    prompt_autonomo = models.TextField(
        blank=True, default='',
        help_text="System prompt para modo autonomo/automacao (se vazio, usa o prompt principal)"
    )
    modelo = models.CharField(max_length=50, default='gpt-4o-mini', help_text="Modelo da OpenAI")
    ativo = models.BooleanField(default=True, db_index=True)
    ordem = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Agente"
        verbose_name_plural = "Agentes"
        ordering = ['ordem', 'nome']


class MensagemChat(models.Model):
    """Mensagem individual no chat 1:1 com agente."""
    ROLE_CHOICES = [
        ('user', 'Usuário'),
        ('assistant', 'Agente'),
    ]
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name='mensagens_chat')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    conteudo = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.conteudo[:50]}"

    class Meta:
        ordering = ['data_criacao']


class ToolAgente(models.Model):
    """Ferramenta disponivel para os agentes IA."""
    TIPO_CHOICES = [
        ('executavel', 'Executável'),
        ('conhecimento', 'Conhecimento'),
    ]
    slug = models.SlugField(max_length=50, unique=True, help_text="ID unico (ex: salvar_documento, calculadora_roi)")
    nome = models.CharField(max_length=100, help_text="Nome de exibicao")
    descricao = models.CharField(max_length=300, help_text="Descricao curta do que a tool faz")
    icone = models.CharField(max_length=50, default='fas fa-wrench', help_text="Classe FontAwesome")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='conhecimento')
    prompt = models.TextField(help_text="Instrucoes/prompt da tool (como o agente deve usar)")
    exemplo = models.TextField(blank=True, help_text="Exemplo de uso ou formato de saida")
    ativo = models.BooleanField(default=True, db_index=True)
    ordem = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Tool de Agente"
        verbose_name_plural = "Tools de Agentes"
        ordering = ['ordem', 'nome']


class LogTool(models.Model):
    """Log de execucao de tools pelos agentes."""
    tool = models.ForeignKey(ToolAgente, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    tool_slug = models.CharField(max_length=50, help_text="Slug da tool no momento da execucao")
    agente = models.ForeignKey(Agente, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_tools')
    resultado = models.TextField(help_text="Resultado da execucao")
    sucesso = models.BooleanField(default=True)
    tempo_ms = models.IntegerField(null=True, blank=True, help_text="Tempo de execucao em ms")
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tool_slug} por {self.agente} — {'OK' if self.sucesso else 'ERRO'}"

    class Meta:
        verbose_name = "Log de Tool"
        verbose_name_plural = "Logs de Tools"
        ordering = ['-data_criacao']


class Reuniao(models.Model):
    """Reuniao com agentes de IA."""
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    agentes = models.CharField(max_length=200, help_text="IDs dos agentes separados por virgula (ex: cto,cpo,cfo)")
    ativa = models.BooleanField(default=True, db_index=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

    @property
    def agentes_lista(self):
        return [a.strip() for a in self.agentes.split(',') if a.strip()]

    @property
    def total_mensagens(self):
        return self.mensagens.count()

    class Meta:
        verbose_name = "Reunião"
        verbose_name_plural = "Reuniões"
        ordering = ['-data_criacao']


class MensagemReuniao(models.Model):
    """Mensagem dentro de uma reuniao."""
    TIPO_CHOICES = [
        ('ceo', 'CEO'),
        ('agente', 'Agente'),
        ('moderador', 'Moderador'),
    ]
    reuniao = models.ForeignKey(Reuniao, on_delete=models.CASCADE, related_name='mensagens')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    agente_id = models.CharField(max_length=20, blank=True, help_text="ID do agente (se tipo=agente)")
    agente_nome = models.CharField(max_length=100, blank=True)
    conteudo = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agente_nome or self.tipo}: {self.conteudo[:50]}"

    class Meta:
        ordering = ['data_criacao']


class Automacao(models.Model):
    """Trigger periodico: executa tool ou acorda agente para trabalhar."""
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('pausado', 'Pausado'),
        ('erro', 'Com Erro'),
    ]
    MODO_CHOICES = [
        ('tool', 'Executar Tool'),
        ('agente', 'Acordar Agente'),
    ]
    modo = models.CharField(max_length=10, choices=MODO_CHOICES, default='tool',
        help_text="tool: executa tool direto. agente: acorda agente para trabalhar sozinho.")
    tool = models.ForeignKey('ToolAgente', on_delete=models.CASCADE,
        null=True, blank=True, related_name='automacoes',
        help_text="Tool que sera executada (modo=tool)")
    agente = models.ForeignKey('Agente', on_delete=models.CASCADE,
        null=True, blank=True, related_name='automacoes_agente',
        help_text="Agente que sera acordado (modo=agente)")
    encaminhar_para = models.ForeignKey('Agente', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='automacoes_encaminhadas',
        help_text="Agente que recebe o resultado para analisar (modo=tool, opcional)")
    intervalo_horas = models.IntegerField(default=24,
        help_text="Intervalo entre execucoes em horas")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo', db_index=True)
    ultima_execucao = models.DateTimeField(null=True, blank=True)
    ultimo_resultado = models.TextField(blank=True)
    ultima_analise = models.TextField(blank=True,
        help_text="Ultima analise do agente sobre o resultado")
    total_execucoes = models.IntegerField(default=0)
    total_erros = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True, db_index=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.modo == 'agente' and self.agente:
            return f"{self.agente.nome} (rotina)"
        destino = f" -> {self.encaminhar_para.nome}" if self.encaminhar_para else ""
        return f"{self.tool.nome if self.tool else '?'}{destino}"

    @property
    def nome(self):
        if self.modo == 'agente' and self.agente:
            return f"Rotina {self.agente.nome}"
        return self.tool.nome if self.tool else '?'

    @property
    def descricao(self):
        if self.modo == 'agente' and self.agente:
            return self.agente.descricao
        return self.tool.descricao if self.tool else ''

    @property
    def icone(self):
        if self.modo == 'agente' and self.agente:
            return self.agente.icone
        return self.tool.icone if self.tool and hasattr(self.tool, 'icone') else 'fas fa-bolt'

    @property
    def cor(self):
        if self.modo == 'agente' and self.agente:
            return self.agente.cor
        if self.encaminhar_para:
            return self.encaminhar_para.cor
        return '#64748b'

    class Meta:
        ordering = ['modo', 'agente__nome', 'tool__nome']
        verbose_name = "Automacao"
        verbose_name_plural = "Automacoes"


class FAQCategoria(models.Model):
    """Categoria de FAQ gerada automaticamente."""
    nome = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    icone = models.CharField(max_length=50, default='fas fa-question-circle')
    cor = models.CharField(max_length=10, default='#3b82f6')
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = "Categoria FAQ"
        verbose_name_plural = "Categorias FAQ"


class FAQItem(models.Model):
    """Pergunta/resposta de FAQ gerada por IA ou manualmente."""
    categoria = models.ForeignKey(FAQCategoria, on_delete=models.CASCADE, related_name='itens')
    pergunta = models.CharField(max_length=500)
    resposta = models.TextField()
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True, db_index=True)
    gerado_por_ia = models.BooleanField(default=False)
    hash_dados_fonte = models.CharField(max_length=64, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pergunta[:80]

    class Meta:
        ordering = ['categoria__ordem', 'ordem']
        verbose_name = "Item FAQ"
        verbose_name_plural = "Itens FAQ"


class Alerta(models.Model):
    """Alerta gerado automaticamente pelo monitoramento dos agentes."""
    SEVERIDADE_CHOICES = [
        ('info', 'Informação'),
        ('aviso', 'Aviso'),
        ('critico', 'Crítico'),
    ]
    TIPO_CHOICES = [
        ('health', 'Saúde do Sistema'),
        ('estoque', 'Estoque Baixo'),
        ('churn', 'Risco de Churn'),
        ('metrica', 'Métrica Anormal'),
        ('erro', 'Erro de Execução'),
        ('outro', 'Outro'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='outro', db_index=True)
    severidade = models.CharField(max_length=10, choices=SEVERIDADE_CHOICES, default='info', db_index=True)
    titulo = models.CharField(max_length=300)
    descricao = models.TextField(blank=True)
    agente = models.ForeignKey('Agente', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='alertas', help_text="Agente que gerou o alerta")
    tool = models.ForeignKey('ToolAgente', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='alertas', help_text="Tool que gerou o alerta")
    dados_json = models.JSONField(default=dict, blank=True,
        help_text="Dados extras estruturados (métricas, IDs afetados, etc.)")
    lido = models.BooleanField(default=False, db_index=True)
    resolvido = models.BooleanField(default=False, db_index=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_severidade_display()}] {self.titulo}"

    class Meta:
        ordering = ['-data_criacao']
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"


class Proposta(models.Model):
    """Ação proposta por um agente que aguarda aprovação do CEO."""
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovada', 'Aprovada'),
        ('rejeitada', 'Rejeitada'),
        ('executada', 'Executada'),
        ('erro', 'Erro na Execução'),
    ]
    PRIORIDADE_CHOICES = [
        ('critica', 'Crítica'),
        ('alta', 'Alta'),
        ('media', 'Média'),
        ('baixa', 'Baixa'),
    ]
    agente = models.ForeignKey('Agente', on_delete=models.CASCADE,
        related_name='propostas', help_text="Agente que propôs a ação")
    titulo = models.CharField(max_length=300)
    descricao = models.TextField(help_text="O que será feito e por quê")
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default='media')
    tool = models.ForeignKey('ToolAgente', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='propostas', help_text="Tool que será executada após aprovação")
    dados_execucao = models.JSONField(default=dict, blank=True,
        help_text="Parâmetros para execução da tool (ex: bloco de ação)")
    alerta = models.ForeignKey('Alerta', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='propostas', help_text="Alerta que originou esta proposta")
    reuniao = models.ForeignKey('Reuniao', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='propostas', help_text="Reunião onde foi discutida")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente', db_index=True)
    motivo_rejeicao = models.TextField(blank=True)
    resultado_execucao = models.TextField(blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_decisao = models.DateTimeField(null=True, blank=True)
    data_execucao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.get_status_display()}] {self.titulo}"

    class Meta:
        ordering = ['-data_criacao']
        verbose_name = "Proposta"
        verbose_name_plural = "Propostas"
