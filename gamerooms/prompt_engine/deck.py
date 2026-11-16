"""Pre-seeded, curated gold prompt deck for party games ('Don't Say the Same Thing as Me', Stop!).

Every prompt is verified for:
1. Coherent linguistic frame (<mod1> <thing> that <action> <article> <mod2> <limiters>).
2. Cardinality 5 <= N <= 35 (guaranteeing both common and obscure valid answers).
3. Instant offline gameplay with zero LLM latency.
4. Rich sample answers and obscurity examples.
"""

from typing import Any

GOLD_PROMPTS: tuple[dict[str, Any], ...] = (
    # =========================================================================
    # GEOGRAPHY & PLACES (geo)
    # =========================================================================
    {
        "id": "geo_01",
        "pack": "geo",
        "text": "European country that borders at least 3 other countries",
        "translations": {
            "pt": "País europeu que faz fronteira com pelo menos 3 outros países",
            "es": "País europeo que limita con al menos 3 otros países",
            "it": "Paese europeo che confina con almeno 3 altri paesi",
            "fr": "Pays européen qui borde au moins 3 autres pays",
            "de": "Europäisches Land, das an mindestens 3 andere Länder grenzt",
        },
        "sample_answers": ["France", "Germany", "Austria", "Switzerland", "Poland", "Italy", "Spain", "Belgium", "Ukraine", "Czech Republic", "Slovakia", "Hungary", "Romania", "Serbia", "Croatia", "Slovenia"],
        "obscurity_examples": ["Slovakia", "Liechtenstein", "Luxembourg", "North Macedonia"],
        "cardinality": 24,
    },
    {
        "id": "geo_02",
        "pack": "geo",
        "text": "South American country that has a coastline on an ocean",
        "translations": {
            "pt": "País da América do Sul banhado por um oceano",
            "es": "País sudamericano con costa en un océano",
            "it": "Paese sudamericano bagnato da un oceano",
            "fr": "Pays d'Amérique du Sud bordé par un océan",
            "de": "Südamerikanisches Land mit einer Küste an einem Ozean",
        },
        "sample_answers": ["Brazil", "Argentina", "Chile", "Peru", "Colombia", "Venezuela", "Ecuador", "Uruguay", "Guyana", "Suriname"],
        "obscurity_examples": ["Suriname", "Guyana", "Uruguay"],
        "cardinality": 10,
    },
    {
        "id": "geo_03",
        "pack": "geo",
        "text": "World capital city that starts with a vowel (A, E, I, O, U)",
        "translations": {
            "pt": "Capital mundial que começa com uma vogal (A, E, I, O, U)",
            "es": "Capital mundial que empieza por vocal (A, E, I, O, U)",
            "it": "Capitale del mondo che inizia con una vocale (A, E, I, O, U)",
            "fr": "Capitale mondiale qui commence par une voyelle (A, E, I, O, U)",
            "de": "Hauptstadt der Welt, die mit einem Vokal (A, E, I, O, U) beginnt",
        },
        "sample_answers": ["Amsterdam", "Athens", "Ankara", "Algiers", "Amman", "Ashgabat", "Asmara", "Astana", "Asunción", "Abu Dhabi", "Oslo", "Ottawa", "Ulaanbaatar"],
        "obscurity_examples": ["Ulaanbaatar", "Ashgabat", "Asmara", "Antananarivo"],
        "cardinality": 20,
    },
    {
        "id": "geo_04",
        "pack": "geo",
        "text": "Island nation that is located in the Pacific or Indian Ocean",
        "translations": {
            "pt": "País insular localizado no Oceano Pacífico ou Índico",
            "es": "Nación insular ubicada en el Océano Pacífico o Índico",
            "it": "Nazione insulare situata nell'Oceano Pacifico o Indiano",
            "fr": "Nation insulaire située dans l'océan Pacifique ou Indien",
            "de": "Inselstaat im Pazifischen oder Indischen Ozean",
        },
        "sample_answers": ["Japan", "New Zealand", "Fiji", "Madagascar", "Mauritius", "Maldives", "Seychelles", "Samoa", "Tonga", "Vanuatu", "Papua New Guinea", "Philippines", "Sri Lanka"],
        "obscurity_examples": ["Vanuatu", "Tuvalu", "Nauru", "Kiribati", "Comoros"],
        "cardinality": 25,
    },
    {
        "id": "geo_05",
        "pack": "geo",
        "text": "Coastal city located along the Mediterranean Sea",
        "translations": {
            "pt": "Cidade costeira localizada ao longo do Mar Mediterrâneo",
            "es": "Ciudad costera situada a orillas del Mar Mediterráneo",
            "it": "Città costiera situata lungo il Mar Mediterraneo",
            "fr": "Ville côtière située au bord de la mer Méditerranée",
            "de": "Küstenstadt am Mittelmeer",
        },
        "sample_answers": ["Barcelona", "Marseille", "Nice", "Rome", "Naples", "Venice", "Valencia", "Athens", "Alexandria", "Beirut", "Tel Aviv", "Split", "Dubrovnik", "Palermo", "Tunis"],
        "obscurity_examples": ["Dubrovnik", "Split", "Antalya", "Tripoli"],
        "cardinality": 30,
    },
    {
        "id": "geo_06",
        "pack": "geo",
        "text": "Landlocked country outside of Europe",
        "translations": {
            "pt": "País sem saída para o mar localizado fora da Europa",
            "es": "País sin salida al mar fuera de Europa",
            "it": "Paese senza sbocco sul mare situato fuori dall'Europa",
            "fr": "Pays sans littoral situé en dehors de l'Europe",
            "de": "Binnenland außerhalb Europas",
        },
        "sample_answers": ["Bolivia", "Paraguay", "Mongolia", "Nepal", "Bhutan", "Chad", "Niger", "Mali", "Uganda", "Rwanda", "Zambia", "Zimbabwe", "Laos", "Afghanistan", "Uzbekistan", "Kazakhstan"],
        "obscurity_examples": ["Bhutan", "Lesotho", "Eswatini", "Laos"],
        "cardinality": 30,
    },

    # =========================================================================
    # POP CULTURE, MOVIES & MEDIA (media)
    # =========================================================================
    {
        "id": "media_01",
        "pack": "media",
        "text": "Animated Disney or Pixar movie that features a non-human main character",
        "translations": {
            "pt": "Filme de animação da Disney ou Pixar com protagonista não humano",
            "es": "Película animada de Disney o Pixar con un protagonista no humano",
            "it": "Film d'animazione Disney o Pixar con protagonista non umano",
            "fr": "Film d'animation Disney ou Pixar avec un personnage principal non humain",
            "de": "Disney- oder Pixar-Animationsfilm mit einer nicht-menschlichen Hauptfigur",
        },
        "sample_answers": ["The Lion King", "Finding Nemo", "Ratatouille", "Cars", "A Bug's Life", "Bambi", "Dumbo", "Zootopia", "WALL-E", "Monsters Inc", "Robin Hood", "Lady and the Tramp", "The Aristocats", "Chicken Little"],
        "obscurity_examples": ["The Great Mouse Detective", "A Bug's Life", "The Rescuers", "Bolt"],
        "cardinality": 28,
    },
    {
        "id": "media_02",
        "pack": "media",
        "text": "Superhero or comic book character that has no natural superhuman powers",
        "translations": {
            "pt": "Super-herói ou personagem de quadrinhos que não tem superpoderes naturais",
            "es": "Superhéroe o personaje de cómic que no tiene superpoderes naturales",
            "it": "Supereroe o personaggio dei fumetti senza superpoteri naturali",
            "fr": "Super-héros ou personnage de BD sans super-pouvoirs naturels",
            "de": "Superheld oder Comicfigur ohne angeborene Superkräfte",
        },
        "sample_answers": ["Batman", "Iron Man", "Hawkeye", "Black Widow", "Green Arrow", "The Punisher", "Robin", "Nightwing", "Batgirl", "Ant-Man", "Catwoman", "War Machine"],
        "obscurity_examples": ["The Question", "Moon Knight", "Kick-Ass", "Rorschach"],
        "cardinality": 18,
    },
    {
        "id": "media_03",
        "pack": "media",
        "text": "Video game franchise that was originally released before the year 2000",
        "translations": {
            "pt": "Franquia de videogame lançada originalmente antes do ano 2000",
            "es": "Franquicia de videojuegos lanzada originalmente antes del año 2000",
            "it": "Serie di videogiochi uscita originariamente prima del 2000",
            "fr": "Franchise de jeux vidéo sortie à l'origine avant l'an 2000",
            "de": "Videospiel-Franchise, das ursprünglich vor dem Jahr 2000 erschien",
        },
        "sample_answers": ["Super Mario", "The Legend of Zelda", "Pokemon", "Sonic the Hedgehog", "Doom", "Final Fantasy", "Resident Evil", "Tomb Raider", "Street Fighter", "Mortal Kombat", "Metal Gear", "Grand Theft Auto", "Crash Bandicoot", "Fallout", "Age of Empires", "Diablo", "Half-Life"],
        "obscurity_examples": ["Earthworm Jim", "Monkey Island", "Chrono Trigger", "Deus Ex"],
        "cardinality": 35,
    },
    {
        "id": "media_04",
        "pack": "media",
        "text": "Movie that features time travel or altering the timeline",
        "translations": {
            "pt": "Filme que envolve viagem no tempo ou alteração da linha temporal",
            "es": "Película que incluye viajes en el tiempo o alterar la línea temporal",
            "it": "Film incentrato sui viaggi nel tempo o sull'alterazione temporale",
            "fr": "Film qui traite de voyage dans le temps ou de modification temporelle",
            "de": "Film, in dem es um Zeitreisen oder die Veränderung der Zeitlinie geht",
        },
        "sample_answers": ["Back to the Future", "The Terminator", "Terminator 2", "Interstellar", "Tenet", "About Time", "Groundhog Day", "Looper", "Edge of Tomorrow", "Avengers: Endgame", "12 Monkeys", "Donnie Darko", "The Butterfly Effect", "Planet of the Apes"],
        "obscurity_examples": ["Primer", "About Time", "Frequency", "Timecrimes"],
        "cardinality": 25,
    },
    {
        "id": "media_05",
        "pack": "media",
        "text": "Legendary music band that has sold over 100 million records",
        "translations": {
            "pt": "Banda lendária que vendeu mais de 100 milhões de discos",
            "es": "Banda legendaria que ha vendido más de 100 millones de discos",
            "it": "Band leggendaria che ha venduto oltre 100 milioni di dischi",
            "fr": "Groupe légendaire ayant vendu plus de 100 millions de disques",
            "de": "Legendäre Band, die über 100 Millionen Tonträger verkauft hat",
        },
        "sample_answers": ["The Beatles", "Queen", "Pink Floyd", "Led Zeppelin", "The Rolling Stones", "AC/DC", "U2", "Metallica", "Eagles", "Fleetwood Mac", "Aerosmith", "Guns N' Roses", "Coldplay", "ABBA", "Bon Jovi"],
        "obscurity_examples": ["Dire Straits", "Scorpions", "Genesis", "Def Leppard"],
        "cardinality": 25,
    },

    # =========================================================================
    # CULINARY & FOOD (food)
    # =========================================================================
    {
        "id": "food_01",
        "pack": "food",
        "text": "Popular Italian dish that does not contain tomato sauce",
        "translations": {
            "pt": "Prato italiano popular que não leva molho de tomate",
            "es": "Plato italiano popular que no lleva salsa de tomate",
            "it": "Piatto italiano popolare che non contiene salsa di pomodoro",
            "fr": "Plat italien populaire qui ne contient pas de sauce tomate",
            "de": "Beliebtes italienisches Gericht, das keine Tomatensauce enthält",
        },
        "sample_answers": ["Carbonara", "Cacio e Pepe", "Risotto alla Milanese", "Fettuccine Alfredo", "Gnocchi al Pesto", "Ossobuco", "Polenta", "Carpaccio", "Vitello Tonnato", "Focaccia", "Tiramisu", "Panna Cotta"],
        "obscurity_examples": ["Cacio e Pepe", "Vitello Tonnato", "Saltimbocca"],
        "cardinality": 20,
    },
    {
        "id": "food_02",
        "pack": "food",
        "text": "Street food or fast food snack that is traditionally eaten with bare hands",
        "translations": {
            "pt": "Comida de rua ou fast-food que se come tradicionalmente com as mãos",
            "es": "Comida callejera o aperitivo que se come tradicionalmente con las manos",
            "it": "Street food o spuntino che si mangia tradizionalmente con le mani",
            "fr": "Encas de rue ou fast-food qui se mange traditionnellement avec les mains",
            "de": "Streetfood oder Fastfood-Snack, den man traditionell mit den Händen isst",
        },
        "sample_answers": ["Tacos", "Burger", "Hot Dog", "Pizza", "Empanada", "Burrito", "Samosa", "Falafel", "Shawarma", "Crepe", "Churros", "Corn on the cob", "Chicken wings", "Spring rolls", "Bao bun"],
        "obscurity_examples": ["Bao bun", "Arancini", "Coxinha", "Pani Puri"],
        "cardinality": 30,
    },
    {
        "id": "food_03",
        "pack": "food",
        "text": "Edible fruit or vegetable that grows underground",
        "translations": {
            "pt": "Fruta, vegetal ou legume comestível que cresce debaixo da terra",
            "es": "Fruta, vegetal o verdura comestible que crece bajo tierra",
            "it": "Frutto, tubero o verdura commestibile che cresce sottoterra",
            "fr": "Fruit ou légume comestible qui pousse sous terre",
            "de": "Essbare Frucht oder Gemüse, das unter der Erde wächst",
        },
        "sample_answers": ["Potato", "Carrot", "Sweet potato", "Onion", "Garlic", "Beetroot", "Radish", "Ginger", "Peanut", "Turnip", "Cassava / Manioc", "Truffle", "Horseradish"],
        "obscurity_examples": ["Truffle", "Jerusalem artichoke", "Parsnip", "Peanut"],
        "cardinality": 20,
    },
    {
        "id": "food_04",
        "pack": "food",
        "text": "Dessert or sweet pastry that features melted or solid chocolate",
        "translations": {
            "pt": "Sobremesa ou doce que leva chocolate derretido ou sólido",
            "es": "Postre o dulce que contiene chocolate derretido o sólido",
            "it": "Dolce o dessert a base di cioccolato fuso o solido",
            "fr": "Dessert ou pâtisserie contenant du chocolat fondu ou solide",
            "de": "Dessert oder süßes Gebäck mit geschmolzener oder fester Schokolade",
        },
        "sample_answers": ["Brownie", "Chocolate Cake", "Fondant au Chocolat / Lava Cake", "Chocolate Mousse", "Éclair", "Pain au Chocolat", "Truffle", "Fudge", "Chocolate Cookie", "Chocolate Donut", "Hot Fudge Sundae", "Profiterole"],
        "obscurity_examples": ["Profiterole", "Sachertorte", "Babka", "Stracciatella"],
        "cardinality": 25,
    },
    {
        "id": "food_05",
        "pack": "food",
        "text": "Fermented food or beverage enjoyed around the world",
        "translations": {
            "pt": "Alimento ou bebida fermentada apreciada pelo mundo",
            "es": "Alimento o bebida fermentada apreciada en todo el mundo",
            "it": "Cibo o bevanda fermentata consumata nel mondo",
            "fr": "Aliment ou boisson fermentée consommée à travers le monde",
            "de": "Fermentiertes Lebensmittel oder Getränk aus aller Welt",
        },
        "sample_answers": ["Yogurt", "Cheese", "Beer", "Wine", "Kimchi", "Sauerkraut", "Kombucha", "Miso", "Sourdough bread", "Kefir", "Tempeh", "Soy sauce", "Cider", "Sake"],
        "obscurity_examples": ["Kombucha", "Tempeh", "Natto", "Kefir"],
        "cardinality": 22,
    },

    # =========================================================================
    # NATURE & WILDLIFE (nature)
    # =========================================================================
    {
        "id": "nature_01",
        "pack": "nature",
        "text": "Mammal that lives predominantly in an aquatic or marine environment",
        "translations": {
            "pt": "Mamífero que vive predominantemente em ambiente aquático ou marinho",
            "es": "Mamífero que vive predominantemente en un entorno acuático o marino",
            "it": "Mammifero che vive prevalentemente in ambiente acquatico o marino",
            "fr": "Mammifère qui vit principalement dans un environnement aquatique ou marin",
            "de": "Säugetier, das überwiegend im Wasser oder Meer lebt",
        },
        "sample_answers": ["Dolphin", "Blue Whale", "Orca / Killer Whale", "Seal", "Sea Lion", "Walrus", "Manatee / Sea Cow", "Sea Otter", "Humpback Whale", "Beluga Whale", "Narwhal", "Platypus", "Hippo"],
        "obscurity_examples": ["Narwhal", "Dugong", "Capybara", "Platypus"],
        "cardinality": 20,
    },
    {
        "id": "nature_02",
        "pack": "nature",
        "text": "Carnivorous predator native to the African continent",
        "translations": {
            "pt": "Predador carnívoro nativo do continente africano",
            "es": "Depredador carnívoro nativo del continente africano",
            "it": "Predatore carnivoro originario del continente africano",
            "fr": "Prédateur carnivore originaire du continent africain",
            "de": "Fleischfressendes Raubtier, das auf dem afrikanischen Kontinent beheimatet ist",
        },
        "sample_answers": ["Lion", "Cheetah", "Leopard", "Spotted Hyena", "Nile Crocodile", "African Wild Dog", "Black Mamba", "Caracal", "Serval", "Jackal", "Honey Badger"],
        "obscurity_examples": ["Caracal", "Serval", "Honey Badger", "Aardwolf"],
        "cardinality": 18,
    },
    {
        "id": "nature_03",
        "pack": "nature",
        "text": "Bird species that is physically incapable of flight",
        "translations": {
            "pt": "Espécie de ave que é incapaz de voar",
            "es": "Especie de ave físicamente incapaz de volar",
            "it": "Specie di uccello incapace di volare",
            "fr": "Espèce d'oiseau incapable de voler",
            "de": "Vogelart, die physisch flugunfähig ist",
        },
        "sample_answers": ["Penguin", "Ostrich", "Emu", "Kiwi", "Cassowary", "Rhea", "Kakapo", "Steamer duck", "Takahe", "Dodo"],
        "obscurity_examples": ["Kakapo", "Takahe", "Cassowary", "Rhea"],
        "cardinality": 12,
    },
    {
        "id": "nature_04",
        "pack": "nature",
        "text": "Animal that has noticeable and distinctive stripes or spots on its body",
        "translations": {
            "pt": "Animal com listras ou manchas marcantes e características no corpo",
            "es": "Animal con rayas o manchas llamativas y distintivas en su cuerpo",
            "it": "Animale con evidenti strisce o macchie sul corpo",
            "fr": "Animal ayant des rayures ou des taches distinctives sur le corps",
            "de": "Tier mit auffälligen Streifen oder Flecken auf dem Körper",
        },
        "sample_answers": ["Zebra", "Tiger", "Giraffe", "Leopard", "Cheetah", "Dalmatian", "Jaguar", "Hyena", "Okapi", "Clownfish", "Skunk", "Poison dart frog", "Ladybug"],
        "obscurity_examples": ["Okapi", "Bongo", "Quagga", "Numbat"],
        "cardinality": 25,
    },

    # =========================================================================
    # HISTORY & INVENTIONS (history)
    # =========================================================================
    {
        "id": "history_01",
        "pack": "history",
        "text": "Scientific invention that was created during the 19th century (1801-1900)",
        "translations": {
            "pt": "Invenção científica criada durante o século XIX (1801-1900)",
            "es": "Invento científico creado durante el siglo XIX (1801-1900)",
            "it": "Invenzione scientifica nata nel XIX secolo (1801-1900)",
            "fr": "Invention scientifique créée au XIXe siècle (1801-1900)",
            "de": "Wissenschaftliche Erfindung aus dem 19. Jahrhundert (1801-1900)",
        },
        "sample_answers": ["Telephone", "Light bulb", "Steam locomotive", "Photography / Camera", "Bicycle", "Typewriter", "Internal combustion engine", "Radio / Telegraph", "Dynamite", "Battery", "Anesthesia", "Sewing machine", "Phonograph"],
        "obscurity_examples": ["Stethoscope", "Braille", "Dynamite", "Bunsen burner"],
        "cardinality": 26,
    },
    {
        "id": "history_02",
        "pack": "history",
        "text": "Ancient empire or civilization that ruled territories around the Mediterranean",
        "translations": {
            "pt": "Império ou civilização antiga que dominou territórios no Mediterrâneo",
            "es": "Imperio o civilización antigua que dominó territorios en el Mediterráneo",
            "it": "Impero o civiltà antica che dominò territori attorno al Mediterraneo",
            "fr": "Empire ou civilisation antique ayant régné autour de la Méditerranée",
            "de": "Antikes Reich oder Zivilisation rund um das Mittelmeer",
        },
        "sample_answers": ["Roman Empire", "Ancient Greece", "Ancient Egypt", "Carthaginian Empire", "Phoenicians", "Persian Empire / Achaemenid", "Byzantine Empire", "Ottoman Empire", "Macedonian Empire", "Umayyad Caliphate"],
        "obscurity_examples": ["Etruscans", "Minoans", "Hittites", "Numidia"],
        "cardinality": 18,
    },
    {
        "id": "history_03",
        "pack": "history",
        "text": "Famous historical explorer or navigator who traveled to another continent",
        "translations": {
            "pt": "Explorador ou navegador histórico que viajou para outro continente",
            "es": "Explorador o navegante histórico que viajó a otro continente",
            "it": "Esploratore o navigatore storico che viaggiò in un altro continente",
            "fr": "Explorateur ou navigateur historique ayant voyagé vers un autre continent",
            "de": "Berühmter historischer Entdecker oder Seefahrer, der einen anderen Kontinent bereiste",
        },
        "sample_answers": ["Christopher Columbus", "Vasco da Gama", "Ferdinand Magellan", "Marco Polo", "James Cook", "Ibn Battuta", "Pedro Alvares Cabral", "Amerigo Vespucci", "Roald Amundsen", "Zheng He", "Francis Drake", "Leif Erikson", "Hernan Cortes"],
        "obscurity_examples": ["Ibn Battuta", "Zheng He", "Vitus Bering", "Bartolomeu Dias"],
        "cardinality": 22,
    },

    # =========================================================================
    # QUIRKY & FUN EVERYDAY (weird)
    # =========================================================================
    {
        "id": "weird_01",
        "pack": "weird",
        "text": "Object you would grab first if your house caught fire",
        "translations": {
            "pt": "Objeto que você pegaria primeiro se sua casa pegasse fogo",
            "es": "Objeto que agarrarías primero si tu casa se incendiara",
            "it": "Oggetto che prenderesti per primo se la tua casa prendesse fuoco",
            "fr": "Objet que vous attraperiez en premier si votre maison prenait feu",
            "de": "Gegenstand, den man zuerst greifen würde, wenn das Haus brennt",
        },
        "sample_answers": ["Smartphone / Phone", "Passport", "Wallet / Money", "Laptop / Computer", "Keys", "Hard drive / Backup", "Family photos", "Pet leash / carrier", "Coat / Shoes", "Medicine"],
        "obscurity_examples": ["Guitar", "Jewelry box", "Glasses", "Sentimental teddy bear"],
        "cardinality": 20,
    },
    {
        "id": "weird_02",
        "pack": "weird",
        "text": "Everyday object that costs under 10 euros or dollars and fits in your pocket",
        "translations": {
            "pt": "Objeto do cotidiano que custa menos de 10 euros ou dólares e cabe no bolso",
            "es": "Objeto cotidiano que cuesta menos de 10 euros o dólares y cabe en el bolsillo",
            "it": "Oggetto quotidiano da meno di 10 euro o dollari che sta in tasca",
            "fr": "Objet du quotidien à moins de 10 euros ou dollars qui rentre dans une poche",
            "de": "Alltagsgegenstand für unter 10 Euro oder Dollar, der in die Hosentasche passt",
        },
        "sample_answers": ["Lighter", "Ballpoint pen", "Lip balm", "Chewing gum", "USB stick", "Pack of tissues", "Coin", "Hair tie", "Earplugs", "Guitar pick", "Keyring", "Hand sanitizer"],
        "obscurity_examples": ["Guitar pick", "Nail clippers", "Safety pin", "Floss"],
        "cardinality": 30,
    },
    {
        "id": "weird_03",
        "pack": "weird",
        "text": "Household appliance or tool that makes a very loud noise when operated",
        "translations": {
            "pt": "Eletrodoméstico ou ferramenta doméstica que faz muito barulho quando ligado",
            "es": "Electrodoméstico o herramienta del hogar que hace mucho ruido al usarse",
            "it": "Elettrodomestico o attrezzo domestico molto rumoroso quando in funzione",
            "fr": "Appareil ménager ou outil qui fait beaucoup de bruit lorsqu'il fonctionne",
            "de": "Haushaltsgerät oder Werkzeug, das im Betrieb sehr laut ist",
        },
        "sample_answers": ["Vacuum cleaner", "Blender", "Hairdryer", "Lawnmower", "Power drill", "Food processor", "Washing machine (spin cycle)", "Chainsaw", "Smoke alarm", "Pressure washer"],
        "obscurity_examples": ["Coffee bean grinder", "Leaf blower", "Pressure washer", "Meat slicer"],
        "cardinality": 18,
    },
    {
        "id": "weird_04",
        "pack": "weird",
        "text": "Board game or party game that ruins friendships when people play it",
        "translations": {
            "pt": "Jogo de tabuleiro ou de festa que estraga amizades quando se joga",
            "es": "Juego de mesa o de fiesta que arruina amistades cuando se juega",
            "it": "Gioco da tavolo o di società che rovina le amicizie quando si gioca",
            "fr": "Jeu de société ou d'ambiance qui ruine les amitiés quand on y joue",
            "de": "Brettspiel oder Partyspiel, das Freundschaften zerstört",
        },
        "sample_answers": ["Monopoly", "Uno", "Risk", "Catan / Settlers of Catan", "Mario Party", "Among Us", "Secret Hitler", "Lupus in Tabula / Werewolf", "Diplomacy", "Scrabble"],
        "obscurity_examples": ["Diplomacy", "Cosmic Encounter", "The Resistance", "Codenames"],
        "cardinality": 15,
    },
)


def get_curated_deck(pack: str = "mix") -> list[dict[str, Any]]:
    """Return all curated gold prompts filtered by pack."""
    if pack == "mix" or not pack:
        return list(GOLD_PROMPTS)
    return [p for p in GOLD_PROMPTS if p.get("pack") == pack]
