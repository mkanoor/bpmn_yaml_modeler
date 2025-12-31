"""
AG-UI Event Category Filter
Maps AG-UI events to categories and filters based on task preferences
"""
import logging
from typing import Set, Dict, Any

logger = logging.getLogger(__name__)


# AG-UI Event to Category Mapping
EVENT_CATEGORY_MAP = {
    # Messaging Events
    'text.message.start': 'messaging',
    'text.message.content': 'messaging',
    'text.message.end': 'messaging',

    # Tool Events
    'task.tool.start': 'tool',
    'task.tool.end': 'tool',
    'agent.tool_use': 'tool',  # Legacy format

    # State Management Events
    'messages.snapshot': 'state',
    'state.snapshot': 'state',
    'state.delta': 'state',

    # Lifecycle Events
    'workflow.started': 'lifecycle',
    'workflow.completed': 'lifecycle',
    'element.activated': 'lifecycle',
    'element.completed': 'lifecycle',
    'task.progress': 'lifecycle',
    'task.error': 'lifecycle',
    'task.cancelled': 'lifecycle',
    'task.cancellable': 'lifecycle',
    'task.cancelling': 'lifecycle',
    'task.cancel.failed': 'lifecycle',
    'gateway.evaluating': 'lifecycle',
    'gateway.path_taken': 'lifecycle',

    # Special Events
    'task.thinking': 'special',
    'userTask.created': 'special',
    'ping': 'special',
    'pong': 'special',
    'replay.request': 'special',
    'clear.history': 'special',
}


class EventFilter:
    """Filter AG-UI events based on task preferences"""

    def __init__(self):
        self.default_categories = {'messaging', 'tool'}  # Default to showing messaging and tool events

    def should_send_event(self, event_type: str, task_preferences: Dict[str, Any]) -> bool:
        """
        Check if an event should be sent based on task preferences.

        Args:
            event_type: The AG-UI event type (e.g., 'text.message.start')
            task_preferences: Task properties dict containing 'aguiEventCategories'

        Returns:
            True if event should be sent, False otherwise
        """
        # Get event category
        category = EVENT_CATEGORY_MAP.get(event_type)

        if not category:
            # Unknown event type - send it by default (safe default)
            logger.warning(f"Unknown AG-UI event type: {event_type}, sending by default")
            return True

        # Get configured categories from task preferences
        custom_props = task_preferences.get('custom', {})
        configured_categories = custom_props.get('aguiEventCategories', self.default_categories)

        # If not configured or empty, use defaults
        if not configured_categories:
            configured_categories = self.default_categories

        # Check if this event's category is enabled
        should_send = category in configured_categories

        if not should_send:
            logger.debug(f"Filtering out event '{event_type}' (category '{category}' not in {configured_categories})")

        return should_send

    def get_event_category(self, event_type: str) -> str:
        """Get the category for a given event type"""
        return EVENT_CATEGORY_MAP.get(event_type, 'unknown')

    def get_enabled_categories(self, task_preferences: Dict[str, Any]) -> Set[str]:
        """Get the set of enabled event categories for a task"""
        custom_props = task_preferences.get('custom', {})
        configured_categories = custom_props.get('aguiEventCategories', self.default_categories)

        if not configured_categories:
            return self.default_categories

        return set(configured_categories)


# Global event filter instance
event_filter = EventFilter()
