*** Settings ***
Documentation     Lupus Internationalization (i18n) & Multi-Language Simulation Suite
...               Verifies presentation boundary localization across all 9 supported
...               languages (en, pt, it, es, fr, el, ru, hi, kn) while strictly proving
...               that engine rules, state dictionaries, and action tapes remain in English.
Library           tests.robot.lupus.LupusLibrary

*** Test Cases ***
Simultaneous Multi-Language Player Views In Active Match
    [Documentation]    Players in the same game viewing the board in Portuguese, Italian, Spanish, French, Russian, Greek, Hindi, and Kannada simultaneously see localized roles and statuses while game state remains English.
    Given A New Game    code=I18N01    limbo_enabled=${FALSE}
    And Player Joins As    Joao       role=werewolf
    And Player Joins As    Marco      role=detective
    And Player Joins As    Elena      role=doctor
    And Player Joins As    Pierre     role=bodyguard
    And Player Joins As    Dmitry     role=sniper
    And Player Joins As    Nikos      role=mayor
    And Player Joins As    Aarav      role=witch
    And Player Joins As    Suresh     role=villager
    When Game Starts
    And Night Falls

    # Canonical Engine Verification (100% English)
    Then Player Role Should Be      Joao      werewolf
    And Player Role Should Be       Marco     detective
    And Player Role Should Be       Elena     doctor
    And Player Role Should Be       Pierre    bodyguard
    And Player Role Should Be       Dmitry    sniper
    And Player Role Should Be       Nikos     mayor
    And Player Role Should Be       Aarav     witch
    And Player Role Should Be       Suresh    villager
    And Player Status Should Be     Joao      alive
    And Player Status Should Be     Marco     alive

    # Presentation Boundary Localization Verification
    # Portuguese (pt)
    And Player View Role Name Should Be        Joao      Lobisomem      lang=pt
    And Player View Status Display Should Be    Joao      Vivo           lang=pt
    And Player View Phase Display Should Be     Joao      Noite          lang=pt
    And Player View UI String Should Be         Joao      hold_to_peek   Segure para espiar o papel secreto    lang=pt

    # Italian (it)
    And Player View Role Name Should Be        Marco     Detective / Veggente    lang=it
    And Player View Status Display Should Be    Marco     Vivo                    lang=it
    And Player View Phase Display Should Be     Marco     Notte                   lang=it
    And Player View UI String Should Be         Marco     hold_to_peek            Tieni premuto per vedere il ruolo segreto    lang=it

    # Spanish (es)
    And Player View Role Name Should Be        Elena     Médico         lang=es
    And Player View Status Display Should Be    Elena     Vivo           lang=es
    And Player View Phase Display Should Be     Elena     Noche          lang=es
    And Player View UI String Should Be         Elena     hold_to_peek   Mantén presionado para ver tu rol    lang=es

    # French (fr)
    And Player View Role Name Should Be        Pierre    Garde du Corps    lang=fr
    And Player View Status Display Should Be    Pierre    Vivant            lang=fr
    And Player View Phase Display Should Be     Pierre    Nuit              lang=fr
    And Player View UI String Should Be         Pierre    hold_to_peek      Maintenez pour voir votre rôle secret    lang=fr

    # Russian (ru)
    And Player View Role Name Should Be        Dmitry    Снайпер / Стрелок        lang=ru
    And Player View Status Display Should Be    Dmitry    Жив            lang=ru
    And Player View Phase Display Should Be     Dmitry    Ночь           lang=ru
    And Player View UI String Should Be         Dmitry    hold_to_peek   Удерживайте, чтобы увидеть секретную роль    lang=ru

    # Greek (el)
    And Player View Role Name Should Be        Nikos     Δήμαρχος       lang=el
    And Player View Status Display Should Be    Nikos     Ζωντανός       lang=el
    And Player View Phase Display Should Be     Nikos     Νύχτα          lang=el
    And Player View UI String Should Be         Nikos     hold_to_peek   Κρατήστε πατημένο για να δείτε τον ρόλο    lang=el

    # Hindi (hi)
    And Player View Role Name Should Be        Aarav     जादूगरनी / डायन    lang=hi
    And Player View Status Display Should Be    Aarav     जीवित              lang=hi
    And Player View Phase Display Should Be     Aarav     रात                lang=hi
    And Player View UI String Should Be         Aarav     hold_to_peek       गुप्त भूमिका देखने के लिए दबाकर रखें    lang=hi

    # Kannada (kn)
    And Player View Role Name Should Be        Suresh    ಗ್ರಾಮಸ್ಥ         lang=kn
    And Player View Status Display Should Be    Suresh    ಜೀವಂತ          lang=kn
    And Player View Phase Display Should Be     Suresh    ರಾತ್ರಿ          lang=kn
    And Player View UI String Should Be         Suresh    hold_to_peek   ರಹಸ್ಯ ಪಾತ್ರವನ್ನು ನೋಡಲು ಒತ್ತಿಹಿಡಿಯಿರಿ    lang=kn

Dynamic Language Preference Switching Preserves Game State
    [Documentation]    Switching languages on the fly updates presentation strings without altering the underlying game engine.
    Given A New Game    code=I18N02    limbo_enabled=${FALSE}
    And Player Joins As    Carlos    role=werewolf
    And Player Joins As    Maria     role=villager
    When Game Starts
    And Night Falls

    # Default English
    Then Player View Role Name Should Be       Carlos    Werewolf    lang=en
    And Player View Phase Display Should Be    Carlos    Night       lang=en

    # Dynamic switch to Portuguese
    Then Player View Role Name Should Be       Carlos    Lobisomem    lang=pt
    And Player View Phase Display Should Be    Carlos    Noite        lang=pt

    # Dynamic switch to Italian
    Then Player View Role Name Should Be       Carlos    Lupo Mannaro    lang=it
    And Player View Phase Display Should Be    Carlos    Notte           lang=it

    # Verify underlying engine role and phase remained untouched
    Then Player Role Should Be    Carlos    werewolf
    And Player Status Should Be   Carlos    alive

Eliminated Player Status And Day Voting Phase Localization
    [Documentation]    When a player is eliminated, their status display updates across languages while preserving canonical dead status.
    Given A New Game    code=I18N03    limbo_enabled=${FALSE}
    And Player Joins As    Wolf      role=werewolf
    And Player Joins As    Victim    role=villager
    And Player Joins As    Voter     role=villager
    When Game Starts
    And Night Falls
    And Wolves Attack    Victim
    And Night Resolves

    # Victim is dead in engine
    Then Player Status Should Be    Victim    dead

    # Localized status displays for dead player
    And Player View Status Display Should Be    Victim    Morto     lang=pt
    And Player View Status Display Should Be    Victim    Morto     lang=it
    And Player View Status Display Should Be    Victim    Muerto    lang=es
    And Player View Status Display Should Be    Victim    Mort      lang=fr
    And Player View Status Display Should Be    Victim    Мёртв     lang=ru
    And Player View Status Display Should Be    Victim    Νεκρός    lang=el
    And Player View Status Display Should Be    Victim    मृत       lang=hi
    And Player View Status Display Should Be    Victim    ಮೃತ       lang=kn

    # Transition to Day Voting
    When Day Voting Begins
    Then Player View Phase Display Should Be    Voter    Votação do Dia         lang=pt
    And Player View Phase Display Should Be     Voter    Votazione del Giorno   lang=it
    And Player View Phase Display Should Be     Voter    Vote du Jour           lang=fr
    And Player View Phase Display Should Be     Voter    Votación del Día       lang=es
    And Player View Phase Display Should Be     Voter    Дневное голосование    lang=ru
    And Player View Phase Display Should Be     Voter    दिन का मतदान           lang=hi
    And Player View Phase Display Should Be     Voter    ಹಗಲಿನ ಮತದಾನ             lang=kn

Game Rooms And Lupus Landing Hub Pages Presentation Localization
    [Documentation]    Game rooms hub (/games/), Lupus active rooms hub (/games/lupus/), and room creation (/games/lupus/create/) dynamically render localized text across all 9 supported languages.
    # /games/ Hub
    Then Game Rooms Hub Content Should Contain    Game Rooms             lang=en
    And Game Rooms Hub Content Should Contain     Salas de Jogos         lang=pt
    And Game Rooms Hub Content Should Contain     Sale Giochi            lang=it
    And Game Rooms Hub Content Should Contain     Salas de Juegos        lang=es
    And Game Rooms Hub Content Should Contain     Salons de Jeux         lang=fr
    And Game Rooms Hub Content Should Contain     Αίθουσες Παιχνιδιών    lang=el
    And Game Rooms Hub Content Should Contain     Игровые комнаты        lang=ru
    And Game Rooms Hub Content Should Contain     गेम रूम                lang=hi
    And Game Rooms Hub Content Should Contain     ಆಟದ ಕೊಠಡಿಗಳು           lang=kn

    # /games/lupus/ Hub
    Then Lupus Hub Content Should Contain         Active Lupus Rooms      lang=en
    And Lupus Hub Content Should Contain          Salas Ativas de Lupus   lang=pt
    And Lupus Hub Content Should Contain          Stanze Lupus Attive     lang=it
    And Lupus Hub Content Should Contain          Salas Activas de Lupus    lang=es
    And Lupus Hub Content Should Contain          Salons Lupus Actifs     lang=fr
    And Lupus Hub Content Should Contain          Ενεργές Αίθουσες Lupus    lang=el
    And Lupus Hub Content Should Contain          Активные комнаты Lupus    lang=ru
    And Lupus Hub Content Should Contain          सक्रिय लुपस कमरे        lang=hi
    And Lupus Hub Content Should Contain          ಸಕ್ರಿಯ ಲೂಪಸ್ ಕೊಠಡಿಗಳು   lang=kn

    # /games/lupus/create/ Page
    Then Lupus Create Content Should Contain      Create Lupus / Werewolf Room    lang=en
    And Lupus Create Content Should Contain       Criar Sala de Lupus / Lobisomem    lang=pt
    And Lupus Create Content Should Contain       Crea Stanza Lupus / Licantropo    lang=it
    And Lupus Create Content Should Contain       Crear Sala de Lupus / Hombre Lobo    lang=es
    And Lupus Create Content Should Contain       Créer un Salon Lupus / Loup-Garou    lang=fr
    And Lupus Create Content Should Contain       Δημιουργία Αίθουσας Lupus / Λυκάνθρωπου    lang=el
    And Lupus Create Content Should Contain       Создать комнату Lupus / Оборотни    lang=ru
    And Lupus Create Content Should Contain       लुपस / वेयरवोल्फ कमरा बनाएं    lang=hi
    And Lupus Create Content Should Contain       ಲೂಪಸ್ / ತೋಳಮಾನವ ಕೊಠಡಿ ರಚಿಸಿ    lang=kn

