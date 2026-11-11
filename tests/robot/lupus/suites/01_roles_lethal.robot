*** Settings ***
Documentation     Lupus Lethal Roles Simulation Suite
...               Covers Werewolf, Serial Killer, Sniper (Danger & Silver), Death Angel, Saboteur
Library           tests.robot.lupus.LupusLibrary

*** Test Cases ***
Werewolves Eliminate Unprotected Villager
    [Documentation]    Normal werewolf attack successfully eliminates unprotected villager
    Given A New Game    code=LETH01    limbo_enabled=${FALSE}
    And Player Joins As    Wolf     role=werewolf
    And Player Joins As    Alice    role=villager
    And Player Joins As    Bob      role=villager
    When Game Starts
    And Wolves Attack    Alice
    And Night Resolves
    Then Player Status Should Be    Alice    dead
    And Player Status Should Be     Bob      alive
    And Player Status Should Be     Wolf     alive

Serial Killer Kills Independently
    [Documentation]    Serial Killer acts alone and strikes their target
    Given A New Game    code=LETH02    limbo_enabled=${FALSE}
    And Player Joins As    Dexter   role=serial_killer
    And Player Joins As    Alice    role=villager
    When Game Starts
    And Serial Killer Attacks    Alice
    And Night Resolves
    Then Player Status Should Be    Alice     dead
    And Player Status Should Be     Dexter    alive

Sniper Danger Bullet Kills Evil Werewolf
    [Documentation]    Sniper fires danger bullet at werewolf, werewolf dies
    Given A New Game    code=LETH03    limbo_enabled=${FALSE}
    And Player Joins As    Hawkeye    role=sniper
    And Player Joins As    Wolf       role=werewolf
    When Game Starts
    And Sniper Shoots    Wolf    bullet_type=danger
    And Night Resolves
    Then Player Status Should Be    Wolf       dead
    And Player Status Should Be     Hawkeye    alive

Sniper Danger Bullet Backfires On Innocent Villager
    [Documentation]    Sniper fires danger bullet at innocent villager; gun backfires, sniper dies of guilt, target unharmed
    Given A New Game    code=LETH04    limbo_enabled=${FALSE}
    And Player Joins As    Hawkeye    role=sniper
    And Player Joins As    Alice      role=villager
    When Game Starts
    And Sniper Shoots    Alice    bullet_type=danger
    And Night Resolves
    Then Player Status Should Be    Hawkeye    dead
    And Player Status Should Be     Alice      alive
    And Event Log Should Contain    backfired

Sniper Silver Bullet Kills Evil Werewolf
    [Documentation]    Sniper fires silver bullet at werewolf, werewolf dies
    Given A New Game    code=LETH05    limbo_enabled=${FALSE}
    And Player Joins As    Hawkeye    role=sniper
    And Player Joins As    Wolf       role=werewolf
    When Game Starts
    And Sniper Shoots    Wolf    bullet_type=silver
    And Night Resolves
    Then Player Status Should Be    Wolf       dead
    And Player Status Should Be     Hawkeye    alive

Sniper Silver Bullet Expends Harmlessly On Innocent Villager
    [Documentation]    Silver bullet fired at innocent does not kill target and does not backfire on sniper
    Given A New Game    code=LETH06    limbo_enabled=${FALSE}
    And Player Joins As    Hawkeye    role=sniper
    And Player Joins As    Alice      role=villager
    When Game Starts
    And Sniper Shoots    Alice    bullet_type=silver
    And Night Resolves
    Then Player Status Should Be    Hawkeye    alive
    And Player Status Should Be     Alice      alive
    And Event Log Should Contain    No harm done

Death Angel Strikes Target In Limbo
    [Documentation]    Death Angel strike severs player in limbo to permanent dead
    Given A New Game    code=LETH07    limbo_enabled=${TRUE}
    And Player Joins As    Reaper     role=death_angel
    And Player Joins As    Alice      role=villager
    When Game Starts
    And Player Status Is Set To    Alice    limbo
    And Death Angel Strikes    Alice
    And Night Resolves
    Then Player Status Should Be    Alice     dead
    And Player Status Should Be     Reaper    alive

Saboteur Wolf Suppresses Doctor Protection
    [Documentation]    Saboteur wolf targets Doctor, disabling their save; Wolves attack succeeds
    Given A New Game    code=LETH08    limbo_enabled=${FALSE}
    And Player Joins As    Wolf        role=werewolf
    And Player Joins As    Saboteur    role=saboteur_wolf
    And Player Joins As    Doc         role=doctor
    And Player Joins As    Alice       role=villager
    When Game Starts
    And Saboteur Blocks    Doc
    And Doctor Protects    Alice
    And Wolves Attack      Alice
    And Night Resolves
    Then Player Status Should Be    Alice       dead
    And Player Status Should Be     Doc         alive
    And Player Status Should Be     Wolf        alive
    And Player Status Should Be     Saboteur    alive
