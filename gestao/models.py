from django.db import models
from django.contrib.auth.models import User


class Projeto(models.Model):
    """Projeto de alto nivel (ex: Lancamento Floriano, Loja de Pontos)."""
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    responsavel = models.CharField(max_length=100, blank=True, help_text="Nome ou papel (ex: CEO, PMM)")
    data_inicio = models.DateField(null=True, blank=True)
    data_fim_prevista = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

    @property
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

    @property
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default='media')
    data_limite = models.DateField(null=True, blank=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    ordem = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)

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


class Reuniao(models.Model):
    """Reuniao com agentes de IA."""
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    agentes = models.CharField(max_length=200, help_text="IDs dos agentes separados por virgula (ex: cto,cpo,cfo)")
    ativa = models.BooleanField(default=True)
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
