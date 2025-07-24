# MLB Optimizer Configuration

class OptimizerConfig:
    # File paths
    DATA_FILE = "/path/to/MLB_FD.csv"
    OUTPUT_PATH = "/path/to/output/"
    
    # Optimization settings
    NUM_LINEUPS = 300
    MAX_SALARY = 35000
    MAX_ATTEMPTS = 1000
    
    # Stack settings
    MAX_PRIMARY_STACK_PCT = 0.2083
    MAX_SECONDARY_STACK_PCT = 0.126
    
    # Late swap settings
    PRESERVE_STACKS = True
    MAX_SWAP_ATTEMPTS = 100
    
    # Logging settings
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/optimizer.log"