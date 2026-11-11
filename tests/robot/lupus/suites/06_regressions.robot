*** Settings ***
Documentation     Lupus Historical Regressions & Rule Edge Cases Simulation Suite
...               Covers v121 simultaneous resolution, dual witch potions, voting rights, and veto limits
Library           tests.robot.lupus.LupusLibrary

*** Test Cases ***
Witch Killed Tonight Still Poisons Target And Revives Limbo
    [Documentation]    Verify v121 simultaneous night resolution: Witch alive at dusk killed tonight
    ...               still successfully brews recorded poison and revival potions, but cannot self-heal
    Given A New Game    code=REG01    limbo_enabled=${TRUE}
    And Player Joins As    Wolf        role=werewolf
    And Player Joins As    Glinda      role=witch
    And Player Joins As    Charlie     role=villager
    And Player Joins As    Danielle    role=villager
    When Game Starts
    # Danielle is already in Limbo from prior trial
    And Player Status Is Set To    Danielle    limbo
    # Wolves attack the Witch tonight
    And Wolves Attack    Glinda
    # Witch brews poison on Charlie, and revives Danielle from limbo
    And Witch Revives And Kills    revive_target=Danielle    kill_target=Charlie
    And Night Resolves
    # Glinda dies (cannot self heal)
    Then Player Status Should Be    Glinda      dead
    # Charlie dies of poison simultaneously
    And Player Status Should Be     Charlie     dead
    # Danielle returns alive from Limbo
    And Player Status Should Be     Danielle    alive
    And Player Status Should Be     Wolf        alive

Dual Witch Potions In Same Night
    [Documentation]    Witch uses both revive and kill potions in the same round
    Given A New Game    code=REG02    limbo_enabled=${TRUE}
    And Player Joins As    Glinda     role=witch
    And Player Joins As    Alice      role=villager
    And Player Joins As    Bob        role=villager
    When Game Starts
    And Player Status Is Set To    Alice    limbo
    And Witch Revives And Kills    revive_target=Alice    kill_target=Bob
    And Night Resolves
    Then Player Status Should Be    Alice     alive
    And Player Status Should Be     Bob       dead
    And Player Status Should Be     Glinda    alive

Silenced Player Can Still Cast Final Vote
    [Documentation]    Silenced player cannot speak, but their execution vote is fully counted
    Given A New Game    code=REG03    limbo_enabled=${FALSE}
    And Player Joins As    Hush     role=silencer
    And Player Joins As    Alice    role=villager
    And Player Joins As    Bob      role=villager
    When Game Starts
    And Silencer Silences    Alice
    And Night Resolves
    Then Player Should Be Silenced    Alice    ${TRUE}
    # Alice can still participate in day voting!
    When Day Voting Begins
    And Set Official Nominees    Bob    Hush
    And Proceed To Final Vote
    And Player Votes For    Alice    Bob
    And Player Votes For    Hush     Bob
    And Final Vote Is Tallied
    Then Player Status Should Be    Bob    dead

Limbo Player Cannot Vote
    [Documentation]    A player hovering in Limbo is not counted as living and cannot cast a vote
    Given A New Game    code=REG04    limbo_enabled=${TRUE}
    And Player Joins As    Alice    role=villager
    And Player Joins As    Bob      role=villager
    When Game Starts
    And Player Status Is Set To    Alice    limbo
    When Day Voting Begins
    And Set Official Nominees    Bob
    And Proceed To Final Vote
    # Alice in Limbo attempts to vote; action should be rejected
    ${status}=    Run Keyword And Return Status    Player Votes For    Alice    Bob
    Should Be Equal As Strings    ${status}    False
