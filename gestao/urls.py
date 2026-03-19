from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/gestao/', views.dashboard_ceo, name='dashboard_ceo'),
    path('dashboard/gestao/projetos/', views.gestao_projetos, name='gestao_projetos'),
    path('dashboard/gestao/kanban/<int:projeto_id>/', views.kanban, name='kanban'),
    path('dashboard/gestao/sessoes/', views.gestao_sessoes, name='gestao_sessoes'),
    path('dashboard/gestao/sessoes/<str:arquivo>/', views.gestao_sessao_detalhe, name='gestao_sessao_detalhe'),
    path('dashboard/gestao/entregas/', views.gestao_entregas, name='gestao_entregas'),
    path('dashboard/gestao/entregas/<str:agente>/<str:arquivo>/', views.gestao_entrega_detalhe, name='gestao_entrega_detalhe'),
    path('dashboard/gestao/sala/', views.sala_agentes, name='sala_agentes'),
    path('dashboard/gestao/sala/reuniao/criar/', views.sala_reuniao_criar, name='sala_reuniao_criar'),
    path('dashboard/gestao/sala/reuniao/<int:reuniao_id>/', views.sala_reuniao, name='sala_reuniao'),
    path('dashboard/gestao/sala/api/chat/', views.api_chat, name='api_chat_agente'),
    path('dashboard/gestao/sala/api/salvar-sessao/', views.api_salvar_sessao, name='api_salvar_sessao'),
    path('dashboard/gestao/entregas/<str:agente>/<str:arquivo>/editar/', views.gestao_entrega_editar, name='gestao_entrega_editar'),
    path('dashboard/gestao/sala/<str:agente_id>/', views.sala_chat, name='sala_chat'),
]
