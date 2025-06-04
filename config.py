"""
Trading App Configuration Settings
"""
from typing import List, Tuple
import os

# Application Settings
APP_CONFIG = {
    'name': 'Trading Assistant',
    'version': '1.0.0',
    'debug': True,  # Set to False in production
    'log_level': 'INFO',
    'theme': 'dark',
    'auto_update_prices': False,  # Disabled by default
    'stale_price_warning_seconds': 30
}

# IB Connection Settings
IB_CONFIG = {
    'host': '127.0.0.1',
    'paper_port': 7497,  # Paper trading port
    'live_port': 7496,   # Live trading port
    'default_mode': 'paper',  # 'paper' or 'live'
    'client_id': 1,
    'account': '',  # Auto-detect
    'readonly': False,
    'timeout': 10
}

# Trading Settings
TRADING_CONFIG = {
    'default_symbol': 'AAPL',
    'default_risk_percent': 0.3,
    'max_risk_percent': 2.0,
    'min_stop_distance': 0.5,  # 0.5% minimum
    'default_entry_buffer': 0.1,  # 0.1% above last
    'entry_buffer_options': [0.1, 0.3, 0.5, 1.0],
    'default_targets': [  # (percentage, R-multiple)
        (0.25, 2),
        (0.25, 4),
        (0.25, 6),
        (0.25, 20)
    ],
    'max_position_percent': 100,  # of buying power
    'enable_margin': True,
    'margin_buffer': 0.25,  # 25% buffer
    'default_agent': 'IBCA',
    'fetch_hotkey': 'F5',  # Hotkey for price fetch
    'show_bid_ask': True,  # Show bid/ask in UI
    'calculate_spread': True  # Calculate and show spread
}

# Price Fetch Settings
PRICE_FETCH_CONFIG = {
    'timeout_seconds': 5,
    'retry_attempts': 3,
    'show_loading_indicator': True,
    'play_sound_on_fetch': False,
    'cache_duration_seconds': 300,  # 5 minutes
    'fetch_historical_for_sl': True,  # Fetch 5-min bars for SL calc
    'fetch_prior_day': True  # Fetch prior day data
}

# Screener Settings
SCREENER_CONFIG = {
    'min_volume': 5000000,  # $5M default
    'volume_range': [100000, 1000000000],  # $100K - $1B
    'min_price': 0.40,
    'price_range': [0.01, 10000],
    'min_change_percent': 8.0,
    'change_range': [0, 500],
    'max_float': 100000000,  # 100M
    'update_interval': 5,  # seconds
    'max_results': 50,
    'auto_refresh': True,  # Screener auto-refreshes
    'manual_refresh_hotkey': 'F6'
}

# Google Integration
GOOGLE_CONFIG = {
    'credentials_file': os.path.join('credentials', 'google_credentials.json'),
    'spreadsheet_id': os.environ.get('GOOGLE_SPREADSHEET_ID', 'your_spreadsheet_id'),
    'worksheet_name': 'Trading Journal',
    'drive_folder_id': os.environ.get('GOOGLE_DRIVE_FOLDER_ID', 'your_folder_id'),
    'scopes': [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
}

# Screenshot Settings
SCREENSHOT_CONFIG = {
    'enabled': True,
    'base_path': os.path.join('data', 'screenshots'),
    'width': 1920,
    'height': 1080,
    'quality': 90,
    'timeframes': ['5min', '1day'],
    'retention_days': 365,
    'upload_to_drive': True,
    'show_r_levels': True,
    'r_levels_to_show': [1, 2, 3, 5, 10, 20]
}

# Chart Settings
CHART_CONFIG = {
    'theme': 'dark',
    'entry_line_color': '#00FF00',
    'stop_line_color': '#FF0000',
    'tp_line_color': '#0080FF',
    'r_level_color': '#FFFF00',
    'indicators': {
        'ema': [5, 10, 21],
        'sma': [50, 100, 200],
        'show_vwap': True,
        'show_volume': True,
        'show_r_grid': True
    }
}

# Trade Styles
TRADE_STYLES = {
    'DAY': 'Day Trade',
    'SWING': 'Swing Trade',
    'EP': 'Extended Play',
    'WRONG': 'Wrong Entry'
}

# UI Settings
UI_CONFIG = {
    'show_tooltips': True,
    'button_size': 'medium',
    'show_confirmations': True,
    'highlight_changes': True,
    'change_highlight_duration': 2000,  # milliseconds
    'number_format': '{:.2f}',
    'percentage_format': '{:.2%}',
    'timestamp_format': '%H:%M:%S',
    'show_keyboard_hints': True
}

# Alert Settings
ALERT_CONFIG = {
    'check_interval': 1,  # seconds
    'max_alerts': 100,
    'sound_enabled': True,
    'popup_enabled': True,
    'expire_hours': 24
}

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(DATA_DIR, 'logs')
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
SCREENSHOTS_DIR = os.path.join(DATA_DIR, 'screenshots')

# Create directories if they don't exist
for directory in [DATA_DIR, LOGS_DIR, CACHE_DIR, SCREENSHOTS_DIR]:
    os.makedirs(directory, exist_ok=True)
