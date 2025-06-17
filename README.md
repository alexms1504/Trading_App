# Trading App

High-Performance Trading Platform for Interactive Brokers

A sophisticated, low-latency (<200ms) trading application designed for a single, advanced user to enhance day-trading performance through a seamless, safety-first workflow. The system integrates real-time data, advanced order management, and automated analysis to streamline the entire trading lifecycle, from discovery to execution.

Live Project Status: 🔴 Not Started - Planning complete. Next action is to begin Phase 0: Critical Safety Fixes & Architecture Simplification.

## Core Functionality (High Level):

**Integrated Trading & Execution:**
1. Smart Order Assistant: Place complex orders (LIMIT, MARKET, STOP LIMIT) with automated, risk-based position sizing.
2. Interactive Chart Trading: Visually set entry, stop-loss, and multiple take-profit targets directly on the chart by dragging price level lines.
3. Advanced Bracket Orders: Automatically calculate and attach multiple profit-taking levels based on R-multiples.

**Interactive Charting & Visual Trading:**
1. Multi-Timeframe Analysis: Visualize market data with candlestick and volume charts across numerous timeframes, from one minute to one day (1m, 5m, 1h, 1d).
2. Key Technical Indicators: Overlay charts with essential indicators like EMA, SMA, and VWAP to inform trading decisions.
3. Trade from the Chart: Visually define your trade by clicking and dragging interactive lines on the chart to precisely set the entry, stop-loss, and take-profit levels for the Order Assistant.
4. High-Performance Tracking: Follow price action with a smooth, 60fps crosshair that displays real-time OHLC data as you move your cursor.

**Market Analysis & Opportunity Flow:**
1. Real-Time Market Screening (Testing Phase with some issues found): Utilize the TWS Scanner API to discover opportunities with customizable filters for price, volume, and volatility.
2. Multi-Symbol Monitoring (Development Not Started Yet): Concurrently track 50+ securities, detecting technical patterns (e.g., EMA crossovers, consolidation) in real-time.
3. Automated Entry Staging (Development Not Started Yet): When a monitored pattern is detected, the system generates an alert and pre-populates the Order Assistant with a staged stop-limit order for one-click review and execution.

**Safety & Risk Management:**
1. Automated Risk Calculations: Position sizes are automatically calculated based on user-defined account risk percentages, preventing costly manual errors.
2. Dynamic Stop-Loss Options: Set stops based on technical levels like prior/current bar lows, day's low, or a fixed percentage.
3. Financial Circuit Breakers: The system is built with multiple validation layers and safety mechanisms (e.g., daily loss limits (TBC), position size limits) to prevent catastrophic losses.


## 📋 Requirements

### General Requirements
- **Low latency**: <200ms for all critical operations
- **Clean architecture**: Well-organized, simple, clean and easy to understand, maintainable code following SOLID principles
- **Robust error handling**: Comprehensive validation and graceful degradation
- **Safety mechanisms**: Multiple validation layers to prevent accidental large losses
- **Comprehensive testing**: Unit tests ensuring reliability and performance

### Technical Stack
- **IB API Integration**: `ib_async` package for Interactive Brokers TWS API
- **Charting**: `matplotlib` for visualization. To be replaced by other package to improve performance
- **UI Framework**: PyQt6 for professional desktop interface
- **Python Environment**: Anaconda environment (ib_trade) with Python 3.11 (path: C:\Users\alanc\anaconda3\envs\ib_trade\python.exe or /mnt/C/Users/alanc/anaconda3/envs/ib_trade/python.exe)


# Project Documentation
This README.md provides a high-level overview. For more detailed information, please refer to the following documents:

claude.md: Contains specific instructions, persona, development standards for developing this project, and Architecture of the project.

MULTI_SYMBOL_MONITORING_PLAN.md: The official blueprint and feature roadmap for the current development epic.

IMPLEMENTATION_TRACKER.md: A detailed, task-level tracker for monitoring progress against the development plan.


## License

Private project - not for distribution