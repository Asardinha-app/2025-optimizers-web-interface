#!/usr/bin/env python3
"""
MLB Optimizer Automation Monitor
Checks the status of automated updates and sends notifications.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

def check_last_update():
    """Check when the last update was performed."""
    last_update_file = Path("MLB_Optimizer/last_update.txt")
    
    if last_update_file.exists():
        try:
            with open(last_update_file, 'r') as f:
                timestamp_str = f.read().strip()
                last_update = datetime.fromisoformat(timestamp_str)
                days_since = (datetime.now() - last_update).days
                
                if days_since > 10:
                    print(f"⚠️  Warning: Last update was {{days_since}} days ago")
                    return False
                else:
                    print(f"✅ Last update: {{days_since}} days ago")
                    return True
        except Exception as e:
            print(f"❌ Error checking last update: {{e}}")
            return False
    else:
        print("⚠️  No update history found")
        return False

def check_logs():
    """Check recent log files for errors."""
    log_dir = Path("MLB_Optimizer/logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            print(f"📄 Latest log: {{latest_log.name}}")
            
            # Check for errors in recent logs
            try:
                with open(latest_log, 'r') as f:
                    content = f.read()
                    if "ERROR" in content or "FAILED" in content:
                        print("⚠️  Errors found in recent logs")
                        return False
                    else:
                        print("✅ No errors in recent logs")
                        return True
            except Exception as e:
                print(f"❌ Error reading logs: {{e}}")
                return False
    return True

def main():
    """Main monitoring function."""
    print("🔍 MLB_Optimizer Automation Monitor")
    print("=" * 40)
    
    update_ok = check_last_update()
    logs_ok = check_logs()
    
    if update_ok and logs_ok:
        print("\n✅ Automation is working correctly")
        sys.exit(0)
    else:
        print("\n❌ Automation issues detected")
        sys.exit(1)

if __name__ == "__main__":
    main()
