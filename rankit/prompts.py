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
    # 100 CURATED SAFE COMMUNITY SCALES
    # =========================================================================
    {
        "id": "scale_safe_001",
        "pack": "superpowers",
        "title": "Superpowers from least to most powerful",
        "low_desc": "1 (Least Powerful): Bare minimum / none",
        "high_desc": "100 (Most Powerful): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Superpoderes do menos para o mais poderoso",
                "low_desc": "1 (Menos Powerful): Mínimo absoluto",
                "high_desc": "100 (Mais Powerful): Máximo absoluto / topo",
            },
            "es": {
                "title": "Superpoderes de menos a más poderosos",
                "low_desc": "1 (Menos Powerful): Mínimo absoluto",
                "high_desc": "100 (Más Powerful): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_002",
        "pack": "classic",
        "title": "Worst to best places to start dancing uncontrollably",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores sítios para começar a dançar incontrolavelmente",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores lugares para empezar a bailar incontrolablemente",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_003",
        "pack": "classic",
        "title": "Dance moves from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Passos de dança do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Pasos de baile de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_004",
        "pack": "everyday",
        "title": "Fragrances and smells from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Fragrâncias e cheiros do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Fragancias y olores de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_005",
        "pack": "deep",
        "title": "Easiest to hardest things to give up for the rest of your life",
        "low_desc": "1 (Easiest): Completely effortless / instant",
        "high_desc": "100 (Hardest): Brutally difficult / near impossible",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas mais fáceis a mais difíceis de abdicar para o resto da vida",
                "low_desc": "1 (Mais fácil): Sem qualquer esforço / instantâneo",
                "high_desc": "100 (Mais difícil): Quase impossível / brutal",
            },
            "es": {
                "title": "Cosas más fáciles a más difíciles de renunciar por el resto de tu vida",
                "low_desc": "1 (Más fácil): Totalmente sin esfuerzo / instantáneo",
                "high_desc": "100 (Más difícil): Casi imposible / brutal",
            },
        },
    },
    {
        "id": "scale_safe_006",
        "pack": "superpowers",
        "title": "Worst to best thing to have the ability to conjure from thin air",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Pior a melhor coisa para conjurar do nada com poderes",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peor a mejor cosa para conjurar de la nada con poderes",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_007",
        "pack": "classic",
        "title": "Celebrities from weakest to strongest in a fight",
        "low_desc": "1 (Weakest): Fragile / zero chance in a fight",
        "high_desc": "100 (Strongest): Unstoppable titan",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Famosos do mais fraco ao mais forte numa luta",
                "low_desc": "1 (Mais fraco): Frágil / sem hipóteses numa luta",
                "high_desc": "100 (Mais forte): Titã imparável e invencível",
            },
            "es": {
                "title": "Famosos del más débil al más fuerte en una pelea",
                "low_desc": "1 (Más débil): Frágil / sin posibilidades en una pelea",
                "high_desc": "100 (Más fuerte): Titán imparable e invencible",
            },
        },
    },
    {
        "id": "scale_safe_008",
        "pack": "everyday",
        "title": "Things you could purchase for $10,000 from least to most practical",
        "low_desc": "1 (Least Practical): Bare minimum / none",
        "high_desc": "100 (Most Practical): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas para comprar com $10.000 da menos para a mais prática",
                "low_desc": "1 (Menos Practical): Mínimo absoluto",
                "high_desc": "100 (Mais Practical): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas para comprar con $10.000 de menos a más práctica",
                "low_desc": "1 (Menos Practical): Mínimo absoluto",
                "high_desc": "100 (Más Practical): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_009",
        "pack": "everyday",
        "title": "Scenarios from least to most annoying",
        "low_desc": "1 (Least Annoying): Bare minimum / none",
        "high_desc": "100 (Most Annoying): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Cenários do menos para o mais irritante",
                "low_desc": "1 (Menos Annoying): Mínimo absoluto",
                "high_desc": "100 (Mais Annoying): Máximo absoluto / topo",
            },
            "es": {
                "title": "Escenarios de menos a más molestos",
                "low_desc": "1 (Menos Annoying): Mínimo absoluto",
                "high_desc": "100 (Más Annoying): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_010",
        "pack": "deep",
        "title": "Worst to best reasons to go on a quest",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores razões para partir numa demanda ou aventura",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores razones para embarcarse en una misión o aventura",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_011",
        "pack": "classic",
        "title": "Things that are least to most cute",
        "low_desc": "1 (Least Cute): Bare minimum / none",
        "high_desc": "100 (Most Cute): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas da menos para a mais fofa",
                "low_desc": "1 (Menos Cute): Mínimo absoluto",
                "high_desc": "100 (Mais Cute): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas de menos a más adorables",
                "low_desc": "1 (Menos Cute): Mínimo absoluto",
                "high_desc": "100 (Más Cute): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_012",
        "pack": "superpowers",
        "title": "Worst to best things you could do if you could freeze time",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas a fazer se conseguisses congelar o tempo",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para hacer si pudieras congelar el tiempo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_013",
        "pack": "classic",
        "title": "Memes from least to most funny",
        "low_desc": "1 (Least Funny): Bare minimum / none",
        "high_desc": "100 (Most Funny): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Memes do menos para o mais engraçado",
                "low_desc": "1 (Menos Funny): Mínimo absoluto",
                "high_desc": "100 (Mais Funny): Máximo absoluto / topo",
            },
            "es": {
                "title": "Memes del menos al más gracioso",
                "low_desc": "1 (Menos Funny): Mínimo absoluto",
                "high_desc": "100 (Más Funny): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_014",
        "pack": "everyday",
        "title": "Things you can poke your finger in from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas onde podes espetar o dedo do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Cosas donde puedes meter el dedo de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_015",
        "pack": "everyday",
        "title": "Worst to best things to give as a gift",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores prendas para oferecer",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores regalos para dar",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_016",
        "pack": "superpowers",
        "title": "Worst to best things to be able to control with your mind",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas para controlar com a mente",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para controlar con la mente",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_017",
        "pack": "scary",
        "title": "Things you would do if you saw a ghost from least to most likely",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas que farias se visses um fantasma da menos para a mais provável",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Cosas que harías si vieras un fantasma de menos a más probable",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_safe_018",
        "pack": "classic",
        "title": "Worst to best places to visit as a tourist",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores lugares para visitar como turista",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores lugares para visitar como turista",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_019",
        "pack": "classic",
        "title": "Movie/tv show endings from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Finais de filmes/séries do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Finales de películas/series de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_020",
        "pack": "classic",
        "title": "Animals which you least to most want to be",
        "low_desc": "1 (Least Want): Bare minimum / none",
        "high_desc": "100 (Most Want): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Animais que menos a mais gostarias de ser",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Mais Want): Máximo absoluto / topo",
            },
            "es": {
                "title": "Animales que menos a más te gustaría ser",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Más Want): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_021",
        "pack": "food",
        "title": "Worst to best snack foods",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores snacks e petiscos",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores snacks y aperitivos",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_022",
        "pack": "everyday",
        "title": "Worst to best advice to give to a child",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores conselhos para dar a uma criança",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores consejos para darle a un niño",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_023",
        "pack": "classic",
        "title": "Activities from least to most fun",
        "low_desc": "1 (Least Fun): Bare minimum / none",
        "high_desc": "100 (Most Fun): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Atividades da menos para a mais divertida",
                "low_desc": "1 (Menos Fun): Mínimo absoluto",
                "high_desc": "100 (Mais Fun): Máximo absoluto / topo",
            },
            "es": {
                "title": "Actividades de menos a más divertidas",
                "low_desc": "1 (Menos Fun): Mínimo absoluto",
                "high_desc": "100 (Más Fun): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_024",
        "pack": "everyday",
        "title": "Scenarios from least to most cringe/awkward",
        "low_desc": "1 (Least Cringe): Bare minimum / none",
        "high_desc": "100 (Most Cringe): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Situações da menos para a mais embaraçosa e cringe",
                "low_desc": "1 (Menos Cringe): Mínimo absoluto",
                "high_desc": "100 (Mais Cringe): Máximo absoluto / topo",
            },
            "es": {
                "title": "Situaciones de menos a más vergonzosas o cringe",
                "low_desc": "1 (Menos Cringe): Mínimo absoluto",
                "high_desc": "100 (Más Cringe): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_025",
        "pack": "food",
        "title": "Worst to best things to put in a smoothie",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores ingredientes para pôr num batido/smoothie",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para poner en un batido",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_026",
        "pack": "everyday",
        "title": "Clothing items from least to most fashionable",
        "low_desc": "1 (Least Fashionable): Bare minimum / none",
        "high_desc": "100 (Most Fashionable): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Peças de roupa da menos para a mais estilosa e na moda",
                "low_desc": "1 (Menos Fashionable): Mínimo absoluto",
                "high_desc": "100 (Mais Fashionable): Máximo absoluto / topo",
            },
            "es": {
                "title": "Prendas de vestir de menos a más a la moda",
                "low_desc": "1 (Menos Fashionable): Mínimo absoluto",
                "high_desc": "100 (Más Fashionable): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_027",
        "pack": "classic",
        "title": "Musical artist or acts from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Artistas ou bandas musicais do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Artistas o grupos musicales de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_028",
        "pack": "everyday",
        "title": "Things that would least to most improve your day",
        "low_desc": "1 (Least Improve): Bare minimum / none",
        "high_desc": "100 (Most Improve): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas que menos a mais melhorariam o teu dia",
                "low_desc": "1 (Menos Improve): Mínimo absoluto",
                "high_desc": "100 (Mais Improve): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas que menos a más mejorarían tu día",
                "low_desc": "1 (Menos Improve): Mínimo absoluto",
                "high_desc": "100 (Más Improve): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_029",
        "pack": "classic",
        "title": "Celebrities from least to most talented",
        "low_desc": "1 (Least Talented): Bare minimum / none",
        "high_desc": "100 (Most Talented): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Famosos do menos para o mais talentoso",
                "low_desc": "1 (Menos Talented): Mínimo absoluto",
                "high_desc": "100 (Mais Talented): Máximo absoluto / topo",
            },
            "es": {
                "title": "Famosos de menos a más talentosos",
                "low_desc": "1 (Menos Talented): Mínimo absoluto",
                "high_desc": "100 (Más Talented): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_030",
        "pack": "superpowers",
        "title": "Animals and fantasy creatures from least to most cool to have as a pet",
        "low_desc": "1 (Least Cool): Bare minimum / none",
        "high_desc": "100 (Most Cool): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Animais e criaturas fantásticas do menos para o mais fixe para animal de estimação",
                "low_desc": "1 (Menos Cool): Mínimo absoluto",
                "high_desc": "100 (Mais Cool): Máximo absoluto / topo",
            },
            "es": {
                "title": "Animales y criaturas fantásticas de menos a más geniales como mascota",
                "low_desc": "1 (Menos Cool): Mínimo absoluto",
                "high_desc": "100 (Más Cool): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_031",
        "pack": "classic",
        "title": "Movies and tv shows from least to most likely to make you laugh",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Filmes e séries do menos para o mais provável de te fazer rir",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Películas y series de menos a más probables de hacerte reír",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_safe_032",
        "pack": "deep",
        "title": "Movies or tv show moments from least to most likely to make you cry",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Momentos de filmes/séries do menos para o mais provável de te fazer chorar",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Momentos de películas/series de menos a más probables de hacerte llorar",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_safe_033",
        "pack": "scary",
        "title": "Worst to best things to do if you were suddenly transported back to the medieval ages",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas a fazer se fosses transportado para a Idade Média",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para hacer si fueras transportado a la Edad Media",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_034",
        "pack": "food",
        "title": "Desserts or sweets from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Sobremesas e doces do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Postres y dulces de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_035",
        "pack": "superpowers",
        "title": "Worst to best superhero names",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores nomes de super-heróis",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores nombres de superhéroes",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_036",
        "pack": "food",
        "title": "Fast food menu items from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Itens de menu de fast food do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Platos de comida rápida de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_037",
        "pack": "scary",
        "title": "Things that would least to most likely scare you",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas que menos a mais provavelmente te assustariam",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Cosas que menos a más probablemente te asustarían",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_safe_038",
        "pack": "scary",
        "title": "Animals and fantasy creatures you’d most to least likely beat in a fist fight",
        "low_desc": "1 (Most likely): First reaction / certain",
        "high_desc": "100 (Least likely): Unthinkable / never",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Criaturas que mais a menos facilmente vencerias numa luta mano a mano",
                "low_desc": "1 (Mais provável): Certeza absoluta / primeiro instinto",
                "high_desc": "100 (Menos provável): Impensável / nunca na vida",
            },
            "es": {
                "title": "Criaturas que más a menos fácilmente vencerías en una pelea a puñetazos",
                "low_desc": "1 (Más probable): Certeza absoluta / primer instinto",
                "high_desc": "100 (Menos probable): Impensable / jamás",
            },
        },
    },
    {
        "id": "scale_safe_039",
        "pack": "superpowers",
        "title": "Fictional characters from weakest to strongest in a fight",
        "low_desc": "1 (Weakest): Fragile / zero chance in a fight",
        "high_desc": "100 (Strongest): Unstoppable titan",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Personagens de ficção da mais fraca para a mais forte numa luta",
                "low_desc": "1 (Mais fraco): Frágil / sem hipóteses numa luta",
                "high_desc": "100 (Mais forte): Titã imparável e invencível",
            },
            "es": {
                "title": "Personajes ficticios del más débil al más fuerte en una pelea",
                "low_desc": "1 (Más débil): Frágil / sin posibilidades en una pelea",
                "high_desc": "100 (Más fuerte): Titán imparable e invencible",
            },
        },
    },
    {
        "id": "scale_safe_040",
        "pack": "deep",
        "title": "Experiences from least to most impactful on someone's life",
        "low_desc": "1 (Least Impactful): Bare minimum / none",
        "high_desc": "100 (Most Impactful): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Experiências da menos para a mais marcante na vida de alguém",
                "low_desc": "1 (Menos Impactful): Mínimo absoluto",
                "high_desc": "100 (Mais Impactful): Máximo absoluto / topo",
            },
            "es": {
                "title": "Experiencias de menos a más impactantes en la vida de alguien",
                "low_desc": "1 (Menos Impactful): Mínimo absoluto",
                "high_desc": "100 (Más Impactful): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_041",
        "pack": "superpowers",
        "title": "Worst to best times in history you would travel to if you could time travel",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores épocas históricas para visitar numa viagem no tempo",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores épocas históricas para viajar en el tiempo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_042",
        "pack": "food",
        "title": "Worst to best things to serve at a 5 star restaurant",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores pratos para servir num restaurante de 5 estrelas",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores platos para servir en un restaurante de 5 estrellas",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_043",
        "pack": "classic",
        "title": "Hobbies from least to most interesting",
        "low_desc": "1 (Least Interesting): Bare minimum / none",
        "high_desc": "100 (Most Interesting): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Hobbies do menos para o mais interessante",
                "low_desc": "1 (Menos Interesting): Mínimo absoluto",
                "high_desc": "100 (Mais Interesting): Máximo absoluto / topo",
            },
            "es": {
                "title": "Pasatiempos de menos a más interesantes",
                "low_desc": "1 (Menos Interesting): Mínimo absoluto",
                "high_desc": "100 (Más Interesting): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_044",
        "pack": "everyday",
        "title": "Things you would do if you had a free day to yourself from least to most likely",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas que farias se tivesses um dia livre só para ti da menos para a mais provável",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Cosas que harías si tuvieras un día libre para ti de menos a más probable",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_safe_045",
        "pack": "everyday",
        "title": "Things that are easiest to hardest to learn",
        "low_desc": "1 (Easiest): Completely effortless / instant",
        "high_desc": "100 (Hardest): Brutally difficult / near impossible",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas mais fáceis a mais difíceis de aprender",
                "low_desc": "1 (Mais fácil): Sem qualquer esforço / instantâneo",
                "high_desc": "100 (Mais difícil): Quase impossível / brutal",
            },
            "es": {
                "title": "Cosas más fáciles a más difíciles de aprender",
                "low_desc": "1 (Más fácil): Totalmente sin esfuerzo / instantáneo",
                "high_desc": "100 (Más difícil): Casi imposible / brutal",
            },
        },
    },
    {
        "id": "scale_safe_046",
        "pack": "deep",
        "title": "Worst to best wish you would make if you could make any wish",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Pior a melhor desejo que pedirias se pudesses pedir qualquer coisa",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peor a mejor deseo que pedirías si pudieras pedir cualquier cosa",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_047",
        "pack": "deep",
        "title": "People from poorest to richest",
        "low_desc": "1 (Poorest): Penniless / broke",
        "high_desc": "100 (Richest): Trillionaire tycoon",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Pessoas do mais pobre ao mais rico",
                "low_desc": "1 (Mais pobre): Sem um tostão furado",
                "high_desc": "100 (Mais rico): Magnata trilionário",
            },
            "es": {
                "title": "Personas del más pobre al más rico",
                "low_desc": "1 (Más pobre): Sin un centavo",
                "high_desc": "100 (Más rico): Magnate trillonario",
            },
        },
    },
    {
        "id": "scale_safe_048",
        "pack": "everyday",
        "title": "Worst to best things to do everyday",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas para fazer todos os dias",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para hacer todos los días",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_049",
        "pack": "everyday",
        "title": "Worst to best ways to travel 1000 kilometres",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores formas de viajar 1000 quilómetros",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores formas de viajar 1000 kilómetros",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_050",
        "pack": "everyday",
        "title": "Sounds and noises from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Sons e ruídos do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Sonidos y ruidos de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_051",
        "pack": "classic",
        "title": "Songs from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Músicas da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Canciones de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_052",
        "pack": "food",
        "title": "Beverages from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Bebidas da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Bebidas de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_053",
        "pack": "superpowers",
        "title": "Fictional worlds or settings you'd least to most like to live in",
        "low_desc": "1 (Least Like): Bare minimum / none",
        "high_desc": "100 (Most Like): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Mundos de ficção onde menos a mais gostarias de viver",
                "low_desc": "1 (Menos Like): Mínimo absoluto",
                "high_desc": "100 (Mais Like): Máximo absoluto / topo",
            },
            "es": {
                "title": "Mundos de ficción donde menos a más te gustaría vivir",
                "low_desc": "1 (Menos Like): Mínimo absoluto",
                "high_desc": "100 (Más Like): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_054",
        "pack": "superpowers",
        "title": "People you'd least to most want to swap bodies with for a day",
        "low_desc": "1 (Least Want): Bare minimum / none",
        "high_desc": "100 (Most Want): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Pessoas com quem menos a mais gostarias de trocar de corpo por um dia",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Mais Want): Máximo absoluto / topo",
            },
            "es": {
                "title": "Personas con las que menos a más te gustaría cambiar de cuerpo por un día",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Más Want): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_055",
        "pack": "classic",
        "title": "People or things you'd least to most want on a deserted island with you",
        "low_desc": "1 (Least Want): Bare minimum / none",
        "high_desc": "100 (Most Want): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Pessoas ou coisas que menos a mais gostarias de ter numa ilha deserta",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Mais Want): Máximo absoluto / topo",
            },
            "es": {
                "title": "Personas o cosas que menos a más querrías en una isla desierta",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Más Want): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_056",
        "pack": "food",
        "title": "Things to pack for lunch from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Comidas para levar na marmita do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Comidas para llevar en el almuerzo de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_057",
        "pack": "classic",
        "title": "Songs you'd hear at a karaoke night from least to most likely",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Músicas de karaoke da menos para a mais provável de ouvir numa noite",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Canciones de karaoke de menos a más probables de escuchar",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_safe_058",
        "pack": "classic",
        "title": "Worst to best things to write a song about",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores temas sobre os quais escrever uma canção",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores temas sobre los que escribir una canción",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_059",
        "pack": "everyday",
        "title": "Animals from most to least common",
        "low_desc": "1 (Most Common): Maximum / extreme",
        "high_desc": "100 (Least Common): Minimum / barely any",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Animais do mais para o menos comum",
                "low_desc": "1 (Mais Common): Máximo absoluto",
                "high_desc": "100 (Menos Common): Quase inexistente",
            },
            "es": {
                "title": "Animales de más a menos comunes",
                "low_desc": "1 (Más Common): Máximo absoluto",
                "high_desc": "100 (Menos Common): Casi inexistente",
            },
        },
    },
    {
        "id": "scale_safe_060",
        "pack": "deep",
        "title": "World records from least to most impressive",
        "low_desc": "1 (Least Impressive): Bare minimum / none",
        "high_desc": "100 (Most Impressive): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Recordes mundiais do menos para o mais impressionante",
                "low_desc": "1 (Menos Impressive): Mínimo absoluto",
                "high_desc": "100 (Mais Impressive): Máximo absoluto / topo",
            },
            "es": {
                "title": "Récords mundiales de menos a más impresionantes",
                "low_desc": "1 (Menos Impressive): Mínimo absoluto",
                "high_desc": "100 (Más Impressive): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_061",
        "pack": "everyday",
        "title": "Things to put on your resume from least to most impressive",
        "low_desc": "1 (Least Impressive): Bare minimum / none",
        "high_desc": "100 (Most Impressive): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas para pôr no currículo da menos para a mais impressionante",
                "low_desc": "1 (Menos Impressive): Mínimo absoluto",
                "high_desc": "100 (Mais Impressive): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas para poner en el currículum de menos a más impresionantes",
                "low_desc": "1 (Menos Impressive): Mínimo absoluto",
                "high_desc": "100 (Más Impressive): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_062",
        "pack": "food",
        "title": "Things you can cook at home from easiest to hardest",
        "low_desc": "1 (Easiest): Completely effortless / instant",
        "high_desc": "100 (Hardest): Brutally difficult / near impossible",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Pratos para cozinhar em casa do mais fácil ao mais difícil",
                "low_desc": "1 (Mais fácil): Sem qualquer esforço / instantâneo",
                "high_desc": "100 (Mais difícil): Quase impossível / brutal",
            },
            "es": {
                "title": "Platos para cocinar en casa del más fácil al más difícil",
                "low_desc": "1 (Más fácil): Totalmente sin esfuerzo / instantáneo",
                "high_desc": "100 (Más difícil): Casi imposible / brutal",
            },
        },
    },
    {
        "id": "scale_safe_063",
        "pack": "food",
        "title": "Worst to best places to get food in your city",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores sítios para comer na tua cidade",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores lugares para comer en tu ciudad",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_064",
        "pack": "everyday",
        "title": "Worst to best person to represent you in a criminal trial",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Pior a melhor pessoa para te defender num julgamento criminal",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peor a mejor persona para defenderte en un juicio penal",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_065",
        "pack": "food",
        "title": "Worst to best things to do at a restaurant",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas a fazer num restaurante",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para hacer en un restaurante",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_066",
        "pack": "deep",
        "title": "Things you least to most want to happen 10 years from now",
        "low_desc": "1 (Least Want): Bare minimum / none",
        "high_desc": "100 (Most Want): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Acontecimentos que menos a mais desejas ver acontecer daqui a 10 anos",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Mais Want): Máximo absoluto / topo",
            },
            "es": {
                "title": "Acontecimientos que menos a más deseas que ocurran dentro de 10 años",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Más Want): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_067",
        "pack": "everyday",
        "title": "Jobs or professions from easiest to hardest",
        "low_desc": "1 (Easiest): Completely effortless / instant",
        "high_desc": "100 (Hardest): Brutally difficult / near impossible",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Trabalhos e profissões do mais fácil ao mais difícil",
                "low_desc": "1 (Mais fácil): Sem qualquer esforço / instantâneo",
                "high_desc": "100 (Mais difícil): Quase impossível / brutal",
            },
            "es": {
                "title": "Trabajos y profesiones del más fácil al más difícil",
                "low_desc": "1 (Más fácil): Totalmente sin esfuerzo / instantáneo",
                "high_desc": "100 (Más difícil): Casi imposible / brutal",
            },
        },
    },
    {
        "id": "scale_safe_068",
        "pack": "everyday",
        "title": "Worst to best excuses for being late to work",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores desculpas para chegar atrasado ao trabalho",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores excusas para llegar tarde al trabajo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_069",
        "pack": "classic",
        "title": "Things to do as a group from least to most exciting",
        "low_desc": "1 (Least Exciting): Bare minimum / none",
        "high_desc": "100 (Most Exciting): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Atividades em grupo da menos para a mais emocionante",
                "low_desc": "1 (Menos Exciting): Mínimo absoluto",
                "high_desc": "100 (Mais Exciting): Máximo absoluto / topo",
            },
            "es": {
                "title": "Actividades en grupo de menos a más emocionantes",
                "low_desc": "1 (Menos Exciting): Mínimo absoluto",
                "high_desc": "100 (Más Exciting): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_070",
        "pack": "classic",
        "title": "Worst to best things to do if you had an audience with the queen",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas a fazer numa audiência com a Rainha",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para hacer en una audiencia con la Reina",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_071",
        "pack": "everyday",
        "title": "Things that least to most likely indicate someone is old",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Sinais que menos a mais indicam que alguém está a ficar velho",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Señales que menos a más indican que alguien está envejeciendo",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_safe_072",
        "pack": "everyday",
        "title": "Things that least to most likely indicate someone is young",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Sinais que menos a mais indicam que alguém é jovem",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Señales que menos a más indican que alguien es joven",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_safe_073",
        "pack": "everyday",
        "title": "Items or things people are least to most likely to own",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Objetos que as pessoas têm menor a maior probabilidade de possuir",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Objetos que las personas tienen menor a mayor probabilidad de poseer",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_safe_074",
        "pack": "scary",
        "title": "Worst to best things to do if you are stranded on tropical island",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas a fazer se ficares preso numa ilha tropical",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para hacer si quedas varado en una isla tropical",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_075",
        "pack": "scary",
        "title": "Items from least to most useful in a fight",
        "low_desc": "1 (Least Useful): Bare minimum / none",
        "high_desc": "100 (Most Useful): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Objetos do menos para o mais útil numa luta",
                "low_desc": "1 (Menos Useful): Mínimo absoluto",
                "high_desc": "100 (Mais Useful): Máximo absoluto / topo",
            },
            "es": {
                "title": "Objetos de menos a más útiles en una pelea",
                "low_desc": "1 (Menos Useful): Mínimo absoluto",
                "high_desc": "100 (Más Useful): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_076",
        "pack": "classic",
        "title": "Worst to best things to make review videos of for a living",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores produtos para fazer vídeos de análise como profissão",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores productos para hacer vídeos de reseñas profesionalmente",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_077",
        "pack": "classic",
        "title": "Celebrities from least to most likeable",
        "low_desc": "1 (Least Likeable): Bare minimum / none",
        "high_desc": "100 (Most Likeable): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Famosos do menos para o mais simpático e adorado",
                "low_desc": "1 (Menos Likeable): Mínimo absoluto",
                "high_desc": "100 (Mais Likeable): Máximo absoluto / topo",
            },
            "es": {
                "title": "Famosos de menos a más simpáticos y queridos",
                "low_desc": "1 (Menos Likeable): Mínimo absoluto",
                "high_desc": "100 (Más Likeable): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_078",
        "pack": "food",
        "title": "Worst to best flavours of ice cream",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Sabores de gelado do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Sabores de helado de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_079",
        "pack": "classic",
        "title": "Worst to best people from history to have dinner with",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores figuras históricas para jantar",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores figuras históricas para cenar",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_080",
        "pack": "food",
        "title": "Things to eat for breakfast from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Comidas de pequeno-almoço da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Comidas de desayuno de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_081",
        "pack": "superpowers",
        "title": "Worst to best things you would do if you could time travel",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores ações que farias se pudesses viajar no tempo",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores acciones que harías si pudieras viajar en el tiempo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_082",
        "pack": "deep",
        "title": "Worst to best mottos to live by",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores lemas de vida para seguir",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores lemas de vida para seguir",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_083",
        "pack": "deep",
        "title": "Worst to best reasons to pursue a career in medicine",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores motivações para seguir carreira em medicina",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores motivaciones para seguir una carrera en medicina",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_084",
        "pack": "everyday",
        "title": "Things you’ve done in your life from least to most often",
        "low_desc": "1 (Least Often): Bare minimum / none",
        "high_desc": "100 (Most Often): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas que fizeste na vida da menos para a mais frequente",
                "low_desc": "1 (Menos Often): Mínimo absoluto",
                "high_desc": "100 (Mais Often): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas que has hecho en la vida de menos a más frecuentes",
                "low_desc": "1 (Menos Often): Mínimo absoluto",
                "high_desc": "100 (Más Often): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_085",
        "pack": "deep",
        "title": "Things you least to most want to happen 300 years from now",
        "low_desc": "1 (Least Want): Bare minimum / none",
        "high_desc": "100 (Most Want): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Cenários que menos a mais desejas ver acontecer daqui a 300 anos",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Mais Want): Máximo absoluto / topo",
            },
            "es": {
                "title": "Escenarios que menos a más deseas que ocurran dentro de 300 años",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Más Want): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_086",
        "pack": "scary",
        "title": "Worst to best things to do in a crowded elevator",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas a fazer num elevador apinhado de gente",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para hacer en un ascensor lleno de gente",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_087",
        "pack": "superpowers",
        "title": "Fictional characters you’d most want to be friends with",
        "low_desc": "1 (MIN): Lowest / minimal",
        "high_desc": "100 (MAX): Highest / maximum",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Personagens fictícias de quem menos a mais gostarias de ser amigo",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
            "es": {
                "title": "Personajes ficticios de quienes menos a más te gustaría ser amigo",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
        },
    },
    {
        "id": "scale_safe_088",
        "pack": "everyday",
        "title": "Worst to best reasons to write a strongly worded letter",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores razões para escrever uma carta de reclamação furiosa",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores motivos para escribir una carta de queja furiosa",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_089",
        "pack": "everyday",
        "title": "Things you least to most want to happen at your wedding",
        "low_desc": "1 (Least Want): Bare minimum / none",
        "high_desc": "100 (Most Want): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Acontecimentos que menos a mais desejas que aconteçam no teu casamento",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Mais Want): Máximo absoluto / topo",
            },
            "es": {
                "title": "Acontecimientos que menos a más deseas que pasen en tu boda",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Más Want): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_090",
        "pack": "superpowers",
        "title": "Worst to best things about being a vampire",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores aspetos de ser um vampiro",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores aspectos de ser un vampiro",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_091",
        "pack": "superpowers",
        "title": "Worst to best reasons to become a supervillain",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores motivos para te tornares um supervilão",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores motivos para convertirte en un supervillano",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_092",
        "pack": "classic",
        "title": "Worst to best things to see happen on a stage",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores momentos para ver acontecer em palco",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores momentos para ver suceder en un escenario",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_093",
        "pack": "everyday",
        "title": "Things you would put in a mansion you were building from least to most practical",
        "low_desc": "1 (Least Practical): Bare minimum / none",
        "high_desc": "100 (Most Practical): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas que colocarias numa mansão que estivesses a construir da menos à mais prática",
                "low_desc": "1 (Menos Practical): Mínimo absoluto",
                "high_desc": "100 (Mais Practical): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas que pondrías en una mansión de menos a más prácticas",
                "low_desc": "1 (Menos Practical): Mínimo absoluto",
                "high_desc": "100 (Más Practical): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_094",
        "pack": "superpowers",
        "title": "Least to most intimidating villains from fiction",
        "low_desc": "1 (Least Intimidating): Bare minimum / none",
        "high_desc": "100 (Most Intimidating): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Vilões de ficção do menos para o mais intimidante",
                "low_desc": "1 (Menos Intimidating): Mínimo absoluto",
                "high_desc": "100 (Mais Intimidating): Máximo absoluto / topo",
            },
            "es": {
                "title": "Villanos de ficción de menos a más intimidantes",
                "low_desc": "1 (Menos Intimidating): Mínimo absoluto",
                "high_desc": "100 (Más Intimidating): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_095",
        "pack": "everyday",
        "title": "Worst to best things to have to wear as your uniform at work",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores roupas para ter como farda de trabalho obrigatória",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores prendas para tener como uniforme de trabajo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_096",
        "pack": "everyday",
        "title": "Worst to best things to catch while going fishing",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas para pescar à linha",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para pescar con caña",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_097",
        "pack": "deep",
        "title": "Investments from least to most stable",
        "low_desc": "1 (Least Stable): Bare minimum / none",
        "high_desc": "100 (Most Stable): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Investimentos financeiros do menos para o mais estável e seguro",
                "low_desc": "1 (Menos Stable): Mínimo absoluto",
                "high_desc": "100 (Mais Stable): Máximo absoluto / topo",
            },
            "es": {
                "title": "Inversiones financieras de menos a más estables y seguras",
                "low_desc": "1 (Menos Stable): Mínimo absoluto",
                "high_desc": "100 (Más Stable): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_safe_098",
        "pack": "everyday",
        "title": "Worst to best things to carry in your purse",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores objetos para trazer na mala ou mochila",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores objetos para llevar en el bolso o mochila",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_099",
        "pack": "everyday",
        "title": "Worse to best things to do if you are a teacher",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Piores a melhores atitudes a tomar se fores professor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores actitudes para tomar si eres profesor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_safe_100",
        "pack": "classic",
        "title": "Things you would do if you were a bird from least to most interesting",
        "low_desc": "1 (Least Interesting): Bare minimum / none",
        "high_desc": "100 (Most Interesting): Maximum / peak",
        "is_nsfw": False,
        "translations": {
            "pt": {
                "title": "Coisas que farias se fosses um pássaro da menos para a mais interessante",
                "low_desc": "1 (Menos Interesting): Mínimo absoluto",
                "high_desc": "100 (Mais Interesting): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas que harías si fueras un pájaro de menos a más interesantes",
                "low_desc": "1 (Menos Interesting): Mínimo absoluto",
                "high_desc": "100 (Más Interesting): Máximo absoluto / cumbre",
            },
        },
    },
    # =========================================================================
    # 100 CURATED SPICY & NSFW (18+) SCALES
    # =========================================================================
    {
        "id": "scale_nsfw_001",
        "pack": "nsfw",
        "title": "Worst to best ways to commit a murder and try to get away with it",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores formas de cometer um homicídio e tentar safar-te",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores formas de cometer un asesinato e intentar salirte con la tuya",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_002",
        "pack": "nsfw",
        "title": "Worst to best things to challenge the grim reaper at to save your life",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores jogos para desafiar a Morte e salvar a tua vida",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores juegos para retar a la Muerte y salvar tu vida",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_003",
        "pack": "nsfw",
        "title": "Worst to best reasons to start a fight",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores motivos para começar uma pancadaria",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores motivos para empezar una pelea",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_004",
        "pack": "nsfw",
        "title": "Worst to best things to get tattooed",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores desenhos para tatuar no corpo",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para tatuarse en el cuerpo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_005",
        "pack": "nsfw",
        "title": "Worst to best things to do if you are stopped by the police",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores reações se fores mandado parar pela polícia",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores reacciones si te detiene la policía",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_006",
        "pack": "nsfw",
        "title": "Worst to best ways to make money",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores formas de ganhar dinheiro rápido",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores formas de ganar dinero",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_007",
        "pack": "nsfw",
        "title": "Worst to best people, characters or creatures to watch have sex",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores personagens ou criaturas para ver a ter sexo",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores personajes o criaturas para ver teniendo sexo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_008",
        "pack": "nsfw",
        "title": "Worst to best things to fight over during a divorce",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores bens para disputar num divórcio litigioso",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores bienes para disputar en un divorcio",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_009",
        "pack": "nsfw",
        "title": "Things you would do if you had no money and were homeless from least to most likely",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Coisas que farias se estivesses sem dinheiro e sem-abrigo da menos para a mais provável",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Cosas que harías si estuvieras sin dinero y sin hogar de menos a más probable",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_010",
        "pack": "nsfw",
        "title": "Things you would do if you knew you would die tomorrow from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Coisas a fazer se soubesses que morrias amanhã da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Cosas para hacer si supieras que mueres mañana de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_011",
        "pack": "nsfw",
        "title": "Things to put on your dating profile that would make you least to most successful",
        "low_desc": "1 (Least Successful): Bare minimum / none",
        "high_desc": "100 (Most Successful): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Coisas para pôr no perfil do Tinder que te tornam do menos para o mais bem-sucedido",
                "low_desc": "1 (Menos Successful): Mínimo absoluto",
                "high_desc": "100 (Mais Successful): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas para poner en tu perfil de citas que te harían de menos a más exitoso",
                "low_desc": "1 (Menos Successful): Mínimo absoluto",
                "high_desc": "100 (Más Successful): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_012",
        "pack": "nsfw",
        "title": "Things to do just before you quit your job from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Coisas para fazer antes de te despedires do trabalho da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Cosas para hacer antes de renunciar a tu trabajo de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_013",
        "pack": "nsfw",
        "title": "Ways to make a child cry from least to most cruel",
        "low_desc": "1 (Least Cruel): Bare minimum / none",
        "high_desc": "100 (Most Cruel): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Maneiras de fazer uma criança chorar da menos para a mais cruel",
                "low_desc": "1 (Menos Cruel): Mínimo absoluto",
                "high_desc": "100 (Mais Cruel): Máximo absoluto / topo",
            },
            "es": {
                "title": "Maneras de hacer llorar a un niño de menos a más cruel",
                "low_desc": "1 (Menos Cruel): Mínimo absoluto",
                "high_desc": "100 (Más Cruel): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_014",
        "pack": "nsfw",
        "title": "Things you would do if you ruled the world from least to most cruel",
        "low_desc": "1 (Least Cruel): Bare minimum / none",
        "high_desc": "100 (Most Cruel): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Ações que tomarias se governasses o mundo da menos para a mais tirânica",
                "low_desc": "1 (Menos Cruel): Mínimo absoluto",
                "high_desc": "100 (Mais Cruel): Máximo absoluto / topo",
            },
            "es": {
                "title": "Acciones que tomarías si gobernaras el mundo de menos a más tiránica",
                "low_desc": "1 (Menos Cruel): Mínimo absoluto",
                "high_desc": "100 (Más Cruel): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_015",
        "pack": "nsfw",
        "title": "Reasons to have sex from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Razões para ter relações sexuais da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Razones para tener relaciones sexuales de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_016",
        "pack": "nsfw",
        "title": "Ways to get high from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Formas de apanhar moca da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Formas de drogarse o colocarse de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_017",
        "pack": "nsfw",
        "title": "Fights between any two fictional characters or creatures you’d least to most want to watch",
        "low_desc": "1 (Least Want): Bare minimum / none",
        "high_desc": "100 (Most Want): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Duelos mortais entre dois seres fictícios que menos a mais gostarias de assistir",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Mais Want): Máximo absoluto / topo",
            },
            "es": {
                "title": "Peleas a muerte entre dos seres ficticios que menos a más te gustaría ver",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Más Want): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_018",
        "pack": "nsfw",
        "title": "Ways you will die from least to most likely",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Formas como vais morrer da menos para a mais provável",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Formas en que morirás de menos a más probable",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_019",
        "pack": "nsfw",
        "title": "Things that could happen in the afterlife from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Cenários do que acontece no além da vida do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Escenarios de lo que ocurre en el más allá de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_020",
        "pack": "nsfw",
        "title": "Worst to best things that would happen after winning a million dollars",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores consequências após ganhares um milhão de euros",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores consecuencias tras ganar un millón de euros",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_021",
        "pack": "nsfw",
        "title": "Things or scenarios that cause the least to the most stress",
        "low_desc": "1 (MIN): Lowest / minimal",
        "high_desc": "100 (MAX): Highest / maximum",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Situações que provocam do menor ao maior nível de stress",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
            "es": {
                "title": "Situaciones que provocan del menor al mayor nivel de estrés",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
        },
    },
    {
        "id": "scale_nsfw_022",
        "pack": "nsfw",
        "title": "Worst to best ways for the world to end",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores formas para o fim do mundo / apocalipse",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores formas para el fin del mundo / apocalipsis",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_023",
        "pack": "nsfw",
        "title": "Things you are most to least likely to do in a bedroom",
        "low_desc": "1 (Most likely): First reaction / certain",
        "high_desc": "100 (Least likely): Unthinkable / never",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Coisas que mais a menos provavelmente farias entre quatro paredes no quarto",
                "low_desc": "1 (Mais provável): Certeza absoluta / primeiro instinto",
                "high_desc": "100 (Menos provável): Impensável / nunca na vida",
            },
            "es": {
                "title": "Cosas que más a menos probablemente harías en un dormitorio",
                "low_desc": "1 (Más probable): Certeza absoluta / primer instinto",
                "high_desc": "100 (Menos probable): Impensable / jamás",
            },
        },
    },
    {
        "id": "scale_nsfw_024",
        "pack": "nsfw",
        "title": "Reasons someone would want to kill you from least to most likely",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Motivos pelos quais alguém te quereria assassinar do menos para o mais provável",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Motivos por los que alguien querría asesinarte de menos a más probable",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_025",
        "pack": "nsfw",
        "title": "Worst to best reasons for a riot to happen",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores motivos para um motim violento na rua",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores motivos para que estalle un motín violento",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_026",
        "pack": "nsfw",
        "title": "Female celebrities from least to most attractive",
        "low_desc": "1 (Least Attractive): Bare minimum / none",
        "high_desc": "100 (Most Attractive): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Mulheres famosas da menos para a mais atraente",
                "low_desc": "1 (Menos Attractive): Mínimo absoluto",
                "high_desc": "100 (Mais Attractive): Máximo absoluto / topo",
            },
            "es": {
                "title": "Celebridades femeninas de menos a más atractivas",
                "low_desc": "1 (Menos Attractive): Mínimo absoluto",
                "high_desc": "100 (Más Attractive): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_027",
        "pack": "nsfw",
        "title": "Social issues from least to most important",
        "low_desc": "1 (Least Important): Bare minimum / none",
        "high_desc": "100 (Most Important): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Problemas e causas sociais do menos para o mais urgente e importante",
                "low_desc": "1 (Menos Important): Mínimo absoluto",
                "high_desc": "100 (Mais Important): Máximo absoluto / topo",
            },
            "es": {
                "title": "Problemas y causas sociales de menos a más urgentes e importantes",
                "low_desc": "1 (Menos Important): Mínimo absoluto",
                "high_desc": "100 (Más Important): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_028",
        "pack": "nsfw",
        "title": "Horror movies you would least to most likely survive",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Filmes de terror onde terias menor a maior probabilidade de sobreviver",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Películas de terror en las que tendrías menor a mayor probabilidad de sobrevivir",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_029",
        "pack": "nsfw",
        "title": "Fantasy creatures that you least to most want to have sex with",
        "low_desc": "1 (Least Want): Bare minimum / none",
        "high_desc": "100 (Most Want): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Criaturas fantásticas com quem menos a mais quererias ir para a cama",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Mais Want): Máximo absoluto / topo",
            },
            "es": {
                "title": "Criaturas fantásticas con las que menos a más querrías acostarte",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Más Want): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_030",
        "pack": "nsfw",
        "title": "Things that least to most turn you on or make you horny",
        "low_desc": "1 (Least Turn): Bare minimum / none",
        "high_desc": "100 (Most Turn): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Coisas que menos a mais te deixam com tesão e excitado",
                "low_desc": "1 (Menos Turn): Mínimo absoluto",
                "high_desc": "100 (Mais Turn): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas que menos a más te ponen caliente o cachondo",
                "low_desc": "1 (Menos Turn): Mínimo absoluto",
                "high_desc": "100 (Más Turn): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_031",
        "pack": "nsfw",
        "title": "Couples from the real world or fiction you'd most want to join in a threesome",
        "low_desc": "1 (MIN): Lowest / minimal",
        "high_desc": "100 (MAX): Highest / maximum",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Casais famosos ou de ficção com quem mais gostarias de fazer um menage a trois",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
            "es": {
                "title": "Parejas famosas o de ficción con quienes más te gustaría hacer un trío",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
        },
    },
    {
        "id": "scale_nsfw_032",
        "pack": "nsfw",
        "title": "Places to hide a body from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores esconderijos para ocultar um cadáver",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores escondites para ocultar un cadáver",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_033",
        "pack": "nsfw",
        "title": "Crimes from most to least easy to get away with",
        "low_desc": "1 (Most Easy): Maximum / extreme",
        "high_desc": "100 (Least Easy): Minimum / barely any",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Crimes do mais para o menos fácil de escapar impune",
                "low_desc": "1 (Mais Easy): Máximo absoluto",
                "high_desc": "100 (Menos Easy): Quase inexistente",
            },
            "es": {
                "title": "Crímenes del más al menos fácil de salir impune",
                "low_desc": "1 (Más Easy): Máximo absoluto",
                "high_desc": "100 (Menos Easy): Casi inexistente",
            },
        },
    },
    {
        "id": "scale_nsfw_034",
        "pack": "nsfw",
        "title": "Worst to best things to share on social media",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas para partilhar publicamente nas redes sociais",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para publicar en redes sociales",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_035",
        "pack": "nsfw",
        "title": "Worst to best ways to answer the question 'Where do you see yourself in 5 years?'",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores respostas para 'onde te vês daqui a 5 anos?' numa entrevista",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores respuestas para '¿dónde te ves en 5 años?' en una entrevista",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_036",
        "pack": "nsfw",
        "title": "Best to worst things your parents did while you grew up",
        "low_desc": "1 (Best): Absolute peak / finest",
        "high_desc": "100 (Worst): Absolute worst / horrific",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Atitudes dos teus pais durante a tua infância da melhor para a pior",
                "low_desc": "1 (Melhor): O topo absoluto / perfeito",
                "high_desc": "100 (Pior): O pior absoluto / horrível",
            },
            "es": {
                "title": "Actitudes de tus padres durante tu infancia de mejor a peor",
                "low_desc": "1 (Mejor): Lo más alto / perfecto",
                "high_desc": "100 (Peor): Lo peor absoluto / horrible",
            },
        },
    },
    {
        "id": "scale_nsfw_037",
        "pack": "nsfw",
        "title": "Worst to best things your boss could tell you",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores frases que o teu chefe te poderia dizer",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores frases que tu jefe te podría decir",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_038",
        "pack": "nsfw",
        "title": "Reasons to divorce from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Razões para pedir o divórcio da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Razones para pedir el divorcio de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_039",
        "pack": "nsfw",
        "title": "Alcoholic drinks from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Bebidas alcoólicas da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Bebidas alcohólicas de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_040",
        "pack": "nsfw",
        "title": "Things to wipe your butt with from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Objetos para limpar o rabo na falta de papel higiénico do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Cosas para limpiarte el culo en emergencia de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_041",
        "pack": "nsfw",
        "title": "Fetishes from most normal to strangest",
        "low_desc": "1 (MIN): Lowest / minimal",
        "high_desc": "100 (MAX): Highest / maximum",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Fetiches sexuais do mais comum e normal ao mais bizarro e estranho",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
            "es": {
                "title": "Fetiches sexuales del más común al más bizarro y extraño",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
        },
    },
    {
        "id": "scale_nsfw_042",
        "pack": "nsfw",
        "title": "Personality traits from least to most attractive",
        "low_desc": "1 (Least Attractive): Bare minimum / none",
        "high_desc": "100 (Most Attractive): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Traços de personalidade do menos para o mais atraente num parceiro",
                "low_desc": "1 (Menos Attractive): Mínimo absoluto",
                "high_desc": "100 (Mais Attractive): Máximo absoluto / topo",
            },
            "es": {
                "title": "Rasgos de personalidad de menos a más atractivos en una pareja",
                "low_desc": "1 (Menos Attractive): Mínimo absoluto",
                "high_desc": "100 (Más Attractive): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_043",
        "pack": "nsfw",
        "title": "Porn scenarios from least to most exciting",
        "low_desc": "1 (Least Exciting): Bare minimum / none",
        "high_desc": "100 (Most Exciting): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Cenários de filmes pornográficos do menos para o mais excitante",
                "low_desc": "1 (Menos Exciting): Mínimo absoluto",
                "high_desc": "100 (Mais Exciting): Máximo absoluto / topo",
            },
            "es": {
                "title": "Escenarios porno de menos a más excitantes",
                "low_desc": "1 (Menos Exciting): Mínimo absoluto",
                "high_desc": "100 (Más Exciting): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_044",
        "pack": "nsfw",
        "title": "Male celebrities from least to most attractive",
        "low_desc": "1 (Least Attractive): Bare minimum / none",
        "high_desc": "100 (Most Attractive): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Homens famosos do menos para o mais atraente",
                "low_desc": "1 (Menos Attractive): Mínimo absoluto",
                "high_desc": "100 (Mais Attractive): Máximo absoluto / topo",
            },
            "es": {
                "title": "Celebridades masculinas de menos a más atractivas",
                "low_desc": "1 (Menos Attractive): Mínimo absoluto",
                "high_desc": "100 (Más Attractive): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_045",
        "pack": "nsfw",
        "title": "Things you would do if you were the only person left on Earth from least to most likely",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Coisas que farias se fosses a última pessoa na Terra da menos para a mais provável",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Cosas que harías si fueras la última persona en la Tierra de menos a más probable",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_046",
        "pack": "nsfw",
        "title": "Magical curses you would inflict on your worst enemy from least to most cruel",
        "low_desc": "1 (Least Cruel): Bare minimum / none",
        "high_desc": "100 (Most Cruel): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Maldições mágicas para rogar ao teu pior inimigo da menos para a mais cruel",
                "low_desc": "1 (Menos Cruel): Mínimo absoluto",
                "high_desc": "100 (Mais Cruel): Máximo absoluto / topo",
            },
            "es": {
                "title": "Maldiciones mágicas para lanzarle a tu peor enemigo de menos a más cruel",
                "low_desc": "1 (Menos Cruel): Mínimo absoluto",
                "high_desc": "100 (Más Cruel): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_047",
        "pack": "nsfw",
        "title": "Worst to best ways to propose marriage to someone",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores formas de pedir alguém em casamento",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores formas de pedir matrimonio",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_048",
        "pack": "nsfw",
        "title": "Things that least to most likely indicate someone is male",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Características que menos a mais indicam que alguém é do sexo masculino",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Rasgos que menos a más indican que alguien es hombre",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_049",
        "pack": "nsfw",
        "title": "Things that least to most likely indicate someone is female",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Características que menos a mais indicam que alguém é do sexo feminino",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Rasgos que menos a más indican que alguien es mujer",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_050",
        "pack": "nsfw",
        "title": "Things that happened in highschool from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Acontecimentos típicos da escola secundária do pior para o melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Sucesos típicos del instituto o secundaria de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_051",
        "pack": "nsfw",
        "title": "Places to fart loudly from best to worst",
        "low_desc": "1 (Best): Absolute peak / finest",
        "high_desc": "100 (Worst): Absolute worst / horrific",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Sítios para dar um peido ruidoso do melhor para o pior",
                "low_desc": "1 (Melhor): O topo absoluto / perfeito",
                "high_desc": "100 (Pior): O pior absoluto / horrível",
            },
            "es": {
                "title": "Lugares para tirarse un pedo ruidoso del mejor al peor",
                "low_desc": "1 (Mejor): Lo más alto / perfecto",
                "high_desc": "100 (Peor): Lo peor absoluto / horrible",
            },
        },
    },
    {
        "id": "scale_nsfw_052",
        "pack": "nsfw",
        "title": "Things you would do if you could turn invisible from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Coisas que farias se ficasses invisível da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Cosas que harías si fueras invisible de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_053",
        "pack": "nsfw",
        "title": "Worst to best things to do on a first date",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas a fazer num primeiro encontro",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para hacer en una primera cita",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_054",
        "pack": "nsfw",
        "title": "Worst to best things to do with a dildo",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores usos para dar a um dildo / vibrador",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores usos para darle a un consolador",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_055",
        "pack": "nsfw",
        "title": "Worst to best things to use as lubricant while being intimate",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores substitutos improvisados para lubrificante íntimo",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores sustitutos improvisados para lubricante íntimo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_056",
        "pack": "nsfw",
        "title": "Worst to best things to learn about your parents",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores revelações embaraçosas para descobrir sobre os teus pais",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores revelaciones vergonzosas para descubrir sobre tus padres",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_057",
        "pack": "nsfw",
        "title": "Worst to best thing to do if you found a dead body",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores reações se encontrasses um cadáver",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores reacciones si encuentras un cadáver",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_058",
        "pack": "nsfw",
        "title": "Worst to best excuses for cheating on your significant other",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores desculpas para justificar uma traição amorosa",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores excusas para justificar una infidelidad",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_059",
        "pack": "nsfw",
        "title": "People or things you’d least to most want to kiss",
        "low_desc": "1 (Least Want): Bare minimum / none",
        "high_desc": "100 (Most Want): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Pessoas ou seres que menos a mais gostarias de beijar na boca",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Mais Want): Máximo absoluto / topo",
            },
            "es": {
                "title": "Personas o seres que menos a más te gustaría besar",
                "low_desc": "1 (Menos Want): Mínimo absoluto",
                "high_desc": "100 (Más Want): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_060",
        "pack": "nsfw",
        "title": "Least to most enjoyable part of a furry convention",
        "low_desc": "1 (Least Enjoyable): Bare minimum / none",
        "high_desc": "100 (Most Enjoyable): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Partes de uma convenção furry da menos para a mais divertida",
                "low_desc": "1 (Menos Enjoyable): Mínimo absoluto",
                "high_desc": "100 (Mais Enjoyable): Máximo absoluto / topo",
            },
            "es": {
                "title": "Partes de una convención furry de menos a más divertidas",
                "low_desc": "1 (Menos Enjoyable): Mínimo absoluto",
                "high_desc": "100 (Más Enjoyable): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_061",
        "pack": "nsfw",
        "title": "Things your partner could dress up as from least to most hot",
        "low_desc": "1 (Least Hot): Bare minimum / none",
        "high_desc": "100 (Most Hot): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Fantasias eróticas para o teu parceiro vestir da menos para a mais sexy",
                "low_desc": "1 (Menos Hot): Mínimo absoluto",
                "high_desc": "100 (Mais Hot): Máximo absoluto / topo",
            },
            "es": {
                "title": "Disfraces eróticos para tu pareja de menos a más calientes",
                "low_desc": "1 (Menos Hot): Mínimo absoluto",
                "high_desc": "100 (Más Hot): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_062",
        "pack": "nsfw",
        "title": "Worst to best things to do in a zombie apocalypse",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores estratégias de sobrevivência num apocalipse zombie",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores estrategias de supervivencia en un apocalipsis zombi",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_063",
        "pack": "nsfw",
        "title": "Worst to best ways to break up with someone",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores maneiras de acabar uma relação com alguém",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores maneras de romper una relación con alguien",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_064",
        "pack": "nsfw",
        "title": "Things that least to most likely indicate a man is gay",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Sinais que menos a mais indicam que um homem é gay",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Señales que menos a más indican que un hombre es gay",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_065",
        "pack": "nsfw",
        "title": "Things that least to most likely indicate a woman is a lesbian",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Sinais que menos a mais indicam que uma mulher é lésbica",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Señales que menos a más indican que una mujer es lesbiana",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_066",
        "pack": "nsfw",
        "title": "Least to most likely thing for a cult to worship",
        "low_desc": "1 (Least likely): Virtually impossible / never",
        "high_desc": "100 (Most likely): 100% guaranteed / first instinct",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Objetos ou entidades que uma seita bizarra menos a mais provavelmente adoraria",
                "low_desc": "1 (Menos provável): Nunca na vida / impossível",
                "high_desc": "100 (Mais provável): Certeza absoluta / primeira reação",
            },
            "es": {
                "title": "Cosas que una secta bizarra menos a más probablemente adoraría",
                "low_desc": "1 (Menos probable): Jamás en la vida / imposible",
                "high_desc": "100 (Más probable): Certeza absoluta / primer instinto",
            },
        },
    },
    {
        "id": "scale_nsfw_067",
        "pack": "nsfw",
        "title": "Worst to best questions to ask on a first date",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores perguntas para fazer num primeiro encontro",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores preguntas para hacer en una primera cita",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_068",
        "pack": "nsfw",
        "title": "Worst to best ways to have sex",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores posições ou formas de ter relações sexuais",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores posturas o formas de tener sexo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_069",
        "pack": "nsfw",
        "title": "Worst to best things to describe as 'sexy'",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas ou adjetivos para descrever como 'sexy'",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas para calificar de 'sexy'",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_070",
        "pack": "nsfw",
        "title": "Worst to best ways to describe someone’s sexual performance",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores formas de descrever a performance sexual de alguém na cama",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores formas de describir el rendimiento sexual de alguien",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_071",
        "pack": "nsfw",
        "title": "Least to most important things to consider when organising an orgy",
        "low_desc": "1 (Least Important): Bare minimum / none",
        "high_desc": "100 (Most Important): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Detalhes do menos para o mais importante ao organizar uma orgia",
                "low_desc": "1 (Menos Important): Mínimo absoluto",
                "high_desc": "100 (Mais Important): Máximo absoluto / topo",
            },
            "es": {
                "title": "Detalles de menos a más importantes al organizar una orgía",
                "low_desc": "1 (Menos Important): Mínimo absoluto",
                "high_desc": "100 (Más Important): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_072",
        "pack": "nsfw",
        "title": "Worst to best things to do at a strip joint",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores atitudes num clube de striptease",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores actitudes en un club de striptease",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_073",
        "pack": "nsfw",
        "title": "Worst to best ways to get everyone's attention",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores formas de captar a atenção de toda a sala",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores formas de llamar la atención de todos",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_074",
        "pack": "nsfw",
        "title": "Things worse than being kicked in the balls from most to least comparable",
        "low_desc": "1 (Most Comparable): Maximum / extreme",
        "high_desc": "100 (Least Comparable): Minimum / barely any",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Dores comparadas a levar um pontapé nos tomates da mais à menos terrível",
                "low_desc": "1 (Mais Comparable): Máximo absoluto",
                "high_desc": "100 (Menos Comparable): Quase inexistente",
            },
            "es": {
                "title": "Dolores comparables a una patada en los huevos del más al menos insoportable",
                "low_desc": "1 (Más Comparable): Máximo absoluto",
                "high_desc": "100 (Menos Comparable): Casi inexistente",
            },
        },
    },
    {
        "id": "scale_nsfw_075",
        "pack": "nsfw",
        "title": "Worst to best things you could say about someone",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores coisas que poderias dizer nas costas de alguém",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores cosas que podrías decir a espaldas de alguien",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_076",
        "pack": "nsfw",
        "title": "Worst to best reasons to drop out of school",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores justificações para abandonar a escola",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores justificaciones para dejar los estudios",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_077",
        "pack": "nsfw",
        "title": "Things that least to most disgust you",
        "low_desc": "1 (Least Disgust): Bare minimum / none",
        "high_desc": "100 (Most Disgust): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Coisas que menos a mais te causam nojo e repulsa",
                "low_desc": "1 (Menos Disgust): Mínimo absoluto",
                "high_desc": "100 (Mais Disgust): Máximo absoluto / topo",
            },
            "es": {
                "title": "Cosas que menos a más te causan asco y repugnancia",
                "low_desc": "1 (Menos Disgust): Mínimo absoluto",
                "high_desc": "100 (Más Disgust): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_078",
        "pack": "nsfw",
        "title": "Worst to best ways to assert dominance",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores formas de afirmar dominância sobre alguém",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores formas de imponer dominancia",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_079",
        "pack": "nsfw",
        "title": "Worst to best places to take a piss",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores locais improvisados para mandar uma mija",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores lugares para echar una meada",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_080",
        "pack": "nsfw",
        "title": "Worst to best things to lie about",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores assuntos sobre os quais mentir descaradamente",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores asuntos sobre los que mentir descaradamente",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_081",
        "pack": "nsfw",
        "title": "Worst to best reasons to never have sex",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores desculpas para nunca ter relações sexuais",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores razones para no tener sexo nunca",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_082",
        "pack": "nsfw",
        "title": "Easiest to hardest things to steal",
        "low_desc": "1 (Easiest): Completely effortless / instant",
        "high_desc": "100 (Hardest): Brutally difficult / near impossible",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Objetos do mais fácil ao mais difícil de roubar sem ser apanhado",
                "low_desc": "1 (Mais fácil): Sem qualquer esforço / instantâneo",
                "high_desc": "100 (Mais difícil): Quase impossível / brutal",
            },
            "es": {
                "title": "Cosas más fáciles a más difíciles de robar sin ser pillado",
                "low_desc": "1 (Más fácil): Totalmente sin esfuerzo / instantáneo",
                "high_desc": "100 (Más difícil): Casi imposible / brutal",
            },
        },
    },
    {
        "id": "scale_nsfw_083",
        "pack": "nsfw",
        "title": "Easiest to hardest people to assassinate",
        "low_desc": "1 (Easiest): Completely effortless / instant",
        "high_desc": "100 (Hardest): Brutally difficult / near impossible",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Alvos do mais fácil ao mais difícil de assassinar discretamente",
                "low_desc": "1 (Mais fácil): Sem qualquer esforço / instantâneo",
                "high_desc": "100 (Mais difícil): Quase impossível / brutal",
            },
            "es": {
                "title": "Personas más fáciles a más difíciles de asesinar discretamente",
                "low_desc": "1 (Más fácil): Totalmente sin esfuerzo / instantáneo",
                "high_desc": "100 (Más difícil): Casi imposible / brutal",
            },
        },
    },
    {
        "id": "scale_nsfw_084",
        "pack": "nsfw",
        "title": "Worst to best ways to die",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores formas de bater as botas",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores formas de estirar la pata y morir",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_085",
        "pack": "nsfw",
        "title": "Worst to best things to search up on google",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores termos para pesquisar no histórico do Google",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores términos para buscar en Google",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_086",
        "pack": "nsfw",
        "title": "Easiest to hardest things to have to tell your parents",
        "low_desc": "1 (Easiest): Completely effortless / instant",
        "high_desc": "100 (Hardest): Brutally difficult / near impossible",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Confissões mais fáceis a mais difíceis de contar aos teus pais",
                "low_desc": "1 (Mais fácil): Sem qualquer esforço / instantâneo",
                "high_desc": "100 (Mais difícil): Quase impossível / brutal",
            },
            "es": {
                "title": "Confesiones más fáciles a más difíciles de confesarle a tus padres",
                "low_desc": "1 (Más fácil): Totalmente sin esfuerzo / instantáneo",
                "high_desc": "100 (Más difícil): Casi imposible / brutal",
            },
        },
    },
    {
        "id": "scale_nsfw_087",
        "pack": "nsfw",
        "title": "Worst to best things to do naked",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores atividades para fazer completamente nu",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores actividades para hacer completamente desnudo",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_088",
        "pack": "nsfw",
        "title": "Worst to best things to nickname your genitals",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores alcunhas para dar aos teus genitais",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores apodos para ponerle a tus genitales",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_089",
        "pack": "nsfw",
        "title": "Things that cause the least to the most pain",
        "low_desc": "1 (MIN): Lowest / minimal",
        "high_desc": "100 (MAX): Highest / maximum",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Causas de dor da menos à mais agonizante e insuportável",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
            "es": {
                "title": "Causas de dolor de menos a más agonizante e insoportable",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
        },
    },
    {
        "id": "scale_nsfw_090",
        "pack": "nsfw",
        "title": "Worst to best things to break",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Objetos ou regras do pior para o melhor de partir ou quebrar",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Cosas o reglas de peor a mejor para romper",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_091",
        "pack": "nsfw",
        "title": "Worst to best places to go swimming",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores sítios para dar um mergulho e nadar",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores lugares para ir a nadar",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_092",
        "pack": "nsfw",
        "title": "Reasons to get married from worst to best",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Motivações para casar da pior para a melhor",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Motivaciones para casarse de peor a mejor",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_093",
        "pack": "nsfw",
        "title": "Worst to best ways to get yourself to fall asleep",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores métodos para conseguir adormecer rápido",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores métodos para conciliar el sueño",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_094",
        "pack": "nsfw",
        "title": "The worst to best movies to make a porn parody of",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores filmes clássicos para criar uma paródia pornográfica",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores películas clásicas para hacer una parodia porno",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_095",
        "pack": "nsfw",
        "title": "Things you would do for $100 from easiest to hardest",
        "low_desc": "1 (Easiest): Completely effortless / instant",
        "high_desc": "100 (Hardest): Brutally difficult / near impossible",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Desafios que farias por 100€ do mais fácil ao mais humilhante e difícil",
                "low_desc": "1 (Mais fácil): Sem qualquer esforço / instantâneo",
                "high_desc": "100 (Mais difícil): Quase impossível / brutal",
            },
            "es": {
                "title": "Desafíos que harías por 100€ del más fácil al más difícil",
                "low_desc": "1 (Más fácil): Totalmente sin esfuerzo / instantáneo",
                "high_desc": "100 (Más difícil): Casi imposible / brutal",
            },
        },
    },
    {
        "id": "scale_nsfw_096",
        "pack": "nsfw",
        "title": "Things to do on the internet from least to most entertaining",
        "low_desc": "1 (Least Entertaining): Bare minimum / none",
        "high_desc": "100 (Most Entertaining): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Atividades na internet da menos para a mais divertida e viciante",
                "low_desc": "1 (Menos Entertaining): Mínimo absoluto",
                "high_desc": "100 (Mais Entertaining): Máximo absoluto / topo",
            },
            "es": {
                "title": "Actividades en internet de menos a más adictivas y entretenidas",
                "low_desc": "1 (Menos Entertaining): Mínimo absoluto",
                "high_desc": "100 (Más Entertaining): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_097",
        "pack": "nsfw",
        "title": "Worst to best nicknames to have",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores alcunhas que alguém te poderia dar",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores apodos o motes que te podrían poner",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
    {
        "id": "scale_nsfw_098",
        "pack": "nsfw",
        "title": "Fictional characters with the easiest to the hardest lives",
        "low_desc": "1 (MIN): Lowest / minimal",
        "high_desc": "100 (MAX): Highest / maximum",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Personagens de ficção com a vida da mais fácil e regalada à mais miserável",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
            "es": {
                "title": "Personajes ficticios con la vida de más fácil a más miserable",
                "low_desc": "1 (Mínimo): Mínimo absoluto",
                "high_desc": "100 (Máximo): Máximo absoluto",
            },
        },
    },
    {
        "id": "scale_nsfw_099",
        "pack": "nsfw",
        "title": "Problems that need to be solved by humanity from least to most important",
        "low_desc": "1 (Least Important): Bare minimum / none",
        "high_desc": "100 (Most Important): Maximum / peak",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Crises e problemas mundiais do menos para o mais urgente de resolver",
                "low_desc": "1 (Menos Important): Mínimo absoluto",
                "high_desc": "100 (Mais Important): Máximo absoluto / topo",
            },
            "es": {
                "title": "Problemas de la humanidad de menos a más urgentes de resolver",
                "low_desc": "1 (Menos Important): Mínimo absoluto",
                "high_desc": "100 (Más Important): Máximo absoluto / cumbre",
            },
        },
    },
    {
        "id": "scale_nsfw_100",
        "pack": "nsfw",
        "title": "Worst to best things you could use to blackmail someone with",
        "low_desc": "1 (Worst): Absolute worst / terrible",
        "high_desc": "100 (Best): Absolute best / legendary",
        "is_nsfw": True,
        "translations": {
            "pt": {
                "title": "Piores a melhores segredos para usar como chantagem contra alguém",
                "low_desc": "1 (Pior): O pior absoluto / terrível",
                "high_desc": "100 (Melhor): O melhor absoluto / lendário",
            },
            "es": {
                "title": "Peores a mejores secretos para usar como chantaje",
                "low_desc": "1 (Peor): Lo peor absoluto / desastroso",
                "high_desc": "100 (Mejor): Lo mejor absoluto / legendario",
            },
        },
    },
)


def get_prompt_pool(pack: str = "mix", allow_nsfw: bool = False) -> list[dict[str, Any]]:
    """Filter prompts according to chosen pack and 18+ spicy/NSFW settings."""
    pack_norm = (pack or "mix").lower()
    pool: list[dict[str, Any]] = []

    for p in RANKIT_PROMPTS:
        if p.get("is_nsfw", False) and not allow_nsfw and pack_norm != "nsfw":
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
