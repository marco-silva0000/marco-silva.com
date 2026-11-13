import json
from pathlib import Path

from django.core.management.base import BaseCommand

from emojinary.models import EmojinaryWord

WORDLIST_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "wordlists.json"
WIKTIONARY_LEXICON_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "wiktionary_lexicon.json"

CATEGORY_DEFAULT_POS = {
    "action": "verb",
    "phrase": "phrase",
    "movie": "proper",
    "tvshow": "proper",
    "song": "proper",
    "person": "proper",
    "place": "proper",
}

WORDS = [
    # Movies
    ("The Lion King", "movie", 1),
    ("Titanic", "movie", 1),
    ("Frozen", "movie", 1),
    ("Star Wars", "movie", 1),
    ("Jurassic Park", "movie", 1),
    ("Finding Nemo", "movie", 1),
    ("The Matrix", "movie", 2),
    ("Inception", "movie", 2),
    ("Interstellar", "movie", 2),
    ("The Shawshank Redemption", "movie", 2),
    ("Pulp Fiction", "movie", 2),
    ("The Silence of the Lambs", "movie", 3),
    ("Eternal Sunshine of the Spotless Mind", "movie", 3),
    ("No Country for Old Men", "movie", 3),
    ("The Grand Budapest Hotel", "movie", 3),
    ("Blade Runner", "movie", 2),
    ("Back to the Future", "movie", 1),
    ("Ghostbusters", "movie", 1),
    ("The Wizard of Oz", "movie", 1),
    ("Jaws", "movie", 1),
    ("E.T.", "movie", 1),
    ("The Godfather", "movie", 2),
    ("Fight Club", "movie", 2),
    ("Forrest Gump", "movie", 1),
    ("The Dark Knight", "movie", 2),
    ("Toy Story", "movie", 1),
    ("Up", "movie", 1),
    ("WALL-E", "movie", 2),
    ("Ratatouille", "movie", 2),
    ("Coco", "movie", 1),
    # Phrases
    ("Break a leg", "phrase", 1),
    ("Piece of cake", "phrase", 1),
    ("Under the weather", "phrase", 2),
    ("Hit the nail on the head", "phrase", 2),
    ("Spill the beans", "phrase", 1),
    ("Let the cat out of the bag", "phrase", 2),
    ("When pigs fly", "phrase", 1),
    ("Raining cats and dogs", "phrase", 1),
    ("The elephant in the room", "phrase", 2),
    ("A penny for your thoughts", "phrase", 2),
    ("Burning the midnight oil", "phrase", 2),
    ("Bite the bullet", "phrase", 2),
    ("Cost an arm and a leg", "phrase", 2),
    ("Once in a blue moon", "phrase", 2),
    ("The best of both worlds", "phrase", 2),
    ("Kill two birds with one stone", "phrase", 2),
    ("A picture is worth a thousand words", "phrase", 3),
    # Songs
    ("Bohemian Rhapsody", "song", 2),
    ("Imagine", "song", 1),
    ("Yesterday", "song", 1),
    ("Thriller", "song", 1),
    ("Hotel California", "song", 2),
    ("Stairway to Heaven", "song", 2),
    ("Dancing Queen", "song", 1),
    ("Sweet Home Alabama", "song", 2),
    ("Smells Like Teen Spirit", "song", 2),
    ("Billie Jean", "song", 2),
    ("Under Pressure", "song", 2),
    ("Rocket Man", "song", 1),
    # TV Shows
    ("Breaking Bad", "tvshow", 1),
    ("Game of Thrones", "tvshow", 1),
    ("Stranger Things", "tvshow", 1),
    ("The Office", "tvshow", 1),
    ("Friends", "tvshow", 1),
    ("The Walking Dead", "tvshow", 1),
    ("Black Mirror", "tvshow", 2),
    ("The Crown", "tvshow", 2),
    ("Squid Game", "tvshow", 1),
    ("Money Heist", "tvshow", 2),
    # Things
    ("Birthday party", "thing", 1),
    ("Traffic jam", "thing", 1),
    ("Solar eclipse", "thing", 2),
    ("Northern lights", "thing", 2),
    ("Roller coaster", "thing", 1),
    ("Hot air balloon", "thing", 1),
    ("Haunted house", "thing", 1),
    ("Time travel", "thing", 2),
    ("Zombie apocalypse", "thing", 2),
    ("Treasure hunt", "thing", 1),
    ("Space station", "thing", 2),
    ("Underwater volcano", "thing", 3),
]


class Command(BaseCommand):
    help = "Seed the emojinary word database from built-in curated words, open-source wordlists, and Wiktionary"

    def handle(self, *args, **options):
        lexicon: dict[str, dict] = {}
        if WIKTIONARY_LEXICON_PATH.exists():
            with open(WIKTIONARY_LEXICON_PATH, "r", encoding="utf-8") as f:
                lexicon = json.load(f)

        combined: list[tuple[str, str, int, str]] = [(t, c, d, "curated") for t, c, d in WORDS]
        if WORDLIST_DATA_PATH.exists():
            with open(WORDLIST_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("emojinary", []):
                if isinstance(item, (list, tuple)) and len(item) == 3:
                    combined.append((str(item[0]), str(item[1]), int(item[2]), "open-wordlists"))

        # Deduplicate case-insensitively per category and skip already-seeded entries
        existing_qs = EmojinaryWord.objects.all()
        existing_map: dict[tuple[str, str], EmojinaryWord] = {}
        for obj in existing_qs.only("id", "text", "category", "definition", "translations", "aliases"):
            existing_map[(obj.text.lower(), obj.category)] = obj

        to_create = []
        seen = set(existing_map.keys())
        for text, category, difficulty, src in combined:
            clean_text = text.strip()
            key = (clean_text.lower(), category)
            if not key[0] or key in seen:
                continue
            seen.add(key)
            lex = lexicon.get(key[0], {})
            default_pos = CATEGORY_DEFAULT_POS.get(category, "noun")
            to_create.append(
                EmojinaryWord(
                    text=clean_text,
                    category=category,
                    pos=lex.get("pos", default_pos),
                    difficulty=difficulty,
                    definition=lex.get("definition", ""),
                    etymology=lex.get("etymology", ""),
                    aliases=lex.get("aliases", []),
                    translations=lex.get("translations", {}),
                    topics=lex.get("topics", []),
                    source="wiktionary" if lex else src,
                )
            )

        if to_create:
            EmojinaryWord.objects.bulk_create(to_create, batch_size=1000)

        # Backfill Wiktionary enrichment on existing rows that lack definitions/translations
        to_update = []
        for (low_text, category), obj in existing_map.items():
            lex = lexicon.get(low_text)
            if not lex:
                continue
            if not obj.definition or not obj.translations:
                obj.pos = lex.get("pos", CATEGORY_DEFAULT_POS.get(category, "noun"))
                obj.definition = lex.get("definition", obj.definition)
                obj.etymology = lex.get("etymology", obj.etymology)
                obj.aliases = lex.get("aliases", obj.aliases)
                obj.translations = lex.get("translations", obj.translations)
                obj.topics = lex.get("topics", obj.topics)
                obj.source = "wiktionary"
                to_update.append(obj)

        if to_update:
            EmojinaryWord.objects.bulk_update(
                to_update,
                ["pos", "definition", "etymology", "aliases", "translations", "topics", "source"],
                batch_size=500,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(to_create)} new words, enriched {len(to_update)} existing ({EmojinaryWord.objects.count()} total)"
            )
        )
