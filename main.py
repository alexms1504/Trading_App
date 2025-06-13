#!/usr/bin/env python3
"""
Trading App - Main Entry Point
A low-latency trading application for Interactive Brokers
"""

import sys
from PyQt6.QtWidgets import QApplication

# Import the refactored MainWindow
from src.ui.main_window import MainWindow


def main():
    """Main entry point"""
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Trading Assistant")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()