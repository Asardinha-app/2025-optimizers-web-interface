"""
Automation Scripts Package

This package contains automation scripts for the MLB Optimizer:
- auto_update: Automated library updates and compliance checks
- monitor_automation: Monitoring automation processes
- requirements_monitor: Monitor and update requirements
- compliance_generator: Generate compliance reports
- requirements_updater: Update requirements automatically
- customize_schedule: Customize automation schedules
- update_checker: Check for updates and changes
- simple_setup: Simple automation setup
"""

from .auto_update import AutoUpdater
from .requirements_monitor import RequirementsMonitor
from .compliance_generator import ComplianceAnalyzer
from .requirements_updater import RequirementsUpdater
from .customize_schedule import ScheduleCustomizer
from .update_checker import LibraryVersionChecker, CodeAnalyzer, DocumentationMonitor, UpdateManager
from .simple_setup import SimpleAutomationSetup

__all__ = [
    'AutoUpdater',
    'RequirementsMonitor',
    'ComplianceAnalyzer',
    'RequirementsUpdater',
    'ScheduleCustomizer',
    'LibraryVersionChecker',
    'CodeAnalyzer', 
    'DocumentationMonitor',
    'UpdateManager',
    'SimpleAutomationSetup'
]
