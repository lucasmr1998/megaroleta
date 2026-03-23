from django.urls import path
from . import views

urlpatterns = [
    # Dashboard CEO
    path('dashboard/gestao/', views.dashboard_ceo, name='dashboard_ceo'),
    path('dashboard/gestao/projetos/', views.gestao_projetos, name='gestao_projetos'),
    path('dashboard/gestao/projetos/<int:projeto_id>/editar/', views.gestao_projeto_editar, name='gestao_projeto_editar'),
    path('dashboard/gestao/projetos/<int:projeto_id>/toggle/', views.gestao_projeto_toggle, name='gestao_projeto_toggle'),
    path('dashboard/gestao/projetos/<int:projeto_id>/excluir/', views.gestao_projeto_excluir, name='gestao_projeto_excluir'),
    path('dashboard/gestao/kanban/<int:projeto_id>/', views.kanban, name='kanban'),
    path('dashboard/gestao/kanban/<int:projeto_id>/tarefa/<int:tarefa_id>/', views.gestao_tarefa_detalhe, name='gestao_tarefa_detalhe'),
    path('dashboard/gestao/kanban/<int:projeto_id>/tarefa/<int:tarefa_id>/editar/', views.gestao_tarefa_editar, name='gestao_tarefa_editar'),

    # Sessões CRUD
    path('dashboard/gestao/sessoes/', views.gestao_sessoes, name='gestao_sessoes'),
    path('dashboard/gestao/sessoes/criar/', views.gestao_sessao_criar, name='gestao_sessao_criar'),
    path('dashboard/gestao/sessoes/<int:sessao_id>/', views.gestao_sessao_detalhe, name='gestao_sessao_detalhe'),
    path('dashboard/gestao/sessoes/<int:sessao_id>/editar/', views.gestao_sessao_editar, name='gestao_sessao_editar'),
    path('dashboard/gestao/sessoes/<int:sessao_id>/excluir/', views.gestao_sessao_excluir, name='gestao_sessao_excluir'),

    # Entregas CRUD
    path('dashboard/gestao/entregas/', views.gestao_entregas, name='gestao_entregas'),
    path('dashboard/gestao/entregas/criar/', views.gestao_entrega_criar, name='gestao_entrega_criar'),
    path('dashboard/gestao/entregas/<int:entrega_id>/', views.gestao_entrega_detalhe, name='gestao_entrega_detalhe'),
    path('dashboard/gestao/entregas/<int:entrega_id>/editar/', views.gestao_entrega_editar, name='gestao_entrega_editar'),
    path('dashboard/gestao/entregas/<int:entrega_id>/excluir/', views.gestao_entrega_excluir, name='gestao_entrega_excluir'),

    # Documentos CRUD
    path('dashboard/gestao/documentos/', views.gestao_documentos, name='gestao_documentos'),
    path('dashboard/gestao/documentos/criar/', views.gestao_documento_criar, name='gestao_documento_criar'),
    path('dashboard/gestao/documentos/<int:documento_id>/', views.gestao_documento_detalhe, name='gestao_documento_detalhe'),
    path('dashboard/gestao/documentos/<int:documento_id>/editar/', views.gestao_documento_editar, name='gestao_documento_editar'),
    path('dashboard/gestao/documentos/<int:documento_id>/excluir/', views.gestao_documento_excluir, name='gestao_documento_excluir'),

    # Agentes CRUD
    path('dashboard/gestao/agentes/', views.gestao_agentes, name='gestao_agentes'),
    path('dashboard/gestao/agentes/criar/', views.gestao_agente_criar, name='gestao_agente_criar'),
    path('dashboard/gestao/agentes/<int:agente_id>/editar/', views.gestao_agente_editar, name='gestao_agente_editar'),
    path('dashboard/gestao/agentes/<int:agente_id>/toggle/', views.gestao_agente_toggle, name='gestao_agente_toggle'),

    # Tools CRUD
    path('dashboard/gestao/tools/', views.gestao_tools, name='gestao_tools'),
    path('dashboard/gestao/tools/criar/', views.gestao_tool_criar, name='gestao_tool_criar'),
    path('dashboard/gestao/tools/<int:tool_id>/editar/', views.gestao_tool_editar, name='gestao_tool_editar'),
    path('dashboard/gestao/tools/<int:tool_id>/toggle/', views.gestao_tool_toggle, name='gestao_tool_toggle'),
    path('dashboard/gestao/tools/<int:tool_id>/excluir/', views.gestao_tool_excluir, name='gestao_tool_excluir'),

    # Automações
    path('dashboard/gestao/automacoes/', views.gestao_automacoes, name='gestao_automacoes'),
    path('dashboard/gestao/automacoes/<int:automacao_id>/editar/', views.gestao_automacao_editar, name='gestao_automacao_editar'),
    path('dashboard/gestao/automacoes/<int:automacao_id>/executar/', views.gestao_automacao_executar, name='gestao_automacao_executar'),
    path('dashboard/gestao/automacoes/<int:automacao_id>/toggle/', views.gestao_automacao_toggle, name='gestao_automacao_toggle'),
    path('dashboard/gestao/mapa/', views.gestao_mapa, name='gestao_mapa'),
    path('dashboard/gestao/automacoes/faq/', views.gestao_automacao_faq, name='gestao_automacao_faq'),
    path('dashboard/gestao/automacoes/health/', views.gestao_automacao_health, name='gestao_automacao_health'),
    path('dashboard/gestao/logs/', views.gestao_logs, name='gestao_logs'),

    # Propostas (fila de aprovação)
    path('dashboard/gestao/propostas/', views.gestao_propostas, name='gestao_propostas'),
    path('dashboard/gestao/propostas/<int:proposta_id>/', views.gestao_proposta_detalhe, name='gestao_proposta_detalhe'),
    path('dashboard/gestao/propostas/<int:proposta_id>/aprovar/', views.gestao_proposta_aprovar, name='gestao_proposta_aprovar'),
    path('dashboard/gestao/propostas/<int:proposta_id>/rejeitar/', views.gestao_proposta_rejeitar, name='gestao_proposta_rejeitar'),

    # Alertas
    path('dashboard/gestao/alertas/', views.gestao_alertas, name='gestao_alertas'),
    path('dashboard/gestao/alertas/<int:alerta_id>/resolver/', views.gestao_alerta_resolver, name='gestao_alerta_resolver'),
    path('dashboard/gestao/alertas/<int:alerta_id>/ler/', views.gestao_alerta_ler, name='gestao_alerta_ler'),

    # Sala de Agentes
    path('dashboard/gestao/sala/', views.sala_agentes, name='sala_agentes'),
    path('dashboard/gestao/sala/reuniao/criar/', views.sala_reuniao_criar, name='sala_reuniao_criar'),
    path('dashboard/gestao/sala/reuniao/<int:reuniao_id>/', views.sala_reuniao, name='sala_reuniao'),
    path('dashboard/gestao/sala/api/chat/', views.api_chat, name='api_chat_agente'),
    path('dashboard/gestao/sala/api/comando/', views.api_slash_command, name='api_slash_command'),
    path('dashboard/gestao/sala/api/salvar-sessao/', views.api_salvar_sessao, name='api_salvar_sessao'),
    path('dashboard/gestao/sala/<str:agente_id>/', views.sala_chat, name='sala_chat'),
]
