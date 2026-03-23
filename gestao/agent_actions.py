"""
Acoes executaveis dos agentes IA.
Processa blocos especiais na resposta e executa no sistema.
"""
import re
import uuid


def _registrar_log(tool_slug, agente_id, resultado, sucesso=True):
    """Registra execucao de tool no log."""
    try:
        from gestao.models import LogTool, ToolAgente, Agente
        tool = ToolAgente.objects.filter(slug=tool_slug).first()
        agente = Agente.objects.filter(slug=agente_id).first()
        LogTool.objects.create(
            tool=tool,
            tool_slug=tool_slug,
            agente=agente,
            resultado=resultado,
            sucesso=sucesso,
        )
    except Exception:
        pass


# Mapa de pattern -> slug da tool
_TOOL_MAP = {
    r'---SALVAR_DOCUMENTO---\s+(.*?)---FIM_DOCUMENTO---': 'salvar_documento',
    r'---SALVAR_ENTREGA---\s+(.*?)---FIM_ENTREGA---': 'salvar_documento',
    r'---SALVAR_SESSAO---\s+(.*?)---FIM_SESSAO---': 'salvar_documento',
    r'---CRIAR_TAREFA---\s+(.*?)---FIM_TAREFA---': 'criar_tarefa',
    r'---ATUALIZAR_TAREFA---\s+(.*?)---FIM_(?:ATUALIZAR_)?TAREFA---': 'atualizar_tarefa',
    r'---CRIAR_PROJETO---\s+(.*?)---FIM_PROJETO---': 'criar_projeto',
    r'---ATUALIZAR_PROJETO---\s+(.*?)---FIM_PROJETO---': 'atualizar_projeto',
    r'---CRIAR_ETAPA---\s+(.*?)---FIM_ETAPA---': 'criar_etapa',
    r'---RESUMO_PROJETO---\s+(.*?)---FIM_RESUMO---': 'resumo_projeto',
    r'---CONSULTAR_DOCUMENTO---\s+(.*?)---FIM_CONSULTA(?:_DOC)?---': 'consultar_documento',
    r'---LISTAR_DOCUMENTOS---\s+(.*?)---FIM_LISTAR(?:_DOCS)?---': 'listar_documentos',
    r'---CONSULTAR_DADOS---\s+(.*?)---FIM_CONSULTA(?:R)?_DADOS---': 'consultar_dados',
    r'---EXPLORAR_CODIGO---\s+(.*?)---FIM_EXPLORAR(?:_CODIGO)?---': 'explorar_codigo',
    r'---VALIDAR_AGENTES---\s*(.*?)---FIM_VALIDAR(?:_AGENTES)?---': 'validar_agentes',
    r'---SALVAR_EMAIL---\s+(.*?)---FIM_EMAIL---': 'salvar_email',
    r'---GERAR_BANNER---\s+(.*?)---FIM_BANNER---': 'gerar_banner',
    r'---GERAR_IMAGEM_CUPOM---\s+(.*?)---FIM_IMAGEM_CUPOM---': 'gerar_imagem_cupom',
    r'---GERAR_ARTE_CAMPANHA---\s+(.*?)---FIM_ARTE_CAMPANHA---': 'gerar_arte_campanha',
}


def processar_acoes(resposta, agente_id):
    """
    Processa acoes embutidas na resposta do agente.
    Retorna (resposta_limpa, acoes_executadas).
    """
    acoes_executadas = []
    resposta_limpa = resposta

    # Handlers por slug
    handlers = {
        'salvar_documento': lambda b, p: _salvar_documento(b, agente_id, 'sessao' if 'SESSAO' in p else ('entrega' if 'ENTREGA' in p else None)),
        'criar_tarefa': lambda b, p: _criar_tarefa(b, agente_id),
        'atualizar_tarefa': lambda b, p: _atualizar_tarefa(b),
        'criar_projeto': lambda b, p: _criar_projeto(b),
        'atualizar_projeto': lambda b, p: _atualizar_projeto(b),
        'criar_etapa': lambda b, p: _criar_etapa(b),
        'resumo_projeto': lambda b, p: _resumo_projeto(b),
        'consultar_documento': lambda b, p: _consultar_documento(b),
        'listar_documentos': lambda b, p: _listar_documentos(b),
        'consultar_dados': lambda b, p: _consultar_dados(b),
        'explorar_codigo': lambda b, p: _explorar_codigo(b),
        'validar_agentes': lambda b, p: _validar_agentes(b),
        'salvar_email': lambda b, p: _salvar_email(b, agente_id),
        'gerar_banner': lambda b, p: _gerar_banner(b, agente_id),
        'gerar_imagem_cupom': lambda b, p: _gerar_imagem_cupom(b, agente_id),
        'gerar_arte_campanha': lambda b, p: _gerar_arte_campanha(b, agente_id),
    }

    for pattern, tool_slug in _TOOL_MAP.items():
        for match in re.finditer(pattern, resposta_limpa, re.DOTALL | re.IGNORECASE):
            handler = handlers[tool_slug]
            resultado = handler(match.group(1), match.group(0))

            # Handlers podem retornar string ou dict com 'log' e 'conteudo'
            if isinstance(resultado, dict):
                log_texto = resultado.get('log', '')
                conteudo = resultado.get('conteudo', log_texto)
                sucesso = 'erro' not in log_texto.lower()
                _registrar_log(tool_slug, agente_id, log_texto, sucesso)
                acoes_executadas.append(log_texto)
                resposta_limpa = resposta_limpa.replace(match.group(0), f"\n{conteudo}\n")
            else:
                sucesso = 'erro' not in resultado.lower() and 'vazi' not in resultado.lower()
                _registrar_log(tool_slug, agente_id, resultado, sucesso)
                acoes_executadas.append(resultado)
                resposta_limpa = resposta_limpa.replace(match.group(0), f"\n> ✅ {resultado}\n")

    # Consultar agente
    contexto_conversa = _montar_contexto_conversa(agente_id)
    consulta_pattern = r'---CONSULTAR_AGENTE---\n(.*?)---FIM_CONSULTA---'
    for match in re.finditer(consulta_pattern, resposta_limpa, re.DOTALL | re.IGNORECASE):
        resultado = _consultar_agente(match.group(1), contexto_conversa)
        _registrar_log('consultar_agente', agente_id, resultado['log'])
        acoes_executadas.append(resultado['log'])
        resposta_limpa = resposta_limpa.replace(
            match.group(0),
            f"\n\n> 🤝 **{resultado['agente_nome']}** respondeu:\n\n{resultado['resposta']}\n"
        )

    return resposta_limpa, acoes_executadas


def _parse_bloco(bloco):
    """Extrai campos chave:valor de um bloco de texto."""
    campos = {}
    conteudo_lines = []
    in_multiline = None  # campo multi-linha ativo
    # conteudo e TERMINAL — tudo depois dele e conteudo, sem sair
    CAMPOS_MULTILINE = {'conteudo', 'descricao', 'objetivo', 'riscos'}
    CAMPOS_TERMINAL = {'conteudo'}  # nunca saem do modo multiline
    # Campos validos que podem aparecer nos blocos
    CAMPOS_VALIDOS = {
        'titulo', 'nome', 'projeto', 'responsavel', 'prioridade', 'status',
        'descricao', 'objetivo', 'riscos', 'conteudo', 'etapa', 'slug',
        'categoria', 'agente', 'consulta', 'periodo', 'cidade', 'limite',
        'assunto', 'prazo', 'data_inicio', 'data_fim',
        'parceiro', 'desconto', 'contexto', 'publico', 'tom',
        'pasta_destino', 'pasta', 'criterios_aceite', 'criterios',
        'entregavel', 'processo', 'tarefa_id',
    }

    for linha in bloco.split('\n'):
        linha_stripped = linha.strip()

        # Detectar novo campo chave:valor
        if ':' in linha_stripped and not in_multiline:
            chave_raw, valor = linha_stripped.split(':', 1)
            # Strip formatacao markdown (bold/italic)
            chave = re.sub(r'[*_]+', '', chave_raw).strip().lower()
            valor = valor.strip()

            if chave in CAMPOS_MULTILINE:
                in_multiline = chave
                if valor:
                    conteudo_lines.append(valor)
            elif chave in CAMPOS_VALIDOS:
                campos[chave] = valor

        elif in_multiline:
            # Campo terminal (conteudo) — tudo ate o final e conteudo
            if in_multiline in CAMPOS_TERMINAL:
                conteudo_lines.append(linha)
            else:
                # Campos multiline nao-terminal: verificar se apareceu um novo campo valido
                if ':' in linha_stripped:
                    possivel_chave = re.sub(r'[*_]+', '', linha_stripped.split(':', 1)[0]).strip().lower()
                    if possivel_chave in CAMPOS_VALIDOS and possivel_chave not in CAMPOS_MULTILINE:
                        campos[in_multiline] = '\n'.join(conteudo_lines)
                        conteudo_lines = []
                        in_multiline = None
                        campos[possivel_chave] = linha_stripped.split(':', 1)[1].strip()
                        continue
                conteudo_lines.append(linha)

    if in_multiline and conteudo_lines:
        campos[in_multiline] = '\n'.join(conteudo_lines)

    return campos


def _montar_contexto_conversa(agente_id):
    """Monta resumo das ultimas mensagens do chat para contexto."""
    try:
        from gestao.models import MensagemChat, Agente
        agente = Agente.objects.filter(slug=agente_id).first()
        if not agente:
            return ""
        msgs = MensagemChat.objects.filter(agente=agente).order_by('-data_criacao')[:10]
        if not msgs:
            return ""
        linhas = []
        for m in reversed(msgs):
            role = "CEO" if m.role == 'user' else agente.nome
            # Truncar mensagens longas
            conteudo = m.conteudo[:500]
            if len(m.conteudo) > 500:
                conteudo += "..."
            linhas.append(f"{role}: {conteudo}")
        return "\n\n".join(linhas)
    except Exception:
        return ""


def _salvar_documento(bloco, agente_id_default, categoria_default=None):
    """Salva um Documento no banco."""
    from gestao.models import Documento, Agente
    campos = _parse_bloco(bloco)
    conteudo = campos.get('conteudo', '')

    if not conteudo:
        return "Documento vazio — nao salvo."

    categoria = campos.get('categoria', categoria_default or 'entrega')
    categorias_validas = [c[0] for c in Documento.CATEGORIA_CHOICES]
    if categoria not in categorias_validas:
        categoria = 'entrega'

    agente_slug = campos.get('agente', agente_id_default)
    agente = Agente.objects.filter(slug=agente_slug).first()

    primeira_linha = conteudo.split('\n')[0].lstrip('#').strip()
    titulo = primeira_linha or f'Documento {agente_slug}'

    doc = Documento.objects.create(
        titulo=titulo,
        slug=f"doc-{uuid.uuid4().hex[:8]}",
        categoria=categoria,
        agente=agente,
        conteudo=conteudo,
        resumo=primeira_linha,
    )
    nome = agente.nome if agente else agente_slug
    return f"Documento salvo: '{doc.titulo}' ({nome})"


def _salvar_email(bloco, agente_id_default):
    """Salva template de e-mail como Documento (categoria=email). HTML nao e sanitizado."""
    from gestao.models import Documento, Agente
    campos = _parse_bloco(bloco)
    conteudo = campos.get('conteudo', '')

    # Limpar backticks de markdown (```html ... ```)
    if conteudo:
        conteudo = conteudo.strip()
        if conteudo.startswith('```'):
            conteudo = conteudo.split('\n', 1)[1] if '\n' in conteudo else conteudo[3:]
        if conteudo.endswith('```'):
            conteudo = conteudo[:-3]
        conteudo = conteudo.strip()

    if not conteudo:
        return "E-mail vazio — nao salvo."

    assunto = campos.get('assunto', campos.get('titulo', ''))
    titulo = f"E-mail: {assunto}" if assunto else f"Template de e-mail"

    agente_slug = campos.get('agente', agente_id_default)
    agente = Agente.objects.filter(slug=agente_slug).first()

    doc = Documento.objects.create(
        titulo=titulo,
        slug=f"email-{uuid.uuid4().hex[:8]}",
        categoria='email',
        agente=agente,
        conteudo=conteudo,
        resumo=assunto or titulo,
        visivel_agentes=False,
    )
    nome = agente.nome if agente else agente_slug
    return f"Template de e-mail salvo: '{doc.titulo}' ({nome})"


def _criar_tarefa(bloco, agente_id=None):
    """Cria uma tarefa no projeto com travas de seguranca para delegacao entre agentes."""
    try:
        from gestao.models import Projeto, Tarefa, Agente
        campos = _parse_bloco(bloco)

        titulo = campos.get('titulo', '')
        if not titulo:
            return "Tarefa sem titulo — nao criada."

        projeto_nome = campos.get('projeto', '')
        projeto = Projeto.objects.filter(nome__icontains=projeto_nome, ativo=True).first() if projeto_nome else None
        if not projeto and projeto_nome:
            nomes_disponiveis = list(Projeto.objects.filter(ativo=True).values_list('nome', flat=True)[:10])
            return f"Projeto '{projeto_nome}' nao encontrado. Projetos ativos: {', '.join(nomes_disponiveis) or 'nenhum'}"
        if not projeto:
            projeto = Projeto.objects.filter(ativo=True).first()
        if not projeto:
            return "Nenhum projeto ativo encontrado."

        prioridade = campos.get('prioridade', 'media')
        if prioridade not in ('critica', 'alta', 'media', 'baixa'):
            prioridade = 'media'

        # Determinar agente criador e nivel de delegacao
        agente_criador = None
        nivel_delegacao = 0
        status_inicial = 'pendente'

        if agente_id:
            agente_criador = Agente.objects.filter(slug=agente_id, ativo=True).first()
            if agente_criador:
                nivel_delegacao = 1
                status_inicial = 'rascunho'  # Tarefas de agentes precisam de aprovacao

                # Anti-loop: nao pode criar tarefa pro agente que criou a tarefa dele
                responsavel_destino = campos.get('responsavel', '').strip().lower()
                # Verificar se o agente destino e o criador da tarefa do agente atual
                # (simplificado: busca no backlog do agente se tem tarefa criada pelo destino)
                if responsavel_destino:
                    agente_destino = Agente.objects.filter(
                        nome__icontains=responsavel_destino, ativo=True
                    ).first() or Agente.objects.filter(
                        slug__icontains=responsavel_destino, ativo=True
                    ).first()
                    if agente_destino and agente_destino.slug == agente_id:
                        return f"Anti-loop: agente nao pode criar tarefa para si mesmo."

                # Nivel maximo de delegacao
                if nivel_delegacao >= 2:
                    return f"Nivel maximo de delegacao atingido (max 2). Tarefa nao criada."

                # Campos obrigatorios para tarefas criadas por agentes
                objetivo = campos.get('objetivo', '').strip()
                if not objetivo:
                    return f"Tarefa criada por agente deve ter campo 'objetivo' preenchido."

        # Vincular processo se mencionado
        processo = None
        processo_nome = campos.get('processo', '')
        if processo_nome:
            from gestao.models import Documento
            processo = Documento.objects.filter(
                categoria='processo',
                titulo__icontains=processo_nome
            ).first()

        # Vincular pasta destino se mencionada
        pasta_destino = None
        pasta_nome = campos.get('pasta_destino', '') or campos.get('pasta', '')
        if pasta_nome:
            from gestao.models import PastaDocumento
            pasta_destino = PastaDocumento.objects.filter(nome__icontains=pasta_nome).first()

        Tarefa.objects.create(
            projeto=projeto,
            titulo=titulo,
            descricao=campos.get('descricao', ''),
            responsavel=campos.get('responsavel', ''),
            prioridade=prioridade,
            status=status_inicial,
            objetivo=campos.get('objetivo', ''),
            contexto=campos.get('contexto', ''),
            passos=campos.get('passos', ''),
            entregavel=campos.get('entregavel', ''),
            criterios_aceite=campos.get('criterios_aceite', '') or campos.get('criterios', ''),
            processo=processo,
            pasta_destino=pasta_destino,
            criado_por_agente=agente_criador,
            nivel_delegacao=nivel_delegacao,
        )
        status_msg = f" (status: {status_inicial})" if status_inicial == 'rascunho' else ''
        return f"Tarefa criada: '{titulo}' no projeto '{projeto.nome}'{status_msg}"
    except Exception as e:
        return f"Erro ao criar tarefa: {str(e)}"


def _atualizar_tarefa(bloco):
    """Atualiza status de uma tarefa."""
    try:
        from gestao.models import Tarefa
        from django.utils import timezone
        campos = _parse_bloco(bloco)

        tarefa_id = campos.get('tarefa_id')
        novo_status = campos.get('status', '')

        if not tarefa_id:
            titulo = campos.get('titulo', '')
            if titulo:
                tarefa = Tarefa.objects.filter(titulo__icontains=titulo).first()
            else:
                return "Tarefa nao identificada."
        else:
            tarefa = Tarefa.objects.filter(id=int(tarefa_id)).first()

        if not tarefa:
            return "Tarefa nao encontrada."

        if novo_status in ('rascunho', 'pendente', 'em_andamento', 'concluida', 'bloqueada'):
            tarefa.status = novo_status
            if novo_status == 'concluida':
                tarefa.data_conclusao = timezone.now()
            tarefa.save()
            return f"Tarefa '{tarefa.titulo}' atualizada para '{tarefa.get_status_display()}'"

        return "Status invalido."
    except Exception as e:
        return f"Erro ao atualizar tarefa: {str(e)}"


def _criar_projeto(bloco):
    """Cria um novo projeto."""
    try:
        from gestao.models import Projeto
        campos = _parse_bloco(bloco)

        nome = campos.get('nome', '')
        if not nome:
            return "Projeto sem nome — nao criado."

        # Evitar duplicata
        if Projeto.objects.filter(nome__iexact=nome).exists():
            return f"Projeto '{nome}' ja existe."

        prioridade = campos.get('prioridade', 'media')
        if prioridade not in ('critica', 'alta', 'media', 'baixa'):
            prioridade = 'media'

        data_fim = None
        if campos.get('data_fim_prevista'):
            try:
                from datetime import datetime
                data_fim = datetime.strptime(campos['data_fim_prevista'], '%Y-%m-%d').date()
            except Exception:
                pass

        projeto = Projeto.objects.create(
            nome=nome,
            descricao=campos.get('descricao', ''),
            objetivo=campos.get('objetivo', ''),
            responsavel=campos.get('responsavel', ''),
            stakeholders=campos.get('stakeholders', ''),
            prioridade=prioridade,
            data_fim_prevista=data_fim,
            riscos=campos.get('riscos', ''),
            premissas=campos.get('premissas', ''),
            publico_alvo=campos.get('publico_alvo', ''),
            criterios_sucesso=campos.get('criterios_sucesso', ''),
            status='planejamento',
            ativo=True,
        )
        return f"Projeto criado: '{projeto.nome}' (prioridade: {prioridade})"
    except Exception as e:
        return f"Erro ao criar projeto: {str(e)}"


def _atualizar_projeto(bloco):
    """Atualiza um projeto existente."""
    try:
        from gestao.models import Projeto
        campos = _parse_bloco(bloco)

        projeto_nome = campos.get('projeto', '')
        projeto = Projeto.objects.filter(nome__icontains=projeto_nome).first()
        if not projeto:
            return f"Projeto '{projeto_nome}' nao encontrado."

        alterados = []
        status_validos = ('planejamento', 'em_andamento', 'pausado', 'concluido', 'cancelado')
        prioridade_validas = ('critica', 'alta', 'media', 'baixa')

        if campos.get('status') and campos['status'] in status_validos:
            projeto.status = campos['status']
            alterados.append(f"status={campos['status']}")

        if campos.get('prioridade') and campos['prioridade'] in prioridade_validas:
            projeto.prioridade = campos['prioridade']
            alterados.append(f"prioridade={campos['prioridade']}")

        if campos.get('nome'):
            projeto.nome = campos['nome']
            alterados.append('nome')

        # Campos de texto
        for campo in ('objetivo', 'riscos', 'premissas', 'descricao', 'responsavel',
                       'stakeholders', 'publico_alvo', 'criterios_sucesso',
                       'contexto_agentes', 'orcamento'):
            if campos.get(campo):
                setattr(projeto, campo, campos[campo])
                alterados.append(campo)

        # Campos de data
        from datetime import datetime
        for campo_data in ('data_inicio', 'data_fim_prevista'):
            if campos.get(campo_data):
                try:
                    setattr(projeto, campo_data, datetime.strptime(campos[campo_data], '%Y-%m-%d').date())
                    alterados.append(campo_data)
                except Exception:
                    pass

        if not alterados:
            return "Nenhum campo para atualizar."

        projeto.save()
        return f"Projeto '{projeto.nome}' atualizado: {', '.join(alterados)}"
    except Exception as e:
        return f"Erro ao atualizar projeto: {str(e)}"


def _criar_etapa(bloco):
    """Cria uma etapa dentro de um projeto."""
    try:
        from gestao.models import Projeto, Etapa
        campos = _parse_bloco(bloco)

        nome = campos.get('nome', '')
        if not nome:
            return "Etapa sem nome — nao criada."

        projeto_nome = campos.get('projeto', '')
        projeto = Projeto.objects.filter(nome__icontains=projeto_nome, ativo=True).first()
        if not projeto:
            projeto = Projeto.objects.filter(ativo=True).first()
        if not projeto:
            return "Nenhum projeto ativo encontrado."

        # Ordem automatica
        ultima_ordem = Etapa.objects.filter(projeto=projeto).count()

        data_inicio = None
        data_fim = None
        try:
            from datetime import datetime
            if campos.get('data_inicio'):
                data_inicio = datetime.strptime(campos['data_inicio'], '%Y-%m-%d').date()
            if campos.get('data_fim'):
                data_fim = datetime.strptime(campos['data_fim'], '%Y-%m-%d').date()
        except Exception:
            pass

        etapa = Etapa.objects.create(
            projeto=projeto,
            nome=nome,
            descricao=campos.get('descricao', ''),
            ordem=ultima_ordem + 1,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        return f"Etapa criada: '{etapa.nome}' no projeto '{projeto.nome}'"
    except Exception as e:
        return f"Erro ao criar etapa: {str(e)}"


def _resumo_projeto(bloco):
    """Gera resumo executivo de um projeto."""
    try:
        from gestao.models import Projeto, Tarefa
        campos = _parse_bloco(bloco)

        projeto_nome = campos.get('projeto', '')
        projeto = Projeto.objects.filter(nome__icontains=projeto_nome, ativo=True).first()
        if not projeto:
            projeto = Projeto.objects.filter(ativo=True).first()
        if not projeto:
            return "Nenhum projeto ativo encontrado."

        tarefas = Tarefa.objects.filter(projeto=projeto)
        total = tarefas.count()
        pendentes = tarefas.filter(status='pendente').count()
        andamento = tarefas.filter(status='em_andamento').count()
        concluidas = tarefas.filter(status='concluida').count()
        bloqueadas = tarefas.filter(status='bloqueada').count()

        linhas = [
            f"Projeto: {projeto.nome}",
            f"Status: {projeto.get_status_display()}",
            f"Progresso: {projeto.progresso}%",
            f"Tarefas: {total} total ({concluidas} concluidas, {andamento} em andamento, {pendentes} pendentes, {bloqueadas} bloqueadas)",
        ]
        if projeto.responsavel:
            linhas.append(f"Responsavel: {projeto.responsavel}")
        if projeto.data_fim_prevista:
            linhas.append(f"Prazo: {projeto.data_fim_prevista.strftime('%d/%m/%Y')}")
        if projeto.riscos:
            linhas.append(f"Riscos: {projeto.riscos[:200]}")

        return '\n'.join(linhas)
    except Exception as e:
        return f"Erro ao gerar resumo: {str(e)}"


def _consultar_agente(bloco, contexto_conversa=None):
    """Consulta outro agente com contexto da conversa atual."""
    try:
        from gestao.ai_service import chat_agente
        from gestao.models import Agente
        campos = _parse_bloco(bloco)

        agente_slug = campos.get('agente', '').lower().strip()
        pergunta = campos.get('pergunta', campos.get('conteudo', ''))

        agente = Agente.objects.filter(slug=agente_slug, ativo=True).first()
        if not agente:
            return {
                'log': f"Agente '{agente_slug}' nao encontrado.",
                'agente_nome': agente_slug,
                'resposta': f"Agente '{agente_slug}' nao encontrado.",
            }

        if not pergunta:
            return {
                'log': "Consulta sem pergunta.",
                'agente_nome': agente.nome,
                'resposta': "Nenhuma pergunta foi feita.",
            }

        # Incluir contexto da conversa + instrucao de comportamento
        mensagem_completa = pergunta
        if contexto_conversa:
            mensagem_completa = (
                f"CONTEXTO DA CONVERSA ATUAL (entre CEO e outro agente):\n"
                f"{contexto_conversa}\n\n"
                f"---\n"
                f"INSTRUCAO: Voce foi consultado por outro agente. "
                f"Analise o contexto acima e responda de forma DIRETA e ASSERTIVA. "
                f"NAO faca perguntas de volta. NAO peca mais informacoes. "
                f"Use o contexto fornecido para dar seu parecer, aprovacao, sugestao ou analise. "
                f"Se faltarem dados, assuma o cenario mais provavel e responda mesmo assim.\n\n"
                f"PERGUNTA:\n{pergunta}"
            )

        resposta = chat_agente(agente_slug, mensagem_completa)
        return {
            'log': f"Consultou {agente.nome}: '{pergunta[:50]}...'",
            'agente_nome': agente.nome,
            'resposta': resposta,
        }
    except Exception as e:
        return {
            'log': f"Erro ao consultar agente: {str(e)}",
            'agente_nome': 'Desconhecido',
            'resposta': f"Erro: {str(e)}",
        }


def _validar_agentes(bloco):
    """Executa validacao de todos os agentes."""
    from gestao.views import TOOL_EXECUTORS
    executor = TOOL_EXECUTORS.get('validar_agentes')
    if executor:
        resultado = executor()
        return {'log': 'Validacao de agentes executada', 'conteudo': resultado}
    return {'log': 'Executor nao encontrado', 'conteudo': 'Erro: executor validar_agentes nao encontrado.'}


def _explorar_codigo(bloco):
    """Explora arquivos do projeto: listar diretorio ou ler arquivo."""
    import os
    from django.conf import settings

    campos = _parse_bloco(bloco)
    modo = campos.get('modo', 'ler').strip().lower()
    caminho = campos.get('caminho', '').strip()

    if not caminho:
        return {'log': 'Caminho vazio', 'conteudo': 'Informe o caminho. Ex: gestao/models.py'}

    # Seguranca: extensoes permitidas
    EXTENSOES_PERMITIDAS = {'.py', '.html', '.js', '.css', '.md', '.txt', '.json', '.yml', '.yaml', '.cfg', '.ini'}
    ARQUIVOS_BLOQUEADOS = {'.env', 'settings.py', 'local_settings.py', 'secrets.py'}
    PASTAS_BLOQUEADAS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}

    # Resolver caminho absoluto (relativo a raiz do projeto)
    raiz = settings.BASE_DIR
    caminho_abs = os.path.normpath(os.path.join(raiz, caminho))

    # Seguranca: nao sair da raiz do projeto
    if not caminho_abs.startswith(str(raiz)):
        return {'log': f'Acesso negado: {caminho}', 'conteudo': 'Caminho fora do projeto.'}

    # Verificar arquivo bloqueado
    nome_arquivo = os.path.basename(caminho_abs)
    if nome_arquivo in ARQUIVOS_BLOQUEADOS:
        return {'log': f'Bloqueado: {nome_arquivo}', 'conteudo': f'Arquivo "{nome_arquivo}" bloqueado por seguranca.'}

    if modo == 'listar':
        if not os.path.isdir(caminho_abs):
            return {'log': f'Nao e diretorio: {caminho}', 'conteudo': f'"{caminho}" nao e um diretorio.'}

        itens = []
        try:
            for item in sorted(os.listdir(caminho_abs)):
                if item.startswith('.') or item in PASTAS_BLOQUEADAS:
                    continue
                item_path = os.path.join(caminho_abs, item)
                if os.path.isdir(item_path):
                    count = len([f for f in os.listdir(item_path) if not f.startswith('.')])
                    itens.append(f"  {item}/ ({count} itens)")
                else:
                    ext = os.path.splitext(item)[1]
                    tamanho = os.path.getsize(item_path)
                    if ext in EXTENSOES_PERMITIDAS:
                        itens.append(f"  {item} ({tamanho:,} bytes)")
        except Exception as e:
            return {'log': f'Erro ao listar: {e}', 'conteudo': f'Erro: {str(e)}'}

        resultado = f"**{caminho}** ({len(itens)} itens)\n\n```\n" + "\n".join(itens) + "\n```"
        return {'log': f'Listou {caminho}: {len(itens)} itens', 'conteudo': resultado}

    else:  # modo == 'ler'
        if not os.path.isfile(caminho_abs):
            return {'log': f'Arquivo nao encontrado: {caminho}', 'conteudo': f'"{caminho}" nao encontrado.'}

        ext = os.path.splitext(caminho_abs)[1]
        if ext not in EXTENSOES_PERMITIDAS:
            return {'log': f'Extensao bloqueada: {ext}', 'conteudo': f'Extensao "{ext}" nao permitida. Permitidas: {", ".join(EXTENSOES_PERMITIDAS)}'}

        try:
            with open(caminho_abs, 'r', encoding='utf-8', errors='replace') as f:
                conteudo = f.read()

            # Limitar tamanho
            if len(conteudo) > 8000:
                conteudo = conteudo[:8000] + f'\n\n... [TRUNCADO - arquivo tem {len(conteudo):,} chars]'

            linhas = conteudo.count('\n') + 1
            resultado = f"**{caminho}** ({linhas} linhas)\n\n```python\n{conteudo}\n```"
            return {'log': f'Leu {caminho}: {linhas} linhas', 'conteudo': resultado}
        except Exception as e:
            return {'log': f'Erro ao ler: {e}', 'conteudo': f'Erro: {str(e)}'}


def _consultar_dados(bloco):
    """Consulta dados reais do sistema."""
    from gestao.consulta_dados_service import executar_consulta

    campos = _parse_bloco(bloco)
    consulta = campos.get('consulta', '').strip()
    periodo = campos.get('periodo', '7d').strip()
    cidade = campos.get('cidade', '').strip() or None

    if not consulta:
        return {'log': 'Consulta vazia', 'conteudo': 'Informe o tipo de consulta. Ex: resumo_geral, membros_novos, giros_periodo'}

    resultado = executar_consulta(consulta, periodo=periodo, cidade=cidade)
    return {'log': f'Consultou: {consulta} (periodo={periodo})', 'conteudo': resultado}


def _consultar_documento(bloco):
    """Busca e retorna conteudo de um documento do banco."""
    from gestao.models import Documento
    from django.db.models import Q

    campos = _parse_bloco(bloco)
    busca = campos.get('busca', '').strip()

    if not busca:
        return {'log': 'Busca vazia', 'conteudo': 'Informe um termo de busca.'}

    # Tentar por slug exato
    doc = Documento.objects.filter(slug=busca).first()

    # Tentar por categoria
    if not doc and busca.startswith('categoria:'):
        cat = busca.replace('categoria:', '').strip()
        docs = Documento.objects.filter(categoria=cat).order_by('-data_atualizacao')[:5]
        if docs:
            resultado = f"**{docs.count()} documentos na categoria '{cat}':**\n\n"
            for d in docs:
                resultado += f"---\n## {d.titulo}\n*Slug: {d.slug} | Atualizado: {d.data_atualizacao.strftime('%d/%m/%Y')}*\n\n{d.conteudo}\n\n"
            return {'log': f'Encontrou {docs.count()} docs na categoria {cat}', 'conteudo': resultado}

    # Busca por titulo/conteudo
    if not doc:
        docs = Documento.objects.filter(
            Q(titulo__icontains=busca) | Q(slug__icontains=busca) | Q(conteudo__icontains=busca)
        ).order_by('-data_atualizacao')[:3]
        if docs:
            doc = docs[0]

    if not doc:
        return {'log': f'Documento nao encontrado: {busca}', 'conteudo': f'Nenhum documento encontrado para "{busca}".'}

    conteudo = f"## {doc.titulo}\n*Categoria: {doc.get_categoria_display()} | Atualizado: {doc.data_atualizacao.strftime('%d/%m/%Y')}*\n\n{doc.conteudo}"
    return {'log': f'Documento encontrado: {doc.titulo}', 'conteudo': conteudo}


def _listar_documentos(bloco):
    """Lista documentos disponiveis no banco. Suporta filtro por categoria e pasta."""
    from gestao.models import Documento, PastaDocumento

    campos = _parse_bloco(bloco)
    categoria = campos.get('categoria', '').strip()
    pasta = campos.get('pasta', '').strip()

    qs = Documento.objects.select_related('pasta').all().order_by('categoria', '-data_atualizacao')
    if categoria:
        qs = qs.filter(categoria=categoria)
    if pasta:
        # Buscar por slug ou nome da pasta (inclui subpastas)
        from django.db.models import Q
        pastas_encontradas = PastaDocumento.objects.filter(
            Q(slug__icontains=pasta) | Q(nome__icontains=pasta)
        )
        if pastas_encontradas.exists():
            # Incluir subpastas
            pasta_ids = set()
            for p in pastas_encontradas:
                pasta_ids.add(p.id)
                pasta_ids.update(p.subpastas.values_list('id', flat=True))
            qs = qs.filter(pasta_id__in=pasta_ids)

    if not qs.exists():
        return {'log': 'Nenhum documento', 'conteudo': 'Nenhum documento encontrado.'}

    resultado = f"**{qs.count()} documentos encontrados:**\n\n"
    resultado += "| Titulo | Categoria | Pasta | Slug | Atualizado |\n|--------|-----------|-------|------|------------|\n"
    for d in qs:
        pasta_nome = d.pasta.caminho if d.pasta else '-'
        resultado += f"| {d.titulo} | {d.get_categoria_display()} | {pasta_nome} | `{d.slug}` | {d.data_atualizacao.strftime('%d/%m/%Y')} |\n"

    resultado += "\n*Use `consultar_documento` com o slug para ler o conteudo completo.*"
    return {'log': f'Listou {qs.count()} documentos', 'conteudo': resultado}


# ============================================================
# GERACAO DE IMAGENS VIA IA
# ============================================================

_imagens_geradas_ciclo = 0
MAX_IMAGENS_POR_CICLO = 5


MODELOS_IMAGEM = ['gemini-3-pro-image-preview', 'gemini-2.5-flash-image']


def _gerar_imagem_ia(prompt, tipo, agente_id=None, campos_originais=None):
    """Gera imagem via Gemini com fallback e salva como Documento."""
    global _imagens_geradas_ciclo
    import os
    import logging
    from django.core.files.base import ContentFile
    from gestao.models import Documento, Agente

    logger = logging.getLogger(__name__)

    if campos_originais is None:
        campos_originais = {}

    # Limite por ciclo
    _imagens_geradas_ciclo += 1
    if _imagens_geradas_ciclo > MAX_IMAGENS_POR_CICLO:
        return f"Limite de {MAX_IMAGENS_POR_CICLO} imagens por ciclo atingido."

    api_key = os.environ.get('GOOGLE_AI_API_KEY', '')
    if not api_key:
        return "Erro: GOOGLE_AI_API_KEY nao configurada."

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Tentar cada modelo com fallback
        img_bytes = None
        modelo_usado = None
        for modelo in MODELOS_IMAGEM:
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT']),
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        img_bytes = part.inline_data.data
                        modelo_usado = modelo
                        break
                if img_bytes:
                    break
            except Exception as e:
                logger.warning(f'Modelo {modelo} falhou: {e}. Tentando proximo...')
                continue

        if not img_bytes:
            return "Erro: nenhuma imagem gerada (todos os modelos falharam)."

        slug = f"img-{tipo}-{uuid.uuid4().hex[:8]}"
        filename = f"{tipo}/{slug}.png"

        # Salvar como Documento
        agente = Agente.objects.filter(slug=agente_id).first() if agente_id else None
        tipo_labels = {'banner': 'Banner', 'cupom': 'Imagem Cupom', 'campanha': 'Arte Campanha'}
        doc = Documento(
            titulo=f"{tipo_labels.get(tipo, tipo)}: {campos_originais.get('objetivo', campos_originais.get('parceiro', prompt[:60]))}",
            slug=slug,
            categoria='imagem',
            agente=agente,
            conteudo=f"Imagem gerada por IA.\n\nPrompt: {prompt}\nTipo: {tipo}\nModelo: {modelo_usado}",
            resumo=f"Imagem {tipo} gerada por IA",
            visivel_agentes=False,
        )
        doc.arquivo.save(filename, ContentFile(img_bytes), save=True)

        _registrar_log(f'gerar_{tipo}', agente_id, f'Imagem gerada: {doc.titulo} (doc #{doc.id})')
        img_url = doc.arquivo.url if doc.arquivo else ''
        return f"Imagem gerada e salva como documento #{doc.id}: '{doc.titulo}'\n![imagem]({img_url})"

    except Exception as e:
        return f"Erro ao gerar imagem: {str(e)}"


def _gerar_banner(bloco, agente_id=None):
    """Gera banner para clube/campanha."""
    campos = _parse_bloco(bloco)
    objetivo = campos.get('objetivo', '')
    contexto = campos.get('contexto', '')

    if not objetivo:
        return "Campo 'objetivo' obrigatorio para gerar banner."

    prompt = (
        f"Generate a professional wide landscape banner image with 16:9 aspect ratio for a telecom loyalty club. "
        f"Objective: {objetivo}. "
        f"Context: {contexto}. "
        f"Dark navy blue background (#000b4a) with golden accents (#f59e0b). "
        f"Modern, clean, professional corporate design. Brazilian style. "
        f"DO NOT include any text in the image - leave space on the right side for text overlay."
    )
    return _gerar_imagem_ia(prompt, 'banner', agente_id, campos)


def _gerar_imagem_cupom(bloco, agente_id=None):
    """Gera imagem para cupom de parceiro."""
    campos = _parse_bloco(bloco)
    parceiro = campos.get('parceiro', '')
    desconto = campos.get('desconto', '')
    categoria = campos.get('categoria', '')

    if not parceiro:
        return "Campo 'parceiro' obrigatorio para gerar imagem de cupom."

    prompt = (
        f"Generate a professional promotional image with 1:1 square aspect ratio for a discount coupon. "
        f"Partner name: {parceiro}. Category: {categoria}. Discount: {desconto}. "
        f"Show appetizing/attractive product related to the category. "
        f"Include text: '{parceiro}' at the top and '{desconto}' in large bold text. "
        f"Clean commercial design, warm inviting colors."
    )
    return _gerar_imagem_ia(prompt, 'cupom', agente_id, campos)


def _gerar_arte_campanha(bloco, agente_id=None):
    """Gera arte para campanha/post de marketing."""
    campos = _parse_bloco(bloco)
    objetivo = campos.get('objetivo', '')
    publico = campos.get('publico', '')
    tom = campos.get('tom', 'profissional')

    if not objetivo:
        return "Campo 'objetivo' obrigatorio para gerar arte de campanha."

    prompt = (
        f"Generate a professional marketing campaign image with 1:1 square aspect ratio. "
        f"Objective: {objetivo}. Target audience: {publico}. Tone: {tom}. "
        f"For a telecom loyalty club called Clube Megalink. "
        f"Colors: dark navy blue (#000b4a) and golden (#f59e0b). "
        f"Modern, eye-catching design suitable for Instagram or WhatsApp. "
        f"Brazilian audience from small cities in Piaui and Maranhao."
    )
    return _gerar_imagem_ia(prompt, 'campanha', agente_id, campos)
