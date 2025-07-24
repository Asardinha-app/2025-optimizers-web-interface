#!/usr/bin/env python3
"""
Local Development Environment Setup Script
Automates the creation of project structure and virtual environment
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def create_project_structure():
    """Create the project directory structure"""
    print("📁 Creating project directory structure...")
    
    # Define the directory structure
    directories = [
        "web_interface",
        "web_interface/frontend",
        "web_interface/frontend/pages",
        "web_interface/frontend/components",
        "web_interface/frontend/utils",
        "web_interface/frontend/assets",
        "web_interface/backend",
        "web_interface/backend/api",
        "web_interface/backend/optimizers",
        "web_interface/backend/scrapers",
        "web_interface/backend/utils",
        "web_interface/shared",
        "web_interface/shared/models",
        "web_interface/shared/config",
        "web_interface/shared/utils",
        "web_interface/deployment"
    ]
    
    # Create directories
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ Created: {directory}")
    
    print("   ✅ Project structure created successfully!")

def create_virtual_environment():
    """Create and activate virtual environment"""
    print("\n🐍 Setting up virtual environment...")
    
    venv_path = Path("web_interface/venv")
    
    if venv_path.exists():
        print("   ⚠️ Virtual environment already exists")
        return True
    
    try:
        # Create virtual environment
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], 
                      check=True, capture_output=True)
        print("   ✅ Virtual environment created successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error creating virtual environment: {e}")
        return False

def install_required_packages():
    """Install required packages in virtual environment"""
    print("\n📦 Installing required packages...")
    
    # Determine the pip executable for the virtual environment
    if os.name == 'nt':  # Windows
        pip_path = "web_interface/venv/Scripts/pip"
    else:  # Unix/Linux/macOS
        pip_path = "web_interface/venv/bin/pip"
    
    # Required packages
    packages = [
        "streamlit",
        "pandas",
        "numpy", 
        "plotly",
        "requests",
        "fastapi",
        "uvicorn",
        "python-multipart"
    ]
    
    # Install packages
    for package in packages:
        try:
            print(f"   📦 Installing {package}...")
            subprocess.run([pip_path, "install", package], 
                         check=True, capture_output=True)
            print(f"   ✅ {package} installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error installing {package}: {e}")
            return False
    
    print("   ✅ All packages installed successfully!")
    return True

def create_initial_files():
    """Create initial project files"""
    print("\n📄 Creating initial project files...")
    
    # Create __init__.py files
    init_files = [
        "web_interface/frontend/__init__.py",
        "web_interface/frontend/pages/__init__.py",
        "web_interface/frontend/components/__init__.py",
        "web_interface/frontend/utils/__init__.py",
        "web_interface/backend/__init__.py",
        "web_interface/backend/api/__init__.py",
        "web_interface/backend/optimizers/__init__.py",
        "web_interface/backend/scrapers/__init__.py",
        "web_interface/backend/utils/__init__.py",
        "web_interface/shared/__init__.py",
        "web_interface/shared/models/__init__.py",
        "web_interface/shared/config/__init__.py",
        "web_interface/shared/utils/__init__.py"
    ]
    
    for init_file in init_files:
        Path(init_file).touch()
        print(f"   ✅ Created: {init_file}")
    
    # Create requirements.txt
    requirements_content = """# Web Interface Requirements
streamlit>=1.28.0
pandas>=1.5.0
numpy>=1.21.0
plotly>=5.0.0
requests>=2.28.0
fastapi>=0.100.0
uvicorn>=0.22.0
python-multipart>=0.0.6
"""
    
    with open("web_interface/requirements.txt", "w") as f:
        f.write(requirements_content)
    print("   ✅ Created: web_interface/requirements.txt")
    
    # Create .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Environment variables
.env
.env.local

# Temporary files
temp/
tmp/
"""
    
    with open("web_interface/.gitignore", "w") as f:
        f.write(gitignore_content)
    print("   ✅ Created: web_interface/.gitignore")
    
    print("   ✅ Initial files created successfully!")

def create_basic_streamlit_app():
    """Create the basic Streamlit app"""
    print("\n🚀 Creating basic Streamlit app...")
    
    app_content = '''import streamlit as st
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="2025 Optimizers",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .main {
        background-color: #1a1a2e;
        color: #f1f1f1;
    }
    .stApp {
        background-color: #1a1a2e;
    }
    .css-1d391kg {
        background-color: #16213e;
    }
    .stButton > button {
        background-color: #0f3460;
        color: #f1f1f1;
        border: 1px solid #e94560;
    }
    .stButton > button:hover {
        background-color: #e94560;
        color: #f1f1f1;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("⚾ 2025 Optimizers")
st.markdown("---")

# Sidebar
st.sidebar.title("Sport Selection")
sport = st.sidebar.selectbox(
    "Choose Sport:",
    ["MLB", "NFL", "NBA", "NHL", "PGA", "WNBA", "CFB"]
)

# Main content
st.header(f"{sport} Optimizer")

# File upload
uploaded_file = st.file_uploader(
    "Upload your data file (CSV)",
    type=['csv'],
    help="Upload a CSV file with player data"
)

if uploaded_file is not None:
    # Read the file
    df = pd.read_csv(uploaded_file)
    st.success(f"✅ File uploaded successfully! {len(df)} players loaded.")
    
    # Show preview
    st.subheader("Data Preview")
    st.dataframe(df.head(), use_container_width=True)
    
    # Basic stats
    st.subheader("Quick Stats")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Players", len(df))
    with col2:
        st.metric("Teams", df['Team'].nunique() if 'Team' in df.columns else "N/A")
    with col3:
        st.metric("Positions", df['Position'].nunique() if 'Position' in df.columns else "N/A")

# Run button
if st.button("🚀 Run Optimization", type="primary"):
    st.info("🔄 Optimization in progress...")
    # Placeholder for optimization logic
    st.success("✅ Optimization complete!")
'''
    
    with open("web_interface/frontend/main.py", "w") as f:
        f.write(app_content)
    print("   ✅ Created: web_interface/frontend/main.py")

def create_readme():
    """Create README file"""
    print("\n📖 Creating README file...")
    
    readme_content = """# 🚀 2025 Optimizers Web Interface

A unified web interface for DFS lineup optimization across multiple sports.

## 🎯 Features

- **Multi-Sport Support**: MLB, NFL, NBA, NHL, PGA, WNBA, CFB
- **Dark Mode Interface**: Modern, eye-friendly design
- **Real-time Optimization**: Live optimization with progress tracking
- **File Upload**: Easy CSV file upload and validation
- **Results Export**: Download optimized lineups
- **Free Hosting**: Deployed on Streamlit Cloud

## 🚀 Quick Start

### Local Development

1. **Navigate to the project directory**:
   ```bash
   cd web_interface
   ```

2. **Activate virtual environment**:
   ```bash
   # On Windows:
   venv\\Scripts\\activate
   
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Run the application**:
   ```bash
   streamlit run frontend/main.py
   ```

4. **Open your browser**:
   Navigate to `http://localhost:8501`

### Deployment

This app is deployed on Streamlit Cloud at: [Your App URL]

## 📁 Project Structure

```
web_interface/
├── frontend/                 # Streamlit application
│   ├── pages/               # Multi-page interface
│   ├── components/          # Reusable UI components
│   ├── utils/              # Frontend utilities
│   └── assets/             # CSS, images, etc.
├── backend/                 # FastAPI backend (future)
│   ├── api/                # API endpoints
│   ├── optimizers/         # Optimizer integrations
│   ├── scrapers/           # Data scraping services
│   └── utils/              # Backend utilities
├── shared/                  # Shared code
│   ├── models/             # Data models
│   ├── config/             # Configuration
│   └── utils/              # Shared utilities
└── deployment/              # Deployment configurations
```

## 🎨 Design

### Dark Mode Color Palette
- **Primary Background**: #1a1a2e
- **Secondary Background**: #16213e
- **Accent Blue**: #0f3460
- **Accent Orange**: #e94560
- **Text Primary**: #f1f1f1
- **Text Secondary**: #cccccc

## 🔧 Development

### Adding New Features
1. Create new components in `frontend/components/`
2. Add new pages in `frontend/pages/`
3. Update configuration in `shared/config/`
4. Test locally before deploying

### Code Style
- Use descriptive variable names
- Add comments for complex logic
- Follow PEP 8 guidelines
- Test all new features

## 📊 Progress Tracking

See `WEB_INTERFACE_PROGRESS.md` for detailed progress tracking and development phases.

## 🤝 Contributing

This is a personal project for DFS optimization. All development is tracked in the progress document.

## 📝 License

Personal use only.

---

**Last Updated**: [Current Date]
"""
    
    with open("web_interface/README.md", "w") as f:
        f.write(readme_content)
    print("   ✅ Created: web_interface/README.md")

def verify_setup():
    """Verify the setup was successful"""
    print("\n🔍 Verifying setup...")
    
    # Check if virtual environment exists
    venv_path = Path("web_interface/venv")
    if venv_path.exists():
        print("   ✅ Virtual environment exists")
    else:
        print("   ❌ Virtual environment not found")
        return False
    
    # Check if main.py exists
    main_path = Path("web_interface/frontend/main.py")
    if main_path.exists():
        print("   ✅ Main app file exists")
    else:
        print("   ❌ Main app file not found")
        return False
    
    # Check if requirements.txt exists
    req_path = Path("web_interface/requirements.txt")
    if req_path.exists():
        print("   ✅ Requirements file exists")
    else:
        print("   ❌ Requirements file not found")
        return False
    
    print("   ✅ Setup verification complete!")
    return True

def main():
    """Main setup function"""
    print("🚀 Web Interface Development - Environment Setup")
    print("=" * 60)
    
    # Create project structure
    create_project_structure()
    
    # Create virtual environment
    if not create_virtual_environment():
        print("❌ Failed to create virtual environment")
        return
    
    # Install packages
    if not install_required_packages():
        print("❌ Failed to install required packages")
        return
    
    # Create initial files
    create_initial_files()
    
    # Create basic Streamlit app
    create_basic_streamlit_app()
    
    # Create README
    create_readme()
    
    # Verify setup
    if not verify_setup():
        print("❌ Setup verification failed")
        return
    
    # Success message
    print("\n" + "=" * 60)
    print("🎉 ENVIRONMENT SETUP COMPLETE!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("   1. Navigate to the project directory:")
    print("      cd web_interface")
    print("\n   2. Activate the virtual environment:")
    print("      # On Windows:")
    print("      venv\\Scripts\\activate")
    print("      # On Mac/Linux:")
    print("      source venv/bin/activate")
    print("\n   3. Run the application:")
    print("      streamlit run frontend/main.py")
    print("\n   4. Open your browser to http://localhost:8501")
    print("\n   5. Proceed to Step 1.3: Create Basic Project Structure")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 