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