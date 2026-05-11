"""
Global exception handler for PyQt6 slots.

Key concept — why PyQt6 crashes on unhandled slot exceptions:
  In Python, an unhandled exception in a normal function just prints
  a traceback. But PyQt6 slots are called FROM C++ code (the Qt event
  loop). When a Python exception propagates back into C++, Qt has no
  way to handle it — it calls qFatal() which calls abort().

  The fix has two parts:
  1. sys.excepthook — catches exceptions that escape to the top level
  2. A slot_safe decorator — wraps individual slots in try/except
     and shows a QMessageBox instead of crashing

  Always use @slot_safe on any method connected to a Qt signal.
"""

import sys
import traceback
from functools import wraps
import inspect
#from sqlalchemy import func, inspect


def install_global_exception_hook():
    """
    Replace sys.excepthook so unhandled exceptions show a dialog
    instead of killing the process.
    Call this once in main() before app.exec().
    """
    def _hook(exc_type, exc_value, exc_tb):
        # Don't intercept KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(f"[CBMS] Unhandled exception:\n{tb_str}", file=sys.stderr)

        try:
            from PyQt6.QtWidgets import QMessageBox, QApplication
            if QApplication.instance():
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Unexpected Error")
                msg.setText(str(exc_value))
                msg.setDetailedText(tb_str)
                msg.exec()
        except Exception:
            pass   # if Qt itself is broken, just print

    sys.excepthook = _hook


def slot_safe(func):
    """
    Decorator for PyQt6 slot methods.
    Catches any exception, prints the traceback, and shows a QMessageBox.
    Prevents the crash-on-unhandled-slot-exception behaviour.

    Usage:
        @slot_safe
        def _on_save(self):
            ...  # any exception here shows a dialog instead of crashing
    """
    sig  = inspect.signature(func)
    max_args = 1  # max args to pass to func

    class _SlotSafe:
        def __init__(self, func):
            self.func = func
            wraps(func)(self)

        def __call__(self, *args, **kwargs):
            try:
                return self.func(*args, **kwargs)
            except Exception as e:
                self._show_error(e)
        
        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            from functools import partial
            func = self.func
            def bound(*args, **kwargs):
                import inspect
                sig = inspect.signature(func)
                max_args = len(sig.parameters) - 1  # exclude 'self'
                return self.__call__(obj, *args[:max_args], **kwargs)
            bound.__name__ = self.func.__name__
            return bound
            
        @staticmethod
        def _show_error(e):
            tb_str = traceback.format_exc()
            print(f"[CBMS] Exception in slot:\n{tb_str}", file=sys.stderr)
            try:
                from PyQt6.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Error")
                msg.setText(f"An error occurred: {e}")
                msg.setDetailedText(tb_str)
                msg.exec()
            except Exception:
                pass

    return _SlotSafe(func)
