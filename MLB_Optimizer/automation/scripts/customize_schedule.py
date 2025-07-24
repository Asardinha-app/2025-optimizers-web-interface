#!/usr/bin/env python3
"""
Customize Automation Schedule for MLB Optimizer
Allows customization of update frequency and timing.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from datetime import datetime
import json

class ScheduleCustomizer:
    """Customize the automation schedule for different frequencies."""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.config_file = self.script_dir / 'automation_config.json'
        self.log_dir = Path("MLB_Optimizer/logs")
        
    def load_config(self) -> dict:
        """Load current automation configuration."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_config(self, config: dict):
        """Save automation configuration."""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get_schedule_options(self) -> dict:
        """Get available schedule options."""
        return {
            '1': {
                'name': 'Daily (9:00 AM)',
                'description': 'Update every day at 9:00 AM',
                'cron': '0 9 * * *',
                'launchd': {'Hour': 9, 'Minute': 0}
            },
            '2': {
                'name': 'Weekly (Monday 9:00 AM)',
                'description': 'Update every Monday at 9:00 AM',
                'cron': '0 9 * * 1',
                'launchd': {'Weekday': 1, 'Hour': 9, 'Minute': 0}
            },
            '3': {
                'name': 'Weekly (Sunday 6:00 PM)',
                'description': 'Update every Sunday at 6:00 PM',
                'cron': '0 18 * * 0',
                'launchd': {'Weekday': 0, 'Hour': 18, 'Minute': 0}
            },
            '4': {
                'name': 'Bi-weekly (Alternating Mondays)',
                'description': 'Update every other Monday at 9:00 AM',
                'cron': '0 9 * * 1',
                'launchd': {'Weekday': 1, 'Hour': 9, 'Minute': 0},
                'custom_logic': 'bi_weekly'
            },
            '5': {
                'name': 'Monthly (First Monday)',
                'description': 'Update first Monday of each month at 9:00 AM',
                'cron': '0 9 1-7 * 1',
                'launchd': {'Weekday': 1, 'Hour': 9, 'Minute': 0},
                'custom_logic': 'monthly'
            },
            '6': {
                'name': 'Custom Schedule',
                'description': 'Define your own schedule',
                'custom': True
            }
        }
    
    def display_schedule_options(self):
        """Display available schedule options."""
        options = self.get_schedule_options()
        
        print("📅 Available Schedule Options:")
        print("=" * 40)
        
        for key, option in options.items():
            print(f"{key}. {option['name']}")
            print(f"   {option['description']}")
            print()
    
    def get_custom_schedule(self) -> dict:
        """Get custom schedule from user input."""
        print("🔧 Custom Schedule Configuration")
        print("=" * 30)
        
        # Frequency
        print("Frequency options:")
        print("1. Daily")
        print("2. Weekly")
        print("3. Monthly")
        print("4. Custom cron expression")
        
        freq_choice = input("Enter frequency choice (1-4): ").strip()
        
        if freq_choice == "1":
            # Daily
            hour = int(input("Enter hour (0-23): "))
            minute = int(input("Enter minute (0-59): "))
            return {
                'name': f'Daily ({hour:02d}:{minute:02d})',
                'description': f'Update every day at {hour:02d}:{minute:02d}',
                'cron': f'{minute} {hour} * * *',
                'launchd': {'Hour': hour, 'Minute': minute}
            }
        
        elif freq_choice == "2":
            # Weekly
            days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            print("Day of week:")
            for i, day in enumerate(days):
                print(f"{i}. {day}")
            
            day_choice = int(input("Enter day choice (0-6): "))
            hour = int(input("Enter hour (0-23): "))
            minute = int(input("Enter minute (0-59): "))
            
            return {
                'name': f'Weekly ({days[day_choice]} {hour:02d}:{minute:02d})',
                'description': f'Update every {days[day_choice]} at {hour:02d}:{minute:02d}',
                'cron': f'{minute} {hour} * * {day_choice}',
                'launchd': {'Weekday': day_choice, 'Hour': hour, 'Minute': minute}
            }
        
        elif freq_choice == "3":
            # Monthly
            day_of_month = int(input("Enter day of month (1-31): "))
            hour = int(input("Enter hour (0-23): "))
            minute = int(input("Enter minute (0-59): "))
            
            return {
                'name': f'Monthly (Day {day_of_month} {hour:02d}:{minute:02d})',
                'description': f'Update monthly on day {day_of_month} at {hour:02d}:{minute:02d}',
                'cron': f'{minute} {hour} {day_of_month} * *',
                'launchd': {'Day': day_of_month, 'Hour': hour, 'Minute': minute}
            }
        
        elif freq_choice == "4":
            # Custom cron
            cron_expr = input("Enter cron expression (e.g., '0 9 * * 1'): ")
            description = input("Enter description: ")
            
            return {
                'name': f'Custom ({cron_expr})',
                'description': description,
                'cron': cron_expr,
                'custom': True
            }
        
        else:
            print("❌ Invalid choice")
            return None
    
    def update_macos_schedule(self, schedule: dict):
        """Update macOS launchd schedule."""
        try:
            # Create new plist content
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
    </array>
    <key>WorkingDirectory</key>
    <string>{self.script_dir}</string>
    <key>StandardOutPath</key>
    <string>{self.log_dir}/weekly_update.log</string>
    <key>StandardErrorPath</key>
    <string>{self.log_dir}/weekly_update_error.log</string>
    <key>StartCalendarInterval</key>
    <dict>"""
            
            # Add schedule-specific keys
            for key, value in schedule['launchd'].items():
                plist_content += f"""
        <key>{key}</key>
        <integer>{value}</integer>"""
            
            plist_content += """
    </dict>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>"""
            
            # Write plist file
            plist_path = Path.home() / "Library/LaunchAgents/com.mlboptimizer.weeklyupdate.plist"
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # Unload and reload the launch agent
            subprocess.run(['launchctl', 'unload', str(plist_path)], capture_output=True)
            subprocess.run(['launchctl', 'load', str(plist_path)], check=True)
            
            print(f"✅ macOS schedule updated: {schedule['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update macOS schedule: {e}")
            return False
    
    def update_linux_schedule(self, schedule: dict):
        """Update Linux cron schedule."""
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crontab = result.stdout if result.returncode == 0 else ""
            
            # Remove old MLB optimizer entries
            lines = current_crontab.split('\n')
            filtered_lines = [line for line in lines if 'mlboptimizer' not in line and line.strip()]
            
            # Add new cron job
            cron_entry = f"{schedule['cron']} cd {self.script_dir} && {sys.executable} auto_update.py >> {self.log_dir}/weekly_update.log 2>&1"
            filtered_lines.append(f"# MLB_Optimizer Update - {schedule['name']}")
            filtered_lines.append(cron_entry)
            
            # Write new crontab
            new_crontab = '\n'.join(filtered_lines) + '\n'
            
            # Create temporary file
            temp_cron = Path("temp_cron")
            with open(temp_cron, 'w') as f:
                f.write(new_crontab)
            
            subprocess.run(['crontab', str(temp_cron)], check=True)
            os.remove(temp_cron)
            
            print(f"✅ Linux schedule updated: {schedule['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update Linux schedule: {e}")
            return False
    
    def update_windows_schedule(self, schedule: dict):
        """Update Windows Task Scheduler."""
        try:
            # Create new batch file
            batch_content = f"""@echo off
cd /d "{self.script_dir}"
"{sys.executable}" auto_update.py >> "{self.log_dir}\\weekly_update.log" 2>&1
"""
            
            batch_file = self.script_dir / "mlb_optimizer_update.bat"
            with open(batch_file, 'w') as f:
                f.write(batch_content)
            
            # Create PowerShell script for new schedule
            if 'custom_logic' in schedule:
                # Handle custom logic (bi-weekly, monthly)
                ps_script = f"""
# Remove existing task
Unregister-ScheduledTask -TaskName "MLB Optimizer Weekly Update" -Confirm:$false

# Create new task with custom logic
$action = New-ScheduledTaskAction -Execute "{batch_file}"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\\$env:USERNAME" -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName "MLB Optimizer Update" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "{schedule['description']}"
"""
            else:
                # Standard schedule
                ps_script = f"""
# Remove existing task
Unregister-ScheduledTask -TaskName "MLB Optimizer Weekly Update" -Confirm:$false

# Create new task
$action = New-ScheduledTaskAction -Execute "{batch_file}"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\\$env:USERNAME" -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName "MLB Optimizer Update" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "{schedule['description']}"
"""
            
            ps_file = self.script_dir / "update_windows_task.ps1"
            with open(ps_file, 'w') as f:
                f.write(ps_script)
            
            print("🔧 Windows Task Scheduler Update")
            print("   Please run the following command in PowerShell as Administrator:")
            print(f"   & '{ps_file}'")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to update Windows schedule: {e}")
            return False
    
    def customize_schedule(self):
        """Main function to customize the automation schedule."""
        print("🔧 MLB_Optimizer Schedule Customization")
        print("=" * 45)
        
        # Display current configuration
        config = self.load_config()
        if config:
            print(f"Current schedule: {config.get('update_schedule', 'Unknown')}")
            print(f"Platform: {config.get('platform', 'Unknown')}")
            print()
        
        # Display options
        self.display_schedule_options()
        
        # Get user choice
        choice = input("Enter your choice (1-6): ").strip()
        
        options = self.get_schedule_options()
        if choice not in options:
            print("❌ Invalid choice")
            return False
        
        selected_schedule = options[choice]
        
        # Handle custom schedule
        if selected_schedule.get('custom', False):
            selected_schedule = self.get_custom_schedule()
            if not selected_schedule:
                return False
        
        # Update platform-specific schedule
        platform = platform.system().lower()
        success = False
        
        if platform == "darwin":
            success = self.update_macos_schedule(selected_schedule)
        elif platform == "linux":
            success = self.update_linux_schedule(selected_schedule)
        elif platform == "windows":
            success = self.update_windows_schedule(selected_schedule)
        else:
            print(f"❌ Unsupported platform: {platform}")
            return False
        
        if success:
            # Update configuration
            config['update_schedule'] = selected_schedule['name']
            config['schedule_description'] = selected_schedule['description']
            config['last_customization'] = datetime.now().isoformat()
            
            self.save_config(config)
            
            print(f"\n✅ Schedule updated successfully!")
            print(f"📅 New schedule: {selected_schedule['name']}")
            print(f"📝 Description: {selected_schedule['description']}")
            print(f"📄 Configuration saved to: {self.config_file}")
        
        return success

def main():
    """Main function."""
    customizer = ScheduleCustomizer()
    
    if customizer.customize_schedule():
        print("\n🎉 Schedule customization complete!")
        print("\n📋 Next Steps:")
        print("1. Monitor the next scheduled update")
        print("2. Check logs to verify the new schedule works")
        print("3. Run 'python monitor_automation.py' to check status")
    else:
        print("\n❌ Schedule customization failed.")
        sys.exit(1)

if __name__ == "__main__":
    main() 