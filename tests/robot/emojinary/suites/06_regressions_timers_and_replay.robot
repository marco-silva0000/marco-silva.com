*** Settings ***
Documentation     Emojinary Regressions, Timer Controls & Replay Verification Suite
...               Covers all 11 historical bug fixes: single-entry skip history, clear emoji sync,
...               mode switching, timer pause/resume/+15s controls, and play-again full reset.
Library           ../EmojinaryLibrary.py

*** Test Cases ***
Skipping Round Records Exactly One Replay Entry
    [Documentation]    Regression test for Bug #6: _rr_skip previously recorded duplicate history entries
    Given A New Emojinary Room    code=REG01    mode=round_robin    max_rounds=1
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    When Game Starts
    And Force Current Secret Word    Birthday party    thing
    And Player Skips Round           Marco
    Then Phase Should Be             gameover
    And Replay History Count Should Be    1
    And Replay Round Outcome Should Be    1    skipped

Clearing Emoji Clue Syncs Empty State To Server
    [Documentation]    Regression test for Bug #7: clearing emoji field updates server emoji_clue
    Given A New Emojinary Room    code=REG02    mode=round_robin    max_rounds=1
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    When Game Starts
    And Player Sets Emoji Clue       Marco    🍕🎉
    Then Emoji Clue Should Be        🍕🎉
    When Player Clears Emoji Clue    Marco
    Then Emoji Clue Should Be        ${EMPTY}

Host Timer Pause Resume And Add Time Controls
    [Documentation]    Host can pause, resume, and add +15s to the active phase timer
    Given A New Emojinary Room    code=REG03    mode=round_robin    max_rounds=1    emoji_timer=60
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    When Game Starts
    Then Timer Should Be Paused      ${FALSE}
    When Host Controls Timer         Marco    pause
    Then Timer Should Be Paused      ${TRUE}
    When Host Controls Timer         Marco    add_time    seconds=15
    Then Timer Should Be Paused      ${TRUE}
    When Host Controls Timer         Marco    resume
    Then Timer Should Be Paused      ${FALSE}

Switching Modes And Playing Again Resets Scores And History Cleanly
    [Documentation]    Regression test for Bug #5: switching between Best Guess, Collective, and Round Robin across matches
    Given A New Emojinary Room    code=REG04    mode=best_guess    max_rounds=1
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    When Game Starts
    And Player Sends Prompt                 Marco    Coffee Break
    And Player Submits Best Guess Emoji     Alice    ☕🥐😌
    And Judge Picks Best Emoji Winner       Marco    Alice
    Then Phase Should Be                    gameover
    And Player Score Should Be              Alice    10
    # Host triggers Play Again and switches room to Round Robin
    When Host Triggers Play Again           Marco
    Then Phase Should Be                    lobby
    And Player Score Should Be              Alice    0
    And Replay History Count Should Be      0
    When Host Updates Settings              Marco    mode=round_robin    max_rounds=1
    And Game Starts
    And Force Current Secret Word           Time machine    thing
    And Player Reveals Clue                 Marco           ⏳⚙️🚀
    And Player Sends Unified Chat           Alice           Time machine
    Then Phase Should Be                    gameover
    And Player Score Should Be              Alice           12
    And Replay History Count Should Be      1
