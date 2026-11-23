---
title: Reference - Decks, Prompts, and Question Packs Catalogue
tags: [reference, decks, questions, prompts, trivia, wordlists]
created: 2026-11-24
updated: 2026-11-24
---

# Reference: Decks, Prompts, and Question Packs Catalogue

This document provides a complete inventory and schema specification of all trivia questions, spectrum scales, speed categories, and word deduction pairs across the party game platform.

---

## 1. SmartN Trivia Deck Catalogue

SmartN utilizes a fact-checked trivia bank defined in `smartn/questions.py` and `smartn/decks/`.

### 1.1 Summary Metrics

- **Total Fact-Checked Questions**: 164
- **Topic Packs**: 7 (6 specialized domain decks + 1 universal mixed deck)
- **Question Types**: 4 (`true_false`, `order`, `match`, `number`)

### 1.2 Breakdown by Domain Pack

| Pack Identifier | Domain Name | Question Count | Question Type Distribution | Sample Title |
| :--- | :--- | :--- | :--- | :--- |
| **`geo`** | Geography & Places | **29** | `true_false`: 21, `order`: 3, `match`: 3, `number`: 2 | *World Capitals by Latitude*, *Island Nations* |
| **`media`** | Pop Culture & Cinema | **28** | `true_false`: 20, `order`: 4, `match`: 2, `number`: 2 | *Oscars Best Picture Winners*, *Streaming Records* |
| **`science`** | Science & Technology | **28** | `true_false`: 19, `order`: 4, `match`: 3, `number`: 2 | *Periodic Table Elements*, *Planetary Distances* |
| **`history`** | History & Civilizations | **27** | `true_false`: 20, `order`: 3, `match`: 2, `number`: 2 | *Roman Emperors*, *Centuries of Inventions* |
| **`food`** | Culinary & Cuisine | **26** | `true_false`: 18, `order`: 3, `match`: 3, `number`: 2 | *Global Cheeses by Origin*, *Scoville Heat Ranks* |
| **`sports`** | Sports & Athletics | **26** | `true_false`: 19, `order`: 3, `match`: 2, `number`: 2 | *Olympic Host Cities*, *Marathon Record Chronology* |
| **`mix`** | Mixed Variety | **164** | Combines all 6 domain decks into a uniform random distribution | Universal random pool |

### 1.3 Breakdown by Question Type

| Question Type | Cardinality | Mechanics & UI Representation | Validation Rule |
| :--- | :--- | :--- | :--- |
| **`true_false`** | **117** | 10 independent statement capsules covering a prompt topic. | Capsule evaluates directly to intrinsic correctness (`is_correct: True/False`). |
| **`order`** | **20** | 10 ranked capsules. Players select a capsule and assign predicted rank (`#1` to `#10`). | Capsule matches predicted rank: `prediction.strip("#") == item["value"].strip("#")`. |
| **`match`** | **15** | 10 association pairs linking clues to key terms. | Candidate association evaluated against canonical match target. |
| **`number`** | **12** | 10 numerical metric capsules (dates, populations, measurements). | Value evaluated against discrete threshold or exact target. |

### 1.4 Item Schema (`card["items"]`)

```json
{
  "slot": 1,
  "label": "Mount Kilimanjaro",
  "value": "#4",
  "is_correct": true,
  "explanation": "Highest peak in Africa at 5,895 meters."
}
```

---

## 2. Rank It! (*ito*) Spectrum Scales Catalogue

Rank It! features 200 spectrum prompts in `rankit/prompts.py` across 7 thematic categories.

### 2.1 Summary Metrics

- **Safe Party Prompts**: **100**
- **Spicy / Adult (18+ NSFW) Prompts**: **100**
- **Total Combined Pool**: **200**

### 2.2 Category Breakdown and Spectrum Scales

| Pack Key | Category Name | Count | Polarity Reference: $1 \to 100$ | Sample Prompt Title |
| :--- | :--- | :--- | :--- | :--- |
| **`everyday`** | Everyday Life & Annoyances | **30** | $1 = \text{Mildly Minor} \to 100 = \text{Pure Rage / Catastrophe}$ | *Things you hate hearing on a Monday morning* |
| **`classic`** | Classic Party Scales | **24** | $1 = \text{Weakest / Lowest} \to 100 = \text{Absolute God-Tier}$ | *Most universally loved foods on Earth* |
| **`superpowers`** | Sci-Fi & Superpowers | **15** | $1 = \text{Useless Trick} \to 100 = \text{Reality-Bending Power}$ | *Superpowers ranked by combat utility* |
| **`deep`** | Deep & Philosophical | **12** | $1 = \text{Trivial / Fleeting} \to 100 = \text{Life-Altering / Eternal}$ | *Hardest ethical dilemmas to resolve* |
| **`food`** | Culinary & Taste | **12** | $1 = \text{Unbearable Taste} \to 100 = \text{Divine Ambroy}$ | *Foods you'd crave on a desert island* |
| **`scary`** | Danger & Spooky | **7** | $1 = \text{Mild Creep} \to 100 = \text{Sheer Primordial Terror}$ | *Scariest sounds to hear in an empty forest* |
| **`nsfw`** | Spicy & NSFW (18+) | **100** | $1 = \text{Tame / Mild Flirt} \to 100 = \text{Outrageously Scandalous}$ | *Opt-in adult dating & taboo spectrums* |

### 2.3 Spectrum Item Schema

```json
{
  "id": "scale_annoyance_01",
  "pack": "everyday",
  "title": "Minor Inconveniences vs Life Ruins",
  "min_label": "1 = Untied shoelace",
  "max_label": "100 = Phone falling into an elevator shaft",
  "is_nsfw": false
}
```

---

## 3. Stop! (Tutti Frutti) Categories Catalogue

Stop! utilizes a composite dictionary and prompt framework (`stop/categories.py`) with 75 preset categories.

### 3.1 Packs Overview

- **`database`**: 21 curated categories with automated dictionary verification against Wiktionary lexicons and wordlists.
- **`party`**: 54 creative, humorous, and situational categories.
- **`spicy`**: Adult/cheeky situational prompts.
- **`mix`**: Weighted combination of Database and Party categories.
- **`custom`**: Room-specific user categories.

### 3.2 Database-Verified Categories (21 Categories)

| Category ID | Title | Wordlist Domain / Topics | Sample Words |
| :--- | :--- | :--- | :--- |
| `db_animal` | 🐾 Animals & Wildlife | `zoology`, `birds`, `mammals`, `fish`, `reptiles` | *Aardvark, Bear, Cheetah, Dolphin* |
| `db_food` | 🍕 Food & Cuisine | `gastronomy`, `dishes`, `cooking` | *Apple, Burrito, Curry, Dumpling* |
| `db_movie` | 🎬 Movies & Cinema | `films`, `cinema`, `blockbusters` | *Avatar, Batman, Casablanca* |
| `db_tvshow` | 📺 TV Shows & Series | `television`, `series`, `broadcast` | *Breaking Bad, Chernobyl, Dark* |
| `db_song` | 🎵 Songs & Tracks | `music`, `singles`, `tracks` | *Billie Jean, Creep, Despacito* |
| `db_place` | 🌍 Cities & Countries | `geography`, `capitals`, `nations` | *Amsterdam, Berlin, Cairo, Dublin* |
| `db_person` | 👤 Famous People | `celebrities`, `historical`, `leaders` | *Aristotle, Beethoven, Cleopatra* |
| `db_action` | 🏃 Verbs & Actions | `verbs`, `movement`, `actions` | *Accelerate, Bounce, Climb, Dance* |
| `db_thing` | 📦 Everyday Objects | `household`, `tools`, `furniture` | *Alarm, Blender, Chair, Door* |
| `db_fruits_veg` | 🥦 Fruits & Vegetables | `botany`, `produce`, `greens` | *Avocado, Broccoli, Carrot, Date* |
| `db_desserts_baking`| 🍰 Desserts & Sweets | `pastry`, `confectionery`, `baking` | *Baklava, Cannoli, Donut, Eclair* |
| `db_sports_games` | ⚽ Sports & Games | `athletics`, `games`, `competitions` | *Archery, Baseball, Cricket, Darts* |
| `db_music` | 🎸 Musical Instruments | `instruments`, `genres`, `audio` | *Accordion, Banjo, Clarinet, Drums* |
| `db_clothing` | 👗 Clothing & Wear | `fashion`, `garments`, `apparel` | *Anorak, Boots, Coat, Dress* |
| `db_computing_tech` | 💻 Tech & Computers | `hardware`, `software`, `internet` | *Algorithm, Browser, CPU, Database* |
| `db_anatomy_medicine`| 🩺 Anatomy & Medicine| `anatomy`, `organs`, `medical` | *Artery, Brain, Clavicle, Diaphragm* |
| `db_transport_travel`| 🚗 Vehicles & Transport| `vehicles`, `transit`, `aviation` | *Airplane, Bicycle, Canoe, Drone* |
| `db_jobs_roles` | 💼 Jobs & Careers | `professions`, `occupations`, `roles`| *Architect, Baker, Carpenter, Doctor* |
| `db_science_nature` | 🔬 Science & Space | `astronomy`, `chemistry`, `physics` | *Asteroid, Black hole, Comet, DNA* |
| `db_buildings_home` | 🏛️ Architecture & Home | `buildings`, `rooms`, `structures` | *Airport, Barn, Cabin, Dome* |
| `db_emotions_traits`| 🎭 Emotions & Traits | `psychology`, `feelings`, `traits` | *Anger, Bravery, Compassion, Delight*|

### 3.3 Sample Web Party Categories (54 Total)

| Category ID | Prompt Title | Context |
| :--- | :--- | :--- |
| `web_fired` | 🔥 Things that will get you fired | Workplace blunders and forbidden actions |
| `web_bad_smells` | 🦨 Things with an awful smell | Sensory horrors and kitchen disasters |
| `web_late_excuse` | ⏰ Excuses for being late to a meeting | Outrageous explanations and fabricated traffic |
| `web_dont_touch` | 🚫 Things you should never touch | Hazardous materials, museum exhibits, hot stoves |
| `web_bad_date` | 💔 Terrible first date activities | Awkward locations and conversation killers |
| `web_dumpster` | 🗑️ Things found behind a bowling alley | Bizarre discarded junk and questionable food |
| `web_fears` | 😱 Common phobias and irrational fears | Spiders, heights, dentists, public speaking |
| `web_zombie_weapon`| 🧟 Improvised zombie apocalypse weapons | Household items turned into lethal defense |

---

## 4. Word Impostor Curated Word Pairs

Word Impostor features 104 hand-curated tuples defined in `impostor/word_pairs.py`.

### 4.1 Category Distribution

$$\text{Total Word Pairs} = 104 = 18 + 18 + 16 + 14 + 12 + 10 + 8 + 8$$

| Category Slug | Category Display | Count | Percentage |
| :--- | :--- | :--- | :--- |
| **`no_theme`** | General Variety | **18** | 17.3% |
| **`thing`** | Objects & Inventions | **18** | 17.3% |
| **`food`** | Food & Drink | **16** | 15.4% |
| **`animal`** | Animals & Wildlife | **14** | 13.5% |
| **`place`** | Places & Architecture | **12** | 11.5% |
| **`person`** | Characters & Roles | **10** | 9.6% |
| **`movie`** | Movies & Cinema | **8** | 7.7% |
| **`sport`** | Sports & Activities | **8** | 7.7% |

### 4.2 Representative Tuple Examples

Each entry is a 4-element tuple: `(citizen_word, impostor_word, lethal_word, category)`.

```python
CURATED_IMPOSTOR_PAIRS = [
    # (Citizen Word, Impostor Word, Lethal Taboo Word, Category)
    ("Cactus", "Hedgehog", "Needle", "no_theme"),
    ("Coffee", "Tea", "Caffeine", "food"),
    ("Guitar", "Violin", "Strings", "thing"),
    ("Submarine", "Spaceship", "Oxygen", "thing"),
    ("Lion", "Tiger", "Stripes", "animal"),
    ("Doctor", "Veterinarian", "Animals", "person"),
    ("Hospital", "Prison", "Guards", "place"),
    ("Football", "Rugby", "Goalposts", "sport"),
    ("Titanic", "Iceberg", "Sink", "movie"),
]
```

### 4.3 Poisoned Citizen Mechanics

In `poisoned_citizen` mode:
- The loyal citizen ("The Drunk") receives a third coordinate term within the same semantic space (e.g. `Citizen: Coffee`, `Impostor: Tea`, `Poisoned Citizen: Hot Chocolate`).
- The verbatim guard rejects clues matching:

$$\text{normalize\_text}(\text{clue}) = \text{normalize\_text}(\text{assigned\_word})$$
