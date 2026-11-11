"""Generate django.po files for all 9 supported languages and compile them to .mo."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = BASE_DIR / "locale"

TRANSLATIONS = {
    "home": {
        "en": "home",
        "pt": "início",
        "it": "home",
        "es": "inicio",
        "fr": "accueil",
        "el": "αρχική",
        "ru": "главная",
        "hi": "होम",
        "kn": "ಮುಖಪುಟ",
    },
    "photos": {
        "en": "photos",
        "pt": "fotos",
        "it": "foto",
        "es": "fotos",
        "fr": "photos",
        "el": "φωτογραφίες",
        "ru": "фотографии",
        "hi": "तस्वीरें",
        "kn": "ಫೋಟೋಗಳು",
    },
    "blog": {
        "en": "blog",
        "pt": "blog",
        "it": "blog",
        "es": "blog",
        "fr": "blog",
        "el": "ιστολόγιο",
        "ru": "блог",
        "hi": "ब्लॉग",
        "kn": "ಬ್ಲಾಗ್",
    },
    "games": {
        "en": "games",
        "pt": "jogos",
        "it": "giochi",
        "es": "juegos",
        "fr": "jeux",
        "el": "παιχνίδια",
        "ru": "игры",
        "hi": "खेल",
        "kn": "ಆಟಗಳು",
    },
    "cv": {
        "en": "cv",
        "pt": "currículo",
        "it": "cv",
        "es": "currículum",
        "fr": "cv",
        "el": "βιογραφικό",
        "ru": "резюме",
        "hi": "सीवी",
        "kn": "ಸಿವಿ",
    },
}

LANGUAGES = ["en", "pt", "it", "es", "fr", "el", "ru", "hi", "kn"]

for lang in LANGUAGES:
    po_dir = LOCALE_DIR / lang / "LC_MESSAGES"
    po_dir.mkdir(parents=True, exist_ok=True)
    po_file = po_dir / "django.po"
    
    lines = [
        r'msgid ""',
        r'msgstr ""',
        r'"Content-Type: text/plain; charset=UTF-8\n"',
        r'"Content-Transfer-Encoding: 8bit\n"',
        f'"Language: {lang}\\n"',
        r'"MIME-Version: 1.0\n"',
        "",
    ]
    
    for msgid, trans_dict in TRANSLATIONS.items():
        msgstr = trans_dict.get(lang, msgid)
        lines.append(f'msgid "{msgid}"')
        lines.append(f'msgstr "{msgstr}"')
        lines.append("")
        
    po_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {po_file}")
