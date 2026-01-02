"""
Event Bus Service
=================
A simple Pub/Sub event bus for internal application state synchronization.
Allows components to react to changes (e.g. watchlist updates) across the UI.
"""

import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        """
        Subscribe to an event type.
        Callback should accept a single argument (the event data).
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"New subscriber for {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]):
        """Unsubscribe a callback from an event type"""
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def emit(self, event_type: str, data: Any = None):
        """
        Emit an event.
        All subscribers will be called synchronously.
        """
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")

# Singleton instance
_event_bus = EventBus()

def get_event_bus() -> EventBus:
    return _event_bus
