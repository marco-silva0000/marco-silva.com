import random

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import EmojinaryWord

# In-memory game state per room (for simplicity — not persistent across restarts)
GAMES = {}


class GameState:
    def __init__(self):
        self.players = {}  # channel_name -> {name, score}
        self.turn_order = []
        self.current_turn = 0
        self.current_word = None
        self.current_category = None
        self.emoji_clue = ""
        self.round_num = 0
        self.started = False
        self.guessed = set()  # players who guessed correctly this round

    @property
    def current_player(self):
        if not self.turn_order:
            return None
        return self.turn_order[self.current_turn % len(self.turn_order)]

    def player_list(self):
        return [
            {"name": info["name"], "score": info["score"], "is_turn": ch == self.current_player}
            for ch, info in self.players.items()
        ]

    def next_round(self):
        self.current_turn += 1
        self.round_num += 1
        self.emoji_clue = ""
        self.guessed = set()
        # Pick a random word
        words = list(EmojinaryWord.objects.values_list("text", "category"))
        if words:
            self.current_word, self.current_category = random.choice(words)
        else:
            self.current_word, self.current_category = "test word", "thing"

    def check_guess(self, guess):
        """Check guess against current word. Returns (correct, partial_matches)."""
        if not self.current_word:
            return False, []
        guess_lower = guess.strip().lower()
        word_lower = self.current_word.lower()
        if guess_lower == word_lower:
            return True, []
        # Partial matching — check individual words
        word_parts = word_lower.split()
        guess_parts = guess_lower.split()
        matches = [w for w in word_parts if w in guess_parts and len(w) > 2]
        return False, matches


class EmojinaryConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"]
        self.group_name = f"emojinary_{self.code}"
        self.player_name = None

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        if self.code not in GAMES:
            GAMES[self.code] = GameState()

    async def disconnect(self, close_code):
        game = GAMES.get(self.code)
        if game and self.channel_name in game.players:
            name = game.players[self.channel_name]["name"]
            del game.players[self.channel_name]
            if self.channel_name in game.turn_order:
                game.turn_order.remove(self.channel_name)
            await self.channel_layer.group_send(
                self.group_name, {"type": "game.message", "msg": f"{name} left", "players": game.player_list()}
            )
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        action = content.get("action")
        game = GAMES.get(self.code)
        if not game:
            return

        if action == "join":
            self.player_name = content.get("name", "anon")
            game.players[self.channel_name] = {"name": self.player_name, "score": 0}
            game.turn_order.append(self.channel_name)
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "game.message", "msg": f"{self.player_name} joined", "players": game.player_list()},
            )

        elif action == "start":
            if len(game.players) < 2:
                await self.send_json({"type": "error", "msg": "need at least 2 players"})
                return
            game.started = True
            game.next_round()
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "game.new_round",
                    "round": game.round_num,
                    "category": game.current_category,
                    "word_length": len(game.current_word),
                    "current_player": game.players[game.current_player]["name"],
                    "players": game.player_list(),
                },
            )
            # Send the actual word only to the current player
            await self.channel_layer.send(game.current_player, {"type": "game.your_word", "word": game.current_word})

        elif action == "emoji":
            if self.channel_name != game.current_player:
                return
            game.emoji_clue = content.get("emoji", "")
            await self.channel_layer.group_send(
                self.group_name, {"type": "game.emoji_update", "emoji": game.emoji_clue}
            )

        elif action == "guess":
            if self.channel_name == game.current_player:
                return
            if self.channel_name in game.guessed:
                return
            guess = content.get("guess", "")
            correct, partial = game.check_guess(guess)
            if correct:
                game.guessed.add(self.channel_name)
                game.players[self.channel_name]["score"] += 10
                game.players[game.current_player]["score"] += 5
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "game.correct",
                        "guesser": self.player_name,
                        "word": game.current_word,
                        "players": game.player_list(),
                    },
                )
                # Auto next round if all guessed
                if len(game.guessed) >= len(game.players) - 1:
                    game.next_round()
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type": "game.new_round",
                            "round": game.round_num,
                            "category": game.current_category,
                            "word_length": len(game.current_word),
                            "current_player": game.players[game.current_player]["name"],
                            "players": game.player_list(),
                        },
                    )
                    await self.channel_layer.send(
                        game.current_player, {"type": "game.your_word", "word": game.current_word}
                    )
            elif partial:
                await self.send_json({"type": "partial", "matches": partial, "guess": guess})
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "game.chat", "name": self.player_name, "msg": f"{'_' * len(guess)} (partial match!)"},
                )
            else:
                await self.channel_layer.group_send(
                    self.group_name, {"type": "game.chat", "name": self.player_name, "msg": guess}
                )

        elif action == "skip":
            if self.channel_name != game.current_player:
                return
            await self.channel_layer.group_send(
                self.group_name, {"type": "game.message", "msg": f"Skipped! The word was: {game.current_word}"}
            )
            game.next_round()
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "game.new_round",
                    "round": game.round_num,
                    "category": game.current_category,
                    "word_length": len(game.current_word),
                    "current_player": game.players[game.current_player]["name"],
                    "players": game.player_list(),
                },
            )
            await self.channel_layer.send(game.current_player, {"type": "game.your_word", "word": game.current_word})

    # Group message handlers
    async def game_message(self, event):
        await self.send_json({"type": "message", "msg": event["msg"], "players": event.get("players")})

    async def game_new_round(self, event):
        await self.send_json(
            {
                "type": "new_round",
                "round": event["round"],
                "category": event["category"],
                "word_length": event["word_length"],
                "current_player": event["current_player"],
                "players": event.get("players"),
            }
        )

    async def game_your_word(self, event):
        await self.send_json({"type": "your_word", "word": event["word"]})

    async def game_emoji_update(self, event):
        await self.send_json({"type": "emoji_update", "emoji": event["emoji"]})

    async def game_correct(self, event):
        await self.send_json(
            {
                "type": "correct",
                "guesser": event["guesser"],
                "word": event["word"],
                "players": event.get("players"),
            }
        )

    async def game_chat(self, event):
        await self.send_json({"type": "chat", "name": event["name"], "msg": event["msg"]})
