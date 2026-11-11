*** Settings ***
Documentation     Lupus Mid-Game Joiners & Near-GameOver Edge Cases Simulation Suite
...               Covers late arrivals, unassigned spectator status isolation,
...               Traveler parity reversal, Successor understudy inheritance
...               (preventing premature Town or Serial Killer wins), Obsessive Lovers
...               heartbreak aversion, Ghost presence, and post-GameOver integrity.
Library           tests.robot.lupus.LupusLibrary

*** Test Cases ***
Unassigned Midgame Spectator Does Not Break Wolf Parity Win Condition
    [Documentation]    A spectator connecting mid-game without an assigned role has status 'waiting' and does not alter living player counts or wolf parity.
    Given A New Game    code=MID01    limbo_enabled=${FALSE}
    And Player Joins As    WolfA       role=werewolf
    And Player Joins As    WolfB       role=werewolf
    And Player Joins As    CitizenA    role=villager
    When Game Starts
    # 2 wolves vs 1 citizen -> Parity reached
    Then Pending Gameover Winner Should Be    wolves
    # Spectator arrives mid-game
    When Player Joins As    LateSpectator
    Then Player Status Should Be    LateSpectator    waiting
    And Living Players Count Should Be    3
    And Pending Gameover Winner Should Be    wolves

Midgame Joiner Assigned As Traveler Reverses Pending Wolf Win
    [Documentation]    When wolves reach parity, admitting a late joiner as a Confirmed Traveler adds a living town member, breaking wolf parity and clearing pending gameover.
    Given A New Game    code=MID02    limbo_enabled=${FALSE}
    And Player Joins As    AlphaWolf    role=werewolf
    And Player Joins As    BetaWolf     role=werewolf
    And Player Joins As    TownA        role=villager
    And Player Joins As    TownB        role=villager
    When Game Starts
    # 2 wolves vs 2 villagers -> Parity reached
    Then Pending Gameover Winner Should Be    wolves
    # Late arrival admitted by GM as Confirmed Traveler
    When Player Joins As    WanderingTraveler
    And Assign Midgame Role    WanderingTraveler    traveler
    Then Player Status Should Be    WanderingTraveler    alive
    And Player Faction Should Be    WanderingTraveler    town
    And Living Players Count Should Be    5
    And Pending Gameover Should Be None

Successor Inherits Last Werewolf Averting Premature Town Win
    [Documentation]    When the sole surviving werewolf is executed by town vote, a waiting Successor inherits the role and keeps the pack alive.
    Given A New Game    code=MID03    limbo_enabled=${FALSE}
    And Player Joins As    LoneWolf      role=werewolf
    And Player Joins As    VillagerA     role=villager
    And Player Joins As    VillagerB     role=villager
    And Player Joins As    Understudy
    When Game Starts
    And Assign Midgame Role    Understudy    successor
    Then Player Status Should Be    Understudy    waiting
    # Day voting begins to execute the LoneWolf
    When Day Voting Begins
    And Set Official Nominees    LoneWolf
    And Proceed To Final Vote
    And Player Votes For    VillagerA    LoneWolf
    And Player Votes For    VillagerB    LoneWolf
    And Final Vote Is Tallied
    # LoneWolf is executed, but Understudy inherits Werewolf mantle!
    Then Player Status Should Be    LoneWolf      dead
    And Player Status Should Be     Understudy    alive
    And Player Role Should Be       Understudy    werewolf
    And Player Faction Should Be    Understudy    wolves
    And Pending Gameover Should Be None
    And Winner Should Be            ${NONE}

Serial Killer Eliminates Last Werewolf But Successor Steps In Averting SK Solo Victory
    [Documentation]    If Serial Killer slashes the last Werewolf at night, the waiting Successor inherits the pack, averting instant SK solo victory.
    Given A New Game    code=MID04    limbo_enabled=${FALSE}
    And Player Joins As    OldWolf       role=werewolf
    And Player Joins As    Dexter        role=serial_killer
    And Player Joins As    Farmer        role=villager
    And Player Joins As    Understudy
    When Game Starts
    And Assign Midgame Role    Understudy    successor
    # Night: SK strikes OldWolf
    When Serial Killer Attacks    OldWolf
    And Night Resolves
    # OldWolf dies, Understudy steps in as Werewolf
    Then Player Status Should Be    OldWolf       dead
    And Player Status Should Be     Understudy    alive
    And Player Role Should Be       Understudy    werewolf
    And Player Faction Should Be    Understudy    wolves
    And Pending Gameover Should Be None
    And Winner Should Be            ${NONE}

Successor Steps In For Fallen Lover Averting Heartbreak And Enabling Lovers Win
    [Documentation]    When an Obsessive Lover is slain, Successor inherits their mantle and binds to the surviving partner, averting heartbreak and claiming Lovers victory.
    Given A New Game    code=MID05    limbo_enabled=${FALSE}
    And Player Joins As    Romeo         role=villager
    And Player Joins As    Juliet        role=villager
    And Player Joins As    StalkerWolf   role=werewolf
    And Player Joins As    Paris
    When Game Starts
    And Pair Lovers    Romeo    Juliet    lover_type=obsessive
    And Assign Midgame Role    Paris    successor
    # Night: Wolf attacks Romeo
    When Wolves Attack    Romeo
    And Night Resolves
    # Romeo dies, but Paris steps in as Juliet's new lover! Heartbreak is averted!
    Then Player Status Should Be    Romeo          dead
    And Player Status Should Be     Paris          alive
    And Player Status Should Be     Juliet         alive
    And Player Status Should Be     StalkerWolf    alive
    And Night Report Should Contain    stepped in as Successor
    # Day: Town executes StalkerWolf
    When Day Voting Begins
    And Set Official Nominees    StalkerWolf
    And Proceed To Final Vote
    And Player Votes For    Paris     StalkerWolf
    And Player Votes For    Juliet    StalkerWolf
    And Final Vote Is Tallied
    Then Player Status Should Be    StalkerWolf    dead
    # Paris and Juliet are the last 2 survivors -> Lovers win!
    And Pending Gameover Winner Should Be    lovers

Spectral Ghost And Disgruntled Ghost Midgame Joiners Do Not Disrupt Living Counts
    [Documentation]    Players entering as ghosts have status 'dead' and do not alter living player counts or vote requirements.
    Given A New Game    code=MID06    limbo_enabled=${FALSE}
    And Player Joins As    WolfHost    role=werewolf
    And Player Joins As    TownieA     role=villager
    And Player Joins As    TownieB     role=villager
    When Game Starts
    # 2 late joiners arrive as ghosts
    When Player Joins As    SpookyGhost
    And Assign Midgame Role    SpookyGhost    ghost
    When Player Joins As    AngrySpirit
    And Assign Midgame Role    AngrySpirit    disgruntled_ghost
    Then Player Status Should Be    SpookyGhost    dead
    And Player Status Should Be     AngrySpirit    dead
    And Living Players Count Should Be    3
    And Pending Gameover Should Be None

Midgame Joiner After Gameover Preserves Concluded Game And Winner
    [Documentation]    Late arrivals after Game Over cannot alter the concluded state or overwrite the recorded winner.
    Given A New Game    code=MID07    limbo_enabled=${FALSE}
    And Player Joins As    WolfChamp    role=werewolf
    And Player Joins As    FallenTown   role=villager
    When Game Starts
    And Trigger Game Over    wolves
    Then Winner Should Be    wolves
    # Late arrival tries to take a town role
    When Player Joins As    VeryLateTraveler
    And Assign Midgame Role    VeryLateTraveler    traveler
    Then Winner Should Be    wolves
