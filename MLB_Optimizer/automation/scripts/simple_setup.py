#!/usr/bin/env python3
"""
Simple Setup Automation for MLB Optimizer Weekly Updates
Configures automated weekly updates using cron jobs and system scheduling.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from datetime import datetime
import json

class SimpleAutomationSetup:
    """Setup automated weekly updates for the MLB optimizer."""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.automation_dir = self.script_dir.parent
        self.optimizer_dir = self.automation_dir.parent
        self.log_dir = self.optimizer_dir / "system_logs"
        self.log_dir.mkdir(exist_ok=True)
    
    def detect_platform(self) -> str:
        """Detect the operating system platform."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        elif system == "windows":
            return "windows"
        else:
            return "unknown"
    
    def setup_macos_automation(self) -> bool:
        """Setup automation for macOS using launchd."""
        try:
            # Create launch agent plist file
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mlboptimizer.weeklyupdate</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{self.script_dir}/auto_update.py</string>
        <string>--silent</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{self.optimizer_dir}</string>
    <key>StandardOutPath</key>
    <string>{self.log_dir}/weekly_update.log</string>
    <key>StandardErrorPath</key>
    <string>{self.log_dir}/weekly_update_error.log</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>"""
            
            # Write plist file
            plist_path = Path.home() / "Library/LaunchAgents/com.mlboptimizer.weeklyupdate.plist"
            plist_path.parent.mkdir(exist_ok=True)
            
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # Load the launch agent
            subprocess.run(['launchctl', 'load', str(plist_path)], check=True)
            
            print(f"✅ macOS automation setup complete!")
            print(f"   - Launch agent: {plist_path}")
            print(f"   - Logs: {self.log_dir}")
            print(f"   - Schedule: Every Monday at 9:00 AM")
            print(f"   - Mode: Silent background operation")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup macOS automation: {e}")
            return False
    
    def setup_linux_automation(self) -> bool:
        """Setup automation for Linux using cron."""
        try:
            # Create cron job entry with silent operation
            cron_entry = f"0 9 * * 1 cd {self.optimizer_dir} && {sys.executable} {self.script_dir}/auto_update.py --silent >> {self.log_dir}/weekly_update.log 2>&1"
            
            # Get current user's crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crontab = result.stdout if result.returncode == 0 else ""
            
            # Check if our job already exists
            if "mlboptimizer" not in current_crontab:
                # Add our cron job
                new_crontab = current_crontab + f"\n# MLB_Optimizer Weekly Update (Silent)\n{cron_entry}\n"
                
                # Write new crontab
                temp_cron = Path("temp_cron")
                with open(temp_cron, 'w') as f:
                    f.write(new_crontab)
                
                subprocess.run(['crontab', str(temp_cron)], check=True)
                os.remove(temp_cron)
            
            print(f"✅ Linux automation setup complete!")
            print(f"   - Cron job: Every Monday at 9:00 AM")
            print(f"   - Logs: {self.log_dir}/weekly_update.log")
            print(f"   - Command: {cron_entry}")
            print(f"   - Mode: Silent background operation")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup Linux automation: {e}")
            return False
    
    def setup_windows_automation(self) -> bool:
        """Setup automation for Windows using Task Scheduler."""
        try:
            # Create batch file for the task with silent operation
            batch_content = f"""@echo off
cd /d "{self.optimizer_dir}"
"{sys.executable}" "{self.script_dir}/auto_update.py" --silent >> "{self.log_dir}\\weekly_update.log" 2>&1
"""
            
            batch_file = self.script_dir / "mlb_optimizer_update.bat"
            with open(batch_file, 'w') as f:
                f.write(batch_content)
            
            # Create PowerShell script to setup Task Scheduler
            ps_script = f"""
# Remove existing task
Unregister-ScheduledTask -TaskName "MLB Optimizer Weekly Update" -Confirm:$false

# Create new task with silent operation
$action = New-ScheduledTaskAction -Execute "{batch_file}"
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 2am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -Hidden
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\\$env:USERNAME" -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName "MLB Optimizer Weekly Update" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Weekly silent update for MLB Optimizer"
"""
            
            ps_file = self.script_dir / "setup_windows_task.ps1"
            with open(ps_file, 'w') as f:
                f.write(ps_script)
            
            # Run PowerShell script as administrator
            print("🔧 Setting up Windows Task Scheduler...")
            print("   Note: This requires administrator privileges.")
            print("   Please run the following command in PowerShell as Administrator:")
            print(f"   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser")
            print(f"   & '{ps_file}'")
            print(f"   - Mode: Silent background operation")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup Windows automation: {e}")
            return False
    
    def create_monitoring_script(self) -> bool:
        """Create a monitoring script to check automation status."""
        monitoring_script = f"""#!/usr/bin/env python3
\"\"\"
MLB_Optimizer Automation Monitor
Checks the status of automated updates and sends notifications.
\"\"\"

import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

def check_last_update():
    \"\"\"Check when the last update was performed.\"\"\"
    last_update_file = Path("{self.optimizer_dir}/last_update.txt")
    
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
    \"\"\"Check recent log files for errors.\"\"\"
    log_dir = Path("{self.log_dir}")
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
    \"\"\"Main monitoring function.\"\"\"
    print("🔍 MLB_Optimizer Automation Monitor")
    print("=" * 40)
    
    update_ok = check_last_update()
    logs_ok = check_logs()
    
    if update_ok and logs_ok:
        print("\\n✅ Automation is working correctly")
        sys.exit(0)
    else:
        print("\\n❌ Automation issues detected")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
        
        try:
            monitor_file = self.script_dir / "monitor_automation.py"
            with open(monitor_file, 'w') as f:
                f.write(monitoring_script)
            
            # Make it executable
            os.chmod(monitor_file, 0o755)
            
            print(f"✅ Monitoring script created: {monitor_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create monitoring script: {e}")
            return False
    
    def setup_automation(self) -> bool:
        """Setup automation for the current platform."""
        print("🚀 Setting up MLB_Optimizer Weekly Automation")
        print("=" * 50)
        
        platform = self.detect_platform()
        print(f"📱 Detected platform: {platform}")
        
        success = True
        
        # Setup platform-specific automation
        if platform == "macos":
            success = self.setup_macos_automation()
        elif platform == "linux":
            success = self.setup_linux_automation()
        elif platform == "windows":
            success = self.setup_windows_automation()
        else:
            print(f"❌ Unsupported platform: {platform}")
            return False
        
        if success:
            # Create monitoring script
            self.create_monitoring_script()
            
            # Create configuration file
            config = {
                'platform': platform,
                'setup_date': datetime.now().isoformat(),
                'update_schedule': 'Weekly (Monday 2:00 AM ET)',
                'log_directory': str(self.log_dir),
                'scripts': {
                    'auto_update': str(self.script_dir / 'auto_update.py'),
                    'monitor': str(self.script_dir / 'monitor_automation.py')
                }
            }
            
            config_file = self.automation_dir / 'automation_config.json'
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✅ Automation setup complete!")
            print(f"📄 Configuration saved to: {config_file}")
            print(f"📊 Logs will be saved to: {self.log_dir}")
            print(f"🔍 Monitor automation with: python3 {self.script_dir}/monitor_automation.py")
        
        return success

def main():
    """Main setup function."""
    setup = SimpleAutomationSetup()
    
    if setup.setup_automation():
        print("\n🎉 MLB_Optimizer automation is now configured!")
        print("\n📋 Next Steps:")
        print("1. Monitor the first weekly update (next Monday at 2:00 AM ET)")
        print("2. Check logs in the 'system_logs' directory")
        print("3. Run 'python3 automation/scripts/monitor_automation.py' to check status")
        print("4. Customize schedule if needed")
    else:
        print("\n❌ Automation setup failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 