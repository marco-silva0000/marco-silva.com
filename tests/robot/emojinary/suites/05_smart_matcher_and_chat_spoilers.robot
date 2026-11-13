*** Settings ***
Documentation     Emojinary Smart Guess Evaluator, Unified Chat Routing & Spoiler Guard Suite
...               Covers article-insensitive matching, punctuation/hyphen tolerance, partial-word
...               feedback, close-typo detection, private vs public chat modes, and spoiler censoring.
Library           ../EmojinaryLibrary.py

*** Test Cases ***
Smart Matcher Accepts Missing Articles And Punctuation Variations
    [Documentation]    Verify 'The Lion King' -> 'Lion King', 'E.T.' -> 'et', and 'WALL-E' -> 'wall e'
    Given A New Emojinary Room    code=SM01    mode=round_robin    max_rounds=3    end_on_first_guess=${TRUE}
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    When Game Starts
    # Round 1: 'The Lion King' guessed as 'lion king!'
    And Force Current Secret Word    The Lion King    movie
    And Player Reveals Clue          Marco            🦁👑
    And Player Sends Unified Chat    Alice            lion king!
    Then Round Number Should Be      2
    # Round 2: 'E.T.' guessed as 'et'
    When Force Current Secret Word   E.T.             movie
    And Player Reveals Clue          Alice            👽🚲🌕
    And Player Sends Unified Chat    Marco            et
    Then Round Number Should Be      3
    # Round 3: 'WALL-E' guessed as 'wall e'
    When Force Current Secret Word   WALL-E           movie
    And Player Reveals Clue          Marco            🤖🌱
    And Player Sends Unified Chat    Alice            wall e
    Then Phase Should Be             gameover
    And Replay History Count Should Be    3

Partial Word Match And Close Typo Feedback Logged In Attempts
    [Documentation]    Partial word matches and 1-letter typos are flagged as 'close' in chat and replay
    Given A New Emojinary Room    code=SM02    mode=round_robin    max_rounds=1
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    When Game Starts
    And Force Current Secret Word    Interstellar    movie
    And Player Reveals Clue          Marco           🚀🕳️⌚
    # Alice makes a 1-character typo ('Interstelar')
    And Player Sends Unified Chat    Alice           Interstelar
    Then Phase Should Be             guess
    And Chat Log Should Contain      Close!
    # Alice then guesses wrong completely ('Matrix')
    When Player Sends Unified Chat   Alice           Matrix
    Then Phase Should Be             guess
    # Alice guesses right ('Interstellar')
    When Player Sends Unified Chat   Alice           Interstellar
    Then Phase Should Be             gameover
    And Replay Round Attempt Count Should Be    1    3

Spoiler Guard Censors Secret Phrase When Clue Giver Or Finished Guesser Chats
    [Documentation]    If the clue-giver or a player who already guessed types the secret word in chat, it is censored
    Given A New Emojinary Room    code=SM03    mode=round_robin    max_rounds=1    end_on_first_guess=${FALSE}
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    And Player Joins Room    Bob
    When Game Starts
    And Force Current Secret Word    The Lion King    movie
    And Player Reveals Clue          Marco            🦁👑
    # Clue-giver Marco tries to type the answer in chat -> censored!
    And Player Sends Unified Chat    Marco            Guys it is The Lion King!
    Then Chat Log Should Not Contain    The Lion King
    # Alice guesses correctly -> now Alice is a finished guesser while Bob is still guessing
    When Player Sends Unified Chat   Alice            The Lion King
    Then Phase Should Be             guess
    # Alice tries to spoil 'Lion King' in chat for Bob -> blocked!
    When Player Sends Unified Chat   Alice            Lion King
    Then Chat Log Should Contain     [spoiler blocked]

Private Chat Mode Hides Wrong Guesses From Other Guessers
    [Documentation]    In private chat_mode, Alice's wrong guess is visible to Alice & clue-giver Marco, but hidden from Bob
    Given A New Emojinary Room    code=SM04    mode=round_robin    max_rounds=1    chat_mode=private
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    And Player Joins Room    Bob
    When Game Starts
    And Force Current Secret Word    Stranger Things    tvshow
    And Player Reveals Clue          Marco              🚲🧇👾
    And Player Sends Unified Chat    Alice              Dark Mirror
    Then Chat Log Should Contain        Dark Mirror    viewer_name=Alice
    And Chat Log Should Contain         Dark Mirror    viewer_name=Marco
    And Chat Log Should Not Contain     Dark Mirror    viewer_name=Bob
