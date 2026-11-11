*** Settings ***
Documentation     Lupus Game Lifecycle & Phase Transition Simulation Suite
...               Covers multi-round cycles, voting tie-breakers, and room lobby resets
Library           tests.robot.lupus.LupusLibrary

*** Test Cases ***
Complete Two Round Game Cycle Town Victory
    [Documentation]    Simulate Night 1, Day 1 voting execution, and final Town victory condition
    Given A New Game    code=CYCLE01    limbo_enabled=${FALSE}
    And Player Joins As    Wolf     role=werewolf
    And Player Joins As    Alice    role=villager
    And Player Joins As    Bob      role=villager
    And Player Joins As    Charlie  role=villager

    # Round 1 (Night 1): Wolves attack Bob
    When Game Starts
    And Wolves Attack    Bob
    And Night Resolves
    Then Player Status Should Be    Bob      dead
    And Player Status Should Be     Alice    alive
    And Player Status Should Be     Wolf     alive

    # Round 1 (Day 1): Town votes to execute Wolf
    When Day Voting Begins
    And Set Official Nominees    Wolf    Alice
    And Proceed To Final Vote
    And Player Votes For    Alice      Wolf
    And Player Votes For    Charlie    Wolf
    And Player Votes For    Wolf       Alice
    And Final Vote Is Tallied
    Then Player Status Should Be    Wolf    dead

    # Victory Assertion: All wolves eliminated, Town wins!
    And Winner Should Be    town

Voting Runoff And Second Tie Peace
    [Documentation]    First tie triggers runoff revote; second tie spares everyone
    Given A New Game    code=CYCLE02    limbo_enabled=${FALSE}
    And Player Joins As    Alice    role=villager
    And Player Joins As    Bob      role=villager
    And Player Joins As    Charlie  role=villager
    When Game Starts
    And Day Voting Begins
    And Set Official Nominees    Alice    Bob
    And Proceed To Final Vote

    # First vote: 1-1 tie (Alice votes Bob, Bob votes Alice, Charlie abstains)
    And Player Votes For    Alice      Bob
    And Player Votes For    Bob        Alice
    And Player Votes For    Charlie    ${NONE}
    And Final Vote Is Tallied
    Then Event Log Should Contain    Runoff revote initiated

    # Runoff vote: 1-1 tie again!
    When Player Votes For    Alice      Bob
    And Player Votes For     Bob        Alice
    And Player Votes For     Charlie    ${NONE}
    And Final Vote Is Tallied
    Then Event Log Should Contain    SECOND TIE
    And Event Log Should Contain     NO ONE gets eliminated
    And Player Status Should Be      Alice    alive
    And Player Status Should Be      Bob      alive

Lobby Reset Archives Completed Game To Room History
    [Documentation]    Verify that return_to_lobby preserves game metrics in room history
    Given A New Game    code=CYCLE03    limbo_enabled=${FALSE}
    And Player Joins As    Wolf     role=werewolf
    And Player Joins As    Alice    role=villager
    When Game Starts
    And Wolves Attack    Alice
    And Night Resolves
    Then Winner Should Be    wolves
    When Return To Lobby
    Then Game History Count Should Be    1
