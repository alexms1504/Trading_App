"""
Simple Logger
A simple logger that doesn't require PyQt6 for testing
"""

import logging
from datetime import datetime


class SimpleLogger:
    """Simple logger for when PyQt6 is not available"""
    
    def __init__(self, name='trading_app'):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def debug(self, message: str, show_status: bool = False):
        self.logger.debug(message)
    
    def info(self, message: str, show_status: bool = False, duration: str = 'normal'):
        self.logger.info(message)
    
    def warning(self, message: str, show_status: bool = True, duration: str = 'normal'):
        self.logger.warning(message)
    
    def error(self, message: str, show_status: bool = True, duration: str = 'long'):
        self.logger.error(message)
    
    def success(self, message: str, show_status: bool = True, duration: str = 'normal'):
        self.logger.info(f"SUCCESS: {message}")


# Create global instance
simple_logger = SimpleLogger()