from django.http import HttpResponse, Http404
from django.conf import settings
import os
import markdown

def documentacao(request):
    """
    Renderiza o arquivo DOCUMENTACAO.md como uma página HTML estilizada.
    Acessível apenas por staff (usuários administradores).
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        from django.shortcuts import redirect
        return redirect('admin_login')

    md_path = os.path.join(settings.BASE_DIR, 'DOCUMENTACAO.md')
    if not os.path.exists(md_path):
        raise Http404("Arquivo de documentação não encontrado.")

    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Converte o markdown para HTML com extensões úteis
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'toc', 'fenced_code', 'nl2br']
    )

    return HttpResponse(f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentação — Roleta MegaLink</title>
    <style>
        :root {{
            --bg: #0f1117;
            --surface: #1a1d27;
            --border: #2a2d3e;
            --primary: #6c63ff;
            --primary-light: #8a83ff;
            --text: #e2e8f0;
            --text-muted: #8892a4;
            --code-bg: #12151f;
            --success: #34d399;
            --warning: #fbbf24;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
            display: flex;
        }}

        /* Sidebar TOC */
        #sidebar {{
            width: 260px;
            min-height: 100vh;
            background: var(--surface);
            border-right: 1px solid var(--border);
            padding: 24px 16px;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            flex-shrink: 0;
        }}

        #sidebar h3 {{
            font-size: 11px;
            font-weight: 600;
            letter-spacing: .1em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}

        #sidebar ul {{ list-style: none; }}
        #sidebar ul li {{ margin: 2px 0; }}
        #sidebar ul li a {{
            color: var(--text-muted);
            text-decoration: none;
            font-size: 13px;
            display: block;
            padding: 4px 8px;
            border-radius: 6px;
            transition: all .15s;
        }}
        #sidebar ul li a:hover {{
            color: var(--primary-light);
            background: rgba(108,99,255,.1);
        }}
        #sidebar ul li ul li a {{
            padding-left: 20px;
            font-size: 12px;
        }}

        /* Back button */
        .back-btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: var(--text-muted);
            text-decoration: none;
            font-size: 13px;
            margin-bottom: 20px;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid var(--border);
            transition: all .15s;
        }}
        .back-btn:hover {{ color: var(--text); border-color: var(--primary); }}

        /* Content */
        #content {{
            flex: 1;
            padding: 48px 64px;
            max-width: 1000px;
        }}

        h1 {{
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }}

        h2 {{
            font-size: 1.35rem;
            font-weight: 600;
            color: var(--text);
            margin: 40px 0 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }}

        h3 {{
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--primary-light);
            margin: 24px 0 8px;
        }}

        h4 {{
            font-size: .95rem;
            font-weight: 600;
            color: var(--text-muted);
            margin: 16px 0 6px;
        }}

        p {{ margin: 10px 0; }}

        blockquote {{
            border-left: 3px solid var(--primary);
            padding: 10px 16px;
            background: rgba(108,99,255,.08);
            border-radius: 0 8px 8px 0;
            margin: 16px 0;
            color: var(--text-muted);
            font-style: italic;
        }}

        code {{
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 13px;
            color: #f472b6;
            border: 1px solid var(--border);
        }}

        pre {{
            background: var(--code-bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            overflow-x: auto;
            margin: 16px 0;
        }}
        pre code {{
            background: none;
            border: none;
            padding: 0;
            color: #a5f3fc;
            font-size: 13px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 14px;
        }}
        th {{
            background: var(--surface);
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: .05em;
            padding: 10px 14px;
            text-align: left;
            border-bottom: 2px solid var(--border);
        }}
        td {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: rgba(255,255,255,.02); }}

        ul, ol {{
            padding-left: 24px;
            margin: 8px 0;
        }}
        li {{ margin: 4px 0; }}

        hr {{
            border: none;
            border-top: 1px solid var(--border);
            margin: 32px 0;
        }}

        a {{ color: var(--primary-light); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}

        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: var(--bg); }}
        ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

        @media (max-width: 768px) {{
            body {{ flex-direction: column; }}
            #sidebar {{ width: 100%; height: auto; position: static; }}
            #content {{ padding: 24px 20px; }}
        }}
    </style>
</head>
<body>
    <nav id="sidebar">
        <a href="/roleta/dashboard/" class="back-btn">&#8592; Dashboard</a>
        <h3>📋 Neste documento</h3>
        <ul>
            <li><a href="#1-visão-geral">1. Visão Geral</a></li>
            <li><a href="#2-fluxo-principal-do-usuário">2. Fluxo do Usuário</a></li>
            <li><a href="#3-regras-de-pontuação-e-gamificação">3. Gamificação</a>
                <ul>
                    <li><a href="#missões-regraPontuacao">Missões</a></li>
                    <li><a href="#xp-e-níveis">XP e Níveis</a></li>
                </ul>
            </li>
            <li><a href="#4-integração-com-o-hubsoft">4. Hubsoft</a></li>
            <li><a href="#5-prêmios-e-sorteio">5. Prêmios e Sorteio</a></li>
            <li><a href="#6-verificação-de-identidade-otp">6. OTP</a></li>
            <li><a href="#7-entidades-do-sistema">7. Entidades</a></li>
            <li><a href="#8-painel-administrativo-dashboard">8. Dashboard Admin</a></li>
            <li><a href="#9-endpoints-da-api-interna">9. Endpoints</a></li>
            <li><a href="#10-configurações-gerais">10. Configurações</a></li>
            <li><a href="#11-integrações-externas">11. Integrações</a></li>
            <li><a href="#12-assets-visuais">12. Assets</a></li>
        </ul>
    </nav>
    <main id="content">
        {html_content}
    </main>
</body>
</html>""")
