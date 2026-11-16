"""Linguistic Semantic Frames for combinatorial prompt synthesis.

Adheres to the Fillmore Frame Semantics schema:
[<mod1>] <thing> that <action> [<article>] [<mod2>] <target> [<limiters>]

Designed to be reusable across 'Don't Say the Same Thing as Me', Stop!,
and party trivia games.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubjectSlot:
    mod1: str
    thing: str
    translations: dict[str, str] = field(default_factory=dict)
    # tags for semantic consistency checks
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionSlot:
    relativizer: str  # "that", "who", "which"
    action: str  # verb phrase e.g. "borders", "was directed by"
    translations: dict[str, str] = field(default_factory=dict)
    compatible_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class TargetSlot:
    article: str  # "a", "an", "the", ""
    mod2: str  # adjective/modifier e.g. "more than 3", "melted"
    target: str  # target noun/concept e.g. "countries", "cheese"
    translations: dict[str, str] = field(default_factory=dict)
    compatible_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class LimiterSlot:
    limiter: str  # modifier constraint e.g. "outside of Europe", "before 2000"
    translations: dict[str, str] = field(default_factory=dict)
    compatible_tags: tuple[str, ...] = ()


@dataclass
class SemanticFrame:
    id: str
    category: str  # 'geo', 'media', 'food', 'nature', 'history', 'weird'
    title: str
    subjects: list[SubjectSlot]
    actions: list[ActionSlot]
    targets: list[TargetSlot]
    limiters: list[LimiterSlot]


# ---------------------------------------------------------------------------
# 1. Geography & Places Frame
# ---------------------------------------------------------------------------
GEOGRAPHY_FRAME = SemanticFrame(
    id="frame_geo",
    category="geo",
    title="🌍 Geography, Nations & Cities",
    subjects=[
        SubjectSlot(
            "European",
            "country",
            {"pt": "País europeu", "es": "País europeo", "it": "Paese europeo", "fr": "Pays européen"},
            ("place", "country", "europe"),
        ),
        SubjectSlot(
            "Landlocked",
            "country",
            {
                "pt": "País sem costa marítima",
                "es": "País sin salida al mar",
                "it": "Paese senza sbocco sul mare",
                "fr": "Pays sans littoral",
            },
            ("place", "country", "landlocked"),
        ),
        SubjectSlot(
            "Island",
            "nation",
            {"pt": "País insular", "es": "Nación insular", "it": "Nazione insulare", "fr": "Nation insulaire"},
            ("place", "country", "island"),
        ),
        SubjectSlot(
            "South American",
            "country",
            {
                "pt": "País da América do Sul",
                "es": "País de América del Sur",
                "it": "Paese sudamericano",
                "fr": "Pays d'Amérique du Sud",
            },
            ("place", "country", "south_america"),
        ),
        SubjectSlot(
            "Coastal",
            "city",
            {"pt": "Cidade costeira", "es": "Ciudad costera", "it": "Città costiera", "fr": "Ville côtière"},
            ("place", "city", "coastal"),
        ),
        SubjectSlot(
            "World capital",
            "city",
            {
                "pt": "Capital mundial",
                "es": "Ciudad capital mundial",
                "it": "Città capitale del mondo",
                "fr": "Capitale mondiale",
            },
            ("place", "city", "capital"),
        ),
        SubjectSlot(
            "Famous",
            "mountain range or river",
            {
                "pt": "Cordilheira ou rio famoso",
                "es": "Cordillera o río famoso",
                "it": "Catena montuosa o fiume famoso",
                "fr": "Chaîne de montagnes ou fleuve célèbre",
            },
            ("place", "nature_geo"),
        ),
    ],
    actions=[
        ActionSlot(
            "that",
            "borders",
            {"pt": "que faz fronteira com", "es": "que limita con", "it": "che confina con", "fr": "qui borde"},
            ("place", "country"),
        ),
        ActionSlot(
            "that",
            "has a coastline on",
            {
                "pt": "que é banhado por",
                "es": "que tiene costa en",
                "it": "che si affaccia su",
                "fr": "qui a une côte sur",
            },
            ("place", "country", "coastal"),
        ),
        ActionSlot(
            "that",
            "is located in",
            {"pt": "que fica em", "es": "que se encuentra en", "it": "che si trova in", "fr": "qui se situe en"},
            ("place", "city", "country"),
        ),
        ActionSlot(
            "that",
            "has a population over",
            {"pt": "que tem mais de", "es": "que tiene más de", "it": "che ha oltre", "fr": "qui compte plus de"},
            ("place", "city", "country"),
        ),
        ActionSlot(
            "that",
            "starts with the letter",
            {
                "pt": "que começa com a letra",
                "es": "que empieza con la letra",
                "it": "che inizia con la lettera",
                "fr": "qui commence par la lettre",
            },
            ("place", "country", "city"),
        ),
    ],
    targets=[
        TargetSlot(
            "",
            "more than 3",
            "countries",
            {"pt": "mais de 3 países", "es": "más de 3 países", "it": "più di 3 paesi", "fr": "plus de 3 pays"},
        ),
        TargetSlot(
            "the",
            "Mediterranean",
            "Sea",
            {
                "pt": "o Mar Mediterrâneo",
                "es": "el Mar Mediterráneo",
                "it": "il Mar Mediterraneo",
                "fr": "la mer Méditerranée",
            },
        ),
        TargetSlot(
            "the",
            "Atlantic",
            "Ocean",
            {
                "pt": "o Oceano Atlântico",
                "es": "el Océano Atlántico",
                "it": "l'Oceano Atlantico",
                "fr": "l'océan Atlantique",
            },
        ),
        TargetSlot(
            "the",
            "Southern",
            "Hemisphere",
            {
                "pt": "o Hemisfério Sul",
                "es": "el Hemisferio Sur",
                "it": "l'emisfero australe",
                "fr": "l'hémisphère sud",
            },
        ),
        TargetSlot(
            "",
            "10 million",
            "inhabitants",
            {
                "pt": "10 milhões de habitantes",
                "es": "10 millones de habitantes",
                "it": "10 milioni di abitanti",
                "fr": "10 millions d'habitants",
            },
        ),
        TargetSlot(
            "",
            "",
            "'M', 'S' or 'P'",
            {"pt": "'M', 'S' ou 'P'", "es": "'M', 'S' o 'P'", "it": "'M', 'S' o 'P'", "fr": "'M', 'S' ou 'P'"},
        ),
    ],
    limiters=[
        LimiterSlot(
            "outside of North America",
            {
                "pt": "fora da América do Norte",
                "es": "fuera de América del Norte",
                "it": "fuori dal Nord America",
                "fr": "en dehors de l'Amérique du Nord",
            },
        ),
        LimiterSlot(
            "with a single-word name",
            {
                "pt": "com nome de apenas uma palavra",
                "es": "con nombre de una sola palabra",
                "it": "con nome di una sola parola",
                "fr": "avec un nom en un seul mot",
            },
        ),
        LimiterSlot(
            "that is not a member of the EU",
            {
                "pt": "que não faz parte da União Europeia",
                "es": "que no es miembro de la UE",
                "it": "che non fa parte dell'UE",
                "fr": "qui ne fait pas partie de l'UE",
            },
        ),
        LimiterSlot(
            "in the Americas",
            {"pt": "no continente americano", "es": "en las Américas", "it": "nelle Americhe", "fr": "aux Amériques"},
        ),
    ],
)

# ---------------------------------------------------------------------------
# 2. Pop Culture, Movies & Media Frame
# ---------------------------------------------------------------------------
MEDIA_FRAME = SemanticFrame(
    id="frame_media",
    category="media",
    title="🎬 Pop Culture, Cinema, Series & Games",
    subjects=[
        SubjectSlot(
            "Oscar-winning",
            "movie",
            {
                "pt": "Filme vencedor do Oscar",
                "es": "Película ganadora del Óscar",
                "it": "Film premio Oscar",
                "fr": "Film oscarisé",
            },
            ("media", "film"),
        ),
        SubjectSlot(
            "Animated",
            "feature film",
            {
                "pt": "Filme de animação",
                "es": "Película de animación",
                "it": "Film d'animazione",
                "fr": "Film d'animation",
            },
            ("media", "film", "animation"),
        ),
        SubjectSlot(
            "Classic",
            "video game franchise",
            {
                "pt": "Franquia clássica de videogame",
                "es": "Franquicia clásica de videojuegos",
                "it": "Serie classica di videogiochi",
                "fr": "Franchise classique de jeu vidéo",
            },
            ("media", "game"),
        ),
        SubjectSlot(
            "Popular",
            "sitcom or TV series",
            {
                "pt": "Série de comédia ou TV famosa",
                "es": "Comedia o serie de televisión popular",
                "it": "Serie TV o sitcom popolare",
                "fr": "Série télévisée ou sitcom populaire",
            },
            ("media", "tv"),
        ),
        SubjectSlot(
            "Fictional",
            "superhero or detective",
            {
                "pt": "Super-herói ou detetive fictício",
                "es": "Superhéroe o detective de ficción",
                "it": "Supereroe o detective immaginario",
                "fr": "Super-héros ou détective de fiction",
            },
            ("media", "character"),
        ),
        SubjectSlot(
            "Famous",
            "song or music hit",
            {
                "pt": "Música famosa ou hit musical",
                "es": "Canción famosa o éxito musical",
                "it": "Canzone famosa o hit musicale",
                "fr": "Chanson célèbre ou tube musical",
            },
            ("media", "music"),
        ),
    ],
    actions=[
        ActionSlot(
            "that",
            "features",
            {"pt": "que conta com", "es": "que cuenta con", "it": "che include", "fr": "qui met en scène"},
            ("media",),
        ),
        ActionSlot(
            "that",
            "was released in",
            {
                "pt": "que foi lançado em",
                "es": "que fue lanzado en",
                "it": "che è uscito negli anni",
                "fr": "qui est sorti dans les années",
            },
            ("media",),
        ),
        ActionSlot(
            "that",
            "takes place in",
            {"pt": "que se passa em", "es": "que tiene lugar en", "it": "ambientato in", "fr": "qui se déroule dans"},
            ("media",),
        ),
        ActionSlot(
            "who",
            "fights against",
            {"pt": "que luta contra", "es": "que lucha contra", "it": "che combatte contro", "fr": "qui lutte contre"},
            ("media", "character"),
        ),
        ActionSlot(
            "that",
            "has at least",
            {"pt": "que tem pelo menos", "es": "que tiene al menos", "it": "che ha almeno", "fr": "qui a au moins"},
            ("media",),
        ),
    ],
    targets=[
        TargetSlot(
            "a",
            "talking",
            "animal or robot",
            {
                "pt": "um animal falante ou robô",
                "es": "un animal que habla o robot",
                "it": "un animale parlante o robot",
                "fr": "un animal parlant ou un robot",
            },
        ),
        TargetSlot(
            "the",
            "",
            "1990s or 2000s",
            {
                "pt": "os anos 1990 ou 2000",
                "es": "los años 1990 o 2000",
                "it": "gli anni '90 o 2000",
                "fr": "les années 1990 ou 2000",
            },
        ),
        TargetSlot(
            "a",
            "fictional",
            "alien world or fantasy kingdom",
            {
                "pt": "um mundo alienígena ou reino de fantasia",
                "es": "un mundo alienígena o reino de fantasía",
                "it": "un pianeta alieno o regno fantastico",
                "fr": "un monde extraterrestre ou royaume fantastique",
            },
        ),
        TargetSlot(
            "",
            "iconic",
            "villains or nemeses",
            {
                "pt": "vilões ou rivais lendários",
                "es": "villanos o archienemigos emblemáticos",
                "it": "antagonisti o rivali storici",
                "fr": "des méchants ou rivaux légendaires",
            },
        ),
        TargetSlot(
            "",
            "3 official",
            "sequels or seasons",
            {
                "pt": "3 sequências oficiais ou temporadas",
                "es": "3 secuelas oficiales o temporadas",
                "it": "3 sequel ufficiali o stagioni",
                "fr": "3 suites officielles ou saisons",
            },
        ),
    ],
    limiters=[
        LimiterSlot(
            "without any human protagonist",
            {
                "pt": "sem nenhum protagonista humano",
                "es": "sin protagonista humano",
                "it": "senza un protagonista umano",
                "fr": "sans protagoniste humain",
            },
        ),
        LimiterSlot(
            "with a single-word title",
            {
                "pt": "com título de apenas uma palavra",
                "es": "con título de una sola palabra",
                "it": "con titolo di una sola parola",
                "fr": "avec un titre en un seul mot",
            },
        ),
        LimiterSlot(
            "made by Disney, Pixar or Nintendo",
            {
                "pt": "criado pela Disney, Pixar ou Nintendo",
                "es": "creado por Disney, Pixar o Nintendo",
                "it": "prodotto da Disney, Pixar o Nintendo",
                "fr": "produit par Disney, Pixar ou Nintendo",
            },
        ),
        LimiterSlot(
            "rated PG / family-friendly",
            {
                "pt": "livre para todos os públicos",
                "es": "apto para todos los públicos",
                "it": "per tutta la famiglia",
                "fr": "tout public",
            },
        ),
    ],
)

# ---------------------------------------------------------------------------
# 3. Culinary & Food Frame
# ---------------------------------------------------------------------------
CULINARY_FRAME = SemanticFrame(
    id="frame_food",
    category="food",
    title="🍕 Culinary, Food & Gastronomy",
    subjects=[
        SubjectSlot(
            "Traditional",
            "dish",
            {
                "pt": "Prato tradicional",
                "es": "Plato tradicional",
                "it": "Piatto tradizionale",
                "fr": "Plat traditionnel",
            },
            ("food", "dish"),
        ),
        SubjectSlot(
            "Popular",
            "dessert or pastry",
            {
                "pt": "Sobremesa ou doce famoso",
                "es": "Postre o dulce popular",
                "it": "Dolce o dessert popolare",
                "fr": "Dessert ou pâtisserie populaire",
            },
            ("food", "sweet"),
        ),
        SubjectSlot(
            "Edible",
            "fruit or vegetable",
            {
                "pt": "Fruta ou legume comestível",
                "es": "Fruta o verdura comestible",
                "it": "Frutta o verdura commestibile",
                "fr": "Fruit ou légume comestible",
            },
            ("food", "produce"),
        ),
        SubjectSlot(
            "Common",
            "breakfast item",
            {
                "pt": "Comida comum de café da manhã",
                "es": "Alimento común del desayuno",
                "it": "Cibo tipico da colazione",
                "fr": "Aliment typique du petit-déjeuner",
            },
            ("food", "dish"),
        ),
        SubjectSlot(
            "Street food",
            "snack",
            {
                "pt": "Petisco de comida de rua",
                "es": "Aperitivo de comida callejera",
                "it": "Street food o spuntino",
                "fr": "Encas de cuisine de rue",
            },
            ("food", "snack"),
        ),
        SubjectSlot(
            "Alcoholic or non-alcoholic",
            "beverage",
            {
                "pt": "Bebida alcoólica ou não alcoólica",
                "es": "Bebida alcohólica o sin alcohol",
                "it": "Bevanda alcolica o analcolica",
                "fr": "Boisson avec ou sans alcool",
            },
            ("food", "drink"),
        ),
    ],
    actions=[
        ActionSlot(
            "that",
            "contains or is cooked with",
            {
                "pt": "que contém ou é cozinhado com",
                "es": "que contiene o se cocina con",
                "it": "che contiene o si prepara con",
                "fr": "qui contient ou se cuisine avec",
            },
            ("food",),
        ),
        ActionSlot(
            "that",
            "is traditionally eaten",
            {
                "pt": "que é tradicionalmente comido",
                "es": "que se come tradicionalmente",
                "it": "che si mangia tradizionalmente",
                "fr": "qui se mange traditionnellement",
            },
            ("food",),
        ),
        ActionSlot(
            "that",
            "originates from",
            {"pt": "que é originário de", "es": "que es originario de", "it": "originario di", "fr": "originaire de"},
            ("food",),
        ),
        ActionSlot(
            "that",
            "is served",
            {"pt": "que é servido", "es": "que se sirve", "it": "che viene servito", "fr": "qui est servi"},
            ("food",),
        ),
    ],
    targets=[
        TargetSlot(
            "",
            "melted",
            "cheese",
            {"pt": "queijo derretido", "es": "queso fundido", "it": "formaggio fuso", "fr": "du fromage fondu"},
        ),
        TargetSlot(
            "",
            "fresh",
            "garlic or onion",
            {
                "pt": "alho ou cebola frescos",
                "es": "ajo o cebolla frescos",
                "it": "aglio o cipolla freschi",
                "fr": "de l'ail ou de l'oignon",
            },
        ),
        TargetSlot(
            "",
            "",
            "chocolate or caramel",
            {
                "pt": "chocolate ou caramelo",
                "es": "chocolate o caramelo",
                "it": "cioccolato o caramello",
                "fr": "du chocolat ou caramel",
            },
        ),
        TargetSlot(
            "",
            "warm or boiling",
            "broth or soup",
            {
                "pt": "caldo ou sopa quente",
                "es": "caldo o sopa caliente",
                "it": "brodo o zuppa calda",
                "fr": "un bouillon ou une soupe chaude",
            },
        ),
        TargetSlot(
            "",
            "",
            "Italy, Mexico or Japan",
            {
                "pt": "Itália, México ou Japão",
                "es": "Italia, México o Japón",
                "it": "Italia, Messico o Giappone",
                "fr": "Italie, Mexique ou Japon",
            },
        ),
        TargetSlot(
            "",
            "completely",
            "cold or iced",
            {
                "pt": "completamente gelado ou frio",
                "es": "completamente frío o helado",
                "it": "completamente freddo o ghiacciato",
                "fr": "totalement froid ou glacé",
            },
        ),
    ],
    limiters=[
        LimiterSlot(
            "without any meat or fish (vegetarian)",
            {
                "pt": "sem qualquer carne ou peixe (vegetariano)",
                "es": "sin carne ni pescado (vegetariano)",
                "it": "senza carne né pesce (vegetariano)",
                "fr": "sans viande ni poisson (végétarien)",
            },
        ),
        LimiterSlot(
            "typically eaten with bare hands",
            {
                "pt": "comido tipicamente com as mãos",
                "es": "comido típicamente con las manos",
                "it": "mangiato tipicamente con le mani",
                "fr": "mangé typiquement avec les mains",
            },
        ),
        LimiterSlot(
            "commonly found in fast food joints",
            {
                "pt": "comum em restaurantes de fast-food",
                "es": "común en restaurantes de comida rápida",
                "it": "comune nei fast food",
                "fr": "courant dans les fast-foods",
            },
        ),
        LimiterSlot(
            "baked in an oven",
            {"pt": "assado no forno", "es": "horneado en el horno", "it": "cotto al forno", "fr": "cuit au four"},
        ),
    ],
)

# ---------------------------------------------------------------------------
# 4. Nature & Wildlife Frame
# ---------------------------------------------------------------------------
NATURE_FRAME = SemanticFrame(
    id="frame_nature",
    category="nature",
    title="🐾 Wildlife, Nature & Zoology",
    subjects=[
        SubjectSlot(
            "Warm-blooded",
            "mammal",
            {
                "pt": "Mamífero de sangue quente",
                "es": "Mamífero de sangre caliente",
                "it": "Mammifero a sangue caldo",
                "fr": "Mammifère à sang chaud",
            },
            ("nature", "animal", "mammal"),
        ),
        SubjectSlot(
            "Feathered",
            "bird",
            {"pt": "Ave ou pássaro", "es": "Ave o pájaro", "it": "Uccello", "fr": "Oiseau"},
            ("nature", "animal", "bird"),
        ),
        SubjectSlot(
            "Aquatic or marine",
            "animal",
            {
                "pt": "Animal aquático ou marinho",
                "es": "Animal acuático o marino",
                "it": "Animale acquatico o marino",
                "fr": "Animal aquatique ou marin",
            },
            ("nature", "animal", "marine"),
        ),
        SubjectSlot(
            "Predatory",
            "carnivore",
            {
                "pt": "Predador carnívoro",
                "es": "Depredador carnívoro",
                "it": "Predatore carnivoro",
                "fr": "Prédateur carnivore",
            },
            ("nature", "animal", "carnivore"),
        ),
        SubjectSlot(
            "Exotic",
            "tree or plant",
            {
                "pt": "Árvore ou planta exótica",
                "es": "Árbol o planta exótica",
                "it": "Albero o pianta esotica",
                "fr": "Arbre ou plante exotique",
            },
            ("nature", "plant"),
        ),
    ],
    actions=[
        ActionSlot(
            "that",
            "lives in",
            {"pt": "que vive em", "es": "que vive en", "it": "che vive in", "fr": "qui vit en"},
            ("nature",),
        ),
        ActionSlot(
            "that",
            "is native to",
            {"pt": "que é nativo de", "es": "que es nativo de", "it": "originario di", "fr": "qui est originaire de"},
            ("nature",),
        ),
        ActionSlot(
            "that",
            "feeds primarily on",
            {
                "pt": "que se alimenta principalmente de",
                "es": "que se alimenta principalmente de",
                "it": "che si nutre principalmente di",
                "fr": "qui se nourrit principalement de",
            },
            ("nature",),
        ),
        ActionSlot(
            "that",
            "has noticeable",
            {"pt": "que possui", "es": "que tiene", "it": "che possiede", "fr": "qui possède"},
            ("nature",),
        ),
    ],
    targets=[
        TargetSlot(
            "the",
            "African",
            "savannah or desert",
            {
                "pt": "a savana ou deserto africano",
                "es": "la sabana o desierto africano",
                "it": "la savana o il deserto africano",
                "fr": "la savane ou le désert africain",
            },
        ),
        TargetSlot(
            "the",
            "tropical",
            "rainforest",
            {
                "pt": "a floresta tropical úmida",
                "es": "la selva tropical húmeda",
                "it": "la foresta pluviale tropicale",
                "fr": "la forêt tropicale humide",
            },
        ),
        TargetSlot(
            "",
            "frozen",
            "polar regions",
            {
                "pt": "regiões polares geladas",
                "es": "regiones polares heladas",
                "it": "regioni polari ghiacciate",
                "fr": "des régions polaires glacées",
            },
        ),
        TargetSlot(
            "",
            "insects or small",
            "rodents",
            {
                "pt": "insetos ou pequenos roedores",
                "es": "insectos o pequeños roedores",
                "it": "insetti o piccoli roditori",
                "fr": "des insectes ou petits rongeurs",
            },
        ),
        TargetSlot(
            "",
            "distinctive",
            "stripes or spots",
            {
                "pt": "listras ou manchas características",
                "es": "rayas o manchas distintivas",
                "it": "strisce o macchie evidenti",
                "fr": "des rayures ou taches distinctives",
            },
        ),
    ],
    limiters=[
        LimiterSlot(
            "that cannot fly or swim",
            {
                "pt": "que não consegue voar nem nadar",
                "es": "que no puede volar ni nadar",
                "it": "che non sa volare né nuotare",
                "fr": "qui ne peut ni voler ni nager",
            },
        ),
        LimiterSlot(
            "larger than an average human",
            {
                "pt": "maior que um ser humano adulto",
                "es": "más grande que un humano promedio",
                "it": "più grande di un essere umano medio",
                "fr": "plus grand qu'un être humain",
            },
        ),
        LimiterSlot(
            "active predominantly at night",
            {
                "pt": "com hábitos predominantemente noturnos",
                "es": "activo predominantemente de noche",
                "it": "attivo soprattutto di notte",
                "fr": "actif principalement la nuit",
            },
        ),
        LimiterSlot(
            "found in the wild in South America or Australia",
            {
                "pt": "selvagem na América do Sul ou Austrália",
                "es": "salvaje en Sudamérica o Australia",
                "it": "allo stato selvatico in Sudamerica o Australia",
                "fr": "à l'état sauvage en Amérique du Sud ou Australie",
            },
        ),
    ],
)

# ---------------------------------------------------------------------------
# 5. History & Science Inventions Frame
# ---------------------------------------------------------------------------
HISTORY_FRAME = SemanticFrame(
    id="frame_history",
    category="history",
    title="📜 History, Science & Human Inventions",
    subjects=[
        SubjectSlot(
            "Historical",
            "figure or ruler",
            {
                "pt": "Líder ou figura histórica",
                "es": "Líder o figura histórica",
                "it": "Figura o sovrano storico",
                "fr": "Figure ou souverain historique",
            },
            ("history", "person"),
        ),
        SubjectSlot(
            "Groundbreaking",
            "scientific invention or tool",
            {
                "pt": "Invenção científica ou ferramenta revolucionária",
                "es": "Invento científico o herramienta revolucionaria",
                "it": "Invenzione scientifica o strumento rivoluzionario",
                "fr": "Invention scientifique ou outil révolutionnaire",
            },
            ("history", "invention"),
        ),
        SubjectSlot(
            "Ancient",
            "empire or civilization",
            {
                "pt": "Império ou civilização antiga",
                "es": "Imperio o civilización antigua",
                "it": "Impero o civiltà antica",
                "fr": "Empire ou civilisation antique",
            },
            ("history", "empire"),
        ),
        SubjectSlot(
            "Famous",
            "explorer or navigator",
            {
                "pt": "Explorador ou navegador famoso",
                "es": "Explorador o navegante famoso",
                "it": "Esploratore o navigatore famoso",
                "fr": "Explorateur ou navigateur célèbre",
            },
            ("history", "explorer"),
        ),
    ],
    actions=[
        ActionSlot(
            "who",
            "lived or ruled during",
            {
                "pt": "que viveu ou governou durante",
                "es": "que vivió o gobernó durante",
                "it": "vissuto o salito al potere durante",
                "fr": "qui a vécu ou régné pendant",
            },
            ("history", "person"),
        ),
        ActionSlot(
            "that",
            "was invented or revolutionized during",
            {
                "pt": "que foi inventado ou revolucionado no",
                "es": "que fue inventado o revolucionado en el",
                "it": "inventato o perfezionato nel",
                "fr": "qui a été inventé ou perfectionné au",
            },
            ("history", "invention"),
        ),
        ActionSlot(
            "who",
            "discovered or explored",
            {
                "pt": "que descobriu ou explorou",
                "es": "que descubrió o exploró",
                "it": "che ha scoperto o esplorato",
                "fr": "qui a découvert ou exploré",
            },
            ("history", "person"),
        ),
        ActionSlot(
            "that",
            "conquered or controlled territories in",
            {
                "pt": "que conquistou ou controlou territórios em",
                "es": "que conquistó o controló territorios en",
                "it": "che ha conquistato o controllato territori in",
                "fr": "qui a conquis ou contrôlé des territoires en",
            },
            ("history", "empire"),
        ),
    ],
    targets=[
        TargetSlot(
            "the",
            "19th or 20th",
            "century",
            {
                "pt": "o século XIX ou XX",
                "es": "el siglo XIX o XX",
                "it": "il XIX o XX secolo",
                "fr": "le XIXe ou XXe siècle",
            },
        ),
        TargetSlot(
            "the",
            "Industrial",
            "Revolution",
            {
                "pt": "a Revolução Industrial",
                "es": "la Revolución Industrial",
                "it": "la Rivoluzione Industriale",
                "fr": "la Révolution Industrielle",
            },
        ),
        TargetSlot(
            "the",
            "Mediterranean or European",
            "continent",
            {
                "pt": "o mar Mediterrâneo ou continente europeu",
                "es": "el mar Mediterráneo o continente europeo",
                "it": "il Mediterraneo o l'Europa",
                "fr": "le bassin méditerranéen ou l'Europe",
            },
        ),
        TargetSlot(
            "the",
            "",
            "Americas or the Pacific Ocean",
            {
                "pt": "as Américas ou o Oceano Pacífico",
                "es": "las Américas o el Océano Pacífico",
                "it": "le Americhe o l'Oceano Pacifico",
                "fr": "les Amériques ou l'Océan Pacifique",
            },
        ),
        TargetSlot(
            "",
            "modern",
            "communication or transport",
            {
                "pt": "as comunicações ou transporte modernos",
                "es": "las comunicaciones o el transporte modernos",
                "it": "le comunicazioni o i trasporti moderni",
                "fr": "les communications ou transports modernes",
            },
        ),
    ],
    limiters=[
        LimiterSlot(
            "before the year 1900",
            {
                "pt": "antes do ano 1900",
                "es": "antes del año 1900",
                "it": "prima dell'anno 1900",
                "fr": "avant l'année 1900",
            },
        ),
        LimiterSlot(
            "without using any electricity",
            {
                "pt": "sem recorrer a eletricidade",
                "es": "sin utilizar electricidad",
                "it": "senza l'uso di elettricità",
                "fr": "sans électricité",
            },
        ),
        LimiterSlot(
            "originating outside of Europe",
            {
                "pt": "com origem fora da Europa",
                "es": "originario de fuera de Europa",
                "it": "originario di fuori dall'Europa",
                "fr": "originaire d'en dehors de l'Europe",
            },
        ),
        LimiterSlot(
            "still widely used today",
            {
                "pt": "ainda amplamente utilizado hoje",
                "es": "todavía ampliamente utilizado hoy",
                "it": "ancora oggi ampiamente utilizzato",
                "fr": "encore largement utilisé aujourd'hui",
            },
        ),
    ],
)

# ---------------------------------------------------------------------------
# 6. Quirky / Lateral Party Limiters Frame
# ---------------------------------------------------------------------------
WEIRD_FRAME = SemanticFrame(
    id="frame_weird",
    category="weird",
    title="🤪 Quirky, Funny & Everyday Objects",
    subjects=[
        SubjectSlot(
            "Everyday",
            "household item",
            {
                "pt": "Objeto doméstico do dia a dia",
                "es": "Objeto cotidiano del hogar",
                "it": "Oggetto di uso quotidiano",
                "fr": "Objet ménager du quotidien",
            },
            ("weird", "object"),
        ),
        SubjectSlot(
            "Piece of",
            "clothing or accessory",
            {
                "pt": "Peça de roupa ou acessório",
                "es": "Prenda de ropa o accesorio",
                "it": "Capo d'abbigliamento o accessorio",
                "fr": "Vêtement ou accessoire de mode",
            },
            ("weird", "clothing"),
        ),
        SubjectSlot(
            "Common",
            "excuse or lie",
            {
                "pt": "Desculpa ou mentira clássica",
                "es": "Excusa o mentira clásica",
                "it": "Scusa o bugia comune",
                "fr": "Excuse ou mensonge classique",
            },
            ("weird", "abstract"),
        ),
        SubjectSlot(
            "Popular",
            "board game or party activity",
            {
                "pt": "Jogo de tabuleiro ou de festa popular",
                "es": "Juego de mesa o actividad festiva",
                "it": "Gioco da tavolo o da festa",
                "fr": "Jeu de société ou d'ambiance",
            },
            ("weird", "game"),
        ),
        SubjectSlot(
            "Portable",
            "electronic device",
            {
                "pt": "Dispositivo eletrônico portátil",
                "es": "Dispositivo electrónico portátil",
                "it": "Dispositivo elettronico portatile",
                "fr": "Appareil électronique portable",
            },
            ("weird", "device"),
        ),
    ],
    actions=[
        ActionSlot(
            "that",
            "you would definitely pack for",
            {
                "pt": "que você certamente levaria para",
                "es": "que sin duda llevarías a",
                "it": "che porteresti sicuramente in",
                "fr": "que vous emporteriez sûrement sur",
            },
            ("weird",),
        ),
        ActionSlot(
            "that",
            "people frequently lose in",
            {
                "pt": "que as pessoas frequentemente perdem em",
                "es": "que la gente pierde a menudo en",
                "it": "che la gente perde spesso in",
                "fr": "que les gens perdent souvent dans",
            },
            ("weird",),
        ),
        ActionSlot(
            "that",
            "costs under",
            {
                "pt": "que custa menos de",
                "es": "que cuesta menos de",
                "it": "che costa meno di",
                "fr": "qui coûte moins de",
            },
            ("weird",),
        ),
        ActionSlot(
            "that",
            "makes an annoying or loud",
            {
                "pt": "que faz um barulho alto ou irritante de",
                "es": "que hace un ruido molesto o fuerte de",
                "it": "che fa un rumore fastidioso o forte di",
                "fr": "qui produit un bruit pénible ou fort de",
            },
            ("weird",),
        ),
    ],
    targets=[
        TargetSlot(
            "a",
            "deserted",
            "island or camping trip",
            {
                "pt": "uma ilha deserta ou acampamento",
                "es": "una isla desierta o campamento",
                "it": "un'isola deserta o campeggio",
                "fr": "une île déserte ou du camping",
            },
        ),
        TargetSlot(
            "their",
            "own",
            "car or couch cushions",
            {
                "pt": "seu próprio carro ou almofadas do sofá",
                "es": "su propio coche o cojines del sofá",
                "it": "la propria auto o i cuscini del divano",
                "fr": "sa propre voiture ou sous les coussins du canapé",
            },
        ),
        TargetSlot(
            "",
            "20",
            "euros or dollars",
            {
                "pt": "20 euros ou dólares",
                "es": "20 euros o dólares",
                "it": "20 euro o dollari",
                "fr": "20 euros ou dollars",
            },
        ),
        TargetSlot(
            "a",
            "sudden",
            "beep or click",
            {
                "pt": "um bipe ou clique repentino",
                "es": "un pitido o clic repentino",
                "it": "un bip o clic improvviso",
                "fr": "un bip ou clic soudain",
            },
        ),
    ],
    limiters=[
        LimiterSlot(
            "that requires zero batteries or electricity",
            {
                "pt": "que não necessita de pilhas nem eletricidade",
                "es": "que no necesita pilas ni electricidad",
                "it": "che non usa batterie né elettricità",
                "fr": "qui ne nécessite ni piles ni électricité",
            },
        ),
        LimiterSlot(
            "that can fit comfortably inside a backpack",
            {
                "pt": "que cabe facilmente numa mochila",
                "es": "que cabe fácilmente en una mochila",
                "it": "che entra comodamente in uno zaino",
                "fr": "qui rentre facilement dans un sac à dos",
            },
        ),
        LimiterSlot(
            "starting with a vowel (A, E, I, O, U)",
            {
                "pt": "começando com uma vogal (A, E, I, O, U)",
                "es": "que empieza por vocal (A, E, I, O, U)",
                "it": "che inizia con una vocale (A, E, I, O, U)",
                "fr": "qui commence par une voyelle (A, E, I, O, U)",
            },
        ),
        LimiterSlot(
            "made mostly out of metal or wood",
            {
                "pt": "feito principalmente de metal ou madeira",
                "es": "hecho principalmente de metal o madera",
                "it": "fatto principalmente di metallo o legno",
                "fr": "fait principalement de métal ou de bois",
            },
        ),
    ],
)

ALL_FRAMES = {
    "geo": GEOGRAPHY_FRAME,
    "media": MEDIA_FRAME,
    "food": CULINARY_FRAME,
    "nature": NATURE_FRAME,
    "history": HISTORY_FRAME,
    "weird": WEIRD_FRAME,
}
