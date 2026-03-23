import hashlib
import json
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)


class FAQService:

    @staticmethod
    def coletar_dados_sistema():
        """Coleta dados reais do sistema para gerar FAQs por categoria."""
        from roleta.models import RoletaConfig, PremioRoleta, NivelClube, RegraPontuacao
        from parceiros.models import Parceiro, CupomDesconto
        from indicacoes.models import IndicacaoConfig

        config, _ = RoletaConfig.objects.get_or_create(id=1)

        dados = {}

        # Roleta
        premios = list(PremioRoleta.objects.all().values('nome', 'quantidade')[:20])
        premios_nomes = [p['nome'] for p in premios if p['nome'].lower() != 'não foi dessa vez']
        dados['roleta'] = {
            'como_funciona': f'O membro gasta {config.custo_giro} créditos (chamados de "giros") para girar a roleta. Os créditos são ganhos completando missões (ativar recorrência, pagar adiantado, indicar amigos, etc). NÃO é cobrado dinheiro.',
            'custo_giro_creditos': config.custo_giro,
            'xp_por_giro': config.xp_por_giro,
            'limite_giros': config.limite_giros_por_membro,
            'periodo_limite': config.periodo_limite,
            'premios_possiveis': premios_nomes if premios_nomes else ['Prêmios a serem cadastrados'],
            'obs': 'A roleta é GRATUITA. O membro ganha créditos ao completar missões e usa esses créditos para girar.',
        }

        # Pontos e Níveis
        niveis = list(NivelClube.objects.all().order_by('xp_necessario').values('nome', 'xp_necessario'))
        regras = list(RegraPontuacao.objects.filter(ativo=True).values(
            'nome_exibicao', 'pontos_saldo', 'pontos_xp', 'limite_por_membro'
        ))
        dados['pontos-niveis'] = {
            'como_funciona': 'O membro ganha créditos (saldo) e XP ao completar missões. Créditos são usados para girar a roleta. XP sobe o nível do membro no clube (Bronze → Prata → Ouro). Níveis mais altos desbloqueiam cupons exclusivos.',
            'niveis': niveis,
            'regras_de_pontuacao': regras,
            'custo_por_giro': f'{config.custo_giro} créditos',
        }

        # Cupons
        parceiros_ativos = list(Parceiro.objects.filter(ativo=True).values_list('nome', flat=True)[:20])
        cupons_ativos = list(CupomDesconto.objects.filter(
            ativo=True, status_aprovacao='aprovado'
        ).values('titulo', 'tipo_desconto', 'valor_desconto', 'modalidade', 'custo_pontos')[:20])
        dados['cupons'] = {
            'parceiros': parceiros_ativos,
            'cupons': cupons_ativos,
        }

        # Indicações
        try:
            ind_config = IndicacaoConfig.objects.get(id=1)
            titulo_ind = ind_config.titulo
        except Exception:
            titulo_ind = "Indique amigos"
        regra_ind = RegraPontuacao.objects.filter(gatilho='indicacao_convertida', ativo=True).first()
        dados['indicacoes'] = {
            'titulo': titulo_ind,
            'pontos_indicacao': regra_ind.pontos_saldo if regra_ind else 0,
            'xp_indicacao': regra_ind.pontos_xp if regra_ind else 0,
        }

        # Carteirinha
        dados['carteirinha'] = {
            'descricao': 'Carteirinha virtual do Clube Megalink com foto, nome, nível e QR code',
        }

        # Conta
        dados['conta'] = {
            'metodo_login': 'CPF + código OTP via WhatsApp',
            'expiracao_otp': '10 minutos',
        }

        return dados

    @staticmethod
    def gerar_hash(dados):
        """Gera SHA256 de um dict para detectar mudanças."""
        texto = json.dumps(dados, sort_keys=True, default=str)
        return hashlib.sha256(texto.encode()).hexdigest()

    @staticmethod
    def _chamar_openai(categoria_nome, dados_texto):
        """Chama OpenAI para gerar FAQs."""
        from openai import OpenAI

        api_key = os.environ.get('OPENAI_API_KEY', getattr(settings, 'OPENAI_API_KEY', ''))
        if not api_key:
            logger.warning("OPENAI_API_KEY não configurada")
            return []

        client = OpenAI(api_key=api_key)

        prompt = f"""Voce e um assistente do Clube Megalink, programa de fidelidade GRATUITO da Megalink Telecom (provedor de internet do Piaui e Maranhao).

CONTEXTO DO CLUBE:
- O Clube Megalink e 100% gratuito para os clientes assinantes da Megalink
- O membro ganha creditos (chamados "giros") ao completar missoes como: ativar recorrencia, pagar fatura adiantada, usar o app, indicar amigos
- Com os creditos, o membro gira a roleta para ganhar premios reais
- Alem da roleta, o membro acessa cupons de desconto em parceiros locais (restaurantes, academias, etc)
- O membro sobe de nivel (Bronze, Prata, Ouro) conforme acumula XP, desbloqueando beneficios exclusivos
- NENHUM dinheiro e cobrado. Os creditos sao ganhos por merito (missoes)

Gere exatamente 5 perguntas frequentes (FAQ) sobre "{categoria_nome}" baseadas nos dados reais abaixo.

DADOS REAIS DO SISTEMA:
{dados_texto}

REGRAS PARA GERAR AS FAQs:
- Perguntas devem ser duvidas REAIS que um cliente da Megalink teria
- Respostas claras, diretas, em 2-4 frases
- Use os dados EXATOS fornecidos (valores reais, nomes reais)
- Se houver uma lista de premios, MENCIONE os premios pelo nome
- NUNCA diga que algo custa dinheiro — os creditos sao GRATUITOS, ganhos por missoes
- Linguagem informal mas profissional, em portugues brasileiro
- NAO invente dados que nao estejam acima
- Retorne APENAS o JSON, sem markdown ou explicacao

Formato de resposta (JSON puro):
[{{"pergunta": "...", "resposta": "..."}}, ...]"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7,
            )
            texto = response.choices[0].message.content.strip()
            # Limpar possível markdown wrapper
            if texto.startswith("```"):
                texto = texto.split("\n", 1)[1] if "\n" in texto else texto[3:]
                if texto.endswith("```"):
                    texto = texto[:-3]
                texto = texto.strip()
            return json.loads(texto)
        except Exception as e:
            logger.error(f"Erro ao gerar FAQ para {categoria_nome}: {e}")
            return []

    @staticmethod
    def atualizar_faqs(force=False, categoria_slug=None, dry_run=False):
        """Atualiza FAQs que mudaram. Retorna resumo."""
        from gestao.models import FAQCategoria, FAQItem

        dados = FAQService.coletar_dados_sistema()
        resultado = {}

        categorias = FAQCategoria.objects.filter(ativo=True)
        if categoria_slug:
            categorias = categorias.filter(slug=categoria_slug)

        for cat in categorias:
            dados_cat = dados.get(cat.slug, {})
            if not dados_cat:
                resultado[cat.slug] = 'sem_dados'
                continue

            novo_hash = FAQService.gerar_hash(dados_cat)

            # Verificar se precisa atualizar
            item_existente = FAQItem.objects.filter(categoria=cat, gerado_por_ia=True).first()
            if not force and item_existente and item_existente.hash_dados_fonte == novo_hash:
                resultado[cat.slug] = 'sem_mudanca'
                continue

            if dry_run:
                resultado[cat.slug] = 'seria_atualizado'
                continue

            # Gerar FAQs via IA
            dados_texto = json.dumps(dados_cat, indent=2, ensure_ascii=False, default=str)
            faqs = FAQService._chamar_openai(cat.nome, dados_texto)

            if not faqs:
                resultado[cat.slug] = 'erro_ia'
                continue

            # Remover FAQs geradas por IA antigas desta categoria
            FAQItem.objects.filter(categoria=cat, gerado_por_ia=True).delete()

            # Criar novas
            for i, faq in enumerate(faqs):
                FAQItem.objects.create(
                    categoria=cat,
                    pergunta=faq.get('pergunta', ''),
                    resposta=faq.get('resposta', ''),
                    ordem=i,
                    ativo=True,
                    gerado_por_ia=True,
                    hash_dados_fonte=novo_hash,
                )

            resultado[cat.slug] = f'atualizado ({len(faqs)} itens)'
            logger.info(f"FAQ '{cat.nome}' atualizada: {len(faqs)} itens")

        return resultado

    @staticmethod
    def garantir_categorias():
        """Cria categorias padrão se não existirem."""
        from gestao.models import FAQCategoria

        categorias_padrao = [
            {'slug': 'roleta', 'nome': 'Roleta', 'icone': 'fas fa-dice', 'cor': '#2563eb', 'ordem': 1},
            {'slug': 'pontos-niveis', 'nome': 'Pontos e Níveis', 'icone': 'fas fa-medal', 'cor': '#f59e0b', 'ordem': 2},
            {'slug': 'cupons', 'nome': 'Cupons', 'icone': 'fas fa-ticket-alt', 'cor': '#059669', 'ordem': 3},
            {'slug': 'indicacoes', 'nome': 'Indicações', 'icone': 'fas fa-user-plus', 'cor': '#d97706', 'ordem': 4},
            {'slug': 'carteirinha', 'nome': 'Carteirinha', 'icone': 'fas fa-id-card', 'cor': '#4f46e5', 'ordem': 5},
            {'slug': 'conta', 'nome': 'Minha Conta', 'icone': 'fas fa-user-circle', 'cor': '#7c3aed', 'ordem': 6},
        ]

        for cat in categorias_padrao:
            FAQCategoria.objects.get_or_create(
                slug=cat['slug'],
                defaults=cat,
            )
