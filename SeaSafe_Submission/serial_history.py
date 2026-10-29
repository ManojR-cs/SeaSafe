from collections import deque
from datetime import datetime, timezone

class EventHistory:
    """In-memory deduplicated event history for a dashboard session."""
    def __init__(self, max_events=5000):
        self.events = deque(maxlen=max_events)
        self.seen = set()

    def add(self, event):
        key = (event.get("node_id"), event.get("event_id"))
        if key in self.seen:
            return False
        self.seen.add(key)
        item = dict(event)
        item.setdefault("dashboard_received_at", datetime.now(timezone.utc).isoformat())
        self.events.append(item)
        # Bound the dedupe set roughly to the history window.
        if len(self.seen) > 2 * len(self.events) + 100:
            self.seen = {(e.get("node_id"), e.get("event_id")) for e in self.events}
        return True

    def all(self):
        return list(self.events)

    def clear(self):
        self.events.clear()
        self.seen.clear()
