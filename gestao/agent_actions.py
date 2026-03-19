"""
Acoes que os agentes podem executar no sistema.
O agente inclui comandos especiais na resposta e o sistema executa.
"""
import os
import re
import json
from datetime import datetime
from django.conf import settings


DOCS_BASE = os.path.join(settings.BASE_DIR, 'docs')


def processar_acoes(resposta, agente_id):
    """
    Processa acoes embutidas na resposta do agente.
    Retorna (resposta_limpa, acoes_executadas).

    Acoes suportadas (o agente inclui no texto):
    ---SALVAR_ENTREGA---
    agente: pmm
    arquivo: nome_do_arquivo.md
    conteudo: (markdown)
    ---FIM_ENTREGA---

    ---SALVAR_SESSAO---
    arquivo: 2026-03-19_agente_topico.md
    conteudo: (markdown)
    ---FIM_SESSAO---

    ---CRIAR_TAREFA---
    projeto: Lancamento Floriano
    titulo: Fazer X
    responsavel: CEO
    prioridade: alta
    ---FIM_TAREFA---

    ---ATUALIZAR_TAREFA---
    tarefa_id: 5
    status: concluida
    ---FIM_TAREFA---
    """
    acoes_executadas = []
    resposta_limpa = resposta

    # Processar SALVAR_ENTREGA
    entrega_pattern = r'---SALVAR_ENTREGA---\n(.*?)---FIM_ENTREGA---'
    for match in re.finditer(entrega_pattern, resposta, re.DOTALL):
        bloco = match.group(1)
        resultado = _salvar_entrega(bloco, agente_id)
        acoes_executadas.append(resultado)
        resposta_limpa = resposta_limpa.replace(match.group(0), f"\n> ✅ {resultado}\n")

    # Processar SALVAR_SESSAO
    sessao_pattern = r'---SALVAR_SESSAO---\n(.*?)---FIM_SESSAO---'
    for match in re.finditer(sessao_pattern, resposta, re.DOTALL):
        bloco = match.group(1)
        resultado = _salvar_sessao(bloco)
        acoes_executadas.append(resultado)
        resposta_limpa = resposta_limpa.replace(match.group(0), f"\n> ✅ {resultado}\n")

    # Processar CRIAR_TAREFA
    tarefa_pattern = r'---CRIAR_TAREFA---\n(.*?)---FIM_TAREFA---'
    for match in re.finditer(tarefa_pattern, resposta, re.DOTALL):
        bloco = match.group(1)
        resultado = _criar_tarefa(bloco)
        acoes_executadas.append(resultado)
        resposta_limpa = resposta_limpa.replace(match.group(0), f"\n> ✅ {resultado}\n")

    # Processar ATUALIZAR_TAREFA
    update_pattern = r'---ATUALIZAR_TAREFA---\n(.*?)---FIM_TAREFA---'
    for match in re.finditer(update_pattern, resposta, re.DOTALL):
        bloco = match.group(1)
        resultado = _atualizar_tarefa(bloco)
        acoes_executadas.append(resultado)
        resposta_limpa = resposta_limpa.replace(match.group(0), f"\n> ✅ {resultado}\n")

    # Processar CONSULTAR_AGENTE (@menção)
    consulta_pattern = r'---CONSULTAR_AGENTE---\n(.*?)---FIM_CONSULTA---'
    for match in re.finditer(consulta_pattern, resposta_limpa, re.DOTALL):
        bloco = match.group(1)
        resultado_consulta = _consultar_agente(bloco)
        acoes_executadas.append(resultado_consulta['log'])
        resposta_limpa = resposta_limpa.replace(
            match.group(0),
            f"\n\n> 🤝 **{resultado_consulta['agente_nome']}** respondeu:\n\n{resultado_consulta['resposta']}\n"
        )

    return resposta_limpa, acoes_executadas


def _parse_bloco(bloco):
    """Extrai campos chave:valor de um bloco de texto."""
    campos = {}
    conteudo_lines = []
    in_conteudo = False

    for linha in bloco.split('\n'):
        if in_conteudo:
            conteudo_lines.append(linha)
        elif linha.strip().startswith('conteudo:'):
            in_conteudo = True
            # Conteudo pode comecar na mesma linha
            resto = linha.split('conteudo:', 1)[1].strip()
            if resto:
                conteudo_lines.append(resto)
        elif ':' in linha:
            chave, valor = linha.split(':', 1)
            campos[chave.strip().lower()] = valor.strip()

    if conteudo_lines:
        campos['conteudo'] = '\n'.join(conteudo_lines)

    return campos


def _salvar_entrega(bloco, agente_id_default):
    """Salva um arquivo de entrega."""
    campos = _parse_bloco(bloco)
    agente = campos.get('agente', agente_id_default)
    arquivo = campos.get('arquivo', f'{agente}_{datetime.now().strftime("%Y%m%d_%H%M")}.md')
    conteudo = campos.get('conteudo', '')

    if not conteudo:
        return f"Entrega vazia — nao salva."

    pasta = os.path.join(DOCS_BASE, 'entregas', agente)
    os.makedirs(pasta, exist_ok=True)

    filepath = os.path.join(pasta, arquivo)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    return f"Entrega salva: entregas/{agente}/{arquivo}"


def _salvar_sessao(bloco):
    """Salva um arquivo de sessao."""
    campos = _parse_bloco(bloco)
    arquivo = campos.get('arquivo', f'{datetime.now().strftime("%Y-%m-%d")}_sessao.md')
    conteudo = campos.get('conteudo', '')

    if not conteudo:
        return f"Sessao vazia — nao salva."

    pasta = os.path.join(DOCS_BASE, 'contexto', 'sessoes')
    os.makedirs(pasta, exist_ok=True)

    filepath = os.path.join(pasta, arquivo)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    return f"Sessao salva: sessoes/{arquivo}"


def _criar_tarefa(bloco):
    """Cria uma tarefa no projeto."""
    try:
        from gestao.models import Projeto, Tarefa
        campos = _parse_bloco(bloco)

        projeto_nome = campos.get('projeto', '')
        titulo = campos.get('titulo', '')
        responsavel = campos.get('responsavel', '')
        prioridade = campos.get('prioridade', 'media')

        if not titulo:
            return "Tarefa sem titulo — nao criada."

        projeto = Projeto.objects.filter(nome__icontains=projeto_nome, ativo=True).first()
        if not projeto:
            projeto = Projeto.objects.filter(ativo=True).first()

        if not projeto:
            return "Nenhum projeto ativo encontrado."

        Tarefa.objects.create(
            projeto=projeto,
            titulo=titulo,
            responsavel=responsavel,
            prioridade=prioridade if prioridade in ('critica', 'alta', 'media', 'baixa') else 'media',
        )
        return f"Tarefa criada: '{titulo}' no projeto '{projeto.nome}'"
    except Exception as e:
        return f"Erro ao criar tarefa: {str(e)}"


def _consultar_agente(bloco):
    """Consulta outro agente e retorna a resposta."""
    try:
        from gestao.ai_service import chat_agente, AGENTES_INFO
        campos = _parse_bloco(bloco)

        agente_id = campos.get('agente', '').lower().strip()
        pergunta = campos.get('pergunta', campos.get('conteudo', ''))

        # Mapear nomes para IDs
        alias = {
            'cto': 'cto', 'cpo': 'cpo', 'cfo': 'cfo', 'cmo': 'cmo',
            'pmm': 'pmm', 'b2b': 'b2b', 'cs': 'cs',
            'comercial': 'b2b', 'customer success': 'cs', 'comercial b2b': 'b2b',
        }
        agente_id = alias.get(agente_id, agente_id)

        info = next((a for a in AGENTES_INFO if a['id'] == agente_id), None)
        if not info:
            return {
                'log': f"Agente '{agente_id}' nao encontrado para consulta.",
                'agente_nome': agente_id,
                'resposta': f"Agente '{agente_id}' nao encontrado.",
            }

        if not pergunta:
            return {
                'log': "Consulta sem pergunta.",
                'agente_nome': info['nome'],
                'resposta': "Nenhuma pergunta foi feita.",
            }

        resposta = chat_agente(agente_id, pergunta)
        return {
            'log': f"Consultou {info['nome']}: '{pergunta[:50]}...'",
            'agente_nome': info['nome'],
            'resposta': resposta,
        }
    except Exception as e:
        return {
            'log': f"Erro ao consultar agente: {str(e)}",
            'agente_nome': 'Desconhecido',
            'resposta': f"Erro: {str(e)}",
        }


def _atualizar_tarefa(bloco):
    """Atualiza status de uma tarefa."""
    try:
        from gestao.models import Tarefa
        from django.utils import timezone
        campos = _parse_bloco(bloco)

        tarefa_id = campos.get('tarefa_id')
        novo_status = campos.get('status', '')

        if not tarefa_id:
            # Tentar buscar por titulo
            titulo = campos.get('titulo', '')
            if titulo:
                tarefa = Tarefa.objects.filter(titulo__icontains=titulo).first()
            else:
                return "Tarefa nao identificada."
        else:
            tarefa = Tarefa.objects.filter(id=int(tarefa_id)).first()

        if not tarefa:
            return "Tarefa nao encontrada."

        if novo_status and novo_status in ('pendente', 'em_andamento', 'concluida', 'bloqueada'):
            tarefa.status = novo_status
            if novo_status == 'concluida':
                tarefa.data_conclusao = timezone.now()
            tarefa.save()
            return f"Tarefa '{tarefa.titulo}' atualizada para '{tarefa.get_status_display()}'"

        return "Status invalido."
    except Exception as e:
        return f"Erro ao atualizar tarefa: {str(e)}"
