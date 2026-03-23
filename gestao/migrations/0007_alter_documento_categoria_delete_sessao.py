# Migrate Sessao -> Documento with categoria='sessao', then delete Sessao

from django.db import migrations, models
import uuid


def migrar_sessoes_para_documentos(apps, schema_editor):
    Sessao = apps.get_model('gestao', 'Sessao')
    Documento = apps.get_model('gestao', 'Documento')

    for s in Sessao.objects.all():
        Documento.objects.create(
            titulo=s.titulo,
            slug=f"sessao-{uuid.uuid4().hex[:8]}",
            categoria='sessao',
            agente_id=s.agente_id,
            conteudo=s.conteudo,
            resumo=s.resumo,
            descricao=s.resumo[:300] if s.resumo else '',
            visivel_agentes=False,
            ordem=60,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('gestao', '0006_documento_agente_documento_resumo_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documento',
            name='categoria',
            field=models.CharField(choices=[('estrategia', 'Estratégia'), ('regras', 'Regras de Negócio'), ('roadmap', 'Roadmap'), ('decisoes', 'Decisões'), ('entrega', 'Entrega de Agente'), ('sessao', 'Sessão com Agente'), ('contexto', 'Base de Conhecimento'), ('outro', 'Outro')], default='outro', max_length=20),
        ),
        migrations.RunPython(migrar_sessoes_para_documentos, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='Sessao',
        ),
    ]
