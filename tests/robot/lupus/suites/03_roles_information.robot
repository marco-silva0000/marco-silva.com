*** Settings ***
Documentation     Lupus Information & Deception Roles Simulation Suite
...               Covers Detective, Alpha Wolf, Framer, Silencer
Library           tests.robot.lupus.LupusLibrary

*** Test Cases ***
Detective Inspects Innocent Villager
    [Documentation]    Detective inspects pure villager, result is Good
    Given A New Game    code=INFO01    limbo_enabled=${FALSE}
    And Player Joins As    Sherlock    role=detective
    And Player Joins As    Alice       role=villager
    When Game Starts
    And Detective Inspects    Alice
    Then Detective Inspection Result Should Be    Good
    And Event Log Should Contain    Detective inspected Alice: Good

Detective Inspects Evil Werewolf
    [Documentation]    Detective inspects regular werewolf, result is Evil
    Given A New Game    code=INFO02    limbo_enabled=${FALSE}
    And Player Joins As    Sherlock    role=detective
    And Player Joins As    Wolf        role=werewolf
    When Game Starts
    And Detective Inspects    Wolf
    Then Detective Inspection Result Should Be    Evil
    And Event Log Should Contain    Detective inspected Wolf: Evil

Detective Inspects Alpha Wolf Passive Deception
    [Documentation]    Detective inspects Alpha Wolf; due to passive camouflage, Alpha Wolf appears Good
    Given A New Game    code=INFO03    limbo_enabled=${FALSE}
    And Player Joins As    Sherlock    role=detective
    And Player Joins As    Alpha       role=alpha_wolf
    When Game Starts
    And Detective Inspects    Alpha
    Then Detective Inspection Result Should Be    Good
    And Event Log Should Contain    Detective inspected Alpha: Good

Detective Inspects Framed Innocent Player
    [Documentation]    Framer frames innocent villager before inspection; result is Evil
    Given A New Game    code=INFO04    limbo_enabled=${FALSE}
    And Player Joins As    Sherlock    role=detective
    And Player Joins As    Trickster   role=framer
    And Player Joins As    Alice       role=villager
    When Game Starts
    And Framer Frames         Alice
    And Detective Inspects    Alice
    Then Detective Inspection Result Should Be    Evil
    And Event Log Should Contain    Detective inspected Alice: Evil

Silencer Silences Player For The Day
    [Documentation]    Silencer targets player during the night; player is marked silenced at dawn
    Given A New Game    code=INFO05    limbo_enabled=${FALSE}
    And Player Joins As    Hush     role=silencer
    And Player Joins As    Alice    role=villager
    When Game Starts
    And Silencer Silences    Alice
    And Night Resolves
    Then Player Should Be Silenced    Alice    ${TRUE}
    And Night Report Should Contain    silenced for the day
