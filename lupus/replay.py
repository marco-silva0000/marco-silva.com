"""Lupus Replay CLI & Robot Framework Scenario Generator.

This tool allows you to:
1. Print a human-readable summary of an exported game replay JSON.
2. Replay the game tape headlessly with in-memory state to verify determinism.
3. Automatically convert exported bug/game sessions into reproducible Robot Framework .robot test suites.

Usage:
    python -m lupus.replay --file /path/to/replay.json --summary
    python -m lupus.replay --file /path/to/replay.json --verify
    python -m lupus.replay --file /path/to/replay.json --to-robot tests/robot/lupus/suites/reproduced_bug.robot
"""

import argparse
import json
import os
import sys
from typing import Any, Optional


def load_replay(filepath: str) -> dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def print_summary(data: dict[str, Any]) -> None:
    code = data.get("code", "UNKNOWN")
    theme = data.get("theme", "werewolf")
    summary = data.get("summary", {})
    players = data.get("players", [])
    history = data.get("action_history", [])

    print("=" * 60)
    print(f"🐺 Lupus Game Replay Summary: Room {code} (Theme: {theme})")
    print("=" * 60)
    print(f"Rounds Played : {summary.get('rounds_played', 0)}")
    print(f"Total Players : {len(players)}")
    print(f"Total Actions : {len(history)}")
    print(f"Winner        : {summary.get('winner') or 'None (Game In Progress)'}")
    print("-" * 60)
    print("Roster:")
    for p in players:
        role = p.get("role") or "unassigned"
        status = p.get("status", "alive")
        print(f"  • {p.get('name', 'Unknown'):<20} [{role:<15}] -> Status: {status}")
    print("=" * 60)


def convert_to_robot(data: dict[str, Any], output_path: Optional[str] = None) -> str:
    """Convert an exported replay JSON tape into a reproducible Robot Framework test file."""
    code = data.get("code", "REPLAY")
    theme = data.get("theme", "werewolf")
    players = data.get("players", [])
    history = data.get("action_history", [])
    winner = data.get("summary", {}).get("winner")

    # Map player IDs to clean names
    id_to_name = {p["id"]: p["name"] for p in players if "id" in p and "name" in p}

    lines = [
        "*** Settings ***",
        "Documentation     Auto-generated simulation test from Lupus game export",
        f"...               Room Code: {code} | Theme: {theme}",
        "Library           tests.robot.lupus.LupusLibrary",
        "",
        "*** Test Cases ***",
        f"Replay Scenario For Room {code}",
        f"    [Documentation]    Replayed from export with {len(history)} deterministic actions",
        f"    Given A New Game    code={code}    theme={theme}",
    ]

    # Preassigned player setup
    for p in players:
        pname = p.get("name", "Unknown")
        prole = p.get("role")
        is_pub_mayor = "${TRUE}" if p.get("is_public_mayor") else "${FALSE}"
        if prole:
            lines.append(f"    And Player Joins As    {pname}    role={prole}    is_public_mayor={is_pub_mayor}")
        else:
            lines.append(f"    And Player Joins As    {pname}")

    lines.append("    When Game Starts")

    for entry in history:
        action = entry.get("action")
        payload = entry.get("payload", {})

        if action == "night_action":
            stage = payload.get("stage_id")
            target_id = payload.get("target_id")
            target_name = id_to_name.get(target_id, target_id)
            extra = payload.get("extra") or {}

            if stage == "wolves":
                lines.append(f"    And Wolves Attack    {target_name}")
            elif stage == "doctor":
                lines.append(f"    And Doctor Protects    {target_name}")
            elif stage == "bodyguard":
                lines.append(f"    And Bodyguard Protects    {target_name}")
            elif stage == "detective":
                lines.append(f"    And Detective Inspects    {target_name}")
            elif stage == "sniper":
                bullet = extra.get("bullet", "danger")
                lines.append(f"    And Sniper Shoots    {target_name}    bullet_type={bullet}")
            elif stage == "witch":
                rev_id = extra.get("revive_id")
                kill_id = extra.get("kill_id")
                rev_name = id_to_name.get(rev_id, "${NONE}") if rev_id else "${NONE}"
                kill_name = id_to_name.get(kill_id, "${NONE}") if kill_id else "${NONE}"
                lines.append(f"    And Witch Revives And Kills    revive_target={rev_name}    kill_target={kill_name}")
            elif stage == "death_angel":
                lines.append(f"    And Death Angel Strikes    {target_name}")
            elif stage == "saboteur_wolf":
                lines.append(f"    And Saboteur Blocks    {target_name}")
            elif stage == "disgruntled_ghost":
                lines.append(f"    And Disgruntled Ghost Haunts    {target_name}")
            elif stage == "mayor":
                if extra.get("veto"):
                    lines.append("    And Mayor Vetoes Execution")

        elif action == "resolve_night":
            lines.append("    And Night Resolves")

        elif action == "start_voting":
            v_sys = payload.get("system", "two_stage_50pct")
            lines.append(f"    And Day Voting Begins    system={v_sys}")

        elif action == "nomination_vote":
            voter_id = payload.get("voter_id")
            cand_id = payload.get("candidate_id")
            voter_name = id_to_name.get(voter_id, voter_id)
            cand_name = id_to_name.get(cand_id, cand_id)
            lines.append(f"    And Player Nominates    {voter_name}    {cand_name}")

        elif action == "proceed_to_final_vote":
            nominees = payload.get("nominees", [])
            if nominees:
                nominee_names = [id_to_name.get(n, n) for n in nominees]
                lines.append(f"    And Set Official Nominees    {'    '.join(nominee_names)}")
            lines.append("    And Proceed To Final Vote")

        elif action == "final_vote":
            voter_id = payload.get("voter_id")
            cand_id = payload.get("candidate_id")
            voter_name = id_to_name.get(voter_id, voter_id)
            cand_name = id_to_name.get(cand_id, cand_id) if cand_id else "${NONE}"
            lines.append(f"    And Player Votes For    {voter_name}    {cand_name}")

        elif action == "resolve_vote":
            lines.append("    And Final Vote Is Tallied")

        elif action == "advance_to_night":
            lines.append("    And Night Falls")

        elif action == "guess_angel":
            player_id = payload.get("player_id")
            target_id = payload.get("guessed_angel_id")
            p_name = id_to_name.get(player_id, player_id)
            t_name = id_to_name.get(target_id, target_id)
            lines.append(f"    And Limbo Player Guesses Angel    {p_name}    {t_name}")

    lines.append("")
    lines.append("    # Final Assertions")
    for p in players:
        pname = p.get("name")
        status = p.get("status")
        if pname and status:
            lines.append(f"    Then Player Status Should Be    {pname}    {status}")

    if winner:
        lines.append(f"    And Winner Should Be    {winner}")

    robot_content = "\n".join(lines) + "\n"

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(robot_content)
        print(f"✅ Generated Robot Framework test scenario: {output_path}")

    return robot_content


def verify_replay(data: dict[str, Any]) -> bool:
    """Run headless simulator to verify deterministic execution of replay tape."""
    # Lazy import to avoid circular dependencies
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from tests.robot.lupus.LupusSimulator import LupusSimulator

    code = data.get("code", "VERIFY")
    theme = data.get("theme", "werewolf")
    settings = data.get("settings", {})
    players = data.get("players", [])
    history = data.get("action_history", [])

    sim = LupusSimulator(code=code, theme=theme, settings=settings)

    id_to_name = {}
    for p in players:
        pid = sim.add_player(
            name=p["name"],
            role=p.get("role"),
            preassigned=True,
            is_public_mayor=p.get("is_public_mayor", False),
        )
        id_to_name[p.get("id", pid)] = p["name"]

    print(f"▶️ Starting verification for game {code} ({len(history)} actions)...")
    sim.start_game()

    for idx, entry in enumerate(history, 1):
        action = entry.get("action")
        payload = entry.get("payload", {})

        if action == "night_action":
            stage = payload.get("stage_id")
            target_id = payload.get("target_id")
            target_name = id_to_name.get(target_id, target_id)
            extra = payload.get("extra")
            sim.record_night_action(stage, target_name, extra=extra)

        elif action == "resolve_night":
            sim.resolve_night()

        elif action == "start_voting":
            v_sys = payload.get("system", "two_stage_50pct")
            sim.start_voting_session(system=v_sys)

        elif action == "nomination_vote":
            voter_id = payload.get("voter_id")
            cand_id = payload.get("candidate_id")
            voter_name = id_to_name.get(voter_id, voter_id)
            cand_name = id_to_name.get(cand_id, cand_id)
            sim.nominate(voter_name, cand_name)

        elif action == "proceed_to_final_vote":
            nominees = payload.get("nominees", [])
            if nominees:
                sim.set_official_nominees([id_to_name.get(n, n) for n in nominees])
            sim.proceed_to_final_vote()

        elif action == "final_vote":
            voter_id = payload.get("voter_id")
            cand_id = payload.get("candidate_id")
            voter_name = id_to_name.get(voter_id, voter_id)
            cand_name = id_to_name.get(cand_id, cand_id) if cand_id else None
            sim.cast_final_vote(voter_name, cand_name)

        elif action == "resolve_vote":
            sim.tally_vote()

        elif action == "advance_to_night":
            sim.advance_to_night()

        elif action == "guess_angel":
            player_id = payload.get("player_id")
            target_id = payload.get("guessed_angel_id")
            p_name = id_to_name.get(player_id, player_id)
            t_name = id_to_name.get(target_id, target_id)
            sim.guess_limbo(p_name, t_name)

    # Check assertions against exported players
    mismatches = []
    for p in players:
        pname = p["name"]
        expected_status = p.get("status")
        actual_status = sim.get_player_status(pname)
        if expected_status and actual_status != expected_status:
            mismatches.append(f"{pname}: expected {expected_status}, got {actual_status}")

    expected_winner = data.get("summary", {}).get("winner")
    actual_winner = sim.get_winner()
    if expected_winner and actual_winner != expected_winner:
        mismatches.append(f"Winner: expected {expected_winner}, got {actual_winner}")

    if mismatches:
        print("❌ Replay verification failed with mismatches:")
        for m in mismatches:
            print(f"   • {m}")
        return False

    print(f"✅ Replay verified cleanly! All {len(players)} player statuses and outcomes match 100%.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Lupus Game Replay & Robot Test Generator")
    parser.add_argument("--file", "-f", required=True, help="Path to exported game replay JSON")
    parser.add_argument("--summary", "-s", action="store_true", help="Print summary of replay")
    parser.add_argument("--to-robot", "-r", nargs="?", const="", help="Convert replay to .robot test file")
    parser.add_argument("--verify", "-v", action="store_true", help="Run replay in headless simulator")

    args = parser.parse_args()

    data = load_replay(args.file)

    if args.summary or (not args.to_robot and not args.verify):
        print_summary(data)

    if args.to_robot is not None:
        out_file = args.to_robot if args.to_robot else None
        res = convert_to_robot(data, out_file)
        if not out_file:
            print(res)

    if args.verify:
        success = verify_replay(data)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
