"""Generate django.po files for all 9 supported languages and compile them to .mo.

Supported languages:
- en: English
- pt: Português
- it: Italiano
- es: Español
- fr: Français
- el: Ελληνικά
- ru: Русский
- hi: हिन्दी
- kn: ಕನ್ನಡ
"""

import os
import shutil
import struct
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = BASE_DIR / "locale"

LANGUAGES = ["en", "pt", "it", "es", "fr", "el", "ru", "hi", "kn"]

TRANSLATIONS = {
    # Base site navigation
    "home": {
        "en": "home", "pt": "início", "it": "home", "es": "inicio", "fr": "accueil", "el": "αρχική", "ru": "главная", "hi": "होम", "kn": "ಮುಖಪುಟ"
    },
    "photos": {
        "en": "photos", "pt": "fotos", "it": "foto", "es": "fotos", "fr": "photos", "el": "φωτογραφίες", "ru": "фотографии", "hi": "तस्वीरें", "kn": "ಫೋಟೋಗಳು"
    },
    "blog": {
        "en": "blog", "pt": "blog", "it": "blog", "es": "blog", "fr": "blog", "el": "ιστολόγιο", "ru": "блог", "hi": "ब्लॉग", "kn": "ಬ್ಲಾಗ್"
    },
    "games": {
        "en": "games", "pt": "jogos", "it": "giochi", "es": "juegos", "fr": "jeux", "el": "παιχνίδια", "ru": "игры", "hi": "खेल", "kn": "ಆಟಗಳು"
    },
    "cv": {
        "en": "cv", "pt": "currículo", "it": "cv", "es": "currículum", "fr": "cv", "el": "βιογραφικό", "ru": "резюме", "hi": "सीवी", "kn": "ಸಿವಿ"
    },

    # Game Rooms Hub (/games/)
    "Game Rooms": {
        "en": "Game Rooms",
        "pt": "Salas de Jogos",
        "it": "Sale Giochi",
        "es": "Salas de Juegos",
        "fr": "Salons de Jeux",
        "el": "Αίθουσες Παιχνιδιών",
        "ru": "Игровые комнаты",
        "hi": "गेम रूम",
        "kn": "ಆಟದ ಕೊಠಡಿಗಳು",
    },
    "Real-time multiplayer browser party games. No accounts required — just jump in and play with friends.": {
        "en": "Real-time multiplayer browser party games. No accounts required — just jump in and play with friends.",
        "pt": "Jogos de festa multijogador em tempo real no navegador. Sem contas necessárias — basta entrar e jogar com amigos.",
        "it": "Party game multigiocatore in tempo reale nel browser. Nessun account richiesto: unisciti e gioca con gli amici.",
        "es": "Juegos de fiesta multijugador en tiempo real en el navegador. No se requieren cuentas: entra y juega con amigos.",
        "fr": "Jeux de société multijoueurs en temps réel sur navigateur. Aucun compte requis : rejoignez et jouez avec vos amis.",
        "el": "Παιχνίδια παρέας για πολλούς παίκτες σε πραγματικό χρόνο στο πρόγραμμα περιήγησης. Δεν απαιτούνται λογαριασμοί — απλώς μπείτε και παίξτε με φίλους.",
        "ru": "Многопользовательские браузерные игры для вечеринок в реальном времени. Без регистрации — просто заходите и играйте с друзьями.",
        "hi": "रीयल-टाइम मल्टीप्लेयर ब्राउज़र पार्टी गेम। किसी खाते की आवश्यकता नहीं — बस शामिल हों और दोस्तों के साथ खेलें।",
        "kn": "ನೈಜ-ಸಮಯದ ಮಲ್ಟಿಪ್ಲೇಯರ್ ಬ್ರೌಸರ್ ಪಾರ್ಟಿ ಆಟಗಳು. ಯಾವುದೇ ಖಾತೆಯ ಅಗತ್ಯವಿಲ್ಲ — ಕೇವಲ ಸೇರಿ ಮತ್ತು ಸ್ನೇಹಿತರೊಂದಿಗೆ ಆಟವಾಡಿ.",
    },
    "🐺 Lupus Hub & Rooms": {
        "en": "🐺 Lupus Hub & Rooms",
        "pt": "🐺 Central e Salas de Lupus",
        "it": "🐺 Hub & Stanze Lupus",
        "es": "🐺 Centro y Salas de Lupus",
        "fr": "🐺 Hub & Salons Lupus",
        "el": "🐺 Κέντρο & Αίθουσες Lupus",
        "ru": "🐺 Центр и комнаты Lupus",
        "hi": "🐺 लुपस हब और कमरे",
        "kn": "🐺 ಲೂಪಸ್ ಹಬ್ ಮತ್ತು ಕೊಠಡಿಗಳು",
    },
    "🐺 create lupus": {
        "en": "🐺 create lupus",
        "pt": "🐺 criar lupus",
        "it": "🐺 crea lupus",
        "es": "🐺 crear lupus",
        "fr": "🐺 créer lupus",
        "el": "🐺 δημιουργία lupus",
        "ru": "🐺 создать lupus",
        "hi": "🐺 लुपस बनाएं",
        "kn": "🐺 ಲೂಪಸ್ ರಚಿಸಿ",
    },
    "+ create room": {
        "en": "+ create room",
        "pt": "+ criar sala",
        "it": "+ crea stanza",
        "es": "+ crear sala",
        "fr": "+ créer un salon",
        "el": "+ δημιουργία αίθουσας",
        "ru": "+ создать комнату",
        "hi": "+ कमरा बनाएं",
        "kn": "+ ಕೊಠಡಿ ರಚಿಸಿ",
    },
    "✏️ pictionary": {
        "en": "✏️ pictionary",
        "pt": "✏️ pictionary",
        "it": "✏️ pictionary",
        "es": "✏️ pictionary",
        "fr": "✏️ pictionary",
        "el": "✏️ pictionary",
        "ru": "✏️ pictionary",
        "hi": "✏️ पिकश्नरी",
        "kn": "✏️ ಪಿಕ್ಶನರಿ",
    },
    "Enter Room Code (e.g. 9B3A1C2D)": {
        "en": "Enter Room Code (e.g. 9B3A1C2D)",
        "pt": "Introduzir Código de Sala (ex. 9B3A1C2D)",
        "it": "Inserisci Codice Stanza (es. 9B3A1C2D)",
        "es": "Introduce el Código de Sala (ej. 9B3A1C2D)",
        "fr": "Entrez le Code du Salon (ex. 9B3A1C2D)",
        "el": "Εισαγάγετε Κωδικό Αίθουσας (π.χ. 9B3A1C2D)",
        "ru": "Введите код комнаты (напр. 9B3A1C2D)",
        "hi": "कमरा कोड दर्ज करें (उदा. 9B3A1C2D)",
        "kn": "ಕೊಠಡಿ ಕೋಡ್ ನಮೂದಿಸಿ (ಉದಾ. 9B3A1C2D)",
    },
    "Join": {
        "en": "Join",
        "pt": "Entrar",
        "it": "Entra",
        "es": "Entrar",
        "fr": "Rejoindre",
        "el": "Σύνδεση",
        "ru": "Войти",
        "hi": "शामिल हों",
        "kn": "ಸೇರಿ",
    },
    "Lupus in Tabula / Werewolf": {
        "en": "Lupus in Tabula / Werewolf",
        "pt": "Lupus in Tabula / Lobisomem",
        "it": "Lupus in Tabula / Licantropo",
        "es": "Lupus in Tabula / Hombre Lobo",
        "fr": "Lupus in Tabula / Loup-Garou",
        "el": "Lupus in Tabula / Λυκάνθρωπος",
        "ru": "Lupus in Tabula / Оборотень",
        "hi": "लुपस इन तबुला / वेयरवोल्फ",
        "kn": "ಲೂಪಸ್ ಇನ್ ತಬುಲಾ / ತೋಳಮಾನವ",
    },
    "Table-first party game with secret roles, live voting, Town Gazette, and GM director cockpit.": {
        "en": "Table-first party game with secret roles, live voting, Town Gazette, and GM director cockpit.",
        "pt": "Jogo de festa à mesa com papéis secretos, votações ao vivo, Gazeta da Aldeia e cabine de comando do Mestre.",
        "it": "Party game da tavolo con ruoli segreti, votazioni dal vivo, Gazzetta della Città e cabina di regia per il GM.",
        "es": "Juego de fiesta de mesa con roles secretos, votaciones en directo, Gaceta del Pueblo y cabina de director para el GM.",
        "fr": "Jeu de société de table avec rôles secrets, votes en direct, Gazette du Village et cockpit de maître de jeu.",
        "el": "Επιτραπέζιο παιχνίδι παρέας με μυστικούς ρόλους, ζωντανή ψηφοφορία, Εφημερίδα του Χωριού και κονσόλα αφηγητή.",
        "ru": "Настольная игра для компании с тайными ролями, живым голосованием, Городской газетой и пультом ведущего.",
        "hi": "गुप्त भूमिकाओं, लाइव वोटिंग, टाउन गजट और जीएम डायरेक्टर कॉकपिट के साथ टेबल-फर्स्ट पार्टी गेम।",
        "kn": "ರಹಸ್ಯ ಪಾತ್ರಗಳು, ನೇರ ಮತದಾನ, ಟೌನ್ ಗೆಜೆಟ್ ಮತ್ತು ಜಿಎಂ ನಿರ್ದೇಶಕರ ಕಾಕ್‌ಪಿಟ್ ಹೊಂದಿರುವ ಟೇಬಲ್-ಆಧಾರಿತ ಪಾರ್ಟಿ ಆಟ.",
    },
    "Browse Active Lupus Rooms": {
        "en": "Browse Active Lupus Rooms",
        "pt": "Ver Salas Ativas de Lupus",
        "it": "Sfoglia Stanze Lupus Attive",
        "es": "Explorar Salas Activas de Lupus",
        "fr": "Parcourir les Salons Lupus Actifs",
        "el": "Περιήγηση σε Ενεργές Αίθουσες Lupus",
        "ru": "Смотреть активные комнаты Lupus",
        "hi": "सक्रिय लुपस कमरे देखें",
        "kn": "ಸಕ್ರಿಯ ಲೂಪಸ್ ಕೊಠಡಿಗಳನ್ನು ಬ್ರೌಸ್ ಮಾಡಿ",
    },
    "+ Host New Room": {
        "en": "+ Host New Room",
        "pt": "+ Criar Nova Sala",
        "it": "+ Crea Nuova Stanza",
        "es": "+ Crear Nueva Sala",
        "fr": "+ Créer Nouveau Salon",
        "el": "+ Δημιουργία Νέας Αίθουσας",
        "ru": "+ Создать новую комнату",
        "hi": "+ नया कमरा बनाएं",
        "kn": "+ ಹೊಸ ಕೊಠಡಿ ರಚಿಸಿ",
    },
    "All Active Rooms": {
        "en": "All Active Rooms",
        "pt": "Todas as Salas Ativas",
        "it": "Tutte le Stanze Attive",
        "es": "Todas las Salas Activas",
        "fr": "Tous les Salons Actifs",
        "el": "Όλες οι Ενεργές Αίθουσες",
        "ru": "Все активные комнаты",
        "hi": "सभी सक्रिय कमरे",
        "kn": "ಎಲ್ಲಾ ಸಕ್ರಿಯ ಕೊಠಡಿಗಳು",
    },
    "Password Protected": {
        "en": "Password Protected",
        "pt": "Protegido por Palavra-passe",
        "it": "Protetto da Password",
        "es": "Protegido por Contraseña",
        "fr": "Protégé par Mot de Passe",
        "el": "Προστατεύεται με Κωδικό",
        "ru": "Защищено паролем",
        "hi": "पासवर्ड से सुरक्षित",
        "kn": "ಪಾಸ್‌ವರ್ಡ್‌ನಿಂದ ಸಂರಕ್ಷಿಸಲಾಗಿದೆ",
    },
    "players": {
        "en": "players",
        "pt": "jogadores",
        "it": "giocatori",
        "es": "jugadores",
        "fr": "joueurs",
        "el": "παίκτες",
        "ru": "игроков",
        "hi": "खिलाड़ी",
        "kn": "ಆಟಗಾರರು",
    },
    "ago": {
        "en": "ago",
        "pt": "atrás",
        "it": "fa",
        "es": "hace",
        "fr": "il y a",
        "el": "πριν",
        "ru": "назад",
        "hi": "पहले",
        "kn": "ಹಿಂದೆ",
    },
    "no active rooms. create one!": {
        "en": "no active rooms. create one!",
        "pt": "sem salas ativas. crie uma!",
        "it": "nessuna stanza attiva. creane una!",
        "es": "no hay salas activas. ¡crea una!",
        "fr": "aucun salon actif. créez-en un !",
        "el": "δεν υπάρχουν ενεργές αίθουσες. δημιουργήστε μία!",
        "ru": "нет активных комнат. создайте первую!",
        "hi": "कोई सक्रिय कमरा नहीं है। एक बनाएं!",
        "kn": "ಯಾವುದೇ ಸಕ್ರಿಯ ಕೊಠಡಿಗಳಿಲ್ಲ. ಒಂದನ್ನು ರಚಿಸಿ!",
    },
    "🐺 Lupus": {
        "en": "🐺 Lupus", "pt": "🐺 Lupus", "it": "🐺 Lupus", "es": "🐺 Lupus", "fr": "🐺 Lupus", "el": "🐺 Lupus", "ru": "🐺 Lupus", "hi": "🐺 लुपस", "kn": "🐺 ಲೂಪಸ್"
    },
    "🎨 Emojinary": {
        "en": "🎨 Emojinary", "pt": "🎨 Emojinary", "it": "🎨 Emojinary", "es": "🎨 Emojinary", "fr": "🎨 Emojinary", "el": "🎨 Emojinary", "ru": "🎨 Emojinary", "hi": "🎨 इमोजीनरी", "kn": "🎨 ಇಮೋಜಿ‌ನರಿ"
    },

    # Lupus Hub (/games/lupus/)
    "Lupus in Tabula - Active Rooms & Game Hub": {
        "en": "Lupus in Tabula - Active Rooms & Game Hub",
        "pt": "Lupus in Tabula - Salas Ativas & Central de Jogo",
        "it": "Lupus in Tabula - Stanze Attive & Hub di Gioco",
        "es": "Lupus in Tabula - Salas Activas y Centro de Juego",
        "fr": "Lupus in Tabula - Salons Actifs & Centre de Jeu",
        "el": "Lupus in Tabula - Ενεργές Αίθουσες & Κέντρο Παιχνιδιού",
        "ru": "Lupus in Tabula - Активные комнаты и игровой центр",
        "hi": "लुपस इन तबुला - सक्रिय कमरे और गेम हब",
        "kn": "ಲೂಪಸ್ ಇನ್ ತಬುಲಾ - ಸಕ್ರಿಯ ಕೊಠಡಿಗಳು ಮತ್ತು ಆಟದ ಹಬ್",
    },
    "+ Create Room": {
        "en": "+ Create Room",
        "pt": "+ Criar Sala",
        "it": "+ Crea Stanza",
        "es": "+ Crear Sala",
        "fr": "+ Créer Salon",
        "el": "+ Δημιουργία Αίθουσας",
        "ru": "+ Создать комнату",
        "hi": "+ कमरा बनाएं",
        "kn": "+ ಕೊಠಡಿ ರಚಿಸಿ",
    },
    "All Games": {
        "en": "All Games",
        "pt": "Todos os Jogos",
        "it": "Tutti i Giochi",
        "es": "Todos los Juegos",
        "fr": "Tous les Jeux",
        "el": "Όλα τα Παιχνίδια",
        "ru": "Все игры",
        "hi": "सभी खेल",
        "kn": "ಎಲ್ಲಾ ಆಟಗಳು",
    },
    "Table-first Werewolf & Mafia party game. Zero account logins required. Each player uses their phone for secret roles and voting while you run the room as Game Master.": {
        "en": "Table-first Werewolf & Mafia party game. Zero account logins required. Each player uses their phone for secret roles and voting while you run the room as Game Master.",
        "pt": "Jogo de festa estilo Lobisomem e Máfia para mesa. Sem contas ou registos. Cada jogador usa o seu telemóvel para papéis secretos e votações enquanto você coordena o jogo como Mestre.",
        "it": "Party game da tavolo stile Licantropo & Mafia. Nessun account richiesto. Ogni giocatore usa il telefono per i ruoli segreti e i voti, mentre tu gestisci la stanza come Game Master.",
        "es": "Juego de fiesta estilo Hombre Lobo y Mafia para mesa. Cero cuentas requeridas. Cada jugador usa su teléfono para roles secretos y votaciones mientras diriges la sala como Game Master.",
        "fr": "Jeu de société style Loup-Garou & Mafia. Aucun compte requis. Chaque joueur utilise son téléphone pour les rôles secrets et les votes pendant que vous dirigez la partie en tant que Maître du Jeu.",
        "el": "Επιτραπέζιο παιχνίδι παρέας τύπου Λυκάνθρωπος & Μαφία. Δεν απαιτούνται λογαριασμοί. Κάθε παίκτης χρησιμοποιεί το κινητό του για μυστικούς ρόλους και ψηφοφορία ενώ εσείς διευθύνετε ως Αφηγητής.",
        "ru": "Настольная игра для компании в стиле Мафия и Оборотни. Без аккаунтов. Каждый игрок использует телефон для тайных ролей и голосований, пока вы управляете партией в роли Ведущего.",
        "hi": "टेबल-फर्स्ट वेयरवोल्फ और माफिया पार्टी गेम। शून्य खाता लॉगिन आवश्यक। प्रत्येक खिलाड़ी गुप्त भूमिकाओं और मतदान के लिए अपने फोन का उपयोग करता है जबकि आप गेम मास्टर के रूप में रूम चलाते हैं।",
        "kn": "ಟೇಬಲ್-ಆಧಾರಿತ ತೋಳಮಾನವ ಮತ್ತು ಮಾಫಿಯಾ ಪಾರ್ಟಿ ಆಟ. ಯಾವುದೇ ಲಾಗಿನ್ ಅಗತ್ಯವಿಲ್ಲ. ಪ್ರತಿಯೊಬ್ಬ ಆಟಗಾರನು ರಹಸ್ಯ ಪಾತ್ರಗಳು ಮತ್ತು ಮತದಾನಕ್ಕಾಗಿ ತಮ್ಮ ಫೋನ್ ಬಳಸುತ್ತಾರೆ ಮತ್ತು ನೀವು ಗೇಮ್ ಮಾಸ್ಟರ್ ಆಗಿ ನಡೆಸುತ್ತೀರಿ.",
    },
    "Join with Room Code": {
        "en": "Join with Room Code",
        "pt": "Entrar com Código de Sala",
        "it": "Entra con Codice Stanza",
        "es": "Entrar con Código de Sala",
        "fr": "Rejoindre avec le Code du Salon",
        "el": "Σύνδεση με Κωδικό Αίθουσας",
        "ru": "Войти по коду комнаты",
        "hi": "कमरा कोड के साथ शामिल हों",
        "kn": "ಕೊಠಡಿ ಕೋಡ್‌ನೊಂದಿಗೆ ಸೇರಿ",
    },
    "Have an 8-character code from your Game Master? Enter it here to jump straight in:": {
        "en": "Have an 8-character code from your Game Master? Enter it here to jump straight in:",
        "pt": "Tem um código de 8 caracteres do seu Mestre? Introduza-o aqui para entrar imediatamente:",
        "it": "Hai un codice di 8 caratteri dal tuo Game Master? Inseriscilo qui per entrare direttamente:",
        "es": "¿Tienes un código de 8 caracteres de tu Game Master? Introdúcelo aquí para entrar directamente:",
        "fr": "Vous avez un code de 8 caractères donné par votre Maître du Jeu ? Entrez-le ici pour rejoindre directement :",
        "el": "Έχετε 8-ψήφιο κωδικό από τον Αφηγητή σας; Εισαγάγετέ τον εδώ για να μπείτε απευθείας:",
        "ru": "Есть 8-значный код от Ведущего? Введите его здесь, чтобы сразу присоединиться:",
        "hi": "क्या आपके गेम मास्टर से 8-अक्षरों का कोड मिला है? सीधे शामिल होने के लिए इसे यहां दर्ज करें:",
        "kn": "ನಿಮ್ಮ ಗೇಮ್ ಮಾಸ್ಟರ್‌ನಿಂದ 8-ಅಕ್ಷರಗಳ ಕೋಡ್ ಹೊಂದಿದ್ದೀರಾ? ನೇರವಾಗಿ ಪ್ರವೇಶಿಸಲು ಇಲ್ಲಿ ನಮೂದಿಸಿ:",
    },
    "Join Game": {
        "en": "Join Game",
        "pt": "Entrar no Jogo",
        "it": "Entra nel Gioco",
        "es": "Entrar a la Partida",
        "fr": "Rejoindre la Partie",
        "el": "Σύνδεση στο Παιχνίδι",
        "ru": "Войти в игру",
        "hi": "गेम में शामिल हों",
        "kn": "ಆಟಕ್ಕೆ ಸೇರಿ",
    },
    "Active Lupus Rooms": {
        "en": "Active Lupus Rooms",
        "pt": "Salas Ativas de Lupus",
        "it": "Stanze Lupus Attive",
        "es": "Salas Activas de Lupus",
        "fr": "Salons Lupus Actifs",
        "el": "Ενεργές Αίθουσες Lupus",
        "ru": "Активные комнаты Lupus",
        "hi": "सक्रिय लुपस कमरे",
        "kn": "ಸಕ್ರಿಯ ಲೂಪಸ್ ಕೊಠಡಿಗಳು",
    },
    "+ New Game": {
        "en": "+ New Game",
        "pt": "+ Novo Jogo",
        "it": "+ Nuova Partita",
        "es": "+ Nueva Partida",
        "fr": "+ Nouvelle Partie",
        "el": "+ Νέο Παιχνίδι",
        "ru": "+ Новая игра",
        "hi": "+ नया खेल",
        "kn": "+ ಹೊಸ ಆಟ",
    },
    "CODE": {
        "en": "CODE", "pt": "CÓDIGO", "it": "CODICE", "es": "CÓDIGO", "fr": "CODE", "el": "ΚΩΔΙΚΟΣ", "ru": "КОД", "hi": "कोड", "kn": "ಕೋಡ್"
    },
    "GM": {
        "en": "GM", "pt": "Mestre", "it": "GM", "es": "GM", "fr": "MJ", "el": "Αφηγητής", "ru": "Ведущий", "hi": "जीएम", "kn": "ಜಿಎಂ"
    },
    "alive": {
        "en": "alive", "pt": "vivos", "it": "vivi", "es": "vivos", "fr": "vivants", "el": "ζωντανοί", "ru": "в живых", "hi": "जीवित", "kn": "ಜೀವಂತ"
    },
    "Password": {
        "en": "Password", "pt": "Palavra-passe", "it": "Password", "es": "Contraseña", "fr": "Mot de passe", "el": "Κωδικός", "ru": "Пароль", "hi": "पासवर्ड", "kn": "ಪಾಸ್‌ವರ್ಡ್"
    },
    "Public": {
        "en": "Public", "pt": "Público", "it": "Pubblico", "es": "Público", "fr": "Public", "el": "Δημόσια", "ru": "Открытая", "hi": "सार्वजनिक", "kn": "ಸಾರ್ವಜನಿಕ"
    },
    "Open GM Cockpit": {
        "en": "Open GM Cockpit",
        "pt": "Abrir Cabine do Mestre",
        "it": "Apri Cabina GM",
        "es": "Abrir Cabina del GM",
        "fr": "Ouvrir Cockpit MJ",
        "el": "Άνοιγμα Κονσόλας Αφηγητή",
        "ru": "Открыть пульт ведущего",
        "hi": "जीएम कॉकपिट खोलें",
        "kn": "ಜಿಎಂ ಕಾಕ್‌ಪಿಟ್ ತೆರೆಯಿರಿ",
    },
    "Return as %(name)s": {
        "en": "Return as %(name)s",
        "pt": "Voltar como %(name)s",
        "it": "Ritorna come %(name)s",
        "es": "Volver como %(name)s",
        "fr": "Revenir en tant que %(name)s",
        "el": "Επιστροφή ως %(name)s",
        "ru": "Вернуться как %(name)s",
        "hi": "%(name)s के रूप में वापस आएं",
        "kn": "%(name)s ಆಗಿ ಹಿಂತಿರುಗಿ",
    },
    "Enter Room": {
        "en": "Enter Room",
        "pt": "Entrar na Sala",
        "it": "Entra nella Stanza",
        "es": "Entrar a la Sala",
        "fr": "Entrer dans le Salon",
        "el": "Είσοδος στην Αίθουσα",
        "ru": "Войти в комнату",
        "hi": "कमरे में प्रवेश करें",
        "kn": "ಕೊಠಡಿಗೆ ಪ್ರವೇಶಿಸಿ",
    },
    "No Active Lupus Games Right Now": {
        "en": "No Active Lupus Games Right Now",
        "pt": "Nenhum Jogo Ativo de Lupus no Momento",
        "it": "Nessuna Partita Lupus Attiva in Questo Momento",
        "es": "No Hay Partidas Activas de Lupus en Este Momento",
        "fr": "Aucune Partie de Lupus Active pour le Moment",
        "el": "Δεν Υπάρχουν Ενεργά Παιχνίδια Lupus Αυτή τη Στιγμή",
        "ru": "Сейчас нет активных игр Lupus",
        "hi": "अभी कोई सक्रिय लुपस गेम नहीं है",
        "kn": "ಪ್ರಸ್ತುತ ಯಾವುದೇ ಸಕ್ರಿಯ ಲೂಪಸ್ ಆಟಗಳಿಲ್ಲ",
    },
    "Rooms are created on demand and stay active for 24 hours. Start a new game session and invite your group!": {
        "en": "Rooms are created on demand and stay active for 24 hours. Start a new game session and invite your group!",
        "pt": "As salas são criadas sob demanda e ficam ativas por 24 horas. Inicie uma nova sessão de jogo e convide o seu grupo!",
        "it": "Le stanze vengono create su richiesta e restano attive per 24 ore. Avvia una nuova sessione e invita il tuo gruppo!",
        "es": "Las salas se crean a petición y permanecen activas durante 24 horas. ¡Inicia una nueva partida e invita a tu grupo!",
        "fr": "Les salons sont créés à la demande et restent actifs 24 heures. Lancez une nouvelle session et invitez vos amis !",
        "el": "Οι αίθουσες δημιουργούνται κατ' απαίτηση και παραμένουν ενεργές για 24 ώρες. Ξεκινήστε μια νέα συνεδρία και προσκαλέστε την παρέα σας!",
        "ru": "Комнаты создаются по запросу и активны 24 часа. Создайте новую партию и пригласите компанию!",
        "hi": "कमरे आवश्यकतानुसार बनाए जाते हैं और 24 घंटे तक सक्रिय रहते हैं। एक नया गेम सत्र शुरू करें और अपने समूह को आमंत्रित करें!",
        "kn": "ಕೊಠಡಿಗಳನ್ನು ಅಗತ್ಯವಿದ್ದಾಗ ರಚಿಸಲಾಗುತ್ತದೆ ಮತ್ತು 24 ಗಂಟೆಗಳ ಕಾಲ ಸಕ್ರಿಯವಾಗಿರುತ್ತವೆ. ಹೊಸ ಆಟದ ಸೆಷನ್ ಪ್ರಾರಂಭಿಸಿ ಮತ್ತು ನಿಮ್ಮ ಗುಂಪನ್ನು ಆಹ್ವಾನಿಸಿ!",
    },
    "Create the First Lupus Room": {
        "en": "Create the First Lupus Room",
        "pt": "Criar a Primeira Sala de Lupus",
        "it": "Crea la Prima Stanza Lupus",
        "es": "Crear la Primera Sala de Lupus",
        "fr": "Créer le Premier Salon Lupus",
        "el": "Δημιουργήστε την Πρώτη Αίθουσα Lupus",
        "ru": "Создать первую комнату Lupus",
        "hi": "पहला लुपस कमरा बनाएं",
        "kn": "ಮೊದಲ ಲೂಪಸ್ ಕೊಠಡಿ ರಚಿಸಿ",
    },
    "Past & Finished Games": {
        "en": "Past & Finished Games",
        "pt": "Jogos Anteriores & Terminados",
        "it": "Partite Passate & Concluse",
        "es": "Partidas Pasadas y Terminadas",
        "fr": "Parties Passées & Terminées",
        "el": "Παλαιότερα & Ολοκληρωμένα Παιχνίδια",
        "ru": "Прошедшие и завершённые игры",
        "hi": "पिछले और समाप्त हुए खेल",
        "kn": "ಹಿಂದಿನ ಮತ್ತು ಪೂರ್ಣಗೊಂಡ ಆಟಗಳು",
    },
    "Replay": {
        "en": "Replay", "pt": "Repetição", "it": "Replay", "es": "Repetición", "fr": "Revoir", "el": "Επανάληψη", "ru": "Повтор", "hi": "रीप्ले", "kn": "ಮರುಪಂದ್ಯ"
    },
    "Cockpit": {
        "en": "Cockpit", "pt": "Cabine", "it": "Cabina", "es": "Cabina", "fr": "Cockpit", "el": "Κονσόλα", "ru": "Пульт", "hi": "कॉकपिट", "kn": "ಕಾಕ್‌ಪಿಟ್"
    },
    "Table-First Lupus Highlights": {
        "en": "Table-First Lupus Highlights",
        "pt": "Destaques do Lupus à Mesa",
        "it": "Punti di Forza del Lupus da Tavolo",
        "es": "Aspectos Destacados de Lupus en Mesa",
        "fr": "Points Forts de Lupus sur Table",
        "el": "Χαρακτηριστικά του Επιτραπέζιου Lupus",
        "ru": "Особенности настольного Lupus",
        "hi": "टेबल-फर्स्ट लुपस की मुख्य विशेषताएं",
        "kn": "ಟೇಬಲ್-ಆಧಾರಿತ ಲೂಪಸ್ ಮುಖ್ಯಾಂಶಗಳು",
    },
    "Hold-to-Peek Secret Roles:": {
        "en": "Hold-to-Peek Secret Roles:",
        "pt": "Segurar para Espiar Papéis Secretos:",
        "it": "Tieni Premuto per i Ruoli Segreti:",
        "es": "Mantén Presionado para Roles Secretos:",
        "fr": "Maintenez pour Révéler les Rôles Secrets :",
        "el": "Κρατήστε Πατημένο για Μυστικούς Ρόλους:",
        "ru": "Удерживайте для просмотра тайных ролей:",
        "hi": "गुप्त भूमिका देखने के लिए दबाकर रखें:",
        "kn": "ರಹಸ್ಯ ಪಾತ್ರಗಳನ್ನು ನೋಡಲು ಒತ್ತಿಹಿಡಿಯಿರಿ:",
    },
    "Privacy shield keeps cards concealed from prying eyes at the table.": {
        "en": "Privacy shield keeps cards concealed from prying eyes at the table.",
        "pt": "A proteção de privacidade mantém as cartas ocultas de olhares curiosos à mesa.",
        "it": "La schermata di riservatezza nasconde le carte dagli sguardi indiscreti al tavolo.",
        "es": "El escudo de privacidad oculta las cartas de miradas curiosas en la mesa.",
        "fr": "L'écran de confidentialité protège vos cartes des regards indiscrets autour de la table.",
        "el": "Η ασπίδα απορρήτου προστατεύει τις κάρτες από περίεργα βλέμματα στο τραπέζι.",
        "ru": "Защита конфиденциальности скрывает карты от любопытных глаз за столом.",
        "hi": "गोपनीयता शील्ड मेज पर ताक-झांक से पत्तों को छिपाकर रखती है।",
        "kn": "ಗೌಪ್ಯತೆ ರಕ್ಷಕವು ಮೇಜಿನ ಮೇಲಿರುವ ಇತರರ ಕಣ್ಣುಗಳಿಂದ ಕಾರ್ಡ್‌ಗಳನ್ನು ರಹಸ್ಯವಾಗಿರಿಸುತ್ತದೆ.",
    },
    "GM Director Cockpit:": {
        "en": "GM Director Cockpit:",
        "pt": "Cabine de Diretor do Mestre:",
        "it": "Cabina di Regia del Game Master:",
        "es": "Cabina de Dirección del GM:",
        "fr": "Cockpit de Réalisation du MJ :",
        "el": "Κονσόλα Σκηνοθέτη Αφηγητή:",
        "ru": "Пульт управления Ведущего:",
        "hi": "जीएम डायरेक्टर कॉकपिट:",
        "kn": "ಜಿಎಂ ನಿರ್ದೇಶಕರ ಕಾಕ್‌ಪಿಟ್:",
    },
    "Step-by-step night stages, bluffing calls, and voting manager.": {
        "en": "Step-by-step night stages, bluffing calls, and voting manager.",
        "pt": "Fases noturnas passo a passo, chamadas de blefe e gestor de votações.",
        "it": "Fasi notturne guidate passo dopo passo, chiamate di bluff e gestione voti.",
        "es": "Fases nocturnas paso a paso, llamadas de farol y gestor de votaciones.",
        "fr": "Phases de nuit étape par étape, appels de bluff et gestionnaire de votes.",
        "el": "Νυχτερινά στάδια βήμα προς βήμα, κλήσεις μπλόφας και διαχείριση ψηφοφορίας.",
        "ru": "Пошаговые ночные фазы, блеф-вызовы и управление голосованием.",
        "hi": "कदम-दर-कदम रात्रि चरण, ब्लफ़िंग कॉल और वोटिंग प्रबंधक।",
        "kn": "ಹಂತ-ಹಂತದ ರಾತ್ರಿ ಹಂತಗಳು, ಬ್ಲಫ್ ಕರೆಗಳು ಮತ್ತು ಮತದಾನ ವ್ಯವಸ್ಥಾಪಕ.",
    },
    "Town Gazette:": {
        "en": "Town Gazette:",
        "pt": "Gazeta da Aldeia:",
        "it": "Gazzetta della Città:",
        "es": "Gaceta del Pueblo:",
        "fr": "Gazette du Village :",
        "el": "Εφημερίδα του Χωριού:",
        "ru": "Городская газета:",
        "hi": "टाउन गजट:",
        "kn": "ಟೌನ್ ಗೆಜೆಟ್:",
    },
    "Living & fallen players submit morning rumors read aloud at dawn.": {
        "en": "Living & fallen players submit morning rumors read aloud at dawn.",
        "pt": "Jogadores vivos e eliminados enviam boatos matinais lidos em voz alta ao amanhecer.",
        "it": "I giocatori vivi ed eliminati inviano pettegolezzi letti ad alta voce all'alba.",
        "es": "Los jugadores vivos y caídos envían rumores matutinos que se leen en voz alta al amanecer.",
        "fr": "Joueurs vivants et défunts soumettent des rumeurs matinales lues à haute voix à l'aube.",
        "el": "Ζωντανοί και νεκροί παίκτες στέλνουν πρωινές φήμες που διαβάζονται δυνατά στην αυγή.",
        "ru": "Живые и выбывшие игроки присылают утренние слухи, зачитываемые на рассвете.",
        "hi": "जीवित और मृत खिलाड़ी सुबह की अफवाहें भेजते हैं जो भोर में जोर से पढ़ी जाती हैं।",
        "kn": "ಜೀವಂತ ಮತ್ತು ಮೃತ ಆಟಗಾರರು ಮುಂಜಾನೆ ಗಟ್ಟಿಯಾಗಿ ಓದಲಾಗುವ ವದಂತಿಗಳನ್ನು ಕಳುಹಿಸುತ್ತಾರೆ.",
    },
    "Midgame Arrivals:": {
        "en": "Midgame Arrivals:",
        "pt": "Chegadas a Meio do Jogo:",
        "it": "Arrivi a Partita in Corso:",
        "es": "Llegadas a Mitad de Partida:",
        "fr": "Arrivées en Cours de Partie :",
        "el": "Αφίξεις στη Μέση του Παιχνιδιού:",
        "ru": "Присоединение посреди игры:",
        "hi": "खेल के बीच में आगमन:",
        "kn": "ಆಟದ ಮಧ್ಯೆ ಬರುವವರು:",
    },
    "Latecomers join as Confirmed Travelers, Town Ghosts, or Successors.": {
        "en": "Latecomers join as Confirmed Travelers, Town Ghosts, or Successors.",
        "pt": "Os recém-chegados entram como Viajantes Confirmados, Fantasmas da Aldeia ou Sucessores.",
        "it": "I ritardatari entrano come Viaggiatori Confermati, Fantasmi o Successori.",
        "es": "Los recién llegados se unen como Viajeros Confirmados, Fantasmas o Sucesores.",
        "fr": "Les retardataires rejoignent comme Voyageurs Confirmés, Fantômes ou Successeurs.",
        "el": "Όσοι αργοπορούν μπαίνουν ως Επιβεβαιωμένοι Ταξιδιώτες, Φαντάσματα ή Διάδοχοι.",
        "ru": "Опоздавшие входят как Доверенные путешественники, Призраки или Преемники.",
        "hi": "देर से आने वाले कन्फर्म्ड ट्रेवलर, टाउन घोस्ट या उत्तराधिकारी के रूप में शामिल होते हैं।",
        "kn": "ತಡವಾಗಿ ಬಂದವರು ದೃಢೀಕೃತ ಪ್ರಯಾಣಿಕರು, ಪ್ರೇತಗಳು ಅಥವಾ ಉತ್ತರಾಧಿಕಾರಿಗಳಾಗಿ ಸೇರುತ್ತಾರೆ.",
    },

    # Lupus Create Room (/games/lupus/create/)
    "Create Lupus / Werewolf Room": {
        "en": "Create Lupus / Werewolf Room",
        "pt": "Criar Sala de Lupus / Lobisomem",
        "it": "Crea Stanza Lupus / Licantropo",
        "es": "Crear Sala de Lupus / Hombre Lobo",
        "fr": "Créer un Salon Lupus / Loup-Garou",
        "el": "Δημιουργία Αίθουσας Lupus / Λυκάνθρωπου",
        "ru": "Создать комнату Lupus / Оборотни",
        "hi": "लुपस / वेयरवोल्फ कमरा बनाएं",
        "kn": "ಲೂಪಸ್ / ತೋಳಮಾನವ ಕೊಠಡಿ ರಚಿಸಿ",
    },
    "Back to Active Lupus Rooms": {
        "en": "Back to Active Lupus Rooms",
        "pt": "Voltar às Salas Ativas de Lupus",
        "it": "Torna alle Stanze Lupus Attive",
        "es": "Volver a las Salas Activas de Lupus",
        "fr": "Retour aux Salons Lupus Actifs",
        "el": "Πίσω στις Ενεργές Αίθουσες Lupus",
        "ru": "Назад к активным комнатам Lupus",
        "hi": "सक्रिय लुपस कमरों पर वापस जाएं",
        "kn": "ಸಕ್ರಿಯ ಲೂಪಸ್ ಕೊಠಡಿಗಳಿಗೆ ಹಿಂತಿರುಗಿ",
    },
    "Table-first hybrid party game. Zero accounts or logins required. Players join via QR code, and you run the game as Game Master.": {
        "en": "Table-first hybrid party game. Zero accounts or logins required. Players join via QR code, and you run the game as Game Master.",
        "pt": "Jogo de festa híbrido para mesa. Sem contas ou logins. Os jogadores entram por código QR e você coordena como Mestre.",
        "it": "Party game ibrido da tavolo. Nessun account richiesto. I giocatori entrano tramite QR code e tu dirigi come Game Master.",
        "es": "Juego de fiesta híbrido para mesa. Sin cuentas ni registros. Los jugadores se unen mediante código QR y diriges como Game Master.",
        "fr": "Jeu de société hybride sur table. Aucun compte requis. Les joueurs rejoignent via QR code et vous dirigez en tant que Maître.",
        "el": "Υβριδικό επιτραπέζιο παιχνίδι παρέας. Δεν απαιτούνται λογαριασμοί. Οι παίκτες μπαίνουν μέσω QR code και διευθύνετε ως Αφηγητής.",
        "ru": "Гибридная настольная игра для компании. Без регистрации. Игроки входят по QR-коду, а вы ведёте игру.",
        "hi": "टेबल-फर्स्ट हाइब्रिड पार्टी गेम। कोई खाता या लॉगिन आवश्यक नहीं। खिलाड़ी क्यूआर कोड से जुड़ते हैं, और आप गेम मास्टर के रूप में चलाते हैं।",
        "kn": "ಟೇಬಲ್-ಆಧಾರಿತ ಹೈಬ್ರಿಡ್ ಪಾರ್ಟಿ ಆಟ. ಯಾವುದೇ ಖಾತೆ ಅಥವಾ ಲಾಗಿನ್ ಅಗತ್ಯವಿಲ್ಲ. ಆಟಗಾರರು QR ಕೋಡ್ ಮೂಲಕ ಸೇರುತ್ತಾರೆ ಮತ್ತು ನೀವು ಗೇಮ್ ಮಾಸ್ಟರ್ ಆಗಿ ನಡೆಸುತ್ತೀರಿ.",
    },
    "Room Setup": {
        "en": "Room Setup",
        "pt": "Configuração da Sala",
        "it": "Configurazione Stanza",
        "es": "Configuración de la Sala",
        "fr": "Configuration du Salon",
        "el": "Ρύθμιση Αίθουσας",
        "ru": "Настройка комнаты",
        "hi": "कमरा सेटअप",
        "kn": "ಕೊಠಡಿ ಸೆಟಪ್",
    },
    "Room Title": {
        "en": "Room Title",
        "pt": "Título da Sala",
        "it": "Titolo Stanza",
        "es": "Título de la Sala",
        "fr": "Titre du Salon",
        "el": "Τίτλος Αίθουσας",
        "ru": "Название комнаты",
        "hi": "कमरे का शीर्षक",
        "kn": "ಕೊಠಡಿಯ ಶೀರ್ಷಿಕೆ",
    },
    "Game Master Display Name": {
        "en": "Game Master Display Name",
        "pt": "Nome de Exibição do Mestre",
        "it": "Nome Visualizzato del Game Master",
        "es": "Nombre Visible del Game Master",
        "fr": "Nom d'Affichage du Maître du Jeu",
        "el": "Όνομα Εμφάνισης Αφηγητή",
        "ru": "Имя Ведущего",
        "hi": "गेम मास्टर का नाम",
        "kn": "ಗೇಮ್ ಮಾಸ್ಟರ್ ಪ್ರದರ್ಶನ ಹೆಸರು",
    },
    "Room Password (optional)": {
        "en": "Room Password (optional)",
        "pt": "Palavra-passe da Sala (opcional)",
        "it": "Password Stanza (opzionale)",
        "es": "Contraseña de la Sala (opcional)",
        "fr": "Mot de passe du Salon (optionnel)",
        "el": "Κωδικός Αίθουσας (προαιρετικό)",
        "ru": "Пароль комнаты (необязательно)",
        "hi": "कमरा पासवर्ड (वैकल्पिक)",
        "kn": "ಕೊಠಡಿ ಪಾಸ್‌ವರ್ಡ್ (ಐಚ್ಛಿಕ)",
    },
    "Leave empty for public join": {
        "en": "Leave empty for public join",
        "pt": "Deixe vazio para entrada livre",
        "it": "Lascia vuoto per accesso pubblico",
        "es": "Dejar vacío para acceso público",
        "fr": "Laisser vide pour accès public",
        "el": "Αφήστε κενό για δημόσια είσοδο",
        "ru": "Оставьте пустым для свободного входа",
        "hi": "सार्वजनिक प्रवेश के लिए खाली छोड़ें",
        "kn": "ಸಾರ್ವಜನಿಕ ಪ್ರವೇಶಕ್ಕಾಗಿ ಖಾಲಿ ಬಿಡಿ",
    },
    "If set, joining via QR code will auto-authenticate players automatically. (💡 Demo trick: GM name containing Marco and password test autofills 10 test players for live demo).": {
        "en": "If set, joining via QR code will auto-authenticate players automatically. (💡 Demo trick: GM name containing Marco and password test autofills 10 test players for live demo).",
        "pt": "Se definido, a entrada via código QR autentica os jogadores automaticamente. (💡 Dica de demonstração: nome do Mestre contendo Marco e palavra-passe test adicionam 10 jogadores de teste).",
        "it": "Se impostata, l'accesso tramite QR code autentica i giocatori automaticamente. (💡 Trucco demo: nome GM contenente Marco e password test riempiono 10 giocatori per il test).",
        "es": "Si se establece, unirse mediante código QR autentica a los jugadores automáticamente. (💡 Truco demo: nombre GM con Marco y contraseña test añade 10 jugadores de prueba).",
        "fr": "Si configuré, l'accès via QR code authentifie les joueurs automatiquement. (💡 Astuce démo : nom MJ contenant Marco et mot de passe test ajoute 10 joueurs de test).",
        "el": "Αν οριστεί, η είσοδος μέσω QR code πιστοποιεί τους παίκτες αυτόματα. (💡 Κόλπο επίδειξης: όνομα Αφηγητή με Marco και κωδικός test προσθέτει 10 δοκιμαστικούς παίκτες).",
        "ru": "Если задан, вход по QR-коду автоматически авторизует игроков. (💡 Трюк для демо: имя ведущего с Marco и пароль test создадут 10 тестовых игроков).",
        "hi": "यदि सेट है, तो क्यूआर कोड से जुड़ने पर खिलाड़ी स्वतः प्रमाणित हो जाएंगे। (💡 डेमो ट्रिक: Marco युक्त जीएम नाम और test पासवर्ड 10 टेस्ट खिलाड़ी जोड़ता है)।",
        "kn": "ಸೆಟ್ ಮಾಡಿದ್ದರೆ, QR ಕೋಡ್ ಮೂಲಕ ಸೇರಿದಾಗ ಆಟಗಾರರು ಸ್ವಯಂಚಾಲಿತವಾಗಿ ದೃಢೀಕರಿಸಲ್ಪಡುತ್ತಾರೆ. (💡 ಡೆಮೊ ಟ್ರಿಕ್: Marco ಹೊಂದಿರುವ ಜಿಎಂ ಹೆಸರು ಮತ್ತು test ಪಾಸ್‌ವರ್ಡ್ 10 ಟೆಸ್ಟ್ ಆಟಗಾರರನ್ನು ಸೇರಿಸುತ್ತದೆ).",
    },
    "Theme & Terms": {
        "en": "Theme & Terms",
        "pt": "Tema e Nomenclatura",
        "it": "Tema e Termini",
        "es": "Tema y Términos",
        "fr": "Thème & Terminologie",
        "el": "Θέμα & Ορολογία",
        "ru": "Тема и термины",
        "hi": "थीम और नियम",
        "kn": "ಥೀಮ್ ಮತ್ತು ನಿಯಮಗಳು",
    },
    "Werewolf / Lupus": {
        "en": "Werewolf / Lupus",
        "pt": "Lobisomem / Lupus",
        "it": "Licantropo / Lupus",
        "es": "Hombre Lobo / Lupus",
        "fr": "Loup-Garou / Lupus",
        "el": "Λυκάνθρωπος / Lupus",
        "ru": "Оборотень / Lupus",
        "hi": "वेयरवोल्फ / लुपस",
        "kn": "ತೋಳಮಾನವ / ಲೂಪಸ್",
    },
    "Villagers, Wolves, Seer": {
        "en": "Villagers, Wolves, Seer",
        "pt": "Aldeões, Lobos, Vidente",
        "it": "Villici, Lupi, Veggente",
        "es": "Aldeanos, Lobos, Vidente",
        "fr": "Villageois, Loups, Voyante",
        "el": "Χωρικοί, Λύκοι, Μάντης",
        "ru": "Мирные, Волки, Провидец",
        "hi": "ग्रामीण, भेड़िए, द्रष्टा",
        "kn": "ಗ್ರಾಮಸ್ಥರು, ತೋಳಗಳು, ದ್ರಷ್ಟಾರ",
    },
    "Mafia": {
        "en": "Mafia", "pt": "Máfia", "it": "Mafia", "es": "Mafia", "fr": "Mafia", "el": "Μαφία", "ru": "Мафия", "hi": "माफिया", "kn": "ಮಾಫಿಯಾ"
    },
    "Civilians, Mobsters, Cop": {
        "en": "Civilians, Mobsters, Cop",
        "pt": "Civis, Mafiosos, Polícia",
        "it": "Cittadini, Mafiosi, Poliziotto",
        "es": "Civiles, Mafiosos, Policía",
        "fr": "Civils, Mafieux, Flic",
        "el": "Πολίτες, Μαφιόζοι, Αστυνόμος",
        "ru": "Мирные, Мафиози, Шериф",
        "hi": "नागरिक, गैंगस्टर, पुलिस",
        "kn": "ನಾಗರಿಕರು, ದರೋಡೆಕೋರರು, ಪೊಲೀಸ್",
    },
    "Game Rules & Timers": {
        "en": "Game Rules & Timers",
        "pt": "Regras de Jogo e Temporizadores",
        "it": "Regole di Gioco & Timer",
        "es": "Reglas de Juego y Temporizadores",
        "fr": "Règles du Jeu & Minuteurs",
        "el": "Κανόνες Παιχνιδιού & Χρονόμετρα",
        "ru": "Правила игры и таймеры",
        "hi": "खेल के नियम और टाइमर",
        "kn": "ಆಟದ ನಿಯಮಗಳು ಮತ್ತು ಟೈಮರ್‌ಗಳು",
    },
    "Discussion Round Timer": {
        "en": "Discussion Round Timer",
        "pt": "Tempo de Discussão",
        "it": "Timer Discussione",
        "es": "Temporizador de Discusión",
        "fr": "Minuteur de Discussion",
        "el": "Χρονόμετρο Συζήτησης",
        "ru": "Время на обсуждение",
        "hi": "चर्चा दौर का टाइमर",
        "kn": "ಚರ್ಚಾ ಸುತ್ತಿನ ಟೈಮರ್",
    },
    "5 Minutes (Standard)": {
        "en": "5 Minutes (Standard)",
        "pt": "5 Minutos (Padrão)",
        "it": "5 Minuti (Standard)",
        "es": "5 Minutos (Estándar)",
        "fr": "5 Minutes (Standard)",
        "el": "5 Λεπτά (Κανονικό)",
        "ru": "5 минут (стандарт)",
        "hi": "5 मिनट (मानक)",
        "kn": "5 ನಿಮಿಷಗಳು (ಪ್ರಮಾಣಿತ)",
    },
    "3 Minutes (Fast)": {
        "en": "3 Minutes (Fast)",
        "pt": "3 Minutos (Rápido)",
        "it": "3 Minuti (Veloce)",
        "es": "3 Minutos (Rápido)",
        "fr": "3 Minutes (Rapide)",
        "el": "3 Λεπτά (Γρήγορο)",
        "ru": "3 минуты (быстро)",
        "hi": "3 मिनट (तेज़)",
        "kn": "3 ನಿಮಿಷಗಳು (ವೇಗವಾಗಿ)",
    },
    "7 Minutes (Deliberate)": {
        "en": "7 Minutes (Deliberate)",
        "pt": "7 Minutos (Moderado)",
        "it": "7 Minuti (Riflessivo)",
        "es": "7 Minutos (Tranquilo)",
        "fr": "7 Minutes (Posé)",
        "el": "7 Λεπτά (Αναλυτικό)",
        "ru": "7 минут (вдумчиво)",
        "hi": "7 मिनट (विचारशील)",
        "kn": "7 ನಿಮಿಷಗಳು (ವಿವರವಾಗಿ)",
    },
    "10 Minutes": {
        "en": "10 Minutes",
        "pt": "10 Minutos",
        "it": "10 Minuti",
        "es": "10 Minutos",
        "fr": "10 Minutes",
        "el": "10 Λεπτά",
        "ru": "10 минут",
        "hi": "10 मिनट",
        "kn": "10 ನಿಮಿಷಗಳು",
    },
    "Defense Timer": {
        "en": "Defense Timer",
        "pt": "Tempo de Defesa",
        "it": "Timer Difesa",
        "es": "Temporizador de Defensa",
        "fr": "Minuteur de Défense",
        "el": "Χρονόμετρο Απολογίας",
        "ru": "Время на защиту",
        "hi": "बचाव का टाइमर",
        "kn": "ರಕ್ಷಣಾ ಟೈಮರ್",
    },
    "30 Seconds (Standard)": {
        "en": "30 Seconds (Standard)",
        "pt": "30 Segundos (Padrão)",
        "it": "30 Secondi (Standard)",
        "es": "30 Segundos (Estándar)",
        "fr": "30 Secondes (Standard)",
        "el": "30 Δευτερόλεπτα (Κανονικό)",
        "ru": "30 секунд (стандарт)",
        "hi": "30 सेकंड (मानक)",
        "kn": "30 ಸೆಕೆಂಡುಗಳು (ಪ್ರಮಾಣಿತ)",
    },
    "45 Seconds": {
        "en": "45 Seconds",
        "pt": "45 Segundos",
        "it": "45 Secondi",
        "es": "45 Segundos",
        "fr": "45 Secondes",
        "el": "45 Δευτερόλεπτα",
        "ru": "45 секунд",
        "hi": "45 सेकंड",
        "kn": "45 ಸೆಕೆಂಡುಗಳು",
    },
    "60 Seconds": {
        "en": "60 Seconds",
        "pt": "60 Segundos",
        "it": "60 Secondi",
        "es": "60 Segundos",
        "fr": "60 Secondes",
        "el": "60 Δευτερόλεπτα",
        "ru": "60 секунд",
        "hi": "60 सेकंड",
        "kn": "60 ಸೆಕೆಂಡುಗಳು",
    },
    "Limbo & Angel Mechanic:": {
        "en": "Limbo & Angel Mechanic:",
        "pt": "Mecânica do Limbo & Anjo:",
        "it": "Meccanica di Limbo & Angelo:",
        "es": "Mecánica del Limbo y el Ángel:",
        "fr": "Mécanique des Limbes & de l'Ange :",
        "el": "Μηχανισμός Καθαρτηρίου & Αγγέλου:",
        "ru": "Механика Лимба и Ангела:",
        "hi": "लिम्बो और एंजेल मैकेनिक्स:",
        "kn": "ಲಿಂಬೋ ಮತ್ತು ದೇವದೂತ ತಂತ್ರ:",
    },
    "Slain players enter Limbo once instead of dying directly. If they guess who the Angel is, they are resurrected!": {
        "en": "Slain players enter Limbo once instead of dying directly. If they guess who the Angel is, they are resurrected!",
        "pt": "Jogadores abatidos entram no Limbo uma vez antes de morrer diretamente. Se adivinharem quem é o Anjo, são ressuscitados!",
        "it": "I giocatori eliminati entrano nel Limbo invece di morire subito. Se indovinano chi è l'Angelo, risorgono!",
        "es": "Los jugadores abatidos entran al Limbo una vez en lugar de morir de inmediato. Si adivinan quién es el Ángel, ¡resucitan!",
        "fr": "Les joueurs éliminés entrent d'abord dans les Limbes. S'ils devinent qui est l'Ange, ils ressuscitent !",
        "el": "Οι παίκτες που χάνουν μπαίνουν στο Καθαρτήριο πριν πεθάνουν οριστικά. Αν μαντέψουν ποιος είναι ο Άγγελος, ανασταίνονται!",
        "ru": "Убитые игроки сначала попадают в Лимб. Если они угадают Ангела, они воскресают!",
        "hi": "मारे गए खिलाड़ी सीधे मरने के बजाय एक बार लिम्बो में प्रवेश करते हैं। यदि वे अनुमान लगाते हैं कि एंजेल कौन है, तो वे पुनर्जीवित हो जाते हैं!",
        "kn": "ಕೊಲ್ಲಲ್ಪಟ್ಟ ಆಟಗಾರರು ನೇರವಾಗಿ ಸಾಯುವ ಬದಲು ಒಮ್ಮೆ ಲಿಂಬೋಗೆ ಪ್ರವೇಶಿಸುತ್ತಾರೆ. ಅವರು ದೇವದೂತ ಯಾರೆಂದು ಊಹಿಸಿದರೆ ಪುನರುತ್ಥಾನಗೊಳ್ಳುತ್ತಾರೆ!",
    },
    "Staggering Doctor:": {
        "en": "Staggering Doctor:",
        "pt": "Médico Intercalado:",
        "it": "Dottore Alternato:",
        "es": "Médico Alternado:",
        "fr": "Médecin Alterné :",
        "el": "Εναλλασσόμενος Γιατρός:",
        "ru": "Доктор без повторов:",
        "hi": "अल्टरनेट डॉक्टर:",
        "kn": "ಬದಲಾಗುವ ವೈದ್ಯ:",
    },
    "The Doctor / Guard cannot protect the same person two consecutive nights.": {
        "en": "The Doctor / Guard cannot protect the same person two consecutive nights.",
        "pt": "O Médico / Guarda não pode proteger a mesma pessoa duas noites consecutivas.",
        "it": "Il Dottore / Guardia non può proteggere la stessa persona per due notti consecutive.",
        "es": "El Médico / Guardaespaldas no puede proteger a la misma persona dos noches consecutivas.",
        "fr": "Le Médecin / Garde ne peut pas protéger la même personne deux nuits de suite.",
        "el": "Ο Γιατρός / Φύλακας δεν μπορεί να προστατεύσει το ίδιο άτομο δύο συνεχόμενες νύχτες.",
        "ru": "Доктор / Телохранитель не может защищать одного и того же игрока две ночи подряд.",
        "hi": "डॉक्टर / गार्ड लगातार दो रातों तक एक ही व्यक्ति की रक्षा नहीं कर सकता।",
        "kn": "ವೈದ್ಯ / ಅಂಗರಕ್ಷಕ ಸತತ ಎರಡು ರಾತ್ರಿಗಳಲ್ಲಿ ಒಬ್ಬನೇ ವ್ಯಕ್ತಿಯನ್ನು ರಕ್ಷಿಸುವಂತಿಲ್ಲ.",
    },
    "Doctor Shields From Sniper:": {
        "en": "Doctor Shields From Sniper:",
        "pt": "Médico Protege Contra Sniper:",
        "it": "Il Dottore Protegge dallo Sniper:",
        "es": "El Médico Protege del Francotirador:",
        "fr": "Le Médecin Protège du Sniper :",
        "el": "Ο Γιατρός Προστατεύει από τον Ελεύθερο Σκοπευτή:",
        "ru": "Доктор защищает от снайпера:",
        "hi": "डॉक्टर स्नाइपर से बचाता है:",
        "kn": "ವೈದ್ಯ ಸ್ನೈಪರ್‌ನಿಂದ ರಕ್ಷಿಸುತ್ತಾನೆ:",
    },
    "If enabled, the Doctor's guard can save a wolf from being shot by the Sniper. (Disabled = sniper penetrates doctor guard).": {
        "en": "If enabled, the Doctor's guard can save a wolf from being shot by the Sniper. (Disabled = sniper penetrates doctor guard).",
        "pt": "Se ativado, a proteção do Médico pode salvar um alvo do tiro do Sniper. (Desativado = o tiro do Sniper penetra a proteção).",
        "it": "Se attivo, la guardia del Dottore può salvare un lupo colpito dallo Sniper. (Disattivato = lo sparo penetra la guardia).",
        "es": "Si se activa, la protección del Médico puede salvar a un objetivo del disparo del Francotirador. (Desactivado = el tiro penetra la guardia).",
        "fr": "Si activé, la protection du Médecin peut sauver une cible d'un tir de Sniper. (Désactivé = le tir pénètre la protection).",
        "el": "Αν ενεργοποιηθεί, η ασπίδα του Γιατρού μπορεί να σώσει έναν στόχο από τον Σκοπευτή. (Ανενεργό = η σφαίρα διαπερνά την προστασία).",
        "ru": "Если включено, защита Доктора может спасти от выстрела Снайпера. (Выключено = выстрел пробивает защиту).",
        "hi": "यदि सक्षम है, तो डॉक्टर का संरक्षण किसी को स्नाइपर की गोली से बचा सकता है। (अक्षम = स्नाइपर सुरक्षा को भेद देगा)।",
        "kn": "ಸಕ್ರಿಯಗೊಳಿಸಿದರೆ, ವೈದ್ಯರ ರಕ್ಷಣೆಯು ಸ್ನೈಪರ್ ಗುಂಡಿನಿಂದ ಗುರಿಯನ್ನು ಉಳಿಸಬಹುದು. (ನಿಷ್ಕ್ರಿಯ = ಸ್ನೈಪರ್ ರಕ್ಷಣೆಯನ್ನು ಭೇದಿಸುತ್ತಾನೆ).",
    },
    "Reveal Roles on Death:": {
        "en": "Reveal Roles on Death:",
        "pt": "Revelar Papéis ao Morrer:",
        "it": "Rivela Ruoli alla Morte:",
        "es": "Revelar Roles al Morir:",
        "fr": "Révéler les Rôles à la Mort :",
        "el": "Αποκάλυψη Ρόλων στον Θάνατο:",
        "ru": "Раскрытие ролей при смерти:",
        "hi": "मृत्यु पर भूमिकाएं प्रकट करें:",
        "kn": "ಮರಣದ ಸಮಯದಲ್ಲಿ ಪಾತ್ರಗಳನ್ನು ಬಹಿರಂಗಪಡಿಸಿ:",
    },
    "0 — Secret (Closed graveyard, roles concealed until game over)": {
        "en": "0 — Secret (Closed graveyard, roles concealed until game over)",
        "pt": "0 — Secreto (Cemitério fechado, papéis ocultos até ao fim do jogo)",
        "it": "0 — Segreto (Cimitero chiuso, ruoli nascosti fino a fine partita)",
        "es": "0 — Secreto (Cementerio cerrado, roles ocultos hasta el fin del juego)",
        "fr": "0 — Secret (Cimetière fermé, rôles masqués jusqu'à la fin)",
        "el": "0 — Μυστικό (Κλειστό νεκροταφείο, κρυφοί ρόλοι μέχρι το τέλος)",
        "ru": "0 — Тайна (Закрытое кладбище, роли скрыты до конца игры)",
        "hi": "0 — गुप्त (बंद कब्रिस्तान, खेल खत्म होने तक भूमिकाएं छिपी रहेंगी)",
        "kn": "0 — ರಹಸ್ಯ (ಮುಚ್ಚಿದ ಸ್ಮಶಾನ, ಆಟ ಮುಗಿಯುವವರೆಗೆ ಪಾತ್ರಗಳು ಗೌಪ್ಯ)",
    },
    "1 — Alignment Only (Announces \"GOOD\" vs \"EVIL\")": {
        "en": "1 — Alignment Only (Announces \"GOOD\" vs \"EVIL\")",
        "pt": "1 — Apenas Alinhamento (Anuncia \"BEM\" vs \"MAL\")",
        "it": "1 — Solo Allineamento (Annuncia \"BENE\" vs \"MALE\")",
        "es": "1 — Solo Alineación (Anuncia \"BIEN\" vs \"MAL\")",
        "fr": "1 — Alignement Seul (Annonce \"BIEN\" vs \"MAL\")",
        "el": "1 — Μόνο Παράταξη (Ανακοινώνει \"ΚΑΛΟ\" vs \"ΚΑΚΟ\")",
        "ru": "1 — Только сторона (Объявляет \"ДОБРО\" или \"ЗЛО\")",
        "hi": "1 — केवल संरेखण (\"अच्छा\" बनाम \"बुरा\" घोषित करता है)",
        "kn": "1 — ನಿಷ್ಠೆ ಮಾತ್ರ (\"ಒಳ್ಳೆಯದು\" ವಿರುದ್ಧ \"ಕೆಟ್ಟದ್ದು\" ಪ್ರಕಟಿಸುತ್ತದೆ)",
    },
    "2 — Faction / Team (Announces \"Town\", \"Werewolves\", \"Neutral\")": {
        "en": "2 — Faction / Team (Announces \"Town\", \"Werewolves\", \"Neutral\")",
        "pt": "2 — Fação / Equipa (Anuncia \"Aldeia\", \"Lobisomens\", \"Neutro\")",
        "it": "2 — Fazione / Squadra (Annuncia \"Città\", \"Lupi\", \"Neutrale\")",
        "es": "2 — Facción / Equipo (Anuncia \"Pueblo\", \"Hombres Lobo\", \"Neutral\")",
        "fr": "2 — Faction / Équipe (Annonce \"Village\", \"Loups-Garous\", \"Neutre\")",
        "el": "2 — Φατρία / Ομάδα (Ανακοινώνει \"Χωριό\", \"Λυκάνθρωποι\", \"Ουδέτερος\")",
        "ru": "2 — Фракция / Команда (Объявляет \"Город\", \"Волки\", \"Нейтрал\")",
        "hi": "2 — गुट / टीम (\"शहर\", \"वेयरवोल्फ\", \"तटस्थ\" घोषित करता है)",
        "kn": "2 — ಬಣ / ತಂಡ (\"ನಗರ\", \"ತೋಳಗಳು\", \"ತಟಸ್ಥ\" ಪ್ರಕಟಿಸುತ್ತದೆ)",
    },
    "3 — Full Role Card (Announces exact card name and icon)": {
        "en": "3 — Full Role Card (Announces exact card name and icon)",
        "pt": "3 — Carta Completa (Anuncia o nome exato do papel e ícone)",
        "it": "3 — Carta Ruolo Completa (Annuncia nome esatto e icona)",
        "es": "3 — Carta Completa (Anuncia el nombre exacto del rol e icono)",
        "fr": "3 — Carte de Rôle Complète (Annonce le nom exact et l'icône)",
        "el": "3 — Πλήρης Κάρτα Ρόλου (Ανακοινώνει το ακριβές όνομα και εικονίδιο)",
        "ru": "3 — Полная карта роли (Объявляет точное имя роли и значок)",
        "hi": "3 — पूरा रोल कार्ड (सटीक भूमिका नाम और आइकन घोषित करता है)",
        "kn": "3 — ಸಂಪೂರ್ಣ ಪಾತ್ರ ಕಾರ್ಡ್ (ನಿಖರವಾದ ಕಾರ್ಡ್ ಹೆಸರು ಮತ್ತು ಐಕಾನ್ ಪ್ರಕಟಿಸುತ್ತದೆ)",
    },
    "💡 In Limbo games, role revelation strictly occurs on permanent death (\"death death\"), never while hovering in Limbo.": {
        "en": "💡 In Limbo games, role revelation strictly occurs on permanent death (\"death death\"), never while hovering in Limbo.",
        "pt": "💡 Em jogos com Limbo, a revelação de papéis ocorre apenas na morte definitiva, nunca enquanto no Limbo.",
        "it": "💡 Nelle partite con Limbo, la rivelazione avviene solo con la morte definitiva, mai nel Limbo.",
        "es": "💡 En partidas con Limbo, la revelación ocurre solo tras la muerte definitiva, nunca en el Limbo.",
        "fr": "💡 Avec les Limbes, la révélation a lieu uniquement lors de la mort définitive, jamais dans les Limbes.",
        "el": "💡 Στα παιχνίδια με Καθαρτήριο, η αποκάλυψη γίνεται μόνο στον οριστικό θάνατο, ποτέ μέσα στο Καθαρτήριο.",
        "ru": "💡 В играх с Лимбом раскрытие роли происходит только при окончательной смерти, но не в Лимбе.",
        "hi": "💡 लिम्बो गेम्स में, भूमिका का खुलासा केवल स्थायी मृत्यु पर होता है, लिम्बो में रहने के दौरान कभी नहीं।",
        "kn": "💡 ಲಿಂಬೋ ಆಟಗಳಲ್ಲಿ, ಪಾತ್ರದ ಬಹಿರಂಗಪಡಿಸುವಿಕೆ ಕೇವಲ ಶಾಶ್ವತ ಮರಣದ ನಂತರವೇ ಆಗುತ್ತದೆ, ಲಿಂಬೋದಲ್ಲಿರುವಾಗಲ್ಲ.",
    },
    "Starting Role Deck Preset": {
        "en": "Starting Role Deck Preset",
        "pt": "Baralho Inicial Pré-definido",
        "it": "Preset Mazzo Ruoli Iniziale",
        "es": "Mazo Inicial Predeterminado",
        "fr": "Paquet de Rôles Prédéfini",
        "el": "Προκαθορισμένη Τράπουλα Ρόλων",
        "ru": "Набор колоды ролей",
        "hi": "प्रारंभिक रोल डेक प्रीसेट",
        "kn": "ಆರಂಭಿಕ ರೋಲ್ ಡೆಕ್ ಪ್ರಿಸೆಟ್",
    },
    "🧑 Simple / Classic (No special powers — pure Wolves vs Villagers)": {
        "en": "🧑 Simple / Classic (No special powers — pure Wolves vs Villagers)",
        "pt": "🧑 Simples / Clássico (Sem poderes especiais — Lobos vs Aldeões puros)",
        "it": "🧑 Semplice / Classico (Senza poteri speciali — solo Lupi vs Villici)",
        "es": "🧑 Simple / Clásico (Sin poderes especiales — Lobos vs Aldeanos puros)",
        "fr": "🧑 Simple / Classique (Sans pouvoirs spéciaux — Loups vs Villageois)",
        "el": "🧑 Απλό / Κλασικό (Χωρίς ειδικές δυνάμεις — μόνο Λύκοι vs Χωρικοί)",
        "ru": "🧑 Простой / Классический (Без суперсил — только Волки против Мирных)",
        "hi": "🧑 सरल / क्लासिक (कोई विशेष शक्तियां नहीं — शुद्ध भेड़िए बनाम ग्रामीण)",
        "kn": "🧑 ಸರಳ / ಕ್ಲಾಸಿಕ್ (ಯಾವುದೇ ವಿಶೇಷ ಶಕ್ತಿಗಳಿಲ್ಲ — ಕೇವಲ ತೋಳಗಳು ವಿರುದ್ಧ ಗ್ರಾಮಸ್ಥರು)",
    },
    "🔍 Standard (Wolves + Detective/Seer + Doctor/Guard + Villagers)": {
        "en": "🔍 Standard (Wolves + Detective/Seer + Doctor/Guard + Villagers)",
        "pt": "🔍 Padrão (Lobos + Detetive/Vidente + Médico/Guarda + Aldeões)",
        "it": "🔍 Standard (Lupi + Detective/Veggente + Dottore/Guardia + Villici)",
        "es": "🔍 Estándar (Lobos + Detective/Vidente + Médico/Guarda + Aldeanos)",
        "fr": "🔍 Standard (Loups + Détective/Voyante + Médecin/Garde + Villageois)",
        "el": "🔍 Κανονικό (Λύκοι + Ντετέκτιβ/Μάντης + Γιατρός/Φύλακας + Χωρικοί)",
        "ru": "🔍 Стандарт (Волки + Детектив/Провидец + Доктор + Мирные)",
        "hi": "🔍 मानक (भेड़िए + जासूस/द्रष्टा + डॉक्टर/गार्ड + ग्रामीण)",
        "kn": "🔍 ಪ್ರಮಾಣಿತ (ತೋಳಗಳು + ಪತ್ತೇದಾರಿ/ದ್ರಷ್ಟಾರ + ವೈದ್ಯ/ಅಂಗರಕ್ಷಕ + ಗ್ರಾಮಸ್ಥರು)",
    },
    "👼 Limbo & Angel (Wolves + Detective + Doctor + Angel + Sniper + Villagers)": {
        "en": "👼 Limbo & Angel (Wolves + Detective + Doctor + Angel + Sniper + Villagers)",
        "pt": "👼 Limbo & Anjo (Lobos + Detetive + Médico + Anjo + Sniper + Aldeões)",
        "it": "👼 Limbo & Angelo (Lupi + Detective + Dottore + Angelo + Sniper + Villici)",
        "es": "👼 Limbo y Ángel (Lobos + Detective + Médico + Ángel + Francotirador + Aldeanos)",
        "fr": "👼 Limbes & Ange (Loups + Détective + Médecin + Ange + Sniper + Villageois)",
        "el": "👼 Καθαρτήριο & Άγγελος (Λύκοι + Ντετέκτιβ + Γιατρός + Άγγελος + Σκοπευτής + Χωρικοί)",
        "ru": "👼 Лимб и Ангел (Волки + Детектив + Доктор + Ангел + Снайпер + Мирные)",
        "hi": "👼 लिम्बो और एंजेल (भेड़िए + जासूस + डॉक्टर + एंजेल + स्नाइपर + ग्रामीण)",
        "kn": "👼 ಲಿಂಬೋ ಮತ್ತು ದೇವದೂತ (ತೋಳಗಳು + ಪತ್ತೇದಾರಿ + ವೈದ್ಯ + ದೇವದೂತ + ಸ್ನೈಪರ್ + ಗ್ರಾಮಸ್ಥರು)",
    },
    "⚡ Chaos & Specials (Alpha Wolf, Silencer, Detective, Doctor, Sniper, Mayor, Witch...)": {
        "en": "⚡ Chaos & Specials (Alpha Wolf, Silencer, Detective, Doctor, Sniper, Mayor, Witch...)",
        "pt": "⚡ Caos & Especiais (Lobo Alfa, Silenciador, Detetive, Médico, Sniper, Presidente, Bruxa...)",
        "it": "⚡ Caos & Speciali (Lupo Alfa, Silenziatore, Detective, Dottore, Cecchino, Sindaco, Strega...)",
        "es": "⚡ Caos y Especiales (Lobo Alfa, Silenciador, Detective, Médico, Francotirador, Alcalde, Bruja...)",
        "fr": "⚡ Chaos & Spéciaux (Loup Alpha, Silencieux, Détective, Médecin, Sniper, Maire, Sorcière...)",
        "el": "⚡ Χάος & Ειδικοί (Άλφα Λύκος, Σιωπηλός, Ντετέκτιβ, Γιατρός, Σκοπευτής, Δήμαρχος, Μάγισσα...)",
        "ru": "⚡ Хаос и спецы (Альфа-волк, Глушитель, Детектив, Доктор, Снайпер, Мэр, Ведьма...)",
        "hi": "⚡ अराजकता और विशेष (अल्फा वुल्फ, साइलेंसर, जासूस, डॉक्टर, स्नाइपर, मेयर, चुड़ैल...)",
        "kn": "⚡ ಅವ್ಯವಸ್ಥೆ ಮತ್ತು ವಿಶೇಷತೆಗಳು (ಆಲ್ಫಾ ತೋಳ, ಸೈಲೆನ್ಸರ್, ಪತ್ತೇದಾರಿ, ವೈದ್ಯ, ಸ್ನೈಪರ್, ಮೇಯರ್, ಮಾಟಗಾತಿ...)",
    },
    "💡 The deck adapts automatically to the number of players who join. You can fine-tune every role and good vs. bad balance live in the Pre-Game Lobby before starting.": {
        "en": "💡 The deck adapts automatically to the number of players who join. You can fine-tune every role and good vs. bad balance live in the Pre-Game Lobby before starting.",
        "pt": "💡 O baralho adapta-se automaticamente ao número de participantes. Poderá ajustar todos os papéis e o equilíbrio bem vs. mal na Sala de Espera antes de iniciar.",
        "it": "💡 Il mazzo si adatta automaticamente al numero di giocatori. Puoi perfezionare ogni ruolo e l'equilibrio bene/male nella lobby prima di iniziare.",
        "es": "💡 El mazo se adapta automáticamente al número de jugadores que se unen. Puedes ajustar cada rol y el equilibrio bien/mal en el vestíbulo antes de comenzar.",
        "fr": "💡 Le paquet s'adapte automatiquement au nombre de joueurs. Vous pouvez ajuster chaque rôle et l'équilibre bien/mal dans le salon d'attente avant de lancer.",
        "el": "💡 Η τράπουλα προσαρμόζεται αυτόματα στον αριθμό παικτών. Μπορείτε να ρυθμίσετε κάθε ρόλο και την ισορροπία καλού/κακού στην αίθουσα αναμονής πριν ξεκινήσετε.",
        "ru": "💡 Колода автоматически подстраивается под число игроков. Вы сможете настроить баланс сил в лобби перед стартом игры.",
        "hi": "💡 डेक शामिल होने वाले खिलाड़ियों की संख्या के अनुसार स्वचालित रूप से अनुकूलित होता है। आप शुरू करने से पहले लॉबी में हर भूमिका को ठीक कर सकते हैं।",
        "kn": "💡 ಸೇರಿದ ಆಟಗಾರರ ಸಂಖ್ಯೆಗೆ ಡೆಕ್ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಹೊಂದಿಕೊಳ್ಳುತ್ತದೆ. ಪ್ರಾರಂಭಿಸುವ ಮೊದಲು ಲಾಬಿಯಲ್ಲಿ ಪ್ರತಿ ಪಾತ್ರವನ್ನು ಮತ್ತು ಸಮತೋಲನವನ್ನು ಸರಿಹೊಂದಿಸಬಹುದು.",
    },
    "Launch Lupus Room": {
        "en": "Launch Lupus Room",
        "pt": "Iniciar Sala de Lupus",
        "it": "Avvia Stanza Lupus",
        "es": "Lanzar Sala de Lupus",
        "fr": "Lancer le Salon Lupus",
        "el": "Έναρξη Αίθουσας Lupus",
        "ru": "Запустить комнату Lupus",
        "hi": "लुपस कमरा शुरू करें",
        "kn": "ಲೂಪಸ್ ಕೊಠಡಿಯನ್ನು ಪ್ರಾರಂಭಿಸಿ",
    },
    "Lupus Party Game": {
        "en": "Lupus Party Game",
        "pt": "Jogo de Festa Lupus",
        "it": "Party Game Lupus",
        "es": "Juego de Fiesta Lupus",
        "fr": "Jeu de Société Lupus",
        "el": "Παιχνίδι Παρέας Lupus",
        "ru": "Игра для вечеринок Lupus",
        "hi": "लुपस पार्टी गेम",
        "kn": "ಲೂಪಸ್ ಪಾರ್ಟಿ ಆಟ",
    },

    # Lupus Join (/games/lupus/join/)
    "Join Lupus Game": {
        "en": "Join Lupus Game",
        "pt": "Entrar no Jogo Lupus",
        "it": "Entra nel Gioco Lupus",
        "es": "Entrar a la Partida de Lupus",
        "fr": "Rejoindre la Partie de Lupus",
        "el": "Σύνδεση στο Παιχνίδι Lupus",
        "ru": "Присоединиться к игре Lupus",
        "hi": "लुपस गेम में शामिल हों",
        "kn": "ಲೂಪಸ್ ಆಟಕ್ಕೆ ಸೇರಿ",
    },
    "Lupus Game": {
        "en": "Lupus Game",
        "pt": "Jogo Lupus",
        "it": "Partita Lupus",
        "es": "Partida Lupus",
        "fr": "Partie Lupus",
        "el": "Παιχνίδι Lupus",
        "ru": "Игра Lupus",
        "hi": "लुपस खेल",
        "kn": "ಲೂಪಸ್ ಆಟ",
    },
    "Room Code:": {
        "en": "Room Code:",
        "pt": "Código da Sala:",
        "it": "Codice Stanza:",
        "es": "Código de la Sala:",
        "fr": "Code du Salon :",
        "el": "Κωδικός Αίθουσας:",
        "ru": "Код комнаты:",
        "hi": "कमरा कोड:",
        "kn": "ಕೊಠಡಿ ಕೋಡ್:",
    },
    "Room Password": {
        "en": "Room Password",
        "pt": "Palavra-passe da Sala",
        "it": "Password Stanza",
        "es": "Contraseña de la Sala",
        "fr": "Mot de passe du Salon",
        "el": "Κωδικός Αίθουσας",
        "ru": "Пароль комнаты",
        "hi": "कमरा पासवर्ड",
        "kn": "ಕೊಠಡಿ ಪಾಸ್‌ವರ್ಡ್",
    },
    "Unlock Room": {
        "en": "Unlock Room",
        "pt": "Desbloquear Sala",
        "it": "Sblocca Stanza",
        "es": "Desbloquear Sala",
        "fr": "Déverrouiller le Salon",
        "el": "Ξεκλείδωμα Αίθουσας",
        "ru": "Разблокировать комнату",
        "hi": "कमरा अनलॉक करें",
        "kn": "ಕೊಠಡಿಯನ್ನು ಅನ್‌ಲಾಕ್ ಮಾಡಿ",
    },
    "Your Name / Nickname": {
        "en": "Your Name / Nickname",
        "pt": "O Seu Nome / Apelido",
        "it": "Il Tuo Nome / Nickname",
        "es": "Tu Nombre / Apodo",
        "fr": "Votre Nom / Pseudo",
        "el": "Το Όνομά / Ψευδώνυμό σας",
        "ru": "Ваше имя / никнейм",
        "hi": "आपका नाम / उपनाम",
        "kn": "ನಿಮ್ಮ ಹೆಸರು / ಅಡ್ಡಹೆಸರು",
    },
    "e.g. Marco": {
        "en": "e.g. Marco",
        "pt": "ex. Marco",
        "it": "es. Marco",
        "es": "ej. Marco",
        "fr": "ex. Marco",
        "el": "π.χ. Μάρκο",
        "ru": "напр. Марко",
        "hi": "उदा. मार्को",
        "kn": "ಉದಾ. ಮಾರ್ಕೊ",
    },
    "Pick the name others at the table know you by.": {
        "en": "Pick the name others at the table know you by.",
        "pt": "Escolha o nome pelo qual as pessoas na mesa o conhecem.",
        "it": "Scegli il nome con cui ti conoscono gli altri al tavolo.",
        "es": "Elige el nombre por el que te conocen en la mesa.",
        "fr": "Choisissez le nom par lequel vos amis à table vous connaissent.",
        "el": "Επιλέξτε το όνομα με το οποίο σας ξέρουν οι υπόλοιποι στο τραπέζι.",
        "ru": "Выберите имя, под которым вас знают за столом.",
        "hi": "वह नाम चुनें जिससे मेज पर मौजूद अन्य लोग आपको जानते हैं।",
        "kn": "ಮೇಜಿನ ಮೇಲಿರುವ ಇತರರು ನಿಮ್ಮನ್ನು ಗುರುತಿಸುವ ಹೆಸರನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
    },
    "Enter Game": {
        "en": "Enter Game",
        "pt": "Entrar no Jogo",
        "it": "Entra nel Gioco",
        "es": "Entrar al Juego",
        "fr": "Entrer dans la Partie",
        "el": "Είσοδος στο Παιχνίδι",
        "ru": "Войти в игру",
        "hi": "गेम में प्रवेश करें",
        "kn": "ಆಟಕ್ಕೆ ಪ್ರವೇಶಿಸಿ",
    },
    "Lupus Active Rooms & Hub": {
        "en": "Lupus Active Rooms & Hub",
        "pt": "Salas Ativas & Central de Lupus",
        "it": "Stanze Lupus Attive & Hub",
        "es": "Salas Activas y Centro de Lupus",
        "fr": "Salons Actifs & Centre Lupus",
        "el": "Ενεργές Αίθουσες & Κέντρο Lupus",
        "ru": "Активные комнаты и центр Lupus",
        "hi": "लुपस सक्रिय कमरे और हब",
        "kn": "ಲೂಪಸ್ ಸಕ್ರಿಯ ಕೊಠಡಿಗಳು ಮತ್ತು ಹಬ್",
    },

    # Gamerooms Simple / Legacy
    "create room": {
        "en": "create room", "pt": "criar sala", "it": "crea stanza", "es": "crear sala", "fr": "créer un salon", "el": "δημιουργία αίθουσας", "ru": "создать комнату", "hi": "कमरा बनाएं", "kn": "ಕೊಠಡಿ ರಚಿಸಿ"
    },
    "title": {
        "en": "title", "pt": "título", "it": "titolo", "es": "título", "fr": "titre", "el": "τίτλος", "ru": "название", "hi": "शीर्षक", "kn": "ಶೀರ್ಷಿಕೆ"
    },
    "password (optional)": {
        "en": "password (optional)", "pt": "palavra-passe (opcional)", "it": "password (opzionale)", "es": "contraseña (opcional)", "fr": "mot de passe (optionnel)", "el": "κωδικός (προαιρετικό)", "ru": "пароль (необязательно)", "hi": "पासवर्ड (वैकल्पिक)", "kn": "ಪಾಸ್‌ವರ್ಡ್ (ಐಚ್ಛಿಕ)"
    },
    "what is %(a)s + %(b)s?": {
        "en": "what is %(a)s + %(b)s?", "pt": "quanto é %(a)s + %(b)s?", "it": "quanto fa %(a)s + %(b)s?", "es": "¿cuánto es %(a)s + %(b)s?", "fr": "combien font %(a)s + %(b)s ?", "el": "πόσο κάνει %(a)s + %(b)s;", "ru": "сколько будет %(a)s + %(b)s?", "hi": "%(a)s + %(b)s कितना होता है?", "kn": "%(a)s + %(b)s ಎಷ್ಟು?"
    },
    "create": {
        "en": "create", "pt": "criar", "it": "crea", "es": "crear", "fr": "créer", "el": "δημιουργία", "ru": "создать", "hi": "बनाएं", "kn": "ರಚಿಸಿ"
    },
    "join": {
        "en": "join", "pt": "entrar", "it": "entra", "es": "entrar", "fr": "rejoindre", "el": "σύνδεση", "ru": "войти", "hi": "शामिल हों", "kn": "ಸೇರಿ"
    },
    "your name": {
        "en": "your name", "pt": "o seu nome", "it": "il tuo nome", "es": "tu nombre", "fr": "votre nom", "el": "το όνομά σας", "ru": "ваше имя", "hi": "आपका नाम", "kn": "ನಿಮ್ಮ ಹೆಸರು"
    },
    "room password": {
        "en": "room password", "pt": "palavra-passe da sala", "it": "password della stanza", "es": "contraseña de la sala", "fr": "mot de passe du salon", "el": "κωδικός αίθουσας", "ru": "пароль комнаты", "hi": "कमरे का पासवर्ड", "kn": "ಕೊಠಡಿ ಪಾಸ್‌ವರ್ಡ್"
    },

    # Unauthorized
    "Access Denied": {
        "en": "Access Denied", "pt": "Acesso Negado", "it": "Accesso Negato", "es": "Acceso Denegado", "fr": "Accès Refusé", "el": "Δεν επιτρέπεται η πρόσβαση", "ru": "Доступ запрещён", "hi": "प्रवेश अस्वीकृत", "kn": "ಪ್ರವೇಶ ನಿರಾಕರಿಸಲಾಗಿದೆ"
    },
    "You need an authorized key to access this page.": {
        "en": "You need an authorized key to access this page.",
        "pt": "Precisa de uma chave autorizada para aceder a esta página.",
        "it": "È necessaria una chiave autorizzata per accedere a questa pagina.",
        "es": "Necesitas una clave autorizada para acceder a esta página.",
        "fr": "Vous avez besoin d'une clé autorisée pour accéder à cette page.",
        "el": "Χρειάζεστε εξουσιοδοτημένο κλειδί για πρόσβαση σε αυτή τη σελίδα.",
        "ru": "Для доступа к этой странице требуется ключ авторизации.",
        "hi": "इस पृष्ठ तक पहुँचने के लिए आपको एक अधिकृत कुंजी की आवश्यकता है।",
        "kn": "ಈ ಪುಟವನ್ನು ಪ್ರವೇಶಿಸಲು ನಿಮಗೆ ಅಧಿಕೃತ ಕೀ ಅಗತ್ಯವಿದೆ.",
    },
    "Join as Player": {
        "en": "Join as Player",
        "pt": "Entrar como Jogador",
        "it": "Entra come Giocatore",
        "es": "Entrar como Jugador",
        "fr": "Rejoindre en tant que Joueur",
        "el": "Σύνδεση ως Παίκτης",
        "ru": "Войти как игрок",
        "hi": "खिलाड़ी के रूप में शामिल हों",
        "kn": "ಆಟಗಾರನಾಗಿ ಸೇರಿ",
    },

    # Lifecycle & Phase Badges
    "Lobby": {
        "en": "Lobby", "pt": "Lobby", "it": "Lobby", "es": "Espera", "fr": "Attente", "el": "Αναμονή", "ru": "Лобби", "hi": "लॉबी", "kn": "ಲಾಬಿ"
    },
    "Lobby (Waiting for Players)": {
        "en": "Lobby (Waiting for Players)", "pt": "Lobby (A aguardar jogadores)", "it": "Lobby (In attesa dei giocatori)", "es": "Lobby (Esperando jugadores)", "fr": "Attente (En attente des joueurs)", "el": "Αναμονή (Αναμονή παικτών)", "ru": "Лобби (Ожидание игроков)", "hi": "लॉबी (खिलाड़ियों का इंतज़ार)", "kn": "ಲಾಬಿ (ಆಟಗಾರರಿಗಾಗಿ ಕಾಯಲಾಗುತ್ತಿದೆ)"
    },
    "Open": {
        "en": "Open", "pt": "Aberta", "it": "Aperta", "es": "Abierta", "fr": "Ouvert", "el": "Ανοιχτή", "ru": "Открыта", "hi": "खुला", "kn": "ತೆರೆದಿದೆ"
    },
    "Open (Lobby)": {
        "en": "Open (Lobby)", "pt": "Aberta (Lobby)", "it": "Aperta (Lobby)", "es": "Abierta (Lobby)", "fr": "Ouvert (Attente)", "el": "Ανοιχτή (Αναμονή)", "ru": "Открыта (Лобби)", "hi": "खुला (लॉबी)", "kn": "ತೆರೆದಿದೆ (ಲಾಬಿ)"
    },
    "Running": {
        "en": "Running", "pt": "Em Curso", "it": "In Corso", "es": "En Curso", "fr": "En Cours", "el": "Σε Εξέλιξη", "ru": "Идёт игра", "hi": "चल रहा है", "kn": "ನಡೆಯುತ್ತಿದೆ"
    },
    "Finished": {
        "en": "Finished", "pt": "Terminado", "it": "Concluso", "es": "Terminado", "fr": "Terminé", "el": "Ολοκληρώθηκε", "ru": "Завершено", "hi": "समाप्त", "kn": "ಮುಕ್ತಾಯವಾಗಿದೆ"
    },
    "Active": {
        "en": "Active", "pt": "Ativo", "it": "Attivo", "es": "Activo", "fr": "Actif", "el": "Ενεργό", "ru": "Активно", "hi": "सक्रिय", "kn": "ಸಕ್ರಿಯ"
    },
    "Day": {
        "en": "Day", "pt": "Dia", "it": "Giorno", "es": "Día", "fr": "Jour", "el": "Ημέρα", "ru": "День", "hi": "दिन", "kn": "ದಿನ"
    },
    "Night": {
        "en": "Night", "pt": "Noite", "it": "Notte", "es": "Noche", "fr": "Nuit", "el": "Νύχτα", "ru": "Ночь", "hi": "रात", "kn": "ರಾತ್ರಿ"
    },
    "Voting": {
        "en": "Voting", "pt": "Votação", "it": "Votazione", "es": "Votación", "fr": "Vote", "el": "Ψηφοφορία", "ru": "Голосование", "hi": "मतदान", "kn": "ಮತದಾನ"
    },
    "Discussion": {
        "en": "Discussion", "pt": "Discussão", "it": "Discussione", "es": "Discusión", "fr": "Discussion", "el": "Συζήτηση", "ru": "Обсуждение", "hi": "चर्चा", "kn": "ಚರ್ಚೆ"
    },
    "Town Voting": {
        "en": "Town Voting", "pt": "Votação da Cidade", "it": "Votazione Cittadina", "es": "Votación del Pueblo", "fr": "Vote du Village", "el": "Ψηφοφορία Χωριού", "ru": "Голосование города", "hi": "नगर मतदान", "kn": "ಪಟ್ಟಣ ಮತದಾನ"
    },
    "Silent Phase": {
        "en": "Silent Phase", "pt": "Fase Silenciosa", "it": "Fase Silenziosa", "es": "Fase Silenciosa", "fr": "Phase Silencieuse", "el": "Σιωπηλή Φάση", "ru": "Тихая фаза", "hi": "शांत चरण", "kn": "ಶಾಂತ ಹಂತ"
    },
    "Limbo": {
        "en": "Limbo", "pt": "Limbo", "it": "Limbo", "es": "Limbo", "fr": "Limbes", "el": "Καθαρτήριο", "ru": "Лимб", "hi": "लिम्बो", "kn": "ಲಿಂಬೋ"
    },
    "Limbo Resolution": {
        "en": "Limbo Resolution", "pt": "Resolução do Limbo", "it": "Risoluzione del Limbo", "es": "Resolución del Limbo", "fr": "Résolution des Limbes", "el": "Επίλυση Καθαρτηρίου", "ru": "Разрешение Лимба", "hi": "लिम्बो समाधान", "kn": "ಲಿಂಬೋ ಪರಿಹಾರ"
    },
    "Game Over": {
        "en": "Game Over", "pt": "Fim de Jogo", "it": "Fine Partita", "es": "Fin de la Partida", "fr": "Fin de Partie", "el": "Τέλος Παιχνιδιού", "ru": "Конец игры", "hi": "खेल समाप्त", "kn": "ಆಟ ಮುಗಿದಿದೆ"
    },
    "In Progress": {
        "en": "In Progress", "pt": "Em Andamento", "it": "In Corso", "es": "En Progreso", "fr": "En Cours", "el": "Σε Εξέλιξη", "ru": "В процессе", "hi": "प्रगति में", "kn": "ಪ್ರಗತಿಯಲ್ಲಿದೆ"
    },

    # Errors & Notifications
    "Please enter a valid room code.": {
        "en": "Please enter a valid room code.",
        "pt": "Por favor introduza um código de sala válido.",
        "it": "Inserisci un codice stanza valido.",
        "es": "Por favor introduce un código de sala válido.",
        "fr": "Veuillez entrer un code de salon valide.",
        "el": "Παρακαλώ εισαγάγετε έναν έγκυρο κωδικό αίθουσας.",
        "ru": "Пожалуйста, введите корректный код комнаты.",
        "hi": "कृपया एक मान्य कमरा कोड दर्ज करें।",
        "kn": "ದಯವಿಟ್ಟು ಮಾನ್ಯವಾದ ಕೊಠಡಿ ಕೋಡ್ ನಮೂದಿಸಿ.",
    },
    "Room code '%(code)s' was not found or is no longer active.": {
        "en": "Room code '%(code)s' was not found or is no longer active.",
        "pt": "O código de sala '%(code)s' não foi encontrado ou já não está ativo.",
        "it": "Il codice stanza '%(code)s' non è stato trovato o non è più attivo.",
        "es": "El código de sala '%(code)s' no se encontró o ya no está activo.",
        "fr": "Le code de salon '%(code)s' est introuvable ou n'est plus actif.",
        "el": "Ο κωδικός αίθουσας '%(code)s' δεν βρέθηκε ή δεν είναι πλέον ενεργός.",
        "ru": "Код комнаты '%(code)s' не найден или комната неактивна.",
        "hi": "कमरा कोड '%(code)s' नहीं मिला या अब सक्रिय नहीं है।",
        "kn": "ಕೊಠಡಿ ಕೋಡ್ '%(code)s' ಕಂಡುಬಂದಿಲ್ಲ ಅಥವಾ ಇನ್ನು ಮುಂದೆ ಸಕ್ರಿಯವಾಗಿಲ್ಲ.",
    },
    "Incorrect room password.": {
        "en": "Incorrect room password.",
        "pt": "Palavra-passe da sala incorreta.",
        "it": "Password della stanza non corretta.",
        "es": "Contraseña de sala incorrecta.",
        "fr": "Mot de passe du salon incorrect.",
        "el": "Εσφαλμένος κωδικός αίθουσας.",
        "ru": "Неверный пароль комнаты.",
        "hi": "कमरे का पासवर्ड गलत है।",
        "kn": "ತಪ್ಪಾದ ಕೊಠಡಿ ಪಾಸ್‌ವರ್ಡ್.",
    },
    "Please enter a player name.": {
        "en": "Please enter a player name.",
        "pt": "Por favor introduza um nome de jogador.",
        "it": "Inserisci un nome giocatore.",
        "es": "Por favor introduce un nombre de jogador.",
        "fr": "Veuillez entrer un nom de joueur.",
        "el": "Παρακαλώ εισαγάγετε όνομα παίκτη.",
        "ru": "Пожалуйста, введите имя игрока.",
        "hi": "कृपया खिलाड़ी का नाम दर्ज करें।",
        "kn": "ದಯವಿಟ್ಟು ಆಟಗಾರನ ಹೆಸರನ್ನು ನಮೂದಿಸಿ.",
    },
    "title is required": {
        "en": "title is required",
        "pt": "o título é obrigatório",
        "it": "il titolo è obbligatorio",
        "es": "el título es obligatorio",
        "fr": "le titre est obligatoire",
        "el": "ο τίτλος είναι υποχρεωτικός",
        "ru": "название обязательно",
        "hi": "शीर्षक आवश्यक है",
        "kn": "ಶೀರ್ಷಿಕೆ ಅಗತ್ಯವಿದೆ",
    },
    "wrong captcha": {
        "en": "wrong captcha",
        "pt": "captcha incorreto",
        "it": "captcha errato",
        "es": "captcha incorrecto",
        "fr": "captcha incorrect",
        "el": "εσφαλμένο captcha",
        "ru": "неверная капча",
        "hi": "गलत कैप्चा",
        "kn": "ತಪ್ಪು ಕ್ಯಾಪ್ಚಾ",
    },
    "wrong password": {
        "en": "wrong password",
        "pt": "palavra-passe incorreta",
        "it": "password errata",
        "es": "contraseña incorrecta",
        "fr": "mot de passe incorrect",
        "el": "εσφαλμένος κωδικός",
        "ru": "неверный пароль",
        "hi": "गलत पासवर्ड",
        "kn": "ತಪ್ಪು ಪಾಸ್‌ವರ್ಡ್",
    },
    "Game not found.": {
        "en": "Game not found.",
        "pt": "Jogo não encontrado.",
        "it": "Partita non trovata.",
        "es": "Partida no encontrada.",
        "fr": "Partie non trouvée.",
        "el": "Το παιχνίδι δεν βρέθηκε.",
        "ru": "Игра не найдена.",
        "hi": "खेल नहीं मिला।",
        "kn": "ಆಟ ಕಂಡುಬಂದಿಲ್ಲ.",
    },
    "Game room does not exist.": {
        "en": "Game room does not exist.",
        "pt": "A sala de jogo não existe.",
        "it": "La stanza di gioco non esiste.",
        "es": "La sala de juego no existe.",
        "fr": "Le salon de jeu n'existe pas.",
        "el": "Η αίθουσα παιχνιδιού δεν υπάρχει.",
        "ru": "Игровая комната не существует.",
        "hi": "गेम रूम मौजूद नहीं है।",
        "kn": "ಆಟದ ಕೊಠಡಿ ಅಸ್ತಿತ್ವದಲ್ಲಿಲ್ಲ.",
    },
    "Invalid Game Master secret key.": {
        "en": "Invalid Game Master secret key.",
        "pt": "Chave secreta do Mestre inválida.",
        "it": "Chiave segreta del Game Master non valida.",
        "es": "Clave secreta del Game Master no válida.",
        "fr": "Clé secrète du Maître du Jeu non valide.",
        "el": "Μη έγκυρο μυστικό κλειδί Αφηγητή.",
        "ru": "Неверный секретный ключ Ведущего.",
        "hi": "अमान्य गेम मास्टर गुप्त कुंजी।",
        "kn": "ಅಮಾನ್ಯ ಗೇಮ್ ಮಾಸ್ಟರ್ ರಹಸ್ಯ ಕೀಲಿ.",
    },
}


def _escape_po_string(s: str) -> str:
    """Escape backslashes and double quotes for .po formatting."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def compile_dict_to_mo(entries: dict[str, str], mo_path: Path):
    """Pure-Python compiler producing binary .mo files conforming to GNU gettext specs."""
    keys = sorted(entries.keys())
    num_strings = len(keys)
    orig_table_offset = 28
    trans_table_offset = orig_table_offset + num_strings * 8
    strings_start = trans_table_offset + num_strings * 8

    orig_indices = []
    trans_indices = []
    orig_data = bytearray()
    trans_data = bytearray()

    cur_offset = strings_start
    for k in keys:
        k_bytes = k.encode("utf-8") + b"\x00"
        orig_indices.append((len(k_bytes) - 1, cur_offset))
        orig_data.extend(k_bytes)
        cur_offset += len(k_bytes)

    for k in keys:
        v_bytes = entries[k].encode("utf-8") + b"\x00"
        trans_indices.append((len(v_bytes) - 1, cur_offset))
        trans_data.extend(v_bytes)
        cur_offset += len(v_bytes)

    with open(mo_path, "wb") as f:
        # Header: magic, format_rev, num_strings, orig_table_offset, trans_table_offset, hash_table_size, hash_table_offset
        f.write(struct.pack("<7I", 0x950412DE, 0, num_strings, orig_table_offset, trans_table_offset, 0, 0))
        for length, offset in orig_indices:
            f.write(struct.pack("<2I", length, offset))
        for length, offset in trans_indices:
            f.write(struct.pack("<2I", length, offset))
        f.write(orig_data)
        f.write(trans_data)


def generate_all_locales():
    """Write .po files and compile them into .mo files for all supported languages."""
    # Find msgfmt binary if present in nix store or PATH
    msgfmt_bin = shutil.which("msgfmt")
    if not msgfmt_bin:
        for candidate in [
            "/nix/store/sz6wx51pnm4dpcliyysd27i0jqywm15x-gettext-0.22.5/bin/msgfmt",
            "/nix/store/sal5l525psrrii8w1c9dhznb8sdajl30-gettext-1.0/bin/msgfmt",
        ]:
            if os.path.exists(candidate):
                msgfmt_bin = candidate
                break

    for lang in LANGUAGES:
        po_dir = LOCALE_DIR / lang / "LC_MESSAGES"
        po_dir.mkdir(parents=True, exist_ok=True)
        po_file = po_dir / "django.po"
        mo_file = po_dir / "django.mo"

        header = [
            'msgid ""',
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Content-Transfer-Encoding: 8bit\\n"',
            f'"Language: {lang}\\n"',
            '"MIME-Version: 1.0\\n"',
            "",
        ]

        mo_dict = {"": f"Content-Type: text/plain; charset=UTF-8\nContent-Transfer-Encoding: 8bit\nLanguage: {lang}\nMIME-Version: 1.0\n"}

        lines = list(header)
        for msgid, trans_dict in TRANSLATIONS.items():
            msgstr = trans_dict.get(lang, trans_dict.get("en", msgid))
            lines.append(f'msgid "{_escape_po_string(msgid)}"')
            lines.append(f'msgstr "{_escape_po_string(msgstr)}"')
            lines.append("")
            mo_dict[msgid] = msgstr

        po_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"Generated {po_file}")

        # Always write standard pure-Python compiled .mo
        compile_dict_to_mo(mo_dict, mo_file)
        print(f"Compiled native {mo_file}")

        # If GNU msgfmt is available, compile with GNU msgfmt as well
        if msgfmt_bin:
            try:
                subprocess.run(
                    [msgfmt_bin, "-o", str(mo_file), str(po_file)],
                    check=True,
                    capture_output=True,
                )
                print(f"Verified GNU msgfmt {mo_file}")
            except Exception as e:
                print(f"GNU msgfmt warning: {e}")


if __name__ == "__main__":
    generate_all_locales()
