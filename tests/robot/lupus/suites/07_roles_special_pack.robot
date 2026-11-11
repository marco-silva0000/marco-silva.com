*** Settings ***
Documentation     Lupus Special Pack Expansion Roles Simulation Suite
...               Covers Wolf Cub (rampage double kill), Martyrdom (live grenade revenge),
...               and The Gull (werewolf bite infection & doctor immunity).
Library           tests.robot.lupus.LupusLibrary

*** Test Cases ***
Wolf Cub Death Triggers Werewolves Rampage Double Kill
    [Documentation]    When the Wolf Cub is killed during the day, the wolf pack goes on rampage and kills two victims next night.
    Given A New Game    code=CUB01    limbo_enabled=${FALSE}
    And Player Joins As    BigWolf     role=werewolf
    And Player Joins As    Pup         role=wolf_cub
    And Player Joins As    Alice       role=villager
    And Player Joins As    Bob         role=villager
    And Player Joins As    Charlie     role=villager
    When Game Starts
    # Pup dies by vote or execution
    And Player Status Is Set To    Pup    dead
    And Event Log Should Contain    The enraged wolf pack will strike TWICE next night
    # Advance to night
    And Night Falls
    And Wolves Attack With Rampage    Alice    Bob
    And Night Resolves
    Then Player Status Should Be    Alice      dead
    And Player Status Should Be     Bob        dead
    And Player Status Should Be     Charlie    alive
    And Player Status Should Be     BigWolf    alive

Martyrdom Eliminates Primed Target When Killed
    [Documentation]    Martyr primes a live grenade on an enemy; when eliminated, the grenade takes the victim down too.
    Given A New Game    code=MART01    limbo_enabled=${FALSE}
    And Player Joins As    Soldier    role=martyrdom
    And Player Joins As    BadWolf    role=werewolf
    And Player Joins As    Innocent   role=villager
    When Game Starts
    And Martyrdom Primes Target    Soldier    BadWolf
    # Soldier is executed or eliminated
    And Player Status Is Set To    Soldier    dead
    Then Player Status Should Be    Soldier     dead
    And Player Status Should Be     BadWolf     dead
    And Player Status Should Be     Innocent    alive
    And Event Log Should Contain    live grenade, blowing up BadWolf

The Gull Converts To Werewolf When Bitten By Wolves
    [Documentation]    The Gull is initially Town, but when bitten by wolves without doctor shield, they survive and convert secretly to Wolves.
    Given A New Game    code=GULL01    limbo_enabled=${FALSE}
    And Player Joins As    Wolf      role=werewolf
    And Player Joins As    Gull      role=gull
    And Player Joins As    Sherlock  role=detective
    When Game Starts
    # Detective inspects Gull before bite: Good
    And Detective Inspects    Gull
    Then Detective Inspection Result Should Be    Good
    When Wolves Attack    Gull
    And Night Resolves
    Then Player Status Should Be    Gull    alive
    And Player Faction Should Be    Gull    wolves
    And Event Log Should Contain    converted into a Werewolf
    # Next night, Detective inspects Gull again: now Evil!
    When Night Falls
    And Detective Inspects    Gull
    Then Detective Inspection Result Should Be    Evil
    When Wolves Attack    Sherlock
    And Night Resolves
    Then Player Status Should Be    Sherlock    dead

Doctor Protects The Gull From Werewolf Bite Preventing Infection
    [Documentation]    If Doctor shields The Gull on the night wolves attack, The Gull is protected and remains Town.
    Given A New Game    code=GULL02    limbo_enabled=${FALSE}
    And Player Joins As    Wolf     role=werewolf
    And Player Joins As    Gull     role=gull
    And Player Joins As    Medic    role=doctor
    When Game Starts
    And Doctor Protects    Gull
    And Wolves Attack      Gull
    And Night Resolves
    Then Player Status Should Be    Gull    alive
    And Player Faction Should Be    Gull    town
    And Event Log Should Contain    Doctor/protection shielded them from infection
