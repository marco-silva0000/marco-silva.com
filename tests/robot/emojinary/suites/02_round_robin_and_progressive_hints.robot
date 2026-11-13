*** Settings ***
Documentation     Emojinary Classic Round Robin & Live Progressive Emoji Hints Suite
...               Covers multi-round turn rotation, progressive live hints during guessing,
...               multi-guesser decaying points vs Speed Blitz first-guess mode, word rerolls,
...               and custom secret phrases.
Library           ../EmojinaryLibrary.py

*** Test Cases ***
Round Robin Multi Guesser Decaying Points And Progressive Hints
    [Documentation]    Clue-giver reveals initial clue, drops Hint #2 & Hint #3 live, and two guessers score decaying points
    Given A New Emojinary Room    code=RR01    mode=round_robin    max_rounds=2    end_on_first_guess=${FALSE}
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    And Player Joins Room    Bob
    When Game Starts
    Then Phase Should Be    emoji
    And Round Number Should Be    1
    And Current Turn Player Should Be    Marco
    When Force Current Secret Word    The Lion King    movie
    And Sanitized View Should Show Secret Word To      Marco    The Lion King
    And Sanitized View Should Hide Secret Word From    Alice
    And Sanitized View Should Hide Secret Word From    Bob
    # Marco reveals initial clue (Hint #1)
    When Player Reveals Clue    Marco    🦁👑
    Then Phase Should Be        guess
    And Emoji Clue Should Be    🦁👑
    And Hint Count Should Be    1
    # Marco drops Hint #2 live during guessing
    When Player Adds Extra Emoji Hint    Marco    🌅🐗
    Then Hint Count Should Be            2
    And Chat Log Should Contain          Hint #2
    # Alice guesses first (12 pts for Alice, +3 pts bonus for Marco) -> round continues for Bob!
    When Player Sends Unified Chat    Alice    The Lion King
    Then Phase Should Be              guess
    And Player Score Should Be        Alice    12
    And Player Score Should Be        Marco    3
    # Marco drops Hint #3 live for Bob
    When Player Adds Extra Emoji Hint    Marco    🐦🎵
    Then Hint Count Should Be            3
    # Bob guesses second (10 pts for Bob) -> all guessers finished, round advances to Round 2!
    When Player Sends Unified Chat    Bob      Lion King
    Then Player Score Should Be       Bob      10
    And Phase Should Be               emoji
    And Round Number Should Be        2
    And Current Turn Player Should Be    Alice

Speed Blitz First Guess Immediately Ends Round
    [Documentation]    When end_on_first_guess is True, the first correct guess immediately advances the round
    Given A New Emojinary Room    code=RR02    mode=round_robin    max_rounds=1    end_on_first_guess=${TRUE}
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    And Player Joins Room    Bob
    When Game Starts
    And Force Current Secret Word    Interstellar    movie
    And Player Reveals Clue          Marco           🚀🕳️⏳
    And Player Sends Unified Chat    Alice           Interstellar
    Then Phase Should Be             gameover
    And Player Score Should Be       Alice           12
    And Player Score Should Be       Bob             0
    And Replay History Count Should Be    1

Word Reroll Respects Configured Limit And Custom Word Override
    [Documentation]    Clue-giver can reroll up to allow_rerolls times and set a custom phrase when enabled
    Given A New Emojinary Room    code=RR03    mode=round_robin    max_rounds=1    allow_rerolls=1    allow_custom_words=${TRUE}
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    When Game Starts
    And Force Current Secret Word    Birthday party
    When Player Rerolls Word         Marco
    # Second reroll is blocked because allow_rerolls=1
    When Player Sets Custom Word     Marco    Golden Retriever
    Then Current Word Should Be      Golden Retriever
    When Player Reveals Clue         Marco    🐕💛🎾
    And Player Sends Unified Chat    Alice    Golden Retriever
    Then Phase Should Be             gameover
    And Replay Round Outcome Should Be    1    guessed
