#!/usr/bin/env python3
"""
Repository Synchronization Script
Keeps the web interface repository and main optimizers repository in sync.
"""

import subprocess
import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/repo_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RepositorySync:
    def __init__(self):
        self.web_interface_repo = "origin"
        self.optimizers_repo = "optimizers"
        self.current_dir = Path.cwd()
        
    def run_command(self, command, capture_output=True):
        """Run a git command and return the result"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                cwd=self.current_dir
            )
            return result
        except Exception as e:
            logger.error(f"Error running command '{command}': {e}")
            return None
    
    def get_current_branch(self):
        """Get the current git branch"""
        result = self.run_command("git branch --show-current")
        if result and result.returncode == 0:
            return result.stdout.strip()
        return None
    
    def get_status(self):
        """Get current git status"""
        result = self.run_command("git status --porcelain")
        if result and result.returncode == 0:
            return result.stdout.strip()
        return ""
    
    def commit_and_push_web_interface(self, message):
        """Commit and push changes to web interface repository"""
        logger.info("Committing and pushing to web interface repository...")
        
        # Add all changes
        self.run_command("git add .")
        
        # Commit
        commit_result = self.run_command(f'git commit -m "{message}"')
        if commit_result and commit_result.returncode == 0:
            logger.info("✅ Successfully committed changes")
        else:
            logger.error("❌ Failed to commit changes")
            return False
        
        # Push to web interface repository
        push_result = self.run_command(f"git push {self.web_interface_repo} main")
        if push_result and push_result.returncode == 0:
            logger.info("✅ Successfully pushed to web interface repository")
            return True
        else:
            logger.error("❌ Failed to push to web interface repository")
            return False
    
    def sync_to_optimizers_repo(self):
        """Sync changes to the main optimizers repository"""
        logger.info("Syncing changes to optimizers repository...")
        
        # Push to optimizers repository
        push_result = self.run_command(f"git push {self.optimizers_repo} main")
        if push_result and push_result.returncode == 0:
            logger.info("✅ Successfully synced to optimizers repository")
            return True
        else:
            logger.error("❌ Failed to sync to optimizers repository")
            return False
    
    def pull_from_optimizers_repo(self):
        """Pull latest changes from optimizers repository"""
        logger.info("Pulling latest changes from optimizers repository...")
        
        # Fetch latest changes
        fetch_result = self.run_command(f"git fetch {self.optimizers_repo}")
        if fetch_result and fetch_result.returncode == 0:
            logger.info("✅ Successfully fetched from optimizers repository")
        else:
            logger.error("❌ Failed to fetch from optimizers repository")
            return False
        
        # Merge changes
        merge_result = self.run_command(f"git merge {self.optimizers_repo}/main")
        if merge_result and merge_result.returncode == 0:
            logger.info("✅ Successfully merged changes from optimizers repository")
            return True
        else:
            logger.error("❌ Failed to merge changes from optimizers repository")
            return False
    
    def sync_repositories(self, commit_message=None):
        """Main synchronization function"""
        logger.info("🔄 Starting repository synchronization...")
        
        # Get current status
        status = self.get_status()
        if not status:
            logger.info("✅ No changes to sync")
            return True
        
        # Use default commit message if none provided
        if not commit_message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Auto-sync: {timestamp}"
        
        # Commit and push to web interface repository
        if not self.commit_and_push_web_interface(commit_message):
            return False
        
        # Sync to optimizers repository
        if not self.sync_to_optimizers_repo():
            return False
        
        logger.info("✅ Repository synchronization completed successfully!")
        return True
    
    def setup_automation(self):
        """Setup automated synchronization"""
        logger.info("Setting up automated repository synchronization...")
        
        # Create automation directory if it doesn't exist
        automation_dir = Path("automation")
        automation_dir.mkdir(exist_ok=True)
        
        # Create automation script
        automation_script = automation_dir / "auto_sync.py"
        with open(automation_script, 'w') as f:
            f.write('''#!/usr/bin/env python3
"""
Automated Repository Synchronization
Runs automatically to keep repositories in sync.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sync_repositories import RepositorySync

if __name__ == "__main__":
    sync = RepositorySync()
    sync.sync_repositories()
''')
        
        # Make script executable
        os.chmod(automation_script, 0o755)
        
        logger.info("✅ Automation setup completed")
        logger.info(f"📁 Automation script created: {automation_script}")

def main():
    """Main function"""
    sync = RepositorySync()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "sync":
            commit_message = sys.argv[2] if len(sys.argv) > 2 else None
            sync.sync_repositories(commit_message)
        
        elif command == "pull":
            sync.pull_from_optimizers_repo()
        
        elif command == "setup":
            sync.setup_automation()
        
        elif command == "status":
            status = sync.get_status()
            if status:
                print("📝 Changes detected:")
                print(status)
            else:
                print("✅ No changes detected")
        
        else:
            print("Usage:")
            print("  python sync_repositories.py sync [commit_message]")
            print("  python sync_repositories.py pull")
            print("  python sync_repositories.py setup")
            print("  python sync_repositories.py status")
    
    else:
        # Default: sync with auto-generated commit message
        sync.sync_repositories()

if __name__ == "__main__":
    main() 