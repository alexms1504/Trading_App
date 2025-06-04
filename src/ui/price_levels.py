"""
Price Level Management for Charts
Interactive price lines for entry, stop loss, and take profit
"""

from typing import Optional, Dict, Any, Tuple
from PyQt6.QtCore import pyqtSignal, QObject
import numpy as np

from src.utils.logger import logger


class PriceLevelManager(QObject):
    """
    Manages interactive price levels on the chart
    Provides draggable lines for entry, stop loss, and take profit
    """
    
    # Signals for price level changes
    entry_changed = pyqtSignal(float)  # Emitted when entry price is dragged
    stop_loss_changed = pyqtSignal(float)  # Emitted when stop loss is dragged
    take_profit_changed = pyqtSignal(float)  # Emitted when take profit is dragged
    drag_completed = pyqtSignal()  # Emitted when drag operation completes
    
    def __init__(self):
        super().__init__()
        
        # Price levels
        self.entry_price = None
        self.stop_loss_price = None
        self.take_profit_price = None
        
        # Line objects (matplotlib)
        self.entry_line = None
        self.stop_loss_line = None
        self.take_profit_line = None
        
        # Drag state
        self.dragging = False
        self.drag_line = None
        self.drag_start_y = None
        
        # Chart reference
        self.chart_ax = None
        self.chart_canvas = None
        
        # Performance optimization for smooth dragging - blitting disabled to prevent chart issues
        self._last_drag_update = 0
        self._drag_throttle_ms = 16.67  # 60fps throttling for good balance
        self._background = None
        self._use_blitting = False
        
    def set_chart_references(self, ax, canvas):
        """Set references to the chart axis and canvas"""
        # Clear any existing lines when setting new references
        self.entry_line = None
        self.stop_loss_line = None
        self.take_profit_line = None
        
        self.chart_ax = ax
        self.chart_canvas = canvas
        
    def update_price_levels(self, entry: Optional[float] = None, 
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None):
        """
        Update price level values and redraw lines
        
        Args:
            entry: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        try:
            if not self.chart_ax:
                return
                
            # Update values
            if entry is not None:
                self.entry_price = entry
            if stop_loss is not None:
                self.stop_loss_price = stop_loss
            if take_profit is not None:
                self.take_profit_price = take_profit
                
            # Redraw lines
            self._draw_price_lines()
            
        except Exception as e:
            logger.error(f"Error updating price levels: {e}")
            
    def _draw_price_lines(self):
        """Draw or update horizontal price lines on the chart"""
        try:
            if not self.chart_ax or not self.chart_canvas:
                return
                
            # Remove existing lines safely
            if self.entry_line:
                try:
                    self.entry_line.remove()
                except:
                    pass  # Line might already be removed
                self.entry_line = None
            if self.stop_loss_line:
                try:
                    self.stop_loss_line.remove()
                except:
                    pass  # Line might already be removed
                self.stop_loss_line = None
            if self.take_profit_line:
                try:
                    self.take_profit_line.remove()
                except:
                    pass  # Line might already be removed
                self.take_profit_line = None
                
            # Get x-axis limits
            xlim = self.chart_ax.get_xlim()
            
            # Draw entry line (blue)
            if self.entry_price:
                self.entry_line = self.chart_ax.axhline(
                    y=self.entry_price,
                    color='#2196F3',  # Blue
                    linestyle='-',
                    linewidth=1.5,
                    alpha=0.8,
                    label=f'Entry: ${self.entry_price:.2f}'
                )
                
            # Draw stop loss line (red)
            if self.stop_loss_price:
                self.stop_loss_line = self.chart_ax.axhline(
                    y=self.stop_loss_price,
                    color='#F44336',  # Red
                    linestyle='--',
                    linewidth=1.5,
                    alpha=0.8,
                    label=f'Stop Loss: ${self.stop_loss_price:.2f}'
                )
                
            # Draw take profit line (green)
            if self.take_profit_price:
                self.take_profit_line = self.chart_ax.axhline(
                    y=self.take_profit_price,
                    color='#4CAF50',  # Green
                    linestyle='-.',
                    linewidth=1.5,
                    alpha=0.8,
                    label=f'Take Profit: ${self.take_profit_price:.2f}'
                )
                
            # Save background for blitting optimization
            if self._use_blitting and hasattr(self.chart_canvas, 'copy_from_bbox'):
                self._background = self.chart_canvas.copy_from_bbox(self.chart_ax.figure.bbox)
            
            # Redraw canvas
            self.chart_canvas.draw_idle()
            
        except Exception as e:
            logger.error(f"Error drawing price lines: {e}")
            
    def _draw_price_lines_optimized(self):
        """Optimized price line drawing for smooth 120fps dragging"""
        try:
            if not self.chart_ax or not self.chart_canvas:
                return
                
            # Use blitting for ultra-fast updates during dragging
            if self._use_blitting and self._background and hasattr(self.chart_canvas, 'restore_region'):
                # Restore background
                self.chart_canvas.restore_region(self._background)
                
                # Remove existing lines
                if self.entry_line:
                    try:
                        self.entry_line.remove()
                    except:
                        pass
                if self.stop_loss_line:
                    try:
                        self.stop_loss_line.remove()
                    except:
                        pass
                if self.take_profit_line:
                    try:
                        self.take_profit_line.remove()
                    except:
                        pass
                
                # Redraw price lines
                if self.entry_price:
                    self.entry_line = self.chart_ax.axhline(
                        y=self.entry_price,
                        color='#2196F3',
                        linestyle='-',
                        linewidth=1.5,
                        alpha=0.8
                    )
                    self.chart_ax.draw_artist(self.entry_line)
                    
                if self.stop_loss_price:
                    self.stop_loss_line = self.chart_ax.axhline(
                        y=self.stop_loss_price,
                        color='#F44336',
                        linestyle='--',
                        linewidth=1.5,
                        alpha=0.8
                    )
                    self.chart_ax.draw_artist(self.stop_loss_line)
                    
                if self.take_profit_price:
                    self.take_profit_line = self.chart_ax.axhline(
                        y=self.take_profit_price,
                        color='#4CAF50',
                        linestyle='-.',
                        linewidth=1.5,
                        alpha=0.8
                    )
                    self.chart_ax.draw_artist(self.take_profit_line)
                
                # Blit only the changed areas
                self.chart_canvas.blit(self.chart_ax.figure.bbox)
            else:
                # Fallback to normal drawing
                self._draw_price_lines()
                
        except Exception as e:
            logger.error(f"Error in optimized price line drawing: {e}")
            # Fallback to normal drawing
            self._draw_price_lines()
            
    def clear_price_levels(self):
        """Clear all price levels from the chart"""
        try:
            # Remove lines safely
            if self.entry_line:
                try:
                    self.entry_line.remove()
                except:
                    pass
                self.entry_line = None
            if self.stop_loss_line:
                try:
                    self.stop_loss_line.remove()
                except:
                    pass
                self.stop_loss_line = None
            if self.take_profit_line:
                try:
                    self.take_profit_line.remove()
                except:
                    pass
                self.take_profit_line = None
                
            # Clear values
            self.entry_price = None
            self.stop_loss_price = None
            self.take_profit_price = None
            
            # Redraw
            if self.chart_canvas:
                self.chart_canvas.draw_idle()
                
        except Exception as e:
            logger.error(f"Error clearing price levels: {e}")
            
    def connect_drag_events(self):
        """Connect mouse events for dragging price lines"""
        if not self.chart_canvas:
            return
            
        # Connect mouse events
        self.chart_canvas.mpl_connect('button_press_event', self._on_press)
        self.chart_canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.chart_canvas.mpl_connect('button_release_event', self._on_release)
        
    def _on_press(self, event):
        """Handle mouse press events"""
        if event.inaxes != self.chart_ax:
            return
            
        # Check if click is near a price line
        tolerance = self._get_click_tolerance()
        
        if self.entry_line and abs(event.ydata - self.entry_price) < tolerance:
            self.dragging = True
            self.drag_line = 'entry'
            self.drag_start_y = event.ydata
        elif self.stop_loss_line and abs(event.ydata - self.stop_loss_price) < tolerance:
            self.dragging = True
            self.drag_line = 'stop_loss'
            self.drag_start_y = event.ydata
        elif self.take_profit_line and abs(event.ydata - self.take_profit_price) < tolerance:
            self.dragging = True
            self.drag_line = 'take_profit'
            self.drag_start_y = event.ydata
            
    def _on_motion(self, event):
        """Handle mouse motion events with 120fps throttling"""
        if not self.dragging or event.inaxes != self.chart_ax:
            return
            
        # Throttle drag updates to 120fps for smooth performance
        import time
        current_time = time.time() * 1000  # milliseconds
        if current_time - self._last_drag_update < self._drag_throttle_ms:
            return
        self._last_drag_update = current_time
            
        # Update the appropriate price based on drag
        if self.drag_line == 'entry':
            self.entry_price = event.ydata
            self.entry_changed.emit(self.entry_price)
        elif self.drag_line == 'stop_loss':
            self.stop_loss_price = event.ydata
            self.stop_loss_changed.emit(self.stop_loss_price)
        elif self.drag_line == 'take_profit':
            self.take_profit_price = event.ydata
            self.take_profit_changed.emit(self.take_profit_price)
            
        # Note: Rescaling will be handled after drag completion to prevent feedback loops
            
        # Redraw lines with optimized blitting
        self._draw_price_lines_optimized()
        
    def _on_release(self, event):
        """Handle mouse release events"""
        was_dragging = self.dragging
        self.dragging = False
        self.drag_line = None
        self.drag_start_y = None
        
        # Emit signal when drag operation completes to trigger potential rescaling
        if was_dragging:
            self.drag_completed.emit()
            logger.debug("Drag operation completed, signaling for potential rescale check")
        
    def _get_click_tolerance(self):
        """Get click tolerance based on y-axis range"""
        if not self.chart_ax:
            return 1.0
            
        ylim = self.chart_ax.get_ylim()
        y_range = ylim[1] - ylim[0]
        return y_range * 0.01  # 1% of y-axis range
        
    def get_risk_reward_ratio(self) -> Optional[float]:
        """Calculate risk/reward ratio from current levels"""
        if not all([self.entry_price, self.stop_loss_price, self.take_profit_price]):
            return None
            
        risk = abs(self.entry_price - self.stop_loss_price)
        reward = abs(self.take_profit_price - self.entry_price)
        
        if risk > 0:
            return reward / risk
        return None
        
    def highlight_active_line(self, line_type: str):
        """Highlight a specific price line (for hover effects)"""
        try:
            # Reset all lines to normal
            if self.entry_line:
                self.entry_line.set_linewidth(1.5)
            if self.stop_loss_line:
                self.stop_loss_line.set_linewidth(1.5)
            if self.take_profit_line:
                self.take_profit_line.set_linewidth(1.5)
                
            # Highlight the specified line
            if line_type == 'entry' and self.entry_line:
                self.entry_line.set_linewidth(2.5)
            elif line_type == 'stop_loss' and self.stop_loss_line:
                self.stop_loss_line.set_linewidth(2.5)
            elif line_type == 'take_profit' and self.take_profit_line:
                self.take_profit_line.set_linewidth(2.5)
                
            # Redraw
            if self.chart_canvas:
                self.chart_canvas.draw_idle()
                
        except Exception as e:
            logger.error(f"Error highlighting line: {e}")
