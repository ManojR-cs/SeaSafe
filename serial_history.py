"""Bounded live-event history with node/event-ID deduplication."""

from collections import deque


class EventHistory:
    """Keep recent unique events and remember IDs across history eviction."""

    def __init__(self, max_events=200, max_seen_keys=5000):
        self.events = deque(maxlen=max_events)
        self._seen_keys = set()
        self._seen_order = deque(maxlen=max_seen_keys)
        self.duplicate_count = 0

    def add(self, event):
        """Add an event unless its node ID and event ID were already seen."""
        event_key = (event["node_id"], event["event_id"])
        if event_key in self._seen_keys:
            self.duplicate_count += 1
            return False

        if len(self._seen_order) == self._seen_order.maxlen:
            oldest_key = self._seen_order[0]
            self._seen_keys.discard(oldest_key)
        self._seen_order.append(event_key)
        self._seen_keys.add(event_key)
        self.events.appendleft(event)
        return True
