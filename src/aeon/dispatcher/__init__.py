"""
Dispatcher Module: Event Routing and Pubsub System.
Implements decoupled component communication via event propagation.
Architecture: Observer Pattern with Type-Safe Events.
"""

from aeon.dispatcher.event import Event, EventType
from aeon.dispatcher.hub import EventHub

__all__ = ["Event", "EventType", "EventHub"]
