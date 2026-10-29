import random
from datetime import datetime, timezone

class SerialSimulator:
    """Produces clearly labelled demo events; it does not simulate a radio link."""
    def __init__(self):
        self.counter = 0

    def next_event(self):
        self.counter += 1
        return {
            "node_id": f"DEMO-VESSEL-{random.randint(1, 4):02d}",
            "event_id": f"DEMO-{self.counter:06d}",
            "event_type": random.choice(["STATUS", "STATUS", "IMPACT_CANDIDATE", "TILT_CANDIDATE", "SOS"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": round(12.90 + random.random() * 0.12, 6),
            "longitude": round(74.68 + random.random() * 0.10, 6),
            "gps_valid": True,
            "test_mode": True,
            "message": "Simulated event — not a real vessel or emergency",
        }
