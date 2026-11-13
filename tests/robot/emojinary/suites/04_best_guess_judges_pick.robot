*** Settings ***
Documentation     Emojinary Best Guess (Judge's Pick) Mode Suite
...               Covers prompt selection, button-text sanitization, anonymous emoji submissions,
...               judging winner selection, score awards, and multi-round rotation.
Library           ../EmojinaryLibrary.py

*** Test Cases ***
Best Guess Full Multi Round Lifecycle And Prompt Sanitization
    [Documentation]    Judge sets prompt (stripping accidental button text), players submit emojis, judge awards winner
    Given A New Emojinary Room    code=BG01    mode=best_guess    max_rounds=2
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    And Player Joins Room    Bob
    When Game Starts
    Then Phase Should Be    picking
    And Current Turn Player Should Be    Marco
    # Marco sends prompt containing accidental button labels -> backend strips them cleanly
    When Player Sends Prompt    Marco    Your word: Space Cow 🎲 reroll ✅ send
    Then Phase Should Be        submitting
    And Current Word Should Be  Space Cow
    # Alice and Bob submit their emoji combinations
    When Player Submits Best Guess Emoji    Alice    🚀🐄🌌
    Then Phase Should Be                    submitting
    When Player Submits Best Guess Emoji    Bob      🛸🐮🧀
    # All non-judge players submitted -> automatically enters judging phase!
    Then Phase Should Be                    judging
    # Marco picks Alice's submission as the winner (+10 pts for Alice, +3 pts judge bonus for Marco)
    When Judge Picks Best Emoji Winner      Marco    Alice
    Then Player Score Should Be             Alice    10
    And Player Score Should Be              Marco    3
    And Phase Should Be                     picking
    And Round Number Should Be              2
    And Current Turn Player Should Be       Alice
    # Round 2: Alice sets prompt, Marco & Bob submit, Alice picks Bob
    When Player Sends Prompt                Alice    Monday Morning
    And Player Submits Best Guess Emoji     Marco    😴☕⏰
    And Player Submits Best Guess Emoji     Bob      🧟‍♂️💻🌧️
    Then Phase Should Be                    judging
    When Judge Picks Best Emoji Winner      Alice    Bob
    Then Phase Should Be                    gameover
    And Player Score Should Be              Bob      10
    And Player Score Should Be              Alice    13
    And Replay History Count Should Be      2
    And Exported Replay Leaderboard Top Player Should Be    Alice

Best Guess Force Advance From Submitting To Judging
    [Documentation]    If one player is slow submitting emojis, Host force-advance moves to judging with existing submissions
    Given A New Emojinary Room    code=BG02    mode=best_guess    max_rounds=1
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    And Player Joins Room    Bob
    When Game Starts
    And Player Sends Prompt                 Marco    Time Travel
    And Player Submits Best Guess Emoji     Alice    ⏳🚗⚡
    # Bob hasn't submitted yet; Marco forces advance to judging
    When Host Forces Advance                Marco
    Then Phase Should Be                    judging
    When Judge Picks Best Emoji Winner      Marco    Alice
    Then Phase Should Be                    gameover
    And Player Score Should Be              Alice    10
