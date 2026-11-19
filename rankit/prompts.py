"""Curated prompt deck for 'Rank It!' (ito party game).

Each prompt establishes a subjective spectrum from 1 (the lowest / weakest / least)
to 100 (the highest / strongest / most). Players receive secret numbers from 1 to 100
and must give hints without saying numbers so the team can play them in ascending order.
"""

import random
from typing import Any

PACK_CHOICES = (
    ("mix", "🎲 Mixed Variety (All Safe)"),
    ("classic", "🏆 Classic Party Scales"),
    ("everyday", "☕ Everyday Life & Annoyances"),
    ("superpowers", "🦸 Sci-Fi & Superpowers"),
    ("food", "🍕 Culinary & Taste"),
    ("scary", "😱 Danger & Spooky"),
    ("deep", "🧠 Deep & Philosophical"),
    ("nsfw", "🌶️ Spicy & NSFW (18+)"),
)

RANKIT_PROMPTS: tuple[dict[str, Any], ...] = (
    # =========================================================================
    # CLASSIC PARTY SCALES
    # =========================================================================
    {
        "id": "scale_classic_01",
        "pack": "classic",
        "title": "Dangerous Animals in a 1-on-1 Duel",
        "low_desc": "Harmless fruit fly or baby ladybug",
        "high_desc": "Armored mutant Tyrannosaurus Rex with laser cannons",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Animais Perigosos num Duelo 1 contra 1",
                "low_desc": "Mosca inofensiva ou joaninha bebé",
                "high_desc": "Tiranossauro Rex mutante blindado com canhões laser",
            },
            "es": {
                "title": "Animales Peligrosos en Duelo 1 a 1",
                "low_desc": "Mosca inofensiva o mariquita bebé",
                "high_desc": "Tiranosaurio Rex acorazado con cañones láser",
            },
        },
    },
    {
        "id": "scale_classic_02",
        "pack": "classic",
        "title": "Painful Physical Sensations",
        "low_desc": "Warm gentle breeze brushing your arm",
        "high_desc": "Stepping on a field of burning Legos while passing a kidney stone",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Sensações Físicas Dolorosas",
                "low_desc": "Brisa morna e suave a tocar no teu braço",
                "high_desc": "Pisar peças de Lego em chamas descalço com uma pedra nos rins",
            },
        },
    },
    {
        "id": "scale_classic_03",
        "pack": "classic",
        "title": "Weapons During a Zombie Apocalypse",
        "low_desc": "A limp soggy noodle or peeled banana",
        "high_desc": "Heavy armored military tank with infinite fuel and ammo",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Armas num Apocalipse Zombie",
                "low_desc": "Esparguete mole ensopado ou banana descascada",
                "high_desc": "Tanque militar blindado com combustível e munições infinitas",
            },
        },
    },
    {
        "id": "scale_classic_04",
        "pack": "classic",
        "title": "Ideal Romantic Proposal Locations",
        "low_desc": "In an uncleaned gas station restroom beside a clogged sink",
        "high_desc": "Sunset private terrace over the Santorini caldera with fireworks",
        "is_nsfw": False,
    },
    {
        "id": "scale_classic_05",
        "pack": "classic",
        "title": "Scariest Horror Movie Monsters to Meet Alone",
        "low_desc": "A fluffy sleepy kitten wearing a toy sheet ghost costume",
        "high_desc": "An unescapable eldritch nightmare that devours sanity across dimensions",
        "is_nsfw": False,
    },
    {
        "id": "scale_classic_06",
        "pack": "classic",
        "title": "Places You Would Want to be Stranded For 1 Year",
        "low_desc": "Naked in the middle of Antarctica during a blizzard",
        "high_desc": "Luxury all-inclusive 5-star tropical private resort island",
        "is_nsfw": False,
    },
    {
        "id": "scale_classic_07",
        "pack": "classic",
        "title": "Things That Make You Feel Instantly Wealthy",
        "low_desc": "Finding a 5-cent coin stuck in the sofa cushions",
        "high_desc": "Buying a fleet of luxury superyachts with pocket change",
        "is_nsfw": False,
    },
    {
        "id": "scale_classic_08",
        "pack": "classic",
        "title": "Excuses For Being 2 Hours Late to Your Own Wedding",
        "low_desc": "'I was watching funny cat videos and lost track of time'",
        "high_desc": "'I was urgently conscripted to disarm an orbital asteroid to save Earth'",
        "is_nsfw": False,
    },
    # =========================================================================
    # EVERYDAY LIFE & ANNOYANCES
    # =========================================================================
    {
        "id": "scale_everyday_01",
        "pack": "everyday",
        "title": "Annoying Daily Inconveniences",
        "low_desc": "A ballpoint pen skipping ink for one second",
        "high_desc": "Your phone falling into an airplane toilet right before a 14-hour flight",
        "is_nsfw": False,
    },
    {
        "id": "scale_everyday_02",
        "pack": "everyday",
        "title": "Things That Make You Feel Instantly Old",
        "low_desc": "Taking a daily vitamin tablet with breakfast",
        "high_desc": "Hearing music from your high school graduation played on 'Golden Oldies' museum radio while your knees pop",
        "is_nsfw": False,
    },
    {
        "id": "scale_everyday_03",
        "pack": "everyday",
        "title": "Worst Birthday Gifts to Open in Front of Everyone",
        "low_desc": "A plain pair of cozy black socks",
        "high_desc": "A framed photo of your ex kissing your landlord with a bill for rent increase",
        "is_nsfw": False,
    },
    {
        "id": "scale_everyday_04",
        "pack": "everyday",
        "title": "Embarrassing Social Blunders",
        "low_desc": "Accidentally saying 'Good morning' at 12:05 PM",
        "high_desc": "Waving enthusiastically at someone who was waving at the person behind you, then tripping into a display shelf",
        "is_nsfw": False,
    },
    {
        "id": "scale_everyday_05",
        "pack": "everyday",
        "title": "Exhausting Household Chores",
        "low_desc": "Putting a single spoon in the dishwasher",
        "high_desc": "Scrubbing calcified grout with a toothbrush in a flooded moldy cellar",
        "is_nsfw": False,
    },
    {
        "id": "scale_everyday_06",
        "pack": "everyday",
        "title": "Things That Ruin a Vacation Day",
        "low_desc": "A 10-minute light drizzle while reading indoors",
        "high_desc": "Lost passport, stolen luggage, food poisoning, and a canceled flight home all at once",
        "is_nsfw": False,
    },
    {
        "id": "scale_everyday_07",
        "pack": "everyday",
        "title": "Suspicious Behavior in an Elevator",
        "low_desc": "Politely checking your wristwatch",
        "high_desc": "Facing directly into the corner while giggling and holding a ticking briefcase",
        "is_nsfw": False,
    },
    {
        "id": "scale_everyday_08",
        "pack": "everyday",
        "title": "Excuses For Not Answering a Phone Call",
        "low_desc": "'My phone was on silent'",
        "high_desc": "'I was being interrogated by international secret agents in a submarine'",
        "is_nsfw": False,
    },
    # =========================================================================
    # SUPERPOWERS & SCI-FI
    # =========================================================================
    {
        "id": "scale_super_01",
        "pack": "superpowers",
        "title": "Superpower Coolness & Practicality",
        "low_desc": "Ability to make your left eyebrow twitch on command",
        "high_desc": "Omnipotent teleportation and total control over time and reality",
        "is_nsfw": False,
    },
    {
        "id": "scale_super_02",
        "pack": "superpowers",
        "title": "Movie Villains by Threat Level",
        "low_desc": "A cartoon burglar who slips on banana peels and surrenders",
        "high_desc": "Thanos with the complete Infinity Gauntlet snapping half the cosmos",
        "is_nsfw": False,
    },
    {
        "id": "scale_super_03",
        "pack": "superpowers",
        "title": "Fictional Universes to Live In as an Average Person",
        "low_desc": "Warhammer 40,000 frontline trench or Doom hellscape",
        "high_desc": "The Shire in Middle-earth during second breakfast",
        "is_nsfw": False,
    },
    {
        "id": "scale_super_04",
        "pack": "superpowers",
        "title": "Sci-Fi Gadgets You Would Want in Real Life",
        "low_desc": "A toaster that burns the battery percentage onto the bread",
        "high_desc": "Star Trek medical replicator that cures all diseases and prints gourmet meals",
        "is_nsfw": False,
    },
    {
        "id": "scale_super_05",
        "pack": "superpowers",
        "title": "Things to Shout Out When Unleashing an Anime Attack",
        "low_desc": "A mild quiet sneeze: 'Achoo...'",
        "high_desc": "METEOR BURST GALAXY COLLAPSE OMEGA DRAGON IMPACT 9000!",
        "is_nsfw": False,
    },
    # =========================================================================
    # FOOD & CULINARY
    # =========================================================================
    {
        "id": "scale_food_01",
        "pack": "food",
        "title": "Disgusting Things to Find in Your Restaurant Soup",
        "low_desc": "An extra harmless bay leaf floating at the bottom",
        "high_desc": "A set of gold dental dentures that grins back at you",
        "is_nsfw": False,
    },
    {
        "id": "scale_food_02",
        "pack": "food",
        "title": "Spiciness of Foods",
        "low_desc": "A refreshing sip of cold spring water",
        "high_desc": "Pure distilled Carolina Reaper extract injected onto fresh magma",
        "is_nsfw": False,
    },
    {
        "id": "scale_food_03",
        "pack": "food",
        "title": "Messiest Foods to Eat on a First Date",
        "low_desc": "A single dry salted almond",
        "high_desc": "Overfilled dripping barbecue pulled pork ribs eaten without napkins or utensils",
        "is_nsfw": False,
    },
    {
        "id": "scale_food_04",
        "pack": "food",
        "title": "Unappealing Ice Cream Flavors",
        "low_desc": "Vanilla bean with slightly too little sugar",
        "high_desc": "Fermented tuna intestine and rancid garlic mayonnaise swirl",
        "is_nsfw": False,
    },
    {
        "id": "scale_food_05",
        "pack": "food",
        "title": "Essential Foods You Could Never Give Up",
        "low_desc": "Boiled celery with no salt or seasoning",
        "high_desc": "Freshly baked pizza straight from a wood-fired oven with melted mozzarella",
        "is_nsfw": False,
    },
    # =========================================================================
    # DANGER & SPOOKY
    # =========================================================================
    {
        "id": "scale_scary_01",
        "pack": "scary",
        "title": "Terrifying Sounds to Hear in the Dark at 3 AM",
        "low_desc": "The gentle hum of the refrigerator cooling",
        "high_desc": "A raspy voice whispering your full legal name from inside your closet door",
        "is_nsfw": False,
    },
    {
        "id": "scale_scary_02",
        "pack": "scary",
        "title": "Creepy Crawlies by Fear Factor",
        "low_desc": "A tiny solitary ant minding its own business on the sidewalk",
        "high_desc": "A flying Peruvian giant centipede crawling on your ceiling directly above your open mouth",
        "is_nsfw": False,
    },
    {
        "id": "scale_scary_03",
        "pack": "scary",
        "title": "Adrenaline Rush Intensity",
        "low_desc": "Clicking 'Send' on an email to a friendly coworker",
        "high_desc": "Wingsuit jumping off an active volcanic precipice through a cloud of lightning",
        "is_nsfw": False,
    },
    {
        "id": "scale_scary_04",
        "pack": "scary",
        "title": "Dangerous Stunts to Attempt With Zero Training",
        "low_desc": "Standing on one foot for five seconds while holding a handrail",
        "high_desc": "Blindfolded tightrope walking between skyscrapers during a hurricane",
        "is_nsfw": False,
    },
    # =========================================================================
    # DEEP & PHILOSOPHICAL
    # =========================================================================
    {
        "id": "scale_deep_01",
        "pack": "deep",
        "title": "Moral Difficulty of a Dilemma",
        "low_desc": "Choosing whether to pick chocolate or vanilla pudding",
        "high_desc": "The ultimate Trolley Problem choosing between the fate of the human race and your closest loved ones",
        "is_nsfw": False,
    },
    {
        "id": "scale_deep_02",
        "pack": "deep",
        "title": "Impact on Human Civilization Over the Next Century",
        "low_desc": "A redesign of the paperclip curve by 2 millimeters",
        "high_desc": "Discovery of faster-than-light travel and limitless fusion energy",
        "is_nsfw": False,
    },
    {
        "id": "scale_deep_03",
        "pack": "deep",
        "title": "Stressful Life Situations",
        "low_desc": "Deciding which pair of comfortable sneakers to wear for a walk",
        "high_desc": "Taking an unannounced high-stakes exam while undergoing a surprise tax audit",
        "is_nsfw": False,
    },
    # =========================================================================
    # SPICY & NSFW (18+ / ADULTS ONLY)
    # =========================================================================
    {
        "id": "scale_nsfw_01",
        "pack": "nsfw",
        "title": "Bedroom Spiciness & Adventure Level",
        "low_desc": "A polite kiss on the cheek under the porch light with eyes closed",
        "high_desc": "An uninhibited 72-hour luxury penthouse marathon with sensory restraints and costume roleplay",
        "is_nsfw": True,
    },
    {
        "id": "scale_nsfw_02",
        "pack": "nsfw",
        "title": "Awkward Places to Get Caught In the Act",
        "low_desc": "Under your own duvet in your locked master bedroom",
        "high_desc": "At the pulpit microphone during a live Sunday televised broadcast",
        "is_nsfw": True,
    },
    {
        "id": "scale_nsfw_03",
        "pack": "nsfw",
        "title": "Risqué Text Messages (Sexts) Heat Scale",
        "low_desc": "'Goodnight! See you tomorrow at lunch 😊'",
        "high_desc": "An uncensored 4-page explicit novel detailing every illicit thing planned for the next 15 minutes",
        "is_nsfw": True,
    },
    {
        "id": "scale_nsfw_04",
        "pack": "nsfw",
        "title": "Wild Party Dares For Adults",
        "low_desc": "Confessing your most embarrassing song on your Spotify playlist",
        "high_desc": "Performing a full sultry lap dance using a mop as your prop in front of everyone",
        "is_nsfw": True,
    },
    {
        "id": "scale_nsfw_05",
        "pack": "nsfw",
        "title": "Dirty Talk Intensity",
        "low_desc": "'You look quite lovely in that sweater'",
        "high_desc": "Filthy unhinged whispering that would make a seasoned pirate captain blush",
        "is_nsfw": True,
    },
    {
        "id": "scale_nsfw_06",
        "pack": "nsfw",
        "title": "Kinkiness of Bedroom Props & Toys",
        "low_desc": "A scented lavender candle on the nightstand",
        "high_desc": "Full Japanese Shibari suspended rope harness with blindfolds and ice clamps",
        "is_nsfw": True,
    },
    {
        "id": "scale_nsfw_07",
        "pack": "nsfw",
        "title": "Walk of Shame Awkwardness the Morning After",
        "low_desc": "Walking out the front door wearing your own neat clothes to your car",
        "high_desc": "Wearing a ripped Halloween pirate cape and one flip-flop on public transit at 8 AM rush hour",
        "is_nsfw": True,
    },
    {
        "id": "scale_nsfw_08",
        "pack": "nsfw",
        "title": "Physical Attractiveness Turn-Ons",
        "low_desc": "Wearing clean ironed socks",
        "high_desc": "Mesmerizing confident smile, magnetic voice, and undeniable electric chemistry",
        "is_nsfw": True,
    },
)


def get_prompt_pool(pack: str = "mix", allow_nsfw: bool = False) -> list[dict[str, Any]]:
    """Return filtered prompts based on pack category and NSFW safety settings."""
    pool = []
    pack_norm = (pack or "mix").strip().lower()

    for p in RANKIT_PROMPTS:
        # If NSFW prompt and adult mode is disabled, skip
        if p.get("is_nsfw", False) and not allow_nsfw:
            continue

        if pack_norm == "mix":
            # Mixed includes all safe prompts (or NSFW too if allow_nsfw is enabled)
            pool.append(p)
        elif pack_norm == "nsfw":
            if p.get("is_nsfw", False):
                pool.append(p)
        elif p.get("pack") == pack_norm:
            pool.append(p)

    return pool or [p for p in RANKIT_PROMPTS if not p.get("is_nsfw", False)]


def get_random_prompt(
    pack: str = "mix",
    allow_nsfw: bool = False,
    used_ids: list[str] | set[str] | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Pick an unused prompt from the pool with fallback to least used."""
    pool = get_prompt_pool(pack=pack, allow_nsfw=allow_nsfw)
    used = set(used_ids or [])

    fresh = [p for p in pool if p["id"] not in used]
    chosen = random.choice(fresh) if fresh else random.choice(pool)

    # Resolve localized title and descriptions if present
    lang_code = (language or "en").split("-")[0].lower()
    title = chosen["title"]
    low_desc = chosen["low_desc"]
    high_desc = chosen["high_desc"]

    trans = chosen.get("translations", {}).get(lang_code)
    if isinstance(trans, dict):
        title = trans.get("title", title)
        low_desc = trans.get("low_desc", low_desc)
        high_desc = trans.get("high_desc", high_desc)

    return {
        "id": chosen["id"],
        "pack": chosen.get("pack", "classic"),
        "title": title,
        "low_desc": low_desc,
        "high_desc": high_desc,
        "is_nsfw": chosen.get("is_nsfw", False),
    }
