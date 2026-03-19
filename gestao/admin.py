from django.contrib import admin
from .models import Projeto, Etapa, Tarefa, Nota

@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'responsavel', 'ativo', 'data_criacao']

@admin.register(Etapa)
class EtapaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'projeto', 'ordem']

@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'projeto', 'etapa', 'responsavel', 'status', 'prioridade']
    list_filter = ['status', 'prioridade', 'projeto']

@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ['tarefa', 'autor', 'data_criacao']
