"""
Trading App Configuration Settings
"""
from typing import List, Tuple
import os

# Application Settings
APP_CONFIG = {
    'name': 'Trading Assistant',
    'version': '1.0.0',
    'version_display': '0.1.0 (MVP)',  # Display version
    'window_title': 'Trading Assistant - MVP',
    'debug': True,  # Set to False in production
    'log_level': 'INFO',
    'theme': 'dark',
    # 'auto_update_prices': False,  # Not implemented
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
    'timeout': 10,
    'connection_timeout': 20
}

# Trading Settings
TRADING_CONFIG = {
    'default_symbol': 'AAPL',
    'default_risk_percent': 0.5,
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

# Price Validation Settings
PRICE_VALIDATION_CONFIG = {
    'min_price': 0.01,
    'max_price': 5000.0,
    'max_decimal_places_high': 2,  # For stocks >= $1
    'max_decimal_places_low': 4,   # For stocks < $1
}

# Screener Settings
SCREENER_CONFIG = {
    'min_volume': 8000000,  # $8M default
    'volume_range': [100000, 1000000000],  # $100K - $1B
    'min_price': 0.40,
    'price_range': [0.01, 10000],
    'min_change_percent': 8.0,
    'change_range': [0, 500],
    'max_float': 100000000,  # 100M
    'update_interval': 5,  # seconds
    'max_results': 50,
    'auto_refresh': True,  # Screener auto-refreshes
    'manual_refresh_hotkey': 'F6',
    'real_price_limit': 20,  # Max symbols to fetch real prices for
    'threaded_price_limit': 25  # Max symbols for threaded price fetching
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
    },
    'default_timeframe': '5m',
    'auto_refresh_intervals': [5000, 10000, 30000, 60000],  # milliseconds
    'max_bars': {
        '1m': 1000,
        '5m': 500,
        '15m': 500,
        '1h': 500,
        '4h': 500,
        '1d': 365
    }
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

# UI Layout Configuration (extracted from hardcoded values)
UI_LAYOUT_CONFIG = {
    'order_assistant_width': 450,
    'market_screener_width': 420,
    'chart_default_width': None,  # Flexible
    'connection_check_interval': 2000,  # milliseconds
    'startup_delay': 500,  # milliseconds
    'min_window_width': 1400,
    'min_window_height': 900
}

# Price Validation Configuration (extracted from hardcoded values)
PRICE_VALIDATION_CONFIG = {
    'min_price': 0.01,
    'max_price': 5000.0,
    'max_spinbox_range': 10000.0,
    'smart_stop_adjustment': {
        'standard': 0.01,
        'penny_stock': 0.0001,
        'threshold': 1.0  # Price threshold for penny stocks
    }
}

# Threading Configuration (consolidated)
THREADING_CONFIG = {
    'max_concurrent_fetches': 3,
    'fetch_timeout': 30000,  # milliseconds
    'retry_attempts': 3,
    'retry_delay': 1000,  # milliseconds
    'thread_pool_size': 3
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

# ===== NEW CONFIGURATION FROM MAIN.PY EXTRACTION =====

# Window and Widget Dimensions
WINDOW_CONFIG = {
    'main_window': {
        'position': (100, 100),
        'size': (1200, 800),
        'min_width': 1400,
        'min_height': 900
    },
    'widget_widths': {
        'order_assistant_max': 450,
        'market_screener_max': 420,
        'connect_button_max': 120,
        'disconnect_button_max': 120,
        'account_selector_min': 150
    },
    'layout': {
        'top_margins': (10, 5, 10, 5),  # left, top, right, bottom
        'section_ratios': (1, 2, 1)  # left, center, right
    }
}

# Timer and Delay Configuration  
TIMER_CONFIG = {
    'startup_dialog_delay': 500,  # ms - Allow UI to render before showing dialog
    'connection_check_interval': 2000,  # ms - IB API rate limit
    'connect_action_delay': 100,  # ms - UI render time
    'account_dialog_delay': 500,  # ms - User experience delay
    'mode_switch_delay': 500,  # ms - Mode switching delay
    'chart_load_delay': 500,  # ms - Prevent IB API concurrent call lockup
    'account_update_interval': 300000,  # ms - 5 minutes to reduce API load
}

# Status Bar Message Durations (milliseconds)
STATUS_MSG_DURATION = {
    'short': 2000,   # 2 seconds
    'normal': 3000,  # 3 seconds  
    'long': 5000     # 5 seconds
}


# Price Validation Configuration
PRICE_LIMITS = {
    'min_price': 0.01,
    'max_price': 5000.0,
    'entry_price_min': 0.0001,
    'entry_price_max': 10000.0,
    'default_bid_offset': 0.01,
    'default_ask_offset': 0.01,
    'stop_loss_factor_buy': 0.98,  # 2% below for BUY
    'stop_loss_factor_sell': 1.02,  # 2% above for SELL
    'default_rr_ratio': 2,  # Risk/Reward ratio
    'penny_stock_threshold': 1.0,
    'stop_adjustment': {
        'standard': 0.01,      # $0.01 for stocks >= $1
        'penny_stock': 0.0001  # $0.0001 for stocks < $1
    }
}

# UI Style Configuration
UI_STYLE = {
    'fonts': {
        'status_size': '14px'
    },
    'colors': {
        'paper_trading': '#2196F3',  # Blue
        'live_trading': '#FF5722',   # Red
        'connected': 'green',
        'disconnected': 'red',
        'disabled': '#999',
        'top_panel_bg': '#f0f0f0',
        'top_panel_border': '#ccc'
    },
    'spacing': {
        'button_padding': '5px 10px'
    },
    'status_indicator': '●',  # Bullet character
    'separator': '|'
}

# Message Templates
UI_MESSAGES = {
    'window_title': 'Trading Assistant - MVP',
    'initial_status': 'Ready to connect...',
    'dialog_titles': {
        'connect': 'Connect to Interactive Brokers',
        'account_select': 'Select Trading Account',
        'account_connected': 'Account Connected'
    },
    'welcome_message': 'Welcome to Trading Assistant!\n\nSelect your trading mode to connect:',
    'trading_mode_info': (
        '📄 Paper Trading (Port 7497) - Safe for testing\n'
        '💰 Live Trading (Port 7496) - Real money\n\n'
        'After connecting, you can choose your account.'
    ),
    'api_config_warning': (
        'IMPORTANT: This order requires confirmation in TWS/Gateway.\n\n'
        'To enable auto-transmission without manual confirmation:\n'
        '1. In TWS: File → Global Configuration → API → Settings\n'
        '2. UNCHECK "Read-Only API"\n' 
        '3. CHECK "Bypass Order Precautions for API Orders"\n\n'
        'Current order will be in "PreSubmitted" or "Inactive" state\n'
        'until you confirm it in TWS.'
    )
}

# Menu Configuration
MENU_CONFIG = {
    'file': {
        'label': '&File',
        'items': {
            'connect': ('&Connect to IB', 'Ctrl+K'),
            'disconnect': ('&Disconnect', 'Ctrl+D'),
            'exit': ('E&xit', 'Ctrl+Q')
        }
    },
    'settings': {
        'label': '&Settings',
        'items': {
            'config': ('&Configuration', 'Ctrl+,')
        }
    },
    'help': {
        'label': '&Help',
        'items': {
            'about': ('&About', 'F1')
        }
    }
}

# Order Status Configuration
ORDER_STATUS = {
    'requires_confirmation': ['PreSubmitted', 'Inactive']
}

# Default Account Values (for testing/display when not connected)
DEFAULT_ACCOUNT_VALUES = {
    'net_liquidation': 100000,
    'buying_power': 100000
}

# ===== PHASE 2 MAGIC NUMBER EXTRACTION =====

# Enhanced Price Limits Configuration
ENHANCED_PRICE_LIMITS = {
    'max_take_profit': 10000.0,
    'limit_price_buffer': 0.001,  # 0.1% for limit orders
}

# Order Assistant UI Configuration
ORDER_ASSISTANT_CONFIG = {
    'widget_sizing': {
        'symbol_max_length': 10,
        'progress_bar_height': 3,
        'entry_price_min_width': 120,
        'limit_price_min_width': 120,
        'stop_price_min_width': 120,
        'take_profit_min_width': 100,
        'button_max_width': 45,
        'adjust_button_max_width': 50,
        'spinbox_max_width': 60,
        'percentage_spinbox_max_width': 80,
        'stop_button_max_height': 28,
        'target_button_max_width': 25,
        'share_label_min_width': 50,
    },
    'layout_spacing': {
        'main_spacing': 10,
        'grid_vertical_spacing': 5,
        'button_group_spacing': 30,
        'small_button_spacing': 20,
        'target_control_spacing': 15,
    },
    'default_values': {
        'account_value': 100000.0,
        'buying_power': 100000.0,
        'active_targets': 2,
        'entry_price': 1.0000,
        'stop_loss': 0.01,
        'take_profit': 2.00,
        'r_multiple': 2.0,
        'stop_loss_percentage': 2.0,
    },
    'spinbox_ranges': {
        'entry_price': (0.0001, 5000.0),
        'limit_price': (0.0001, 5000.0),
        'stop_price': (0.01, 5000.0),
        'take_profit': (0.01, 5000.0),
        'target_price': (0.01, 5000.0),
        'risk_slider': (1, 1000),  # 0.01% to 10%
        'position_size': (1, 999999),
        'r_multiple': (0.1, 10.0),
        'stop_loss_percentage': (0.1, 20.0),
        'target_percentage': (10, 100),
    },
    'decimal_places': {
        'entry_price': 4,
        'limit_price': 4,
        'stop_price': 4,
        'take_profit': 2,
        'target_price': 2,
    },
    'step_sizes': {
        'price_step': 0.01,
    },
    'validation': {
        'min_valid_price': 0.01,
        'risk_distance_warning': 0.5,  # 50% warning threshold
        'target_percentage_total': 100,
    },
    'timers': {
        'immediate_callback': 0,
        'short_delay': 100,
    }
}

# Market Screener Configuration  
MARKET_SCREENER_CONFIG = {
    'layout': {
        'spacing': 5,
        'title_font_size': 12,
    },
    'price_volume_defaults': {
        'min_price_range': (0.01, 1000.0),
        'min_price_default': 0.4,
        'max_price_range': (1.0, 10000.0),
        'max_price_default': 500.0,
        'min_volume_range': (1, 1000),  # millions
        'min_volume_default': 8,  # $8M default
    },
    'timers': {
        'auto_refresh_interval': 5000,  # ms
        'status_reset_delay': 3000,  # ms
    },
    'formatting': {
        'billion_threshold': 1000000000,
        'million_threshold': 1000000,
        'thousand_threshold': 1000,
        'high_gainer_threshold': 15,  # % for green
        'good_gainer_threshold': 10,  # % for yellow
    },
    'table': {
        'symbol_font': 'Arial',
        'symbol_font_size': 10,
    }
}

# Chart Widget Configuration
CHART_WIDGET_CONFIG = {
    'figure': {
        'size': (10, 6),
        'height_ratios': [5, 1],  # price:volume
        'subplot_spacing': 0.02,
        'margins': {
            'hspace': 0.05,
            'top': 0.98,
            'bottom': 0.08,
            'left': 0.05,
            'right': 0.98,
        }
    },
    'performance': {
        'crosshair_throttle': 16.67,  # 60fps
        'downsample_threshold': 1000,
        'downsample_max_points': 800,
    },
    'visual': {
        'grid_linewidth': 0.5,
        'grid_alpha': 0.5,
        'candlestick_linewidth': 1,
        'volume_alpha': 0.7,
        'volume_width': 0.8,
        'title_fontsize': 14,
        'axis_label_fontsize': 7,
        'legend_fontsize': 6,
        'ohlc_fontsize': 8,
    },
    'margins': {
        'price_margin_percent': 0.05,  # 5%
        'price_margin_min': 0.01,  # 1 cent
        'volume_margin_factor': 1.1,  # 10%
        'y_axis_margin': 0.1,  # 10%
        'price_level_margin': 0.08,  # 8%
    },
    'refresh_intervals': {
        'minimum': 2000,  # ms
        '5s': 5000,
        '10s': 10000,
        '30s': 30000,
        '60s': 60000,
    },
    'widget_heights': {
        'controls': 40,
        'separator': 25,
        'status': 25,
        'combo_box': 28,
        'chart_min': 400,
    },
    'timeframe_bars': {
        '1m': 60,
        '3m': 20,
        '5m': 12,
        '15m': 4,
        '30m': 2,
        '1h': 1,
    }
}

# Price Levels Configuration
PRICE_LEVELS_CONFIG = {
    'visual': {
        'drag_throttle': 16.67,  # 60fps
        'default_linewidth': 1.5,
        'default_alpha': 0.8,
        'highlighted_linewidth': 2.5,
    },
    'colors': {
        'entry': '#2196F3',  # blue
        'stop_loss': '#F44336',  # red
        'take_profit': '#4CAF50',  # green
        'limit_price': '#FF9800',  # orange
        'targets': ['#9C27B0', '#E91E63', '#673AB7'],  # purple, pink, deep purple
    },
    'calculations': {
        'y_axis_sensitivity': 0.01,  # 1% of range
        'time_to_ms': 1000,
    }
}

# Data Fetcher Configuration
DATA_FETCHER_CONFIG = {
    'timers': {
        'qt_timer_interval': 10,  # ms
    },
    'limits': {
        'threaded_price_default': 25,
        'real_price_default': 20,
    },
    'delays': {
        'initial_sleep': 0.3,  # seconds
        'additional_sleep': 0.2,  # seconds
        'total_wait_reduction': 0.8,  # instead of 1.0s
    },
    'validation': {
        'invalid_price': 0,
    }
}
