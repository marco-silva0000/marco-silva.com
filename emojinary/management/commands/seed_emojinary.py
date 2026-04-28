from django.core.management.base import BaseCommand

from emojinary.models import EmojinaryWord

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
    help = "Seed the emojinary word database"

    def handle(self, *args, **options):
        created = 0
        for text, category, difficulty in WORDS:
            _, was_created = EmojinaryWord.objects.get_or_create(
                text=text, defaults={"category": category, "difficulty": difficulty}
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} words ({EmojinaryWord.objects.count()} total)"))
