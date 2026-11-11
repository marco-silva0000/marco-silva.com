*** Settings ***
Documentation     Lupus Protection Roles Simulation Suite
...               Covers Doctor, Bodyguard, Witch (Revive), and Angel / Limbo mechanics
Library           tests.robot.lupus.LupusLibrary

*** Test Cases ***
Doctor Saves Villager From Wolves Attack
    [Documentation]    Doctor successfully shields target from werewolf attack
    Given A New Game    code=PROT01    limbo_enabled=${FALSE}
    And Player Joins As    Wolf     role=werewolf
    And Player Joins As    Doc      role=doctor
    And Player Joins As    Alice    role=villager
    When Game Starts
    And Wolves Attack      Alice
    And Doctor Protects    Alice
    And Night Resolves
    Then Player Status Should Be    Alice    alive
    And Player Status Should Be     Doc      alive
    And Night Report Should Contain    peaceful night

Bodyguard Intercepts Werewolves Attack
    [Documentation]    Bodyguard intercepts attack on guarded player; Bodyguard sacrifices self and victim survives
    Given A New Game    code=PROT02    limbo_enabled=${FALSE}
    And Player Joins As    Wolf      role=werewolf
    And Player Joins As    Knight    role=bodyguard
    And Player Joins As    Alice     role=villager
    When Game Starts
    And Wolves Attack         Alice
    And Bodyguard Protects    Alice
    And Night Resolves
    Then Player Status Should Be    Alice     alive
    And Player Status Should Be     Knight    dead
    And Player Status Should Be     Wolf      alive

Bodyguard Double Intercept
    [Documentation]    Werewolf and Serial Killer attack the same guarded player; Bodyguard intercepts both
    Given A New Game    code=PROT03    limbo_enabled=${FALSE}
    And Player Joins As    Wolf      role=werewolf
    And Player Joins As    Dexter    role=serial_killer
    And Player Joins As    Knight    role=bodyguard
    And Player Joins As    Alice     role=villager
    When Game Starts
    And Wolves Attack            Alice
    And Serial Killer Attacks    Alice
    And Bodyguard Protects       Alice
    And Night Resolves
    Then Player Status Should Be    Alice     alive
    And Player Status Should Be     Knight    dead

Witch Revives Player In Limbo
    [Documentation]    Witch uses revival potion to restore a limbo player back to the living
    Given A New Game    code=PROT04    limbo_enabled=${TRUE}
    And Player Joins As    Glinda    role=witch
    And Player Joins As    Alice     role=villager
    When Game Starts
    And Player Status Is Set To    Alice    limbo
    And Witch Revives And Kills    revive_target=Alice    kill_target=${NONE}
    And Night Resolves
    Then Player Status Should Be    Alice     alive
    And Player Status Should Be     Glinda    alive
    And Event Log Should Contain    revival potion

Limbo Player Guesses Living Angel Successfully
    [Documentation]    Player in limbo correctly identifies the living Angel and returns to life
    Given A New Game    code=PROT05    limbo_enabled=${TRUE}
    And Player Joins As    Gabriel    role=angel
    And Player Joins As    Alice      role=villager
    When Game Starts
    And Player Status Is Set To    Alice    limbo
    And Limbo Player Guesses Angel    Alice    Gabriel
    Then Player Status Should Be    Alice      alive
    And Event Log Should Contain    Divine Revelation

Limbo Player Guesses Wrong Person And Dies Permanently
    [Documentation]    Player in limbo guesses non-angel and dies permanently
    Given A New Game    code=PROT06    limbo_enabled=${TRUE}
    And Player Joins As    Gabriel    role=angel
    And Player Joins As    Bob        role=villager
    And Player Joins As    Alice      role=villager
    When Game Starts
    And Player Status Is Set To    Alice    limbo
    And Limbo Player Guesses Angel    Alice    Bob
    Then Player Status Should Be    Alice    dead
    And Event Log Should Contain    died permanently
