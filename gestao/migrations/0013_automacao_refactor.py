# Refatora Automacao: remove campos legados, adiciona FK tool, remove LogAutomacao

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gestao', '0012_automacoes_e_faq'),
    ]

    operations = [
        # 1. Deletar LogAutomacao (logs agora vão para LogTool)
        migrations.DeleteModel(
            name='LogAutomacao',
        ),

        # 2. Deletar Automacao antiga e recriar com schema novo
        migrations.DeleteModel(
            name='Automacao',
        ),
        migrations.CreateModel(
            name='Automacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('intervalo_horas', models.IntegerField(default=24, help_text='Intervalo entre execuções em horas')),
                ('status', models.CharField(choices=[('ativo', 'Ativo'), ('pausado', 'Pausado'), ('erro', 'Com Erro')], db_index=True, default='ativo', max_length=20)),
                ('ultima_execucao', models.DateTimeField(blank=True, null=True)),
                ('ultimo_resultado', models.TextField(blank=True)),
                ('total_execucoes', models.IntegerField(default=0)),
                ('total_erros', models.IntegerField(default=0)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('agente', models.ForeignKey(help_text='Agente responsável pela execução', on_delete=django.db.models.deletion.CASCADE, related_name='automacoes', to='gestao.agente')),
                ('tool', models.ForeignKey(help_text='Tool que será executada', on_delete=django.db.models.deletion.CASCADE, related_name='automacoes', to='gestao.toolagente')),
            ],
            options={
                'verbose_name': 'Automação',
                'verbose_name_plural': 'Automações',
                'ordering': ['agente__nome', 'tool__nome'],
                'unique_together': {('agente', 'tool')},
            },
        ),

        # 3. Adicionar icone ao ToolAgente
        migrations.AddField(
            model_name='toolagente',
            name='icone',
            field=models.CharField(default='fas fa-wrench', help_text='Classe FontAwesome', max_length=50),
        ),
    ]
