"""
Configuration Manager for DFS Optimizers Web Interface
Handles loading, validation, and management of application configuration.
"""

import yaml
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import streamlit as st


@dataclass
class SportConfig:
    """Configuration for a specific sport"""
    name: str
    display_name: str
    enabled: bool
    required_columns: List[str]
    optional_columns: List[str]
    max_players: int
    salary_cap: int


@dataclass
class UIConfig:
    """UI configuration settings"""
    theme: str
    primary_color: str
    secondary_color: str
    background_color: str
    text_color: str
    accent_color: str
    warning_color: str
    error_color: str
    sidebar_width: int
    main_padding: int
    max_width: int
    show_progress_bars: bool
    show_status_messages: bool
    enable_animations: bool
    auto_refresh_interval: int


@dataclass
class FileUploadConfig:
    """File upload configuration settings"""
    max_file_size: int
    allowed_extensions: List[str]
    auto_detect_encoding: bool
    preview_rows: int
    require_headers: bool
    min_rows: int
    max_rows: int


class ConfigManager:
    """
    Manages application configuration loading, validation, and access.
    Provides a centralized way to access all configuration settings.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file. If None, uses default.
        """
        self.config_path = config_path or "web_interface/config/settings.yaml"
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize session state for configuration
        self._init_session_state()
        
        # Load configuration
        self.load_config()
    
    def _init_session_state(self):
        """Initialize Streamlit session state for configuration"""
        if 'config_loaded' not in st.session_state:
            st.session_state.config_loaded = False
        if 'current_sport' not in st.session_state:
            st.session_state.current_sport = None
        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None
        if 'optimization_results' not in st.session_state:
            st.session_state.optimization_results = None
        if 'error_messages' not in st.session_state:
            st.session_state.error_messages = []
        if 'success_messages' not in st.session_state:
            st.session_state.success_messages = []
    
    def load_config(self) -> bool:
        """
        Load configuration from YAML file.
        
        Returns:
            bool: True if configuration loaded successfully, False otherwise
        """
        try:
            config_file = Path(self.config_path)
            
            if not config_file.exists():
                self.logger.error(f"Configuration file not found: {self.config_path}")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            # Validate configuration
            if self._validate_config():
                self.logger.info("Configuration loaded successfully")
                st.session_state.config_loaded = True
                return True
            else:
                self.logger.error("Configuration validation failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            return False
    
    def _validate_config(self) -> bool:
        """
        Validate the loaded configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        required_sections = ['app', 'ui', 'file_upload', 'sports', 'optimizers']
        
        for section in required_sections:
            if section not in self.config:
                self.logger.error(f"Missing required configuration section: {section}")
                return False
        
        # Validate sports configuration
        for sport_key, sport_config in self.config['sports'].items():
            required_fields = ['name', 'display_name', 'enabled', 'required_columns', 
                             'optional_columns', 'max_players', 'salary_cap']
            
            for field in required_fields:
                if field not in sport_config:
                    self.logger.error(f"Missing required field '{field}' in sport '{sport_key}'")
                    return False
        
        return True
    
    def get_app_config(self) -> Dict[str, Any]:
        """Get application configuration"""
        return self.config.get('app', {})
    
    def get_ui_config(self) -> UIConfig:
        """Get UI configuration"""
        ui_config = self.config.get('ui', {})
        layout = ui_config.get('layout', {})
        components = ui_config.get('components', {})
        
        return UIConfig(
            theme=ui_config.get('theme', 'dark'),
            primary_color=ui_config.get('primary_color', '#0f3460'),
            secondary_color=ui_config.get('secondary_color', '#e94560'),
            background_color=ui_config.get('background_color', '#1a1a2e'),
            text_color=ui_config.get('text_color', '#f1f1f1'),
            accent_color=ui_config.get('accent_color', '#4ade80'),
            warning_color=ui_config.get('warning_color', '#f59e0b'),
            error_color=ui_config.get('error_color', '#ef4444'),
            sidebar_width=layout.get('sidebar_width', 300),
            main_padding=layout.get('main_padding', 20),
            max_width=layout.get('max_width', 1200),
            show_progress_bars=components.get('show_progress_bars', True),
            show_status_messages=components.get('show_status_messages', True),
            enable_animations=components.get('enable_animations', True),
            auto_refresh_interval=components.get('auto_refresh_interval', 30)
        )
    
    def get_file_upload_config(self) -> FileUploadConfig:
        """Get file upload configuration"""
        upload_config = self.config.get('file_upload', {})
        validation = upload_config.get('validation', {})
        
        return FileUploadConfig(
            max_file_size=upload_config.get('max_file_size', 50),
            allowed_extensions=upload_config.get('allowed_extensions', ['.csv', '.xlsx', '.xls']),
            auto_detect_encoding=upload_config.get('auto_detect_encoding', True),
            preview_rows=upload_config.get('preview_rows', 10),
            require_headers=validation.get('require_headers', True),
            min_rows=validation.get('min_rows', 1),
            max_rows=validation.get('max_rows', 10000)
        )
    
    def get_sport_config(self, sport_key: str) -> Optional[SportConfig]:
        """
        Get configuration for a specific sport.
        
        Args:
            sport_key: The sport key (e.g., 'mlb', 'nfl')
            
        Returns:
            SportConfig: Sport configuration or None if not found
        """
        sports_config = self.config.get('sports', {})
        sport_config = sports_config.get(sport_key)
        
        if not sport_config:
            return None
        
        return SportConfig(
            name=sport_config.get('name', sport_key.upper()),
            display_name=sport_config.get('display_name', sport_key.upper()),
            enabled=sport_config.get('enabled', True),
            required_columns=sport_config.get('required_columns', []),
            optional_columns=sport_config.get('optional_columns', []),
            max_players=sport_config.get('max_players', 9),
            salary_cap=sport_config.get('salary_cap', 50000)
        )
    
    def get_enabled_sports(self) -> List[str]:
        """Get list of enabled sports"""
        sports_config = self.config.get('sports', {})
        return [key for key, config in sports_config.items() 
                if config.get('enabled', True)]
    
    def get_optimizer_config(self) -> Dict[str, Any]:
        """Get optimizer configuration"""
        return self.config.get('optimizers', {})
    
    def get_data_processing_config(self) -> Dict[str, Any]:
        """Get data processing configuration"""
        return self.config.get('data_processing', {})
    
    def get_error_handling_config(self) -> Dict[str, Any]:
        """Get error handling configuration"""
        return self.config.get('error_handling', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return self.config.get('performance', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return self.config.get('security', {})
    
    def get_development_config(self) -> Dict[str, Any]:
        """Get development configuration"""
        return self.config.get('development', {})
    
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        app_config = self.get_app_config()
        dev_config = self.get_development_config()
        return app_config.get('debug', False) or dev_config.get('debug_mode', False)
    
    def reload_config(self) -> bool:
        """
        Reload configuration from file.
        
        Returns:
            bool: True if reloaded successfully, False otherwise
        """
        self.logger.info("Reloading configuration...")
        return self.load_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current configuration.
        
        Returns:
            Dict containing configuration summary
        """
        return {
            'app_name': self.get_app_config().get('name', 'Unknown'),
            'version': self.get_app_config().get('version', 'Unknown'),
            'enabled_sports': self.get_enabled_sports(),
            'debug_mode': self.is_debug_mode(),
            'config_loaded': st.session_state.config_loaded
        }


# Global configuration manager instance
config_manager = None


def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance.
    Creates a new instance if one doesn't exist.
    
    Returns:
        ConfigManager: The global configuration manager instance
    """
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager


def reload_config() -> bool:
    """
    Reload the global configuration.
    
    Returns:
        bool: True if reloaded successfully, False otherwise
    """
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager.reload_config() 