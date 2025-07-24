import streamlit as st
import pandas as pd
import sys
import os
from pathlib import Path

# Add the config directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from config import get_config_manager, SportConfig

# Initialize configuration manager
config_manager = get_config_manager()

# Get configuration
app_config = config_manager.get_app_config()
ui_config = config_manager.get_ui_config()

# Page configuration
st.set_page_config(
    page_title=app_config.get('name', '2025 Optimizers'),
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme using configuration
st.markdown(f"""
<style>
    .main {{
        background-color: {ui_config.background_color};
        color: {ui_config.text_color};
    }}
    .stApp {{
        background-color: {ui_config.background_color};
    }}
    .css-1d391kg {{
        background-color: {ui_config.primary_color};
    }}
    .stButton > button {{
        background-color: {ui_config.primary_color};
        color: {ui_config.text_color};
        border: 1px solid {ui_config.secondary_color};
    }}
    .stButton > button:hover {{
        background-color: {ui_config.secondary_color};
        color: {ui_config.text_color};
    }}
    .stSuccess {{
        color: {ui_config.accent_color};
    }}
    .stError {{
        color: {ui_config.error_color};
    }}
    .stWarning {{
        color: {ui_config.warning_color};
    }}
</style>
""", unsafe_allow_html=True)

# Header
st.title(f"⚾ {app_config.get('name', '2025 Optimizers')}")
st.markdown("---")

# Sidebar
st.sidebar.title("Sport Selection")

# Get enabled sports from configuration
enabled_sports = config_manager.get_enabled_sports()
sport_options = [sport.upper() for sport in enabled_sports]

if not sport_options:
    st.error("No sports are enabled in the configuration!")
    st.stop()

sport = st.sidebar.selectbox(
    "Choose Sport:",
    sport_options
)

# Get sport configuration
sport_key = sport.lower()
sport_config = config_manager.get_sport_config(sport_key)

if not sport_config:
    st.error(f"Configuration not found for sport: {sport}")
    st.stop()

# Main content
st.header(f"{sport_config.display_name} Optimizer")

# Display sport configuration info
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Max Players", sport_config.max_players)
with col2:
    st.metric("Salary Cap", f"${sport_config.salary_cap:,}")
with col3:
    st.metric("Required Columns", len(sport_config.required_columns))

# File upload configuration
file_upload_config = config_manager.get_file_upload_config()

# File upload
uploaded_file = st.file_uploader(
    f"Upload your data file ({', '.join(file_upload_config.allowed_extensions)})",
    type=[ext.replace('.', '') for ext in file_upload_config.allowed_extensions],
    help=f"Upload a data file with player data. Max size: {file_upload_config.max_file_size}MB"
)

if uploaded_file is not None:
    # Validate file size
    file_size = uploaded_file.size / (1024 * 1024)  # Convert to MB
    if file_size > file_upload_config.max_file_size:
        st.error(f"File size ({file_size:.1f}MB) exceeds maximum allowed size ({file_upload_config.max_file_size}MB)")
        st.stop()
    
    try:
        # Read the file based on extension
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'csv':
            df = pd.read_csv(uploaded_file)
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(uploaded_file)
        else:
            st.error(f"Unsupported file type: {file_extension}")
            st.stop()
        
        st.success(f"✅ File uploaded successfully! {len(df)} players loaded.")
        
        # Validate required columns
        missing_columns = [col for col in sport_config.required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            st.info(f"Required columns for {sport_config.display_name}: {', '.join(sport_config.required_columns)}")
            st.stop()
        
        # Show preview
        st.subheader("Data Preview")
        st.dataframe(df.head(file_upload_config.preview_rows), use_container_width=True)
        
        # Basic stats
        st.subheader("Quick Stats")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Players", len(df))
        with col2:
            st.metric("Teams", df['Team'].nunique() if 'Team' in df.columns else "N/A")
        with col3:
            st.metric("Positions", df['Position'].nunique() if 'Position' in df.columns else "N/A")
        
        # Store in session state
        st.session_state.uploaded_file = uploaded_file
        st.session_state.current_sport = sport_key
        st.session_state.dataframe = df
        
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        st.stop()

# Run button
if st.button("🚀 Run Optimization", type="primary"):
    if 'dataframe' not in st.session_state:
        st.error("Please upload a file first!")
        st.stop()
    
    st.info("🔄 Optimization in progress...")
    
    # Get optimizer configuration
    optimizer_config = config_manager.get_optimizer_config()
    
    # Placeholder for optimization logic
    with st.spinner("Running optimization..."):
        # Simulate optimization process
        import time
        time.sleep(2)
        
        # Mock results
        mock_results = {
            'lineup': ['Player 1', 'Player 2', 'Player 3', 'Player 4', 'Player 5'],
            'total_salary': 45000,
            'total_projection': 125.5,
            'optimization_time': 1.2
        }
        
        st.session_state.optimization_results = mock_results
    
    st.success("✅ Optimization complete!")
    
    # Display results
    if st.session_state.optimization_results:
        results = st.session_state.optimization_results
        st.subheader("Optimization Results")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Salary", f"${results['total_salary']:,}")
        with col2:
            st.metric("Total Projection", f"{results['total_projection']:.1f}")
        with col3:
            st.metric("Optimization Time", f"{results['optimization_time']:.1f}s")
        
        st.subheader("Optimal Lineup")
        for i, player in enumerate(results['lineup'], 1):
            st.write(f"{i}. {player}")

# Configuration info in sidebar
with st.sidebar.expander("Configuration Info"):
    config_summary = config_manager.get_config_summary()
    st.write(f"**App Version:** {config_summary['version']}")
    st.write(f"**Debug Mode:** {config_summary['debug_mode']}")
    st.write(f"**Config Loaded:** {config_summary['config_loaded']}")
    st.write(f"**Enabled Sports:** {', '.join(config_summary['enabled_sports'])}") 