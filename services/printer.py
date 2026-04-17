import json
import re
import textwrap
from IPython.display import display, Markdown


def clean_text_output(text):
    if text is None:
        return "[no content]"

    cleaned = str(text).strip()

    # Unwrap JSON string values like "..." if present
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        try:
            cleaned = json.loads(cleaned)
        except Exception:
            pass

    # Replace escaped newline/tab artifacts with real whitespace
    cleaned = cleaned.replace('\\n', '\n').replace('\\t', '    ')
    cleaned = re.sub(r'\\+"', '"', cleaned)

    # Try to pretty-print valid JSON payloads
    try:
        parsed = json.loads(cleaned)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except Exception:
        return cleaned


def print_section(title, text, width=88):
    print("=" * width)
    print(title)
    print("-" * width)

    cleaned = clean_text_output(text)
    for line in cleaned.splitlines():
        print(textwrap.fill(line, width=width))



