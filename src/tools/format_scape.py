import re

def escape_markdown(text):
    """
    Escapa el texto para Telegram MarkdownV2, preservando el formato básico de Markdown
    como negritas, cursivas, enlaces y bloques de código.
    """
    # Convierte negritas de Markdown estándar (**) a MarkdownV2 (*)
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    
    # Convierte títulos de Markdown (# Título) a negritas (*Título*) para evitar el carácter #
    text = re.sub(r'^#+\s*(.*)$', r'*\1*', text, flags=re.MULTILINE)
    
    # Caracteres que deben escaparse en MarkdownV2

    escape_chars = r'_*[]()~`>#+-=|{}.!'
    
    def escape_basic(t):
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', t)

    placeholders = []
    
    def p(match):
        val = match.group(0)
        if val.startswith('```'):
            # Bloque de código: escapar solo ` y \
            content = val[3:-3]
            content = content.replace('\\', '\\\\').replace('`', '\\`')
            val = f'```{content}```'
        elif val.startswith('`'):
            # Código en línea: escapar solo ` y \
            content = val[1:-1]
            content = content.replace('\\', '\\\\').replace('`', '\\`')
            val = f'`{content}`'
        elif val.startswith('['):
            # Enlace: [texto](url)
            m = re.match(r'\[(.*?)\]\((.*?)\)', val)
            if m:
                link_text, link_url = m.groups()
                link_text = escape_basic(link_text)
                link_url = link_url.replace('\\', '\\\\').replace(')', '\\)')
                val = f'[{link_text}]({link_url})'
        
        placeholders.append(val)
        return f"@@PH{len(placeholders)-1}@@"

    # Protege bloques de código, código en línea y enlaces
    text = re.sub(r'(```[\s\S]*?```|`.*?`|\[.*?\]\(.*?\))', p, text)
    
    # Protege marcadores de negrita y cursiva (si están en pares)
    def p_bold_italic(match):
        val = match.group(0)
        marker = val[0]
        inner = val[1:-1]
        # Escapa el contenido interno
        inner = escape_basic(inner)
        placeholders.append(f"{marker}{inner}{marker}")
        return f"@@PH{len(placeholders)-1}@@"

    # Protege *texto* y _texto_
    text = re.sub(r'(\*.*?\*|_.*?_)', p_bold_italic, text)
    
    # Escapa el resto del texto
    text = escape_basic(text)
    
    # Restaura los placeholders
    for i, val in enumerate(placeholders):
        text = text.replace(f"@@PH{i}@@", val)
        
    return text

