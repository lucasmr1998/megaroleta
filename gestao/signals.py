from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache


def _invalidar_contexto(**kwargs):
    cache.delete('gestao:contexto_leve')


@receiver(post_save, sender='gestao.Projeto')
@receiver(post_delete, sender='gestao.Projeto')
def projeto_changed(sender, **kwargs):
    _invalidar_contexto()


@receiver(post_save, sender='gestao.Tarefa')
@receiver(post_delete, sender='gestao.Tarefa')
def tarefa_changed(sender, **kwargs):
    _invalidar_contexto()


@receiver(post_save, sender='gestao.Documento')
@receiver(post_delete, sender='gestao.Documento')
def documento_changed(sender, **kwargs):
    _invalidar_contexto()
