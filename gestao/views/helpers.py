import markdown
import bleach


def _render_md_text(conteudo):
    """Renderiza texto markdown para HTML, sanitizado contra XSS."""
    html_raw = markdown.markdown(conteudo, extensions=['tables', 'fenced_code', 'toc'])
    return bleach.clean(
        html_raw,
        tags=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'abbr', 'acronym',
              'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'ul', 'pre',
              'strong', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'br', 'hr',
              'div', 'span', 'img', 'sup', 'sub', 'del'],
        attributes={'a': ['href', 'title'], 'img': ['src', 'alt', 'title'],
                    'th': ['align'], 'td': ['align'], '*': ['class', 'id']},
        protocols=['http', 'https', 'mailto'],
    )


def _sanitizar_markdown(texto):
    """Sanitiza texto markdown/HTML na entrada (antes de salvar no banco)."""
    if not texto:
        return texto
    return bleach.clean(
        texto,
        tags=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'abbr', 'acronym',
              'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'ul', 'pre',
              'strong', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'br', 'hr',
              'div', 'span', 'img', 'sup', 'sub', 'del'],
        attributes={'a': ['href', 'title'], 'img': ['src', 'alt', 'title'],
                    'th': ['align'], 'td': ['align'], '*': ['class', 'id']},
        protocols=['http', 'https', 'mailto'],
    )
