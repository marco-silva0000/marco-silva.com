*** Settings ***
Documentation     Emojinary Collective Prep + Progressive Hints Mode Suite
...               Covers simultaneous secret phrase assignment, parallel emoji clue locking,
...               automatic transition to sequential Round Robin guessing rounds, and live
...               additional emoji hints from each word writer during their round.
Library           ../EmojinaryLibrary.py

*** Test Cases ***
Collective Mode Parallel Prep And Sequential Guessing With Live Extra Hints
    [Documentation]    3 players prepare emoji clues in parallel, then guess each other's words with live hints
    Given A New Emojinary Room    code=COLL01    mode=collective    max_rounds=3
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    And Player Joins Room    Bob
    When Game Starts
    Then Phase Should Be    prep
    # Pin deterministic words for each player in the collective queue
    And Force Collective Word For Player    Marco    The Lion King    movie
    And Force Collective Word For Player    Alice    E.T.             movie
    And Force Collective Word For Player    Bob      WALL-E           movie
    # Each player sees their own word during prep
    And Sanitized View Should Show Secret Word To    Marco    The Lion King
    And Sanitized View Should Show Secret Word To    Alice    E.T.
    And Sanitized View Should Show Secret Word To    Bob      WALL-E
    # Players lock in their initial emoji clues in parallel
    When Player Submits Collective Prep    Marco    🦁👑
    Then Phase Should Be                   prep
    When Player Submits Collective Prep    Alice    👽🚲🌕
    Then Phase Should Be                   prep
    When Player Submits Collective Prep    Bob      🤖🌱🚀
    # Once all 3 players lock in, Round 1 guessing begins automatically for Marco's word!
    Then Phase Should Be                   guess
    And Round Number Should Be             1
    And Current Turn Player Should Be      Marco
    And Emoji Clue Should Be               🦁👑
    And Sanitized View Should Show Secret Word To      Marco    The Lion King
    And Sanitized View Should Hide Secret Word From    Alice
    And Sanitized View Should Hide Secret Word From    Bob
    # Marco drops an extra live emoji hint during Round 1 guessing
    When Player Adds Extra Emoji Hint      Marco    🌅🐗
    Then Hint Count Should Be              2
    # Alice and Bob guess Marco's word -> advances immediately to Round 2 (Alice's word)!
    When Player Sends Unified Chat         Alice    The Lion King
    And Player Sends Unified Chat          Bob      Lion King
    Then Phase Should Be                   guess
    And Round Number Should Be             2
    And Current Turn Player Should Be      Alice
    And Emoji Clue Should Be               👽🚲🌕
    # Marco and Bob guess Alice's word -> advances to Round 3 (Bob's word)!
    When Player Sends Unified Chat         Marco    et
    And Player Sends Unified Chat          Bob      E.T.
    Then Phase Should Be                   guess
    And Round Number Should Be             3
    And Current Turn Player Should Be      Bob
    And Emoji Clue Should Be               🤖🌱🚀
    # Marco and Alice guess Bob's word -> Game Over!
    When Player Sends Unified Chat         Marco    wall e
    And Player Sends Unified Chat          Alice    walle
    Then Phase Should Be                   gameover
    And Replay History Count Should Be     3
    And Replay Round Hint Count Should Be  1    2

Collective Mode Force Advance When One Player Is AFK During Prep
    [Documentation]    If one player is AFK during prep, Host force-advance launches guessing for submitted clues
    Given A New Emojinary Room    code=COLL02    mode=collective    max_rounds=2
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    And Player Joins Room    Bob
    When Game Starts
    And Force Collective Word For Player    Marco    Spill the beans    phrase
    And Player Submits Collective Prep      Marco    🫘🫗😱
    # Alice and Bob haven't submitted yet, Host forces advance
    When Host Forces Advance                Marco
    Then Phase Should Be                    guess
    And Current Turn Player Should Be       Marco
    And Emoji Clue Should Be                🫘🫗😱
