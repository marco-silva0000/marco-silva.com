"""Generate .po and .mo catalogs for all 64 languages requested by the user.

Reads existing translations from locale/ and scripts/generate_locales.py,
preserves all existing work, generates catalogs for all 64 languages,
and compiles pure-Python .mo binary catalogs.
"""

import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

LOCALE_DIR = BASE_DIR / "locale"

from scripts.translations_tool import (  # noqa: E402
    LANGUAGES,
    extract_translatable_strings,
    get_locale_dir,
    parse_po_file,
    write_po_file,
)

# Primary multilingual translations for common navigation, footer, and core UI
SEED_TRANSLATIONS = {
    "home": {
        "de": "Startseite",
        "nl": "Home",
        "ja": "ホーム",
        "ko": "홈",
        "zh-cn": "首页",
        "zh-tw": "首頁",
        "pl": "Strona główna",
        "tr": "Ana Sayfa",
        "sv": "Hem",
        "da": "Hjem",
        "fi": "Koti",
        "no": "Hjem",
        "cs": "Domů",
        "uk": "Головна",
        "vi": "Trang chủ",
        "id": "Beranda",
        "ro": "Acasă",
        "hu": "Kezdőlap",
        "iw": "בית",
        "yi": "היים",
        "ca": "Inici",
        "gl": "Inicio",
        "eu": "Hasiera",
        "af": "Tuisblad",
        "bg": "Начало",
        "hr": "Početna",
        "sr": "Почетна",
        "sk": "Domov",
        "sl": "Domov",
        "et": "Avaleht",
        "lv": "Sākums",
        "lt": "Pradžia",
        "is": "Heim",
        "ga": "Baile",
        "ms": "Laman Utama",
        "th": "หน้าแรก",
        "tl": "Tahanan",
        "sw": "Mwanzo",
        "eo": "Ĉefpaĝo",
        "la": "Domus",
        "cy": "Hafan",
    },
    "photos": {
        "de": "Fotos",
        "nl": "Foto's",
        "ja": "写真",
        "ko": "사진",
        "zh-cn": "照片",
        "zh-tw": "照片",
        "pl": "Zdjęcia",
        "tr": "Fotoğraflar",
        "sv": "Foton",
        "da": "Billeder",
        "fi": "Kuvat",
        "no": "Bilder",
        "cs": "Fotky",
        "uk": "Фотографії",
        "vi": "Hình ảnh",
        "id": "Foto",
        "ro": "Fotografii",
        "hu": "Fotók",
        "iw": "תמונות",
        "yi": "פאָטאָס",
        "ca": "Fotos",
        "gl": "Fotos",
        "eu": "Argazkiak",
        "af": "Foto's",
        "bg": "Снимки",
        "hr": "Fotografije",
        "sr": "Фотографије",
        "sk": "Fotografie",
        "sl": "Fotografije",
        "et": "Fotod",
        "lv": "Fotoattēli",
        "lt": "Nuotraukos",
        "is": "Myndir",
        "ga": "Grianghraif",
        "ms": "Gambar",
        "th": "รูปภาพ",
        "tl": "Mga Larawan",
        "sw": "Picha",
        "eo": "Fotoj",
        "la": "Photographemata",
        "cy": "Lluniau",
    },
    "blog": {
        "de": "Blog",
        "nl": "Blog",
        "ja": "ブログ",
        "ko": "블로그",
        "zh-cn": "博客",
        "zh-tw": "部落格",
        "pl": "Blog",
        "tr": "Blog",
        "sv": "Blogg",
        "da": "Blog",
        "fi": "Blogi",
        "no": "Blogg",
        "cs": "Blog",
        "uk": "Блог",
        "vi": "Blog",
        "id": "Blog",
        "ro": "Blog",
        "hu": "Blog",
        "iw": "בלוג",
        "yi": "בלאָג",
        "ca": "Blog",
        "gl": "Blog",
        "eu": "Bloga",
        "af": "Blog",
        "bg": "Блог",
        "hr": "Blog",
        "sr": "Блог",
        "sk": "Blog",
        "sl": "Blog",
        "et": "Blogi",
        "lv": "Emuārs",
        "lt": "Tinklaraštis",
        "is": "Blogg",
        "ga": "Blag",
        "ms": "Blog",
        "th": "บล็อก",
        "tl": "Blog",
        "sw": "Blogu",
        "eo": "Blogo",
        "la": "Ephemeris",
        "cy": "Blog",
    },
    "games": {
        "de": "Spiele",
        "nl": "Spellen",
        "ja": "ゲーム",
        "ko": "게임",
        "zh-cn": "游戏",
        "zh-tw": "遊戲",
        "pl": "Gry",
        "tr": "Oyunlar",
        "sv": "Spel",
        "da": "Spil",
        "fi": "Pelit",
        "no": "Spill",
        "cs": "Hry",
        "uk": "Ігри",
        "vi": "Trò chơi",
        "id": "Permainan",
        "ro": "Jocuri",
        "hu": "Játékok",
        "iw": "משחקים",
        "yi": "שפּילן",
        "ca": "Jocs",
        "gl": "Xogos",
        "eu": "Jokoak",
        "af": "Speletjies",
        "bg": "Игри",
        "hr": "Igre",
        "sr": "Игре",
        "sk": "Hry",
        "sl": "Igre",
        "et": "Mängud",
        "lv": "Spēles",
        "lt": "Žaidimai",
        "is": "Leikir",
        "ga": "Cluichí",
        "ms": "Permainan",
        "th": "เกม",
        "tl": "Mga Laro",
        "sw": "Michezo",
        "eo": "Ludoj",
        "la": "Ludi",
        "cy": "Gemau",
    },
    "cv": {
        "de": "Lebenslauf",
        "nl": "CV",
        "ja": "履歴書",
        "ko": "이력서",
        "zh-cn": "简历",
        "zh-tw": "履歷",
        "pl": "Życiorys",
        "tr": "Özgeçmiş",
        "sv": "CV",
        "da": "CV",
        "fi": "Ansioluettelo",
        "no": "CV",
        "cs": "Životopis",
        "uk": "Резюме",
        "vi": "Hồ sơ",
        "id": "CV",
        "ro": "CV",
        "hu": "Önéletrajz",
        "iw": "קורות חיים",
        "yi": "רעזומע",
        "ca": "Currículum",
        "gl": "Currículo",
        "eu": "Curriculuma",
        "af": "CV",
        "bg": "Автобиография",
        "hr": "Životopis",
        "sr": "Биографија",
        "sk": "Životopis",
        "sl": "Življenjepis",
        "et": "CV",
        "lv": "CV",
        "lt": "CV",
        "is": "Ferilskrá",
        "ga": "CV",
        "ms": "CV",
        "th": "ประวัติย่อ",
        "tl": "CV",
        "sw": "Wasifu",
        "eo": "Vivresumo",
        "la": "Curriculum Vitae",
        "cy": "CV",
    },
    "latest posts": {
        "de": "Neueste Beiträge",
        "nl": "Nieuwste berichten",
        "ja": "最新の投稿",
        "ko": "최신 글",
        "zh-cn": "最新文章",
        "zh-tw": "最新文章",
        "pl": "Najnowsze wpisy",
        "tr": "Son Yazılar",
        "sv": "Senaste inläggen",
        "da": "Seneste indlæg",
        "fi": "Uusimmat julkaisut",
        "no": "Siste innlegg",
        "cs": "Nejnovější příspěvky",
        "uk": "Останні дописи",
        "vi": "Bài viết mới nhất",
        "id": "Postingan terbaru",
        "ro": "Ultimele articole",
        "hu": "Legújabb bejegyzések",
        "iw": "פוסטים אחרונים",
        "yi": "לעצטע אַרטיקלען",
        "ca": "Últimes publicacions",
        "gl": "Últimas publicacións",
        "eu": "Azken mezuak",
        "af": "Nuutste plasings",
    },
    "I code, take pics and many other things": {
        "de": "Ich programmiere, fotografiere und vieles mehr",
        "nl": "Ik programmeer, maak foto's en nog veel meer",
        "ja": "コードを書き、写真を撮り、さまざまなことをしています",
        "ko": "코딩하고 사진을 찍으며 다양한 일을 합니다",
        "zh-cn": "我写代码、拍照，以及很多其他事情",
        "zh-tw": "我寫代碼、拍照，以及很多其他事情",
        "pl": "Programuję, robię zdjęcia i wiele innych rzeczy",
        "tr": "Kod yazarım, fotoğraf çekerim ve daha pek çok şey",
        "sv": "Jag kodar, fotograferar och gör mycket annat",
        "da": "Jeg koder, tager billeder og meget andet",
        "fi": "Koodaan, valokuvaan ja teen monia muita asioita",
        "no": "Jeg koder, tar bilder og mye annet",
        "uk": "Я програмую, фотографую та багато іншого",
        "iw": "אני כותב קוד, מצלם ועוד דברים רבים",
        "yi": "איך פּראָגראַמיר, נעמען בילדער און פילע אַנדערע זאַכן",
    },
    "Hobbies": {
        "de": "Hobbys",
        "nl": "Hobby's",
        "ja": "趣味",
        "ko": "취미",
        "zh-cn": "爱好",
        "zh-tw": "愛好",
        "pl": "Hobby",
        "tr": "Hobiler",
        "sv": "Hobbyer",
        "da": "Hobbyer",
        "fi": "Harrastukset",
        "no": "Hobbyer",
        "cs": "Koníčky",
        "uk": "Хобі",
        "vi": "Sở thích",
        "id": "Hobi",
        "ro": "Hobby-uri",
        "hu": "Hobbik",
        "iw": "תחביבים",
        "yi": "האָביעס",
        "ca": "Aficions",
        "gl": "Afeccións",
        "eu": "Zaletasunak",
        "af": "Stokperdjies",
    },
    "Create Room": {
        "de": "Raum erstellen",
        "nl": "Kamer aanmaken",
        "ja": "ルーム作成",
        "ko": "방 만들기",
        "zh-cn": "创建房间",
        "zh-tw": "建立房間",
        "pl": "Stwórz pokój",
        "tr": "Oda Oluştur",
        "sv": "Skapa rum",
        "da": "Opret rum",
        "fi": "Luo huone",
        "no": "Opprett rom",
        "cs": "Vytvořit místnost",
        "uk": "Створити кімнату",
        "vi": "Tạo phòng",
        "id": "Buat Ruangan",
        "ro": "Creează cameră",
        "hu": "Szoba létrehozása",
        "iw": "צור חדר",
        "yi": "שאַפֿן אַ צימער",
    },
    "Lupus in Tabula": {
        "de": "Lupus in Tabula — Werwolf",
        "nl": "Lupus in Tabula — Weerwolf",
        "ja": "人狼 (Lupus in Tabula)",
        "ko": "타불라의 늑대 (Lupus in Tabula)",
        "zh-cn": "米勒山谷狼人 (Lupus in Tabula)",
        "zh-tw": "米勒山谷狼人 (Lupus in Tabula)",
        "pl": "Wilkołaki (Lupus in Tabula)",
        "tr": "Kurt Adam (Lupus in Tabula)",
        "sv": "Varulv (Lupus in Tabula)",
        "no": "Varulv (Lupus in Tabula)",
        "uk": "Перевертні (Lupus in Tabula)",
        "iw": "איש זאב (Lupus in Tabula)",
    },
}


def main():
    print(f"Generating and compiling catalogs for all {len(LANGUAGES)} languages...")

    # Load master extracted strings
    all_strings = sorted(extract_translatable_strings().keys())
    print(f"Extracted {len(all_strings)} translatable strings from codebase.")

    # Also import generate_locales TRANSLATIONS if available
    try:
        from scripts.generate_locales import TRANSLATIONS as GL_TRANSLATIONS
    except Exception:
        GL_TRANSLATIONS = {}

    for code in LANGUAGES:
        target_dir = get_locale_dir(code) / "LC_MESSAGES"
        target_dir.mkdir(parents=True, exist_ok=True)
        po_path = target_dir / "django.po"

        # Load existing entries if any (preserves all existing human work!)
        existing = parse_po_file(po_path)

        # Build catalog
        catalog = {}
        for s in all_strings:
            if code == "en":
                catalog[s] = s
            elif s in existing and existing[s].strip():
                catalog[s] = existing[s].strip()
            elif s in SEED_TRANSLATIONS and code in SEED_TRANSLATIONS[s]:
                catalog[s] = SEED_TRANSLATIONS[s][code]
            elif s in GL_TRANSLATIONS and code in GL_TRANSLATIONS[s]:
                catalog[s] = GL_TRANSLATIONS[s][code]
            else:
                # Default to English string so translation functions never return blank
                catalog[s] = s

        # Write PO & MO via standard translations_tool compiler
        write_po_file(code, catalog, po_path)

        # Create alias directories (e.g. zh_Hans for zh_CN, he for iw, nb for no, fil for tl)
        aliases = []
        if code == "zh-cn":
            aliases = ["zh_Hans", "zh-cn", "zh-CN", "zh_CN"]
        elif code == "zh-tw":
            aliases = ["zh_Hant", "zh-tw", "zh-TW", "zh_TW"]
        elif code == "iw":
            aliases = ["he"]
        elif code == "no":
            aliases = ["nb"]
        elif code == "tl":
            aliases = ["fil"]

        for alias in aliases:
            alias_dir = LOCALE_DIR / alias / "LC_MESSAGES"
            alias_dir.mkdir(parents=True, exist_ok=True)
            dst_po = alias_dir / "django.po"
            if dst_po.resolve() != po_path.resolve():
                shutil.copy2(po_path, dst_po)
            mo_src = target_dir / "django.mo"
            dst_mo = alias_dir / "django.mo"
            if mo_src.exists() and dst_mo.resolve() != mo_src.resolve():
                shutil.copy2(mo_src, dst_mo)

    print(f"Successfully generated and compiled all {len(LANGUAGES)} locales in {LOCALE_DIR}/!")


if __name__ == "__main__":
    main()
