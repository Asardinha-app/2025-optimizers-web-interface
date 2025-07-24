#!/usr/bin/env python3
"""
MLB Optimizer Main Entry Point

This is the main entry point for the MLB Optimizer with the new organized structure.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

def main():
    """Main entry point for MLB Optimizer"""
    print("🚀 MLB Optimizer - Main Entry Point")
    print("=" * 50)
    
    try:
        # Test imports from new structure
        from core.optimizer import Config, Player, Lineup
        from core.late_swap.optimizer import LateSwapOptimizer, LateSwapConfig
        from core.models.player import Player as PlayerModel
        from core.models.lineup import Lineup as LineupModel
        from core.models.swap import SwapAnalysis, LateSwapLineup
        
        print("✅ All core components imported successfully")
        print()
        print("📋 Available Components:")
        print("- Core Optimizer: core.optimizer")
        print("- Late Swap: core.late_swap.optimizer")
        print("- Data Models: core.models")
        print("- Configuration: config.settings")
        print()
        print("🔧 Usage Examples:")
        print("1. Run optimizer: python scripts/run_optimizer.py")
        print("2. Run late swap: python scripts/run_late_swap.py")
        print("3. Run scrapers: python scripts/run_scrapers.py")
        print()
        print("📚 Documentation: docs/")
        print("🧪 Tests: tests/")
        print("📁 Examples: examples/")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Please check that all components are properly installed.")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())