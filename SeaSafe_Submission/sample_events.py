from datetime import datetime, timezone

SAMPLE_EVENTS = [
    {
        "node_id": "DEMO-VESSEL-01",
        "event_id": "DEMO-001",
        "event_type": "STATUS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latitude": 12.95,
        "longitude": 74.72,
        "gps_valid": True,
        "test_mode": True,
        "message": "Demonstration status only",
    },
    {
        "node_id": "DEMO-VESSEL-02",
        "event_id": "DEMO-002",
        "event_type": "SOS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latitude": 12.97,
        "longitude": 74.70,
        "gps_valid": True,
        "test_mode": True,
        "message": "Simulated SOS — not a real emergency",
    },
]
