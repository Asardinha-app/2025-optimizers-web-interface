NHL Optimizer Documentation
==========================

Overview
--------

The NHL Optimizer is a sophisticated daily fantasy sports lineup generator specifically designed for NHL contests on FanDuel. It implements advanced stacking strategies, exposure management, and player filtering to create optimized lineups that maximize expected value while maintaining proper diversification.

Key Features
-----------

* **Advanced Line Stacking**: Implements primary and secondary line stacks with goalie correlation
* **Exposure Management**: Prevents over-exposure to specific lines and players using lockout mechanisms
* **Premium Defensemen Filtering**: Focuses on high-salary, high-shot defensemen using percentile thresholds
* **Deterministic Generation**: Creates consistent, reproducible lineups using highest-projected eligible players
* **Comprehensive Export**: Exports lineups with detailed statistics, rankings, and z-scores
* **Popular Line Prevention**: Prevents pairing the two most popular lines together

Architecture
-----------

The optimizer is built around several core data structures and algorithms:

Data Structures
~~~~~~~~~~~~~~

**Player Class**
    Represents individual players with all relevant attributes:

    .. code-block:: python

        @dataclass
        class Player:
            id: str                    # Unique player identifier
            name: str                  # Player name
            position: str              # Position (C, W, D, G)
            team: str                  # Player's team
            opponent: str              # Opposing team
            salary: int                # Player salary
            projection: float          # Fantasy points projection
            roster_order: int          # Line number (1-4 for forwards)
            is_goalie: bool = False    # Goalie flag
            shatt: float = 0.0        # Shots attempted
            ceiling: float = 0.0      # Ceiling projection
            projected_ownership: float = 0.0  # Ownership percentage

**Lineup Class**
    Represents a complete lineup with stacking information:

    .. code-block:: python

        @dataclass
        class Lineup:
            players: List[Player]      # All 9 players
            primary_stack: str         # Team:RO format (with goalie)
            secondary_stack: str       # Team:RO format (no goalie)
            total_salary: int          # Total salary
            total_projection: float    # Total projection

Configuration
------------

The optimizer uses a centralized configuration class for all settings:

.. code-block:: python

    class Config:
        DATA_FILE = "/Users/adamsardinha/Desktop/NHL_FD.csv"
        NUM_LINEUPS = 300
        MAX_SALARY = 55000
        MAX_ATTEMPTS_PER_LINEUP = 500
        MAX_PRIMARY_STACK_PCT = 0.20   # 20% max exposure for Primary stack
        MAX_SECONDARY_STACK_PCT = 0.15 # 15% max exposure for Secondary stack

Configuration Parameters
~~~~~~~~~~~~~~~~~~~~~~~

* **DATA_FILE**: Path to the CSV file containing player data
* **NUM_LINEUPS**: Number of lineups to generate
* **MAX_SALARY**: Maximum salary cap for each lineup ($55,000)
* **MAX_ATTEMPTS_PER_LINEUP**: Maximum attempts per lineup (unused in current implementation)
* **MAX_PRIMARY_STACK_PCT**: Maximum exposure percentage for primary stacks (20%)
* **MAX_SECONDARY_STACK_PCT**: Maximum exposure percentage for secondary stacks (15%)

Data Requirements
----------------

The optimizer expects a CSV file with specific column requirements:

Required Columns
~~~~~~~~~~~~~~~

* **Id**: Unique player identifier
* **Player ID + Player Name**: Player name in format "ID: Name"
* **Position**: Player position (C, W, D, G)
* **Team**: Player's team
* **Opponent**: Opposing team
* **Salary**: Player salary (numeric)
* **FPPG**: Fantasy points per game (projection)
* **Roster Order**: Line number (1-4 for forwards)

Optional Columns
~~~~~~~~~~~~~~~

* **Goalie**: Goalie status ("Confirmed" or "Expected")
* **shatt**: Shots attempted (numeric)
* **Projection Ceil**: Ceiling projection (numeric)
* **Projected Ownership**: Projected ownership percentage (numeric)
* **pp_line**: Power play line (0 = no PP time)

Data Processing Pipeline
-----------------------

The optimizer follows a structured data processing pipeline:

1. **Data Loading**
   - Loads CSV file and converts numeric columns
   - Validates data format and ranges
   - Prints salary range for verification

2. **Player Filtering**
   - Applies position-specific filters
   - Removes invalid players based on projections
   - Separates skaters and goalies

3. **Line Identification**
   - Groups players by team and roster order
   - Identifies valid lines with 3+ C/W players
   - Calculates line ownership using product of player ownership

4. **Premium Defensemen Calculation**
   - Calculates 65th percentile salary threshold
   - Calculates 50th percentile shots threshold
   - Filters defensemen to premium tier only

Player Filtering Logic
---------------------

Skaters (C, W, D)
~~~~~~~~~~~~~~~~~

* Must have Roster Order 1-4
* Projection > -1 (excludes extremely poor projections)
* Defensemen with pp_line = 0 are excluded (no power play time)

Goalies (G)
~~~~~~~~~~~

* Must have "Confirmed" or "Expected" in Goalie column
* Projection > 0 (excludes backup goalies)

Lineup Structure
---------------

Each lineup consists of exactly 9 players in specific positions:

* **2 Centers (C1, C2)**
* **4 Wings (W1, W2, W3, W4)**
* **2 Defensemen (D1, D2)**
* **1 Goalie (G)**

Stacking Strategy
----------------

The optimizer implements a sophisticated stacking strategy with two types of stacks:

Primary Stack
~~~~~~~~~~~~

* **3 forwards + 1 goalie** from the same team
* Maximum 20% exposure across all lineups
* Goalie must be from the same team as the forwards
* **Goalie Correlation Constraint**: No skaters from the goalie's opponent team
* Automatically locked out for 1 lineup after use

Secondary Stack
~~~~~~~~~~~~~~

* **3 forwards** from a different team
* Maximum 15% exposure across all lineups
* Cannot be paired with primary stack from the same team
* **Popular Line Prevention**: Cannot be paired with the two most popular lines together
* Automatically locked out for 1 lineup after use

Defensemen Strategy
------------------

Premium Defensemen Filter
~~~~~~~~~~~~~~~~~~~~~~~~

The optimizer uses percentile-based thresholds to identify premium defensemen:

* **Salary Threshold**: 65th percentile of all defensemen salaries
* **Shots Threshold**: 50th percentile of defensemen shots attempted
* Only defensemen meeting both thresholds are considered for lineup construction

Exposure Management
------------------

The optimizer implements sophisticated exposure management using lockout mechanisms:

After Each Lockout
~~~~~~~~~~~~~~~~~

* **Primary stacks**: Locked out for 1 lineup after use
* **Secondary stacks**: Locked out for 1 lineup after use
* **Individual defensemen**: Locked out for 1 lineup after use
* **Automatic unlocking**: Stacks are unlocked when their exposure drops below threshold

Exposure Thresholds
~~~~~~~~~~~~~~~~~~~

* **Primary stacks**: 20% maximum exposure
* **Secondary stacks**: 15% maximum exposure
* **Defensemen**: 25% maximum exposure

Lineup Constraints
-----------------

Salary Cap
~~~~~~~~~~

* Total salary must not exceed $55,000

Team Limits
~~~~~~~~~~

* Maximum 4 players per team
* Minimum 3 different teams

Player Uniqueness
~~~~~~~~~~~~~~~~

* All 9 players must be unique
* Lineups must have at least 3 unique players compared to all previous lineups

Popular Line Prevention
~~~~~~~~~~~~~~~~~~~~~

* The two most popular lines (by ownership) cannot be paired together

Algorithm Details
----------------

Deterministic Lineup Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The optimizer uses a deterministic algorithm that always selects the highest-projected eligible players:

1. **Sort lines by total projection** (highest first)
2. **For each lineup**:
   * Select highest-projected eligible primary stack
   * Select highest-projected eligible secondary stack
   * Select highest-projected eligible premium defensemen
   * Apply all constraints and validation

Lineup Validation
~~~~~~~~~~~~~~~~

Each lineup is validated against multiple constraints:

* Salary cap compliance
* Team limits (max 4 per team, min 3 teams)
* Player uniqueness
* Goalie correlation (no opponent skaters)
* Popular line prevention
* Similarity threshold (max 6 shared players with previous lineups)

Output Format
------------

The optimizer exports lineups to CSV with comprehensive statistics:

Slot Columns
~~~~~~~~~~~

* **C1, C2**: Center positions
* **W1, W2, W3, W4**: Wing positions
* **D1, D2**: Defensemen positions
* **G**: Goalie position

Summary Columns
~~~~~~~~~~~~~~

* **Primary_Stack**: Team and line number for primary stack
* **Secondary_Stack**: Team and line number for secondary stack
* **Total_Projection**: Sum of all player projections
* **Total_Salary**: Sum of all player salaries
* **Total Ceiling**: Sum of all player ceiling projections
* **Total Shots**: Sum of all player shots attempted
* **Product Ownership**: Product of all player ownership percentages

Ranking Columns
~~~~~~~~~~~~~~

* **Projection Rank**: Rank by total projection (higher is better)
* **Ceiling Rank**: Rank by total ceiling (higher is better)
* **Shots Rank**: Rank by total shots (higher is better)
* **Ownership Rank**: Rank by product ownership (lower is better)
* **Average**: Average of all ranks (lower is better)
* **Projection Z, Ceiling Z, Shots Z, Ownership Z**: Z-scores for each metric

Usage Example
------------

.. code-block:: python

    from NHL_Optimizer import main
    
    # Run the optimizer
    main()

The optimizer will:

1. **Load and filter player data**
   * Load CSV file
   * Apply position and projection filters
   * Create Player objects

2. **Identify valid lines**
   * Group players by team and roster order
   * Calculate line ownership
   * Identify top ownership lines

3. **Generate lineups**
   * Create deterministic lineups with stacking
   * Apply exposure management
   * Validate all constraints

4. **Print detailed information**
   * Display each lineup with stack breakdown
   * Show salary and projection totals
   * Highlight primary and secondary stacks

5. **Export results**
   * Save lineups to CSV with rankings
   * Include all statistics and z-scores

Output Files
-----------

* **Console Output**: Detailed lineup information and exposure summary
* **nhl_lineups.csv**: Exported lineups with rankings and statistics

Console Output Example
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

    NHL DFS Lineup Optimizer
    ==================================================
    Loading data...
    Salary range: 3,000 - 12,000
    Player pool: 150 -> 120 after filtering
    Found 25 valid lines
    Premium defensemen pool: 15 out of 45 total defensemen
    Salary threshold: $6,500
    Shots threshold: 2.5 shots attempted
    
    === Lineup 1 ===
    Total Salary: $54,200
    Total Projection: 145.8
    
    PRIMARY STACK: TOR:1 (with goalie)
    --------------------------------------------------
      C: Auston Matthews - $9,200 - 25.5
      W: Mitch Marner - $8,800 - 22.3
      W: William Nylander - $7,500 - 20.1
      G: Ilya Samsonov - $8,000 - 18.2

Troubleshooting
--------------

Common Issues
~~~~~~~~~~~~

**No eligible primary stacks**
* Check that lines have at least 3 C/W players
* Verify goalie availability for primary team
* Ensure goalie correlation constraint is satisfied

**No eligible secondary stacks**
* Ensure sufficient line diversity
* Check exposure thresholds
* Verify popular line prevention logic

**Salary cap violations**
* Verify salary data format
* Check for data entry errors
* Review premium defensemen thresholds

**No premium defensemen**
* Review salary and shots data
* Adjust percentile thresholds if needed
* Check data quality for defensemen

**Lineup generation stops early**
* Check exposure management settings
* Verify constraint satisfaction
* Review player pool size and diversity

Performance Notes
----------------

* **Deterministic algorithms** ensure reproducible results
* **Exposure management** prevents over-concentration
* **Lineup generation stops** when constraints cannot be satisfied
* **Processing time scales** with number of lineups and player pool size
* **Memory usage** is minimal due to efficient data structures

Advanced Configuration
--------------------

For advanced users, the following parameters can be modified in the code:

* **d_salary_threshold**: Defensemen salary percentile (default: 65)
* **d_shots_threshold**: Defensemen shots percentile (default: 50)
* **defensemen_exposure_pct**: Maximum defensemen exposure (default: 25%)
* **similarity_threshold**: Maximum shared players between lineups (default: 6)

These parameters are defined in the ``create_deterministic_lineups`` function.

Algorithm Complexity
------------------

* **Time Complexity**: O(n * m * k) where n = number of lineups, m = number of lines, k = number of defensemen
* **Space Complexity**: O(n) for storing lineups and exposure tracking
* **Deterministic**: Always produces the same results given the same input

Best Practices
-------------

* **Data Quality**: Ensure accurate projections and ownership data
* **Lineup Count**: Start with 100-300 lineups for optimal diversification
* **Exposure Limits**: Adjust exposure percentages based on contest size
* **Premium Defensemen**: Monitor defensemen pool size and adjust thresholds
* **Validation**: Always verify exported lineups against site requirements

Integration
-----------

The optimizer can be integrated into larger systems:

* **Batch Processing**: Run multiple optimizations with different parameters
* **API Integration**: Import functions for programmatic access
* **Data Pipeline**: Connect to external data sources
* **Automation**: Schedule regular optimizations

Future Enhancements
------------------

Potential improvements for future versions:

* **Multi-site support**: Extend to other DFS sites
* **Advanced projections**: Integrate with projection models
* **Machine learning**: Implement ML-based player selection
* **Real-time updates**: Live data integration
* **Web interface**: GUI for easier configuration 