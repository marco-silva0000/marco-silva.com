"""WebSocket consumer for real-time Lupus game synchronization."""

from typing import Any, Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import (
    add_player,
    adjust_timer,
    cast_final_vote,
    clear_gm_night_action,
    get_game,
    get_gm_view,
    get_sanitized_player_view,
    guess_angel_in_limbo,
    move_player,
    pause_timer,
    proceed_to_defense,
    proceed_to_final_vote,
    record_gm_final_vote_tally,
    record_gm_night_action,
    remove_player,
    reorder_players,
    reset_timer,
    reset_voting,
    resolve_night,
    resume_timer,
    return_to_lobby,
    reveal_detective_to_player,
    save_game,
    set_broadcast_message,
    set_deck,
    set_manual_player_role,
    set_night_stage_index,
    set_nomination_tally_direct,
    set_player_status,
    set_round_number,
    setup_demo_room,
    start_game,
    start_timer,
    start_voting_session,
    tally_and_resolve_vote,
    toggle_nomination_vote,
    toggle_official_nomination,
)


class LupusConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str = ""
        self.group_name: str = ""
        self.is_gm: bool = False
        self.player_id: Optional[str] = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"lupus_{self.code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        state = get_game(self.code)
        if state and self.player_id and self.player_id in state["players"]:
            state["players"][self.player_id]["connected"] = False
            state["players"][self.player_id]["channel_name"] = None
            save_game(self.code, state)
            await self.broadcast_sync()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def broadcast_sync(self):
        """Instruct all connected clients in the room to re-render their perspective."""
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "game.state.sync"},
        )

    async def game_state_sync(self, event):
        """Handle room broadcast by delivering private sanitized state to this connection."""
        state = get_game(self.code)
        if not state:
            return

        if self.is_gm:
            await self.send_json({"type": "gm_state", "data": get_gm_view(state)})
        elif self.player_id:
            if self.player_id not in state["players"]:
                await self.send_json(
                    {"type": "player_kicked", "message": "You were removed from this room by the Game Master."}
                )
                return
            await self.send_json(
                {
                    "type": "player_state",
                    "data": get_sanitized_player_view(state, self.player_id),
                }
            )

    async def player_kicked_event(self, event):
        await self.send_json(
            {
                "type": "player_kicked",
                "message": event.get("message", "You were removed from this room by the Game Master."),
            }
        )

    async def receive_json(self, content: dict[str, Any]):
        action = content.get("action")
        state = get_game(self.code)
        if not state:
            await self.send_json({"type": "error", "message": "Room not found."})
            return

        # 1. Connection Identification & Reconnection Handshake
        if action == "init":
            gm_token = content.get("gm_token")
            player_token = content.get("player_token")
            player_id = content.get("player_id")

            if gm_token and gm_token == state.get("gm_token"):
                self.is_gm = True
                await self.send_json({"type": "gm_state", "data": get_gm_view(state)})
                return

            if player_token or player_id:
                for pid, p in state["players"].items():
                    if (player_token and p["token"] == player_token) or (player_id and p["id"] == player_id):
                        self.player_id = pid
                        p["connected"] = True
                        p["channel_name"] = self.channel_name
                        save_game(self.code, state)
                        await self.send_json(
                            {
                                "type": "player_state",
                                "data": get_sanitized_player_view(state, self.player_id),
                            }
                        )
                        await self.broadcast_sync()
                        return

            await self.send_json({"type": "auth_error", "message": "Unrecognized session."})
            return

        # 2. Game Master Authorized Operations
        if self.is_gm:
            if action == "start_game":
                deck = content.get("deck")
                start_game(state, deck)
                await self.broadcast_sync()

            elif action == "return_to_lobby":
                return_to_lobby(state)
                await self.broadcast_sync()

            elif action == "set_deck":
                deck = content.get("deck", [])
                set_deck(state, deck)
                await self.broadcast_sync()

            elif action == "deal_roles":
                deck = content.get("deck")
                start_game(state, deck)
                await self.broadcast_sync()

            elif action == "set_manual_role":
                pid = content.get("player_id")
                rid = content.get("role_id")
                if pid and rid:
                    set_manual_player_role(state, pid, rid)
                    await self.broadcast_sync()

            elif action == "set_status":
                pid = content.get("player_id")
                status = content.get("status")
                if pid and status in ("alive", "limbo", "dead"):
                    set_player_status(state, pid, status)
                    await self.broadcast_sync()

            elif action == "add_offline_player":
                name = content.get("name", "").strip()
                if name:
                    add_player(state, name, is_offline=True)
                    await self.broadcast_sync()

            elif action == "autofill_demo_players":
                if state.get("phase") == "lobby":
                    setup_demo_room(state)
                    await self.broadcast_sync()

            elif action == "remove_player":
                pid = content.get("player_id")
                if pid:
                    target_player = state["players"].get(pid)
                    if target_player and target_player.get("channel_name"):
                        try:
                            await self.channel_layer.send(
                                target_player["channel_name"],
                                {
                                    "type": "player.kicked.event",
                                    "message": "You were removed from this room by the Game Master.",
                                },
                            )
                        except Exception:
                            pass
                    remove_player(state, pid)
                    await self.broadcast_sync()

            elif action == "reorder_players":
                order = content.get("player_order", [])
                if isinstance(order, list):
                    reorder_players(state, order)
                    await self.broadcast_sync()

            elif action == "move_player":
                pid = content.get("player_id")
                direction = content.get("direction")
                if pid and direction in ("up", "down"):
                    move_player(state, pid, direction)
                    await self.broadcast_sync()

            elif action == "set_round_number":
                round_num = content.get("round_number", 1)
                set_round_number(state, round_num)
                await self.broadcast_sync()

            elif action == "broadcast_message":
                msg_text = content.get("message", "")
                set_broadcast_message(state, msg_text)
                await self.broadcast_sync()

            elif action == "clear_broadcast":
                set_broadcast_message(state, "")
                await self.broadcast_sync()

            elif action == "change_phase":
                new_phase = content.get("phase")
                if new_phase in ("lobby", "night", "day_discussion", "day_defense", "day_voting", "gameover"):
                    if new_phase == "day_voting":
                        start_voting_session(state)
                    else:
                        state["phase"] = new_phase
                        if new_phase == "night":
                            set_night_stage_index(state, 0)
                            state["revealed_inspect"] = None
                        elif new_phase == "day_discussion":
                            start_timer(state, state["settings"].get("discussion_timer", 300), "Discussion")
                        save_game(self.code, state)
                    await self.broadcast_sync()

            elif action == "set_night_stage":
                idx = int(content.get("stage_index", 0))
                set_night_stage_index(state, idx)
                await self.broadcast_sync()

            elif action == "record_night_action":
                stage_id = content.get("stage_id")
                target_id = content.get("target_id")
                extra = content.get("extra")
                record_gm_night_action(state, stage_id, target_id, extra)
                await self.broadcast_sync()

            elif action == "clear_night_action":
                stage_id = content.get("stage_id")
                clear_gm_night_action(state, stage_id)
                await self.broadcast_sync()

            elif action == "reveal_detective":
                reveal_detective_to_player(state)
                await self.broadcast_sync()

            elif action == "start_timer":
                duration = int(content.get("duration", 300))
                label = content.get("label", "Timer")
                start_timer(state, duration, label)
                await self.broadcast_sync()

            elif action == "adjust_timer":
                delta = int(content.get("delta", 60))
                adjust_timer(state, delta)
                await self.broadcast_sync()

            elif action == "pause_timer":
                pause_timer(state)
                await self.broadcast_sync()

            elif action == "resume_timer":
                resume_timer(state)
                await self.broadcast_sync()

            elif action == "reset_timer":
                duration = content.get("duration")
                reset_timer(state, int(duration) if duration else None)
                await self.broadcast_sync()

            elif action == "start_defense":
                pid = content.get("player_id")
                if pid and pid in state["players"]:
                    proceed_to_defense(state, pid)
                    await self.broadcast_sync()

            elif action == "start_voting":
                sys = content.get("system")
                start_voting_session(state, sys)
                await self.broadcast_sync()

            elif action == "toggle_nomination":
                voter_id = content.get("voter_id", "gm")
                cid = content.get("candidate_id")
                if cid:
                    toggle_nomination_vote(state, voter_id, cid)
                    await self.broadcast_sync()

            elif action == "set_nomination_tally":
                cid = content.get("candidate_id")
                count = int(content.get("count", 0))
                if cid:
                    set_nomination_tally_direct(state, cid, count)
                    await self.broadcast_sync()

            elif action == "toggle_official_nominee":
                pid = content.get("player_id")
                if pid:
                    toggle_official_nomination(state, pid)
                    await self.broadcast_sync()

            elif action == "proceed_defense":
                pid = content.get("player_id")
                proceed_to_defense(state, pid)
                await self.broadcast_sync()

            elif action == "proceed_final_vote":
                proceed_to_final_vote(state)
                await self.broadcast_sync()

            elif action == "record_final_vote_tally":
                cid = content.get("candidate_id")
                count = int(content.get("count", 0))
                if cid:
                    record_gm_final_vote_tally(state, cid, count)
                    await self.broadcast_sync()

            elif action == "tally_vote":
                tally_and_resolve_vote(state)
                await self.broadcast_sync()

            elif action == "reset_voting":
                reset_voting(state)
                await self.broadcast_sync()

            elif action == "resolve_night":
                resolve_night(state)
                await self.broadcast_sync()

            elif action == "update_settings":
                new_settings = content.get("settings", {})
                state["settings"].update(new_settings)
                save_game(self.code, state)
                await self.broadcast_sync()

            return

        # 3. Player Operations
        if self.player_id and self.player_id in state["players"]:
            if action == "night_action":
                await self.send_json(
                    {
                        "type": "action_result",
                        "success": False,
                        "message": (
                            "Night actions are performed by silently pointing fingers to the "
                            "Game Master to prevent cheating."
                        ),
                    }
                )

            elif action == "vote_nominate":
                cid = content.get("candidate_id")
                if cid:
                    success, msg = toggle_nomination_vote(state, self.player_id, cid)
                    await self.send_json({"type": "vote_result", "success": success, "message": msg})
                    await self.broadcast_sync()

            elif action == "vote_final":
                cid = content.get("candidate_id")
                success, msg = cast_final_vote(state, self.player_id, cid)
                await self.send_json({"type": "vote_result", "success": success, "message": msg})
                await self.broadcast_sync()

            elif action == "guess_angel":
                target_id = content.get("target_id")
                success, msg = guess_angel_in_limbo(state, self.player_id, target_id)
                await self.send_json({"type": "angel_guess_result", "success": success, "message": msg})
                await self.broadcast_sync()
