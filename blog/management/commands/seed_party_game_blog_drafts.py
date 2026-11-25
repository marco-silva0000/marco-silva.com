from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand

from blog.models import BlogIndexPage, BlogPostPage

BLOG_DRAFTS: list[dict] = [
    {
        "slug": "mathematics-of-secret-santa-hamiltonian-cycles",
        "title": "The Mathematics of Secret Santa: Why Naive Shuffles Ruin Gift Exchanges",
        "tags": ["algorithms", "combinatorics", "python", "party-games", "secret-santa"],
        "markdown": """Every December, thousands of offices, university dorms, and friend groups face the exact same coordination ritual: drop everyone's name into a hat, mix it up, and draw who buys a gift for whom.

And almost immediately, something goes wrong. Someone pulls their own name and announces it to the room, forcing a messy restart. Even when nobody draws themselves, half the room discovers at the gift unwrapping that Alice bought for Bob *and* Bob bought right back for Alice—turning a communal circle into an awkward little bilateral bubble.

When I built the [Secret Santa & Target Matcher](/games/create/?game=secretsanta) engine for `marco-silva.com`, I wanted the draw to feel completely effortless for guests while solving the underlying graph theory properly. As it turns out, "just shuffle a list" breaks down fast once you look at permutation cycles and real-world exclusions.

---

## Why Naive Shuffles Fail 63% of the Time

The classic developer instinct for Secret Santa is a five-line Python snippet:

```python
# BROKEN ANTI-PATTERN
targets = list(participants)
random.shuffle(targets)
matches = dict(zip(participants, targets))
```

In combinatorics, a permutation where no element maps to itself ($f(p_i) \\neq p_i$) is called a **derangement**, written $!n$. Using the Principle of Inclusion-Exclusion, the exact number of derangements of $n$ people is:

$$
!n = n! \\sum_{k=0}^{n} \\frac{(-1)^k}{k!}
$$

As the group grows, the fraction of valid derangements rapidly converges to $1/e \\approx 36.8\\%$. That means a naive random shuffle lands in an invalid state—with at least one person gifting themselves—roughly **63.2% of the time**.

You *could* wrap that shuffle in a retry loop (rejection sampling) until nobody matches themselves. For an unconstrained office party, that finishes quickly. But it completely collapses the moment you add two real-world requirements: **avoiding 2-cycles** and **handling social exclusions**.

---

## The Pathology of Isolated 2-Cycles

By the Fundamental Theorem of Permutations, every valid matching decomposes into disjoint directed cycles:

```mermaid
flowchart LR
    subgraph Bad["Disjoint 2-Cycles (Socially Awkward)"]
        A1["Alice"] <--> B1["Bob"]
        C1["Carol"] --> D1["Dave"]
        D1 --> E1["Emma"]
        E1 --> C1
    end
    subgraph Good["Unified Hamiltonian Cycle (Ideal Party Flow)"]
        A2["Alice"] --> B2["Bob"]
        B2 --> C2["Carol"]
        C2 --> D2["Dave"]
        D2 --> E2["Emma"]
        E2 --> A2
    end
```

A 2-cycle happens whenever $f(A) = B$ and $f(B) = A$. Mathematically, that is a completely valid derangement. Socially, it ruins the surprise:

- **In a 4-person exchange**, two 2-cycles reduce the whole party to two isolated pairs swapping gifts across the table.
- **Deduction leakage**: If Alice hands her gift to Bob and Bob immediately hands his gift back to Alice, the suspense evaporates.

What a party actually wants is a **single directed Hamiltonian cycle** of length $N$: $p_1 \\to p_2 \\to \\dots \\to p_n \\to p_1$. For any group of $N \\ge 3$ participants, a single unified cycle guarantees **zero 2-cycles** and connects the entire room into one unbroken chain.

---

## Real-World Exclusions: Couples, Roommates, and NP-Completeness

Real groups rarely allow every person to draw every other person. Partners who share a bank account don't want to buy for each other; roommates want a surprise outside their apartment; repeat annual groups ban last year's pairing.

With exclusions, we are no longer sampling permutations of a complete graph—we are searching for a directed Hamiltonian cycle inside an arbitrary directed compatibility graph $G = (V, E)$. Finding a Hamiltonian cycle in an arbitrary directed graph is one of Richard Karp's classic NP-complete problems. Worse yet, heavily constrained exclusion graphs might not have *any* single Hamiltonian cycle even when valid multi-cycle derangements exist (for example, two separate 3-cycles).

---

## The Two-Tier Solver in `secretsanta`

To give groups sub-millisecond draws without stalling, `solve_matching` in `secretsanta/game_state.py` runs a hybrid two-tier pipeline:

```mermaid
flowchart TD
    Start["solve_matching(pids, exclusions)"] --> Preflight["O(V+E) Pre-Flight Checks<br>Every giver has >= 1 target<br>Every target has >= 1 giver"]
    Preflight --> Tier1["Tier 1: Randomized Hamiltonian Path Extension<br>(Up to 400 randomized trials)"]
    Tier1 -->|Closed N-Cycle Found| Done1["Return Unified Cycle (0 Two-Cycles)"]
    Tier1 -->|Blocked by Dense Exclusions| Tier2["Tier 2: Randomized MRV Backtracking<br>+ 2-Cycle Penalty Heuristic"]
    Tier2 --> Done2["Return Best Valid Derangement"]
```

1. **Pre-Flight Feasibility Checks**: Before searching, it verifies every participant has out-degree $\\ge 1$ and in-degree $\\ge 1$. If someone over-excluded the room, the host gets an immediate, clear error message instead of a spinning wheel.
2. **Tier 1 — Randomized Hamiltonian Extension**: Up to 400 times, the solver walks an unvisited random path from a random starter and checks whether the final person has a valid edge back to the starter. For almost every real party, this finds a clean, single-loop cycle in microseconds.
3. **Tier 2 — MRV Backtracking with 2-Cycle Penalty**: If dense exclusions prevent a single loop, the solver switches to Minimum Remaining Values (MRV) backtracking—assigning the most constrained participant first so impossible branches fail at depth 1—while sorting candidate targets to push immediate 2-cycles ($A \\leftrightarrow B$) to the very back of the queue unless mathematically unavoidable.

Once matched, every participant uses a **Tap-and-Hold privacy curtain** over WebSockets so nobody sitting beside you on the couch can glance at your target either.

### Deep Dive in the Docs
- **Explanation**: [Combinatorics of Secret Santa](/docs/explanation/explanation-combinatorics-of-secret-santa/)
- **Reference**: [Matching Algorithms & Constraints](/docs/reference/reference-matching-algorithms-and-constraints/)
- **How-To**: [Host Secret Santa with Exclusions](/docs/how-to/how-to-host-secret-santa-with-exclusions/)
""",
    },
    {
        "slug": "designing-anti-hivemind-games-penalizing-groupthink",
        "title": "Designing Anti-Hivemind Games: The Joy of Penalizing Groupthink",
        "tags": ["game-theory", "linguistics", "python", "party-games", "dontsay", "stop"],
        "markdown": """Traditional quiz games reward knowing what everyone else knows. If a trivia card asks for a famous Italian painter and you shout *"Leonardo da Vinci"* fastest, you win the point.

Anti-hivemind games flip that instinct upside down. In [*Don't Say the Same Thing as Me*](/games/create/?game=dontsay) and [*Stop!*](/games/create/?game=stop), the most obvious answer in your head isn't a free point—it's a landmine. If you thought of *"Paris"* or *"Apple"* within half a second, chances are three other people at the table just typed the exact same word.

Building both games on `marco-silva.com` taught me that penalizing groupthink produces incredible living-room comedy—and a surprisingly tricky string-matching problem on the backend.

---

## Inverting the Schelling Point

In 1960, economist Thomas Schelling described the **focal point** (now called a *Schelling point*): the default solution strangers converge on when they cannot communicate, simply because it feels culturally prominent or obvious. Ask two strangers to pick a meeting spot in New York City without talking, and they overwhelmingly converge on Grand Central Terminal at noon.

In anti-hivemind party games, the Schelling point becomes toxic, triggering what behavioral game theorists call **$k$-level recursive thinking**:

```mermaid
flowchart TD
    Prompt["Prompt: 'Name a European Country'"] --> L0["Level-0: Immediate Salience<br>'France! Germany! Italy!'"]
    L0 --> L1["Level-1: Crowd Avoidance<br>'Everyone will pick France.<br>I will pick Portugal.'"]
    L1 --> L2["Level-2: The Overthinking Trap<br>'Wait, my friends are clever.<br>They will all pick Portugal!<br>Let me write Liechtenstein!'"]
    L2 --> Crash["3 Clever Friends Crash on 'Liechtenstein' -> 0 Points!"]
```

The magic happens on reveal: three players groan in unison because they all outsmarted themselves into writing *"Liechtenstein"*, while someone who panicked at the buzzer with *"Belgium"* pockets $+100$ points untouched.

To push that tension even further, `dontsay` includes **Harsh Mode** ($-50$ points per collision, introducing real loss aversion) and **"The ME" Elimination Mode**, where one designated player becomes a moving target—regular players don't clash with each other, *only* colliding with The ME's secret word eliminates you.

---

## Speed vs. Obscurity in *Stop!*

*Stop!* layers clock pressure right on top of the Schelling trap. Everyone receives the same letter (say, `M`) and five categories. The moment the fastest player fills their sheet and slams **STOP!**, the server broadcasts a synchronized 10-second final rush across every connected phone.

Now you face a brutal trade-off:
- **Fast Level-0 answers** (*Monkey*, *Mango*) let you hit STOP first, but duplicate clashes drop your payoff from $+10$ (plus up to $+5$ speed rank bonus) down to $+5$ or $0$.
- **Level-1/2 obscure answers** (*Marmoset*, *Mangosteen*) protect uniqueness, yet slow your typing down while the 10-second alarm ticks away.

---

## The Engineering Problem: When Are Two Strings "The Same"?

On paper, friends instantly agree that `"apple"` and `"Apples"` are a clash, or that `"The Beatles"` and `"beatles"` collide. On mobile phones in five different languages, naive equality (`a == b`) fails immediately: one player's keyboard autocorrects `"maçã"`, another types `"maca"`, and a third drops the silent letter in `"rasberry"`.

At the same time, naive Levenshtein edit distance creates disastrous false positives: `"cat"` and `"car"`, `"bear"` and `"beer"`, and `"rose"` and `"rome"` all have edit distance $1$, yet they are completely different answers!

To balance strictness with fairness, `gamerooms/prompt_engine/evaluator.py` runs a five-stage deterministic pipeline:

1. **Unicode NFKD/NFD Normalization**: Decomposes accents and strips all non-spacing combining marks (`Mn`), collapsing `"São Paulo"` and `"sao paulo"` cleanly.
2. **Multilingual Article Stripping**: Removes leading articles across English, Portuguese, Spanish, Italian, and French (`the`, `o/a`, `el/la`, `il/lo`, `le/la`, etc.).
3. **Spacing & Plural Folding**: Collapses internal spaces (`"mona lisa"` vs `"monalisa"`) and simple plural suffixes (`s`, `es`).
4. **Short-Word & Phonetic Guards**: Words of $N \\le 3$ letters must match **exactly**—never clashing `"cat"` with `"car"`. For 4-letter words, edit distance $1$ is only allowed for narrow phonetic swaps (`c/k`, `i/y`, `s/z`), rejecting `"rose"` vs `"rome"`.
5. **Length-Bounded Edit Distance**: Longer words ($5+$ characters) forgive genuine keyboard typos like `"rasberry"` vs `"raspberry"` when combined with a high sequence similarity ratio.

---

## Human Sovereignty Over Algorithms

No regex or distance metric knows whether `"Holland"` and `"The Netherlands"` should clash in geography trivia, or whether an inside joke deserves validity. That is why every automated cluster in `dontsay` and `stop` is paired with 1-tap host overrides (`toggle_clash`, `toggle_validity`)—the server does the tedious cleanup, and the room's host holds the final gavel.

### Deep Dive in the Docs
- **Explanation**: [Anti-Hivemind Game Design](/docs/explanation/explanation-anti-hivemind-game-design/)
- **Reference**: [Scoring Formulas & Point Matrices](/docs/reference/reference-scoring-formulas-and-point-matrices/)
- **How-To**: [Play Don't Say Anti-Hivemind](/docs/how-to/how-to-play-dontsay-anti-hivemind/) · [Run a High-Speed Stop! Race](/docs/how-to/how-to-run-high-speed-stop-race/)
""",
    },
    {
        "slug": "push-your-luck-psychology-couch-party-games",
        "title": "Push-Your-Luck Psychology: Bringing Physical Party Games to Couches and WebSockets",
        "tags": ["ux-design", "game-design", "websockets", "smartn", "rankit", "lupus"],
        "markdown": """Most browser party games assume everyone at the table wants to stare down at their own phone screen for two hours. Anyone who has actually hosted a dinner party knows that falls apart fast: one guest's battery is at 4%, an older relative doesn't want to scan a QR code, and half the fun of a board game is watching everyone's eyes lock onto the same physical object in the middle of the table.

While building the party game suite on `marco-silva.com`, some of the most rewarding design problems weren't about networking at all—they were about preserving living-room rituals across both multi-phone rooms and single-device couch play.

---

## Prospect Theory and the Round Basket in SmartN

[*SmartN*](/games/create/?game=smartn) is a push-your-luck trivia wheel built around 10 hidden capsules per card. Every correct answer drops $+1$ point into your temporary round basket. On every turn, you make one agonizing choice: **Pass & Bank** what you have earned into your permanent score, or **Push Your Luck** for one more capsule—knowing that a single wrong answer zeroes your entire basket and knocks you out of the card.

```mermaid
stateDiagram-v2
    [*] --> TurnDecision: Active Player's Turn
    TurnDecision --> Banked: Tap "Pass & Bank" (Keep Basket Safely)
    TurnDecision --> RevealCapsule: Tap Covered Capsule (Push Luck)
    RevealCapsule --> TurnDecision: Correct! (+1 to Basket, Higher Stakes)
    RevealCapsule --> Busted: Wrong! (Basket Drops to 0, Eliminated from Card)
```

In behavioral economics, Kahneman and Tversky's **Prospect Theory** explains why a three-capsule streak makes the whole couch shout at the screen. Losing $B$ points hurts roughly twice as much as gaining $B$ points feels good, and the **endowment effect** makes unbanked points feel like yours the moment they sit in your basket. Mathematically, your expected value on the next guess is:

$$
E(V) = p_{\\text{correct}} \\cdot (B + 1) + (1 - p_{\\text{correct}}) \\cdot (-B)
$$

Every extra capsule linearly increases what you stand to lose $(-B)$ while adding at most $+1$. Rational play says bank early—yet the living room's Greek chorus dares you to push just once more.

---

## Designing One Phone as a Physical Toy ("Couch Mode")

A physical *Smart 10* box feels great because you literally pass a shared plastic wheel around the table. To recreate that ritual digitally, SmartN includes a first-class **Single-Device Couch Mode**:

- **The Animated Handoff Banner**: Between turns, the UI clearly announces *"Pass the Smartbox to Alice!"* so the phone acts as a physical baton around the table.
- **Hidden GM Drawer (`#gm-drawer`)**: If host controls (score target changes, capsule answer overrides, adding a friend who just walked into the room) sat right on the main board, players passing the phone would see spoilers or tap admin controls by mistake. Tucking them inside a discrete slide-out drawer keeps the playing board pure and toy-like.
- **Direct Capsule Overrides**: In living-room trivia, edge cases happen (*"Wait, does Pluto count?"*). Tapping any already-revealed capsule lets the host adjudicate disputed answers cleanly without breaking the flow of the card.

---

## Empathy and Psychological Safety in *Rank It!* (*ito*)

Not every room wants cutthroat push-your-luck bets. [*Rank It!*](/games/create/?game=rankit) creates the exact opposite social energy: cooperative calibration. Each player secretly draws numbers from $1$ to $100$ and gives qualitative clues along an absurd spectrum (*"Least painful to most painful"* or *"Weakest superpower to god-tier"*), without ever saying a number aloud.

The UX trick that kills "alpha-gamer blame" is the **face-down communal timeline** paired with the **Swap Consensus Engine**. Placements feel provisional rather than permanent, and any player can propose swapping two adjacent cards before the left-to-right reveal flips them over. When an inversion costs the team a heart, everyone laughs together because everyone debated the swap.

---

## From Couch Warm-Up to Tribal Courtroom

Having distinct psychological engines on one platform lets a host deliberately pace a night: start with warm empathetic debate in *Rank It!*, crank up spectator cheering with *SmartN*'s push-your-luck busts, and finish late at night with the paranoia of *Word Impostor* (especially with a clueless Poisoned Citizen defending themselves in full sincerity) or a circular ring-table trial in *Lupus in Tabula*.

### Deep Dive in the Docs
- **Explanation**: [Party Game Psychology & Group Dynamics](/docs/explanation/explanation-party-game-psychology-and-group-dynamics/)
- **Tutorials**: [Playing SmartN in Couch Mode](/docs/tutorials/tutorial-playing-smartn-couch-mode/)
- **How-To**: [Calibrate Clues in Rank It!](/docs/how-to/how-to-calibrate-clues-in-rank-it-ito/) · [Use SmartN GM Drawer & Overrides](/docs/how-to/how-to-use-smartn-gm-drawer-and-overrides/)
""",
    },
    {
        "slug": "zero-spoiler-architecture-django-channels-websockets",
        "title": "Zero-Spoiler Architecture: Securing Real-Time Hidden Role Games with Django Channels",
        "tags": ["security", "architecture", "django-channels", "websockets", "asgi", "redis"],
        "markdown": """When developers build a multiplayer web game for friends, the fastest prototype looks something like this: keep the game dictionary in memory, dump the whole JSON object into a Django Channels `group_send()`, and let the browser hide what the player shouldn't see using `display: none` or an `if (player.id === me)` check.

In any game with hidden information—Werewolf roles, Impostor secret words, Secret Santa targets, face-down numbers in *Rank It!*, or covered trivia capsules in *SmartN*—that shortcut is a total security failure. Any player with Chrome DevTools open on the Network tab can read the entire game state in plaintext before round one even starts.

This is how I designed the **Zero-Spoiler Security Architecture** across all 9 game engines on `marco-silva.com`—and the two unexpected production bugs (seat-hijacking URLs and a 5-second Redis disconnect loop) we solved along the way.

---

## The Zero-Spoiler Projection Invariant

Every engine on the platform treats the browser as an **untrusted display terminal**:

> Secret state (unopened answers, other players' roles, hidden card numbers, Secret Santa assignments) must never leave server memory toward an unauthorized WebSocket. Inspecting the raw WebSocket frame must show `null` or completely omit forbidden fields.

That creates a subtle problem in Django Channels. Pub/sub channel layers exist to broadcast **one identical message** efficiently to every subscriber in a room group. But in a 10-person *Lupus* or *Secret Santa* match, all 10 players require 10 mathematically distinct views of the same state!

### The Signal-and-Project Pattern

Instead of sending game state *through* the Redis channel layer, the channel layer carries **zero-data synchronization ticks**:

```mermaid
sequenceDiagram
    autonumber
    actor A as Alice's Browser
    participant CA as Daphne Consumer (Alice)
    participant CL as Redis Channel Layer
    participant DB as Redis Game State
    participant CB as Daphne Consumer (Bob)
    actor B as Bob's Browser

    A->>CA: action: "draw_matches"
    CA->>DB: Save canonical truth in Redis
    CA->>CL: group_send(room, {"type": "sync_state"})
    Note over CL: Empty wakeup signal (0 secrets on pub/sub)
    par Independent Unicast Projections
        CL->>CA: sync_state
        CA->>DB: Read canonical state
        CA->>A: send_json(get_sanitized_player_view(state, Alice))
    and
        CL->>CB: sync_state
        CB->>DB: Read canonical state
        CB->>B: send_json(get_sanitized_player_view(state, Bob))
    end
```

Each consumer wakes up independently, reads the authoritative room dictionary from Redis, passes it through `get_sanitized_player_view(state, viewer_id=self.player_id)`, and unicasts only what that specific connection is allowed to know at the current phase. Even if someone intercepts Alice's WebSocket stream, Bob's secret target or role literally does not exist in the JSON bytes.

For physical co-located play, we layer a **Tap-and-Hold Privacy Shield** in the DOM (`pointerdown` reveals, `pointerup`/`pointercancel`/`blur` snaps shut immediately) so adjacent eyes on the couch are defeated too.

---

## Eliminating Seat-Hijacking URLs

Early versions of several games encoded the player's name right in the path: `/games/impostor/ABCD/Alice/`. That created a classic human failure mode in living rooms: the host copies their browser address bar to invite friends on WhatsApp, everyone taps the link, and five phones simultaneously hijack `"Alice"`'s seat and admin controls.

We unified all 9 engines onto **Generation 3 Clean URLs** (`/games/<slug>/<CODE>/play/`) backed by a strict split:
- **Public Invite Links (`/games/<CODE>/`)**: What QR modals and Copy Link buttons share. Always onboards a new participant cleanly.
- **Session-First Identity**: Tokens live inside encrypted HTTP sessions (with explicit private `?token=` reconnect links tucked behind a warning inside the settings drawer). Legacy name URLs automatically return a 302 redirect via `legacy_game_redirect`.

---

## Hunting Down a 5-Second Redis Disconnect Loop

Right after launching Secret Santa under Daphne 4.2, `channels-redis 4.3.0`, and `redis-py 8.1.0`, live rooms hit an infuriating bug: every client WebSocket connected cleanly, stayed open for ~5.5 seconds, disconnected, reconnected, and repeated forever.

Tracing the ASGI worker logs revealed a **microsecond race condition**:

1. `channels-redis` polls Redis group queues with a hardcoded 5-second blocking call: `bzpopmin(channel_key, timeout=5)`.
2. Under `redis-py 8.1.0`, implicit pool socket timeouts also defaulted closely to 5 seconds.
3. Whenever Redis unblocked at `5.000s` and network jitter delayed the empty response packet by half a millisecond, the OS TCP read timeout fired *first*, raising `redis.exceptions.TimeoutError` inside the Daphne listener coroutine and tearing down the WebSocket.

The fix in `website/settings.py` was decoupling the TCP socket timeout cleanly from the 5-second `bzpopmin` interval (`"socket_timeout": 30`, `"socket_connect_timeout": 10`). With a 25-second cushion, empty polls return gracefully and WebSockets stay open indefinitely.

### Deep Dive in the Docs
- **Explanation**: [Zero-Spoiler Security Architecture](/docs/explanation/explanation-zero-spoiler-security-architecture/) · [Evolution of Party Game URLs & WebSockets](/docs/explanation/explanation-evolution-of-party-game-urls/)
- **Reference**: [WebSocket Actions & URL Routes](/docs/reference/reference-websocket-actions-and-url-routes/)
""",
    },
]


class Command(BaseCommand):
    help = "Seed the 4 party-game narrative blog posts as Wagtail DRAFTS (never published)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-drafts",
            action="store_true",
            help="Update existing unpublished draft posts matching these slugs (live posts are never touched).",
        )

    def handle(self, *args, **options):
        update_drafts = options["update_drafts"]

        if not BlogIndexPage.objects.exists():
            self.stdout.write("BlogIndexPage missing — running setup_blog first...")
            call_command("setup_blog")

        blog_index = BlogIndexPage.objects.first()
        if not blog_index:
            self.stderr.write("Unable to resolve BlogIndexPage after setup_blog.")
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for spec in BLOG_DRAFTS:
            slug = spec["slug"]
            existing = BlogPostPage.objects.child_of(blog_index).filter(slug=slug).first()

            if existing is not None:
                if existing.live or not update_drafts:
                    skipped_count += 1
                    state_label = "live" if existing.live else "draft"
                    self.stdout.write(f"Skipped existing {state_label} post: {slug}")
                    continue

                existing.title = spec["title"]
                existing.body = [("markdown", spec["markdown"])]
                existing.tags.set(spec["tags"])
                existing.live = False
                existing.has_unpublished_changes = True
                existing.save()
                existing.save_revision()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"Updated draft revision: {slug}"))
                continue

            post = BlogPostPage(
                title=spec["title"],
                slug=slug,
                body=[("markdown", spec["markdown"])],
                live=False,
                has_unpublished_changes=True,
            )
            post.tags.add(*spec["tags"])
            blog_index.add_child(instance=post)
            post.save()
            post.save_revision()
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"Created draft post: {slug} (id={post.id}, live={post.live})"))

        self.stdout.write(f"Summary: created={created_count}, updated={updated_count}, skipped={skipped_count}")
