*** Settings ***
Documentation     Emojinary Room Mechanics, Persistent Player Identity & Host Controls Suite
...               Covers token-backed reconnects, live self-service renaming, host transfer,
...               spectator toggles, kicking players, and preset application.
Library           ../EmojinaryLibrary.py

*** Test Cases ***
Persistent Player Identity Preserves Score And Turn Across Disconnects
    [Documentation]    Verify that disconnecting a WebSocket does not delete the player or reset scores
    Given A New Emojinary Room    code=ID01    max_rounds=2
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    Then Player Should Be Admin    Marco    ${TRUE}
    And Player Should Be Admin     Alice    ${FALSE}
    When Game Starts
    And Force Current Secret Word    The Lion King
    And Player Reveals Clue          Marco    🦁👑
    And Player Sends Unified Chat    Alice    The Lion King
    Then Player Score Should Be      Alice    12
    And Player Score Should Be       Marco    3
    # Alice disconnects mid-game and reconnects with her secret token on a new channel
    When Player Disconnects          Alice
    Then Player Should Be Connected  Alice    ${FALSE}
    And Player Score Should Be       Alice    12
    When Player Reconnects With Token    Alice
    Then Player Should Be Connected  Alice    ${TRUE}
    And Player Score Should Be       Alice    12
    And Current Turn Player Should Be    Alice

Live Self Service Player Rename Updates Creator And Rejects Collisions
    [Documentation]    Players can rename live; duplicate names are rejected and logged in chat
    Given A New Emojinary Room    code=ID02
    And Player Joins Room    Alice
    And Player Joins Room    Bob
    # Collision attempt: Bob tries to rename to Alice
    When Player Renames To    Bob      Alice
    Then Player Count Should Be    2
    # Valid rename: Alice renames to Alicia
    When Player Renames To    Alice    Alicia
    Then Chat Log Should Contain    changed their name to Alicia
    And Player Should Be Admin      Alicia    ${TRUE}

Host Admin Transfer Spectator Toggle And Player Kick
    [Documentation]    Host can toggle spectator status, transfer host rights, and kick offline/active players
    Given A New Emojinary Room    code=ID03
    And Player Joins Room    Marco
    And Player Joins Room    Alice
    And Player Joins Room    Charlie
    # Marco toggles himself to spectator and back
    When Player Toggles Spectator    Marco
    Then Player Should Be Spectator  Marco    ${TRUE}
    When Player Toggles Spectator    Marco
    Then Player Should Be Spectator  Marco    ${FALSE}
    # Marco transfers admin to Alice
    When Host Transfers Admin To     Marco    Alice
    Then Player Should Be Admin      Alice    ${TRUE}
    # Alice kicks Charlie
    When Host Kicks Player           Alice    Charlie
    Then Player Count Should Be      2
    And Chat Log Should Contain      Charlie was removed by Alice

Host Applies Game Presets Cleanly
    [Documentation]    Verify all 4 built-in presets update mode and settings accurately
    Given A New Emojinary Room    code=ID04
    And Player Joins Room    Marco
    When Host Applies Preset    Marco    collective_fast
    Then Mode Should Be         collective
    When Host Applies Preset    Marco    best_guess_party
    Then Mode Should Be         best_guess
    When Host Applies Preset    Marco    speed_blitz
    Then Mode Should Be         round_robin
    When Host Applies Preset    Marco    standard
    Then Mode Should Be         round_robin
