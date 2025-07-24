#!/usr/bin/env python3
"""CLI entry point for MLB Optimizer"""

import sys
import os
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.optimizer import MLBOptimizer, Config

def main():
    """Run the MLB Optimizer with command line arguments"""
    parser = argparse.ArgumentParser(
        description="MLB Daily Fantasy Sports Lineup Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/run_optimizer.py
  python3 scripts/run_optimizer.py --data-file /path/to/MLB_FD.csv
  python3 scripts/run_optimizer.py --num-lineups 150 --max-attempts 500
  python3 scripts/run_optimizer.py --output-file /path/to/output.csv
        """
    )
    
    parser.add_argument(
        '--data-file',
        type=str,
        default=Config.DATA_FILE,
        help=f'Path to player data CSV file (default: {Config.DATA_FILE})'
    )
    
    parser.add_argument(
        '--num-lineups',
        type=int,
        default=Config.NUM_LINEUPS_TO_GENERATE,
        help=f'Number of lineups to generate (default: {Config.NUM_LINEUPS_TO_GENERATE})'
    )
    
    parser.add_argument(
        '--max-attempts',
        type=int,
        default=Config.MAX_ATTEMPTS,
        help=f'Maximum optimization attempts (default: {Config.MAX_ATTEMPTS})'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        default="/Users/adamsardinha/Desktop/FD_MLB_Lineups.csv",
        help='Path to output CSV file (default: /Users/adamsardinha/Desktop/FD_MLB_Lineups.csv)'
    )
    
    parser.add_argument(
        '--max-salary',
        type=int,
        default=Config.MAX_SALARY,
        help=f'Maximum salary cap (default: {Config.MAX_SALARY})'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    print("🚀 MLB Optimizer CLI")
    print("=" * 50)
    
    try:
        # Create optimizer instance
        optimizer = MLBOptimizer()
        
        # Update config with command line arguments
        optimizer.config.DATA_FILE = args.data_file
        optimizer.config.NUM_LINEUPS_TO_GENERATE = args.num_lineups
        optimizer.config.MAX_ATTEMPTS = args.max_attempts
        optimizer.config.MAX_SALARY = args.max_salary
        
        print(f"📊 Configuration:")
        print(f"   Data file: {args.data_file}")
        print(f"   Number of lineups: {args.num_lineups}")
        print(f"   Max attempts: {args.max_attempts}")
        print(f"   Max salary: ${args.max_salary:,}")
        print(f"   Output file: {args.output_file}")
        print()
        
        # Load data
        print("📥 Loading player data...")
        if not optimizer.load_data(args.data_file):
            print("❌ Failed to load player data")
            return 1
        
        print(f"✅ Loaded {len(optimizer.players)} players from {len(optimizer.teams)} teams")
        print()
        
        # Generate lineups
        print("⚡ Generating optimized lineups...")
        lineups = optimizer.generate_lineups(args.num_lineups, args.max_attempts)
        
        if not lineups:
            print("❌ No lineups were generated. Please check your configuration settings.")
            return 1
        
        # Export lineups
        print(f"💾 Exporting {len(lineups)} lineups...")
        optimizer.export_lineups(lineups, args.output_file)
        
        print()
        print("✅ Optimization completed successfully!")
        print(f"📁 Lineups exported to: {args.output_file}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        print("Please check that the data file exists and the path is correct.")
        return 1
    except ValueError as e:
        print(f"❌ Validation error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())