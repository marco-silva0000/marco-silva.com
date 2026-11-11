*** Settings ***
Documentation     Lupus Social & Political Roles Simulation Suite
...               Covers Public & Hidden Mayor, Mayor Veto, Innocent Lovers, Jester, Successor
Library           tests.robot.lupus.LupusLibrary

*** Test Cases ***
Public Mayor Has Executive Immunity From Town Lynch
    [Documentation]    Town votes out Public Mayor; immunity activates and Mayor is spared
    Given A New Game    code=SOC01    limbo_enabled=${FALSE}    mayor_type=public
    And Player Joins As    JudgeBob    role=mayor       is_public_mayor=${TRUE}
    And Player Joins As    Alice       role=villager
    And Player Joins As    Charlie     role=villager
    When Game Starts
    And Day Voting Begins
    And Set Official Nominees    JudgeBob    Alice
    And Proceed To Final Vote
    And Player Votes For    Alice      JudgeBob
    And Player Votes For    Charlie    JudgeBob
    And Player Votes For    JudgeBob   ${NONE}
    And Final Vote Is Tallied
    Then Player Status Should Be    JudgeBob    alive
    And Event Log Should Contain    executive immunity

Public Mayor Has Double Vote Weight
    [Documentation]    Public Mayor's single vote counts as 2 votes, breaking tie in their favor
    Given A New Game    code=SOC02    limbo_enabled=${FALSE}    mayor_type=public
    And Player Joins As    JudgeBob    role=mayor       is_public_mayor=${TRUE}
    And Player Joins As    Alice       role=villager
    And Player Joins As    Charlie     role=villager
    When Game Starts
    And Day Voting Begins
    And Set Official Nominees    Alice    Charlie
    And Proceed To Final Vote
    # Alice votes Charlie (1 vote). Charlie votes Alice (1 vote). JudgeBob votes Alice (2 votes!).
    # Total: Alice=2 votes, Charlie=1 vote -> Alice is eliminated!
    And Player Votes For    Alice       Charlie
    And Player Votes For    Charlie     Alice
    And Player Votes For    JudgeBob    Alice
    And Final Vote Is Tallied
    Then Player Status Should Be    Alice       dead
    And Player Status Should Be     Charlie     alive
    And Player Status Should Be     JudgeBob    alive

Hidden Mayor Can Be Executed By Town
    [Documentation]    Hidden Mayor does not have public immunity and can be lynched
    Given A New Game    code=SOC03    limbo_enabled=${FALSE}    mayor_type=hidden    public_mayor=${FALSE}
    And Player Joins As    SecretMayor    role=mayor    is_public_mayor=${FALSE}
    And Player Joins As    Alice          role=villager
    And Player Joins As    Charlie        role=villager
    When Game Starts
    And Day Voting Begins
    And Set Official Nominees    SecretMayor    Alice
    And Proceed To Final Vote
    And Player Votes For    Alice          SecretMayor
    And Player Votes For    Charlie        SecretMayor
    And Player Votes For    SecretMayor    Alice
    And Final Vote Is Tallied
    Then Player Status Should Be    SecretMayor    dead
    And Player Status Should Be     Alice          alive

Mayor Veto Pardons Executed Player During Night
    [Documentation]    Player is executed during day vote; Mayor vetoes at night, reviving them
    Given A New Game    code=SOC04    limbo_enabled=${FALSE}    mayor_type=public
    And Player Joins As    JudgeBob    role=mayor       is_public_mayor=${TRUE}
    And Player Joins As    Alice       role=villager
    And Player Joins As    Charlie     role=villager
    When Game Starts
    # Day 1 vote executes Alice
    And Day Voting Begins
    And Set Official Nominees    Alice    Charlie
    And Proceed To Final Vote
    And Player Votes For    JudgeBob    Alice
    And Player Votes For    Charlie     Alice
    And Final Vote Is Tallied
    Then Player Status Should Be    Alice    dead
    # Night 2 Mayor exercises veto
    When Night Falls
    And Mayor Vetoes Execution
    And Night Resolves
    Then Player Status Should Be    Alice       alive
    And Event Log Should Contain    exercised official veto

Innocent Lovers Die Together From Heartbreak
    [Documentation]    Two players bound as Innocent Lovers; when one is killed, the other dies of heartbreak
    Given A New Game    code=SOC05    limbo_enabled=${FALSE}
    And Player Joins As    Romeo     role=lover
    And Player Joins As    Juliet    role=lover
    And Player Joins As    Wolf      role=werewolf
    When Game Starts
    And Wolves Attack    Romeo
    And Night Resolves
    Then Player Status Should Be    Romeo     dead
    And Player Status Should Be     Juliet    dead

Jester Lynched By Town Wins Solo Victory
    [Documentation]    Town executes the Jester; Jester achieves immediate solo victory
    Given A New Game    code=SOC06    limbo_enabled=${FALSE}
    And Player Joins As    Clown    role=jester
    And Player Joins As    Alice    role=villager
    And Player Joins As    Bob      role=villager
    When Game Starts
    And Day Voting Begins
    And Set Official Nominees    Clown    Alice
    And Proceed To Final Vote
    And Player Votes For    Alice    Clown
    And Player Votes For    Bob      Clown
    And Final Vote Is Tallied
    Then Player Status Should Be    Clown    dead
    And Winner Should Be    jester
    And Event Log Should Contain    SOLO VICTORY
