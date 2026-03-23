import logging
import os
import time

from django.conf import settings

logger = logging.getLogger(__name__)


class HealthService:
    """Verifica saúde de todos os serviços externos e internos."""

    @staticmethod
    def verificar_tudo():
        """Executa todos os checks e retorna relatório completo."""
        checks = [
            HealthService._check_banco_principal,
            HealthService._check_hubsoft,
            HealthService._check_openai,
            HealthService._check_membros,
            HealthService._check_premios,
            HealthService._check_cupons,
        ]

        resultados = []
        for check_fn in checks:
            try:
                resultado = check_fn()
                resultados.append(resultado)
            except Exception as e:
                resultados.append({
                    'nome': check_fn.__doc__ or check_fn.__name__,
                    'status': 'erro',
                    'detalhe': str(e),
                    'ms': 0,
                })

        # Resumo
        total = len(resultados)
        ok = sum(1 for r in resultados if r['status'] == 'ok')
        warn = sum(1 for r in resultados if r['status'] == 'aviso')
        erros = sum(1 for r in resultados if r['status'] == 'erro')

        return {
            'checks': resultados,
            'total': total,
            'ok': ok,
            'avisos': warn,
            'erros': erros,
            'saudavel': erros == 0,
        }

    @staticmethod
    def _check_banco_principal():
        """Banco Principal (PostgreSQL)"""
        inicio = time.time()
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            ms = int((time.time() - inicio) * 1000)

            from roleta.models import MembroClube
            total = MembroClube.objects.count()

            return {
                'nome': 'Banco Principal (PostgreSQL)',
                'icone': 'fas fa-database',
                'status': 'ok',
                'detalhe': f'Conectado — {total} membros no banco',
                'ms': ms,
            }
        except Exception as e:
            return {
                'nome': 'Banco Principal (PostgreSQL)',
                'icone': 'fas fa-database',
                'status': 'erro',
                'detalhe': f'Falha na conexão: {e}',
                'ms': int((time.time() - inicio) * 1000),
            }

    @staticmethod
    def _check_hubsoft():
        """Hubsoft (PostgreSQL Read-Only)"""
        inicio = time.time()
        try:
            from roleta.services.hubsoft_service import HubsoftService
            conn = HubsoftService._get_hubsoft_connection(connect_timeout=5)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            ms = int((time.time() - inicio) * 1000)

            return {
                'nome': 'Hubsoft (PostgreSQL Read-Only)',
                'icone': 'fas fa-server',
                'status': 'ok' if ms < 3000 else 'aviso',
                'detalhe': f'Conectado em {ms}ms' + (' (lento!)' if ms > 3000 else ''),
                'ms': ms,
            }
        except Exception as e:
            ms = int((time.time() - inicio) * 1000)
            erro_str = str(e)
            if 'timeout' in erro_str.lower():
                detalhe = f'Timeout após {ms}ms — servidor inacessível'
            else:
                detalhe = f'Falha: {erro_str[:150]}'
            return {
                'nome': 'Hubsoft (PostgreSQL Read-Only)',
                'icone': 'fas fa-server',
                'status': 'erro',
                'detalhe': detalhe,
                'ms': ms,
            }

    @staticmethod
    def _check_openai():
        """API OpenAI"""
        inicio = time.time()
        try:
            api_key = os.environ.get('OPENAI_API_KEY', getattr(settings, 'OPENAI_API_KEY', ''))
            if not api_key:
                return {
                    'nome': 'API OpenAI',
                    'icone': 'fas fa-brain',
                    'status': 'erro',
                    'detalhe': 'OPENAI_API_KEY não configurada no .env',
                    'ms': 0,
                }

            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Responda apenas: ok"}],
                max_tokens=5,
            )
            ms = int((time.time() - inicio) * 1000)
            texto = response.choices[0].message.content.strip()

            return {
                'nome': 'API OpenAI',
                'icone': 'fas fa-brain',
                'status': 'ok' if ms < 5000 else 'aviso',
                'detalhe': f'Respondeu "{texto}" em {ms}ms' + (' (lento!)' if ms > 5000 else ''),
                'ms': ms,
            }
        except Exception as e:
            return {
                'nome': 'API OpenAI',
                'icone': 'fas fa-brain',
                'status': 'erro',
                'detalhe': f'Falha: {str(e)[:150]}',
                'ms': int((time.time() - inicio) * 1000),
            }

    @staticmethod
    def _check_membros():
        """Membros do Clube"""
        inicio = time.time()
        try:
            from roleta.models import MembroClube
            total = MembroClube.objects.count()
            validados = MembroClube.objects.filter(validado=True).count()
            ms = int((time.time() - inicio) * 1000)

            status = 'ok'
            if total == 0:
                status = 'aviso'

            return {
                'nome': 'Membros do Clube',
                'icone': 'fas fa-users',
                'status': status,
                'detalhe': f'{total} membros ({validados} validados)',
                'ms': ms,
            }
        except Exception as e:
            return {
                'nome': 'Membros do Clube',
                'icone': 'fas fa-users',
                'status': 'erro',
                'detalhe': str(e),
                'ms': int((time.time() - inicio) * 1000),
            }

    @staticmethod
    def _check_premios():
        """Estoque de Prêmios"""
        inicio = time.time()
        try:
            from roleta.models import PremioRoleta
            total = PremioRoleta.objects.count()
            com_estoque = PremioRoleta.objects.filter(quantidade__gt=0).count()
            sem_estoque = total - com_estoque

            # Prêmios acabando (< 5 unidades)
            acabando = list(
                PremioRoleta.objects.filter(quantidade__gt=0, quantidade__lt=5)
                .exclude(nome__icontains='não foi dessa vez')
                .values_list('nome', 'quantidade')
            )
            ms = int((time.time() - inicio) * 1000)

            status = 'ok'
            detalhe = f'{com_estoque} prêmios com estoque'
            if sem_estoque > 0:
                detalhe += f', {sem_estoque} esgotados'
            if acabando:
                status = 'aviso'
                nomes = ', '.join(f'{n} ({q})' for n, q in acabando)
                detalhe += f' ⚠ Acabando: {nomes}'

            return {
                'nome': 'Estoque de Prêmios',
                'icone': 'fas fa-gift',
                'status': status,
                'detalhe': detalhe,
                'ms': ms,
            }
        except Exception as e:
            return {
                'nome': 'Estoque de Prêmios',
                'icone': 'fas fa-gift',
                'status': 'erro',
                'detalhe': str(e),
                'ms': int((time.time() - inicio) * 1000),
            }

    @staticmethod
    def _check_cupons():
        """Cupons Ativos"""
        inicio = time.time()
        try:
            from parceiros.models import CupomDesconto, Parceiro
            from django.utils import timezone

            cupons_ativos = CupomDesconto.objects.filter(ativo=True, status_aprovacao='aprovado').count()
            parceiros_ativos = Parceiro.objects.filter(ativo=True).count()
            pendentes = CupomDesconto.objects.filter(status_aprovacao='pendente').count()

            # Cupons vencidos ainda ativos
            vencidos = CupomDesconto.objects.filter(
                ativo=True, data_fim__lt=timezone.now()
            ).count()

            ms = int((time.time() - inicio) * 1000)

            status = 'ok'
            detalhe = f'{cupons_ativos} cupons ativos, {parceiros_ativos} parceiros'
            if pendentes > 0:
                detalhe += f', {pendentes} pendentes de aprovação'
            if vencidos > 0:
                status = 'aviso'
                detalhe += f' ⚠ {vencidos} cupons vencidos ainda ativos!'

            return {
                'nome': 'Cupons Ativos',
                'icone': 'fas fa-ticket-alt',
                'status': status,
                'detalhe': detalhe,
                'ms': ms,
            }
        except Exception as e:
            return {
                'nome': 'Cupons Ativos',
                'icone': 'fas fa-ticket-alt',
                'status': 'erro',
                'detalhe': str(e),
                'ms': int((time.time() - inicio) * 1000),
            }
