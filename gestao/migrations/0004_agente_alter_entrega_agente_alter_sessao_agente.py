# Custom migration: Create Agente, populate, convert Entrega/Sessao FK

from django.db import migrations, models
import django.db.models.deletion


AGENTES_INICIAIS = [
    {'slug': 'cto', 'nome': 'CTO', 'descricao': 'Tecnologia e Arquitetura', 'icone': 'fas fa-code', 'cor': '#3b82f6', 'time': 'executivo', 'ordem': 1},
    {'slug': 'cpo', 'nome': 'CPO', 'descricao': 'Produto e Priorização', 'icone': 'fas fa-cube', 'cor': '#8b5cf6', 'time': 'executivo', 'ordem': 2},
    {'slug': 'cfo', 'nome': 'CFO', 'descricao': 'Finanças e ROI', 'icone': 'fas fa-chart-pie', 'cor': '#10b981', 'time': 'executivo', 'ordem': 3},
    {'slug': 'cmo', 'nome': 'CMO', 'descricao': 'Marketing e Growth', 'icone': 'fas fa-bullhorn', 'cor': '#f59e0b', 'time': 'comercial', 'ordem': 4},
    {'slug': 'pmm', 'nome': 'PMM', 'descricao': 'Posicionamento e Messaging', 'icone': 'fas fa-bullseye', 'cor': '#ec4899', 'time': 'comercial', 'ordem': 5},
    {'slug': 'b2b', 'nome': 'Comercial B2B', 'descricao': 'Prospecção de Parceiros', 'icone': 'fas fa-handshake', 'cor': '#6366f1', 'time': 'comercial', 'ordem': 6},
    {'slug': 'cs', 'nome': 'Customer Success', 'descricao': 'Onboarding e Retenção', 'icone': 'fas fa-heart', 'cor': '#ef4444', 'time': 'comercial', 'ordem': 7},
    {'slug': 'ceo', 'nome': 'CEO', 'descricao': 'Visão Estratégica', 'icone': 'fas fa-crown', 'cor': '#f59e0b', 'time': 'executivo', 'ordem': 0},
]


def criar_agentes_e_converter(apps, schema_editor):
    Agente = apps.get_model('gestao', 'Agente')
    Entrega = apps.get_model('gestao', 'Entrega')
    Sessao = apps.get_model('gestao', 'Sessao')

    # Criar agentes
    agentes_map = {}
    for dados in AGENTES_INICIAIS:
        agente = Agente.objects.create(prompt='(prompt pendente)', **dados)
        agentes_map[dados['slug']] = agente.id

    # Converter entregas
    for entrega in Entrega.objects.all():
        slug = entrega.agente_slug
        if slug and slug in agentes_map:
            entrega.agente_fk_id = agentes_map[slug]
            entrega.save(update_fields=['agente_fk_id'])

    # Converter sessoes
    for sessao in Sessao.objects.all():
        slug = sessao.agente_slug
        if slug and slug in agentes_map:
            sessao.agente_fk_id = agentes_map[slug]
            sessao.save(update_fields=['agente_fk_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('gestao', '0003_entrega_sessao'),
    ]

    operations = [
        # 1. Criar tabela Agente
        migrations.CreateModel(
            name='Agente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(help_text='ID unico', max_length=20, unique=True)),
                ('nome', models.CharField(max_length=100)),
                ('descricao', models.CharField(max_length=200)),
                ('icone', models.CharField(default='fas fa-robot', max_length=50)),
                ('cor', models.CharField(default='#3b82f6', max_length=10)),
                ('time', models.CharField(choices=[('executivo', 'Executivo'), ('comercial', 'Comercial'), ('tools', 'Tools')], default='executivo', max_length=20)),
                ('prompt', models.TextField()),
                ('modelo', models.CharField(default='gpt-4o-mini', max_length=50)),
                ('ativo', models.BooleanField(default=True)),
                ('ordem', models.IntegerField(default=0)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Agente',
                'verbose_name_plural': 'Agentes',
                'ordering': ['ordem', 'nome'],
            },
        ),

        # 2. Renomear campo antigo para agente_slug
        migrations.RenameField(model_name='entrega', old_name='agente', new_name='agente_slug'),
        migrations.RenameField(model_name='sessao', old_name='agente', new_name='agente_slug'),

        # 3. Adicionar novo campo FK
        migrations.AddField(
            model_name='entrega',
            name='agente_fk',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entregas', to='gestao.agente'),
        ),
        migrations.AddField(
            model_name='sessao',
            name='agente_fk',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sessoes', to='gestao.agente'),
        ),

        # 4. Data migration: criar agentes + converter slugs para FKs
        migrations.RunPython(criar_agentes_e_converter, migrations.RunPython.noop),

        # 5. Remover campo antigo slug
        migrations.RemoveField(model_name='entrega', name='agente_slug'),
        migrations.RemoveField(model_name='sessao', name='agente_slug'),

        # 6. Renomear agente_fk -> agente
        migrations.RenameField(model_name='entrega', old_name='agente_fk', new_name='agente'),
        migrations.RenameField(model_name='sessao', old_name='agente_fk', new_name='agente'),
    ]
