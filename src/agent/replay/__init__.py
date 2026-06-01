"""
Replay module for web automation recording playback.

Provides two main components:
1. SeleniumReplayer - Replays recordings using Selenium WebDriver
2. EnhancedRecorder - Records actions with Selenium-friendly metadata

Usage:
    from src.agent.replay import SeleniumReplayer, ReplayConfig
    
    config = ReplayConfig(browser="chrome", headless=False)
    results = SeleniumReplayer.replay_record("records/session.json", config)
"""

from .selenium_replayer import SeleniumReplayer, ReplayConfig, replay_record
from .enhanced_recorder import EnhancedRecorder, EnhancedActionRecord, ElementLocator, convert_to_enhanced_format

__all__ = [
    "SeleniumReplayer",
    "ReplayConfig",
    "replay_record",
    "EnhancedRecorder",
    "EnhancedActionRecord",
    "ElementLocator",
    "convert_to_enhanced_format",
]
