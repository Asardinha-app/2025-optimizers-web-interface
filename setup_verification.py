#!/usr/bin/env python3
"""
Software Verification Script for Web Interface Development
Checks what's already installed and what needs to be installed
"""

import sys
import subprocess
import platform
import os
from pathlib import Path

def check_python():
    """Check Python installation"""
    print("🐍 Checking Python installation...")
    
    python_version = sys.version_info
    print(f"   Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version >= (3, 8):
        print("   ✅ Python 3.8+ is installed and ready")
        return True
    else:
        print("   ❌ Python 3.8+ is required. Please install Python 3.8 or higher")
        return False

def check_git():
    """Check Git installation"""
    print("\n📦 Checking Git installation...")
    
    try:
        result = subprocess.run(['git', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"   ✅ Git is installed: {version}")
            return True
        else:
            print("   ❌ Git is not installed or not accessible")
            return False
    except FileNotFoundError:
        print("   ❌ Git is not installed")
        return False
    except Exception as e:
        print(f"   ❌ Error checking Git: {e}")
        return False

def check_pip():
    """Check pip installation"""
    print("\n📦 Checking pip installation...")
    
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"   ✅ pip is installed: {version}")
            return True
        else:
            print("   ❌ pip is not installed or not accessible")
            return False
    except Exception as e:
        print(f"   ❌ Error checking pip: {e}")
        return False

def check_required_packages():
    """Check if required packages are installed"""
    print("\n📚 Checking required packages...")
    
    required_packages = [
        'streamlit',
        'pandas', 
        'numpy',
        'plotly',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package} is installed")
        except ImportError:
            print(f"   ❌ {package} is NOT installed")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n   📋 Missing packages: {', '.join(missing_packages)}")
        print("   💡 These will be installed in Step 1.2")
        return False
    else:
        print("   ✅ All required packages are installed")
        return True

def check_system_info():
    """Display system information"""
    print("\n💻 System Information:")
    print(f"   Operating System: {platform.system()} {platform.release()}")
    print(f"   Architecture: {platform.machine()}")
    print(f"   Python Executable: {sys.executable}")
    print(f"   Current Working Directory: {os.getcwd()}")

def generate_installation_guide():
    """Generate installation guide based on system"""
    print("\n📋 Installation Guide:")
    
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        print("""
   🍎 macOS Installation Guide:
   
   1. Python:
      - Download from https://www.python.org/downloads/
      - Or install via Homebrew: brew install python
   
   2. Git:
      - Download from https://git-scm.com/download/mac
      - Or install via Homebrew: brew install git
   
   3. GitHub Account:
      - Go to https://github.com and create an account
      - Set up SSH keys (optional but recommended)
        """)
    
    elif system == "windows":
        print("""
   🪟 Windows Installation Guide:
   
   1. Python:
      - Download from https://www.python.org/downloads/
      - Make sure to check "Add Python to PATH" during installation
   
   2. Git:
      - Download from https://git-scm.com/download/win
      - Use default settings during installation
   
   3. GitHub Account:
      - Go to https://github.com and create an account
      - Install GitHub Desktop (optional)
        """)
    
    elif system == "linux":
        print("""
   🐧 Linux Installation Guide:
   
   1. Python:
      - Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip
      - CentOS/RHEL: sudo yum install python3 python3-pip
      - Or download from https://www.python.org/downloads/
   
   2. Git:
      - Ubuntu/Debian: sudo apt install git
      - CentOS/RHEL: sudo yum install git
      - Or download from https://git-scm.com/download/linux
   
   3. GitHub Account:
      - Go to https://github.com and create an account
      - Set up SSH keys: ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
        """)
    
    else:
        print("""
   ❓ Unknown Operating System:
   
   Please install the following manually:
   1. Python 3.8+: https://www.python.org/downloads/
   2. Git: https://git-scm.com/downloads
   3. GitHub Account: https://github.com
        """)

def main():
    """Main verification function"""
    print("🚀 Web Interface Development - Software Verification")
    print("=" * 60)
    
    # Check system info
    check_system_info()
    
    # Check installations
    python_ok = check_python()
    git_ok = check_git()
    pip_ok = check_pip()
    packages_ok = check_required_packages()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY:")
    print(f"   Python 3.8+: {'✅ Ready' if python_ok else '❌ Needs Installation'}")
    print(f"   Git: {'✅ Ready' if git_ok else '❌ Needs Installation'}")
    print(f"   pip: {'✅ Ready' if pip_ok else '❌ Needs Installation'}")
    print(f"   Required Packages: {'✅ Ready' if packages_ok else '⚠️ Will Install in Step 1.2'}")
    
    # Next steps
    print("\n🎯 NEXT STEPS:")
    if not python_ok or not git_ok:
        print("   1. Install missing software (see guide below)")
        print("   2. Run this verification script again")
        print("   3. Proceed to Step 1.2 when all software is installed")
        generate_installation_guide()
    else:
        print("   ✅ All required software is installed!")
        print("   🚀 Ready to proceed to Step 1.2: Set Up Local Development Environment")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 