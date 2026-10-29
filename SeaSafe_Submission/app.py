
"""SeaSafe shore-monitoring dashboard."""

import random
from datetime import datetime

import pandas as pd
import streamlit as st

from serial_reader import SerialReader
from serial_history import EventHistory
from sample_events import SAMPLE_EVENTS


# ---------------------------------------------------------
# Page configuration and styling
# ---------------------------------------------------------

st.set_page_config(
    page_title="SeaSafe | Shore Monitoring",
    page_icon="⚓",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f3f6f8;
        color: #142b3b;
    }
    .block-container {
        max-width: 1400px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .stApp h1, .stApp h2, .stApp h3 {
        color: #12344a;
    }
    .stApp [data-testid="stMarkdownContainer"] {
        color: #142b3b;
    }
    .brand-row {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .brand-mark {
        background: #0e4057;
        color: white;
        padding: 10px 14px;
        border-radius: 10px;
        font-size: 24px;
    }
    .status-pill {
        background: #fff0cd;
        color: #805100;
        border: 1px solid #e4b84c;
        border-radius: 20px;
        padding: 6px 12px;
        font-weight: 800;
        font-size: 12px;
    }
    .alert-card {
        background: #fff5f2;
        border: 1px solid #e8b5a8;
        border-left: 5px solid #c43d32;
        border-radius: 9px;
        padding: 14px 16px;
        margin: 8px 0;
    }
    .alert-title {
        color: #a52e26;
        font-weight: 800;
        letter-spacing: .04em;
    }
    .alert-vessel {
        color: #18364a;
        font-size: 20px;
        font-weight: 750;
        margin-top: 7px;
    }
    .stApp [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #dce5e9;
        border-radius: 10px;
        padding: 14px 16px;
    }
    .stApp [data-testid="stMetricLabel"],
    .stApp [data-testid="stMetricValue"] {
        color: #142b3b;
    }
    .stApp [data-testid="stButton"] > button {
        background: #0e4057;
        color: #ffffff;
        border-color: #0e4057;
    }
    .stApp [data-testid="stButton"] > button:hover {
        background: #17536d;
        color: #ffffff;
    }
    .stApp [data-testid="stTable"] {
        overflow-x: auto;
        background: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------

def current_time():
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def format_sample_coordinates(event):
    latitude = event.get("latitude")
    longitude = event.get("longitude")

    if (
        not event.get("gps_valid", False)
        or latitude is None
        or longitude is None
    ):
        return "Unavailable — no valid GPS fix"

    return f"{latitude:.5f}, {longitude:.5f}"


def format_live_coordinates(event):
    if not event.get("gps_valid", False):
        return "Unavailable — no valid GPS fix"

    latitude = event.get("lat")
    longitude = event.get("lon")

    if latitude is None or longitude is None:
        return "Unavailable — coordinates missing"

    return f"{latitude:.5f}, {longitude:.5f}"


def get_serial_ports():
    try:
        from serial.tools import list_ports
        return sorted(port.device for port in list_ports.comports())
    except ImportError:
        return []


def stop_serial_reader():
    reader = st.session_state.get("serial_reader")

    if reader is not None:
        reader.stop()
        st.session_state.serial_reader = None

    st.session_state.connection_state = "Disconnected"


# ---------------------------------------------------------
# Sample data mode
# ---------------------------------------------------------

def render_sample_alerts(events):
    st.subheader("Emergency alerts")

    sos_events = [
        event for event in events
        if event.get("event_type") == "SOS"
    ]

    if not sos_events:
        st.info("No SOS sample events are configured.")
        return

    for event in sos_events:
        st.markdown(
            f"""
            <div class="alert-card">
                <div class="alert-title">SIMULATED SOS ALERT</div>
                <div class="alert-vessel">
                    {event.get("vessel_id", "Unknown vessel")}
                </div>
                <div>{event.get("message", "Sample distress alert")}</div>
                <div><b>Event ID:</b> {event.get("event_id", "Unavailable")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Timestamp**  \n{event.get('timestamp', 'Unavailable')}")
        c2.markdown(
            f"**Coordinates**  \n{format_sample_coordinates(event)}"
        )
        c3.markdown(
            f"**Delivery**  \n{event.get('delivery_status', 'Not confirmed')}"
        )


def render_sample_history(events):
    st.subheader("Sample event history")

    rows = []
    for event in events:
        rows.append({
            "Timestamp": event.get("timestamp", "Unavailable"),
            "Vessel": event.get("vessel_id", "Unknown"),
            "Event ID": event.get("event_id", "Unavailable"),
            "Event": event.get("event_type", "Unknown"),
            "Coordinates": format_sample_coordinates(event),
            "Delivery": event.get("delivery_status", "Unavailable"),
            "Acknowledgement": event.get("ack_status", "Unavailable"),
            "Source": "SIMULATED",
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_demo_mode():
    st.warning(
        "DEMO MODE — all displayed events are preset examples, "
        "not real vessel transmissions."
    )

    sos_count = sum(
        event.get("event_type") == "SOS"
        for event in SAMPLE_EVENTS
    )
    vessel_count = len({
        event.get("vessel_id")
        for event in SAMPLE_EVENTS
    })

    c1, c2, c3 = st.columns(3)
    c1.metric("Sample SOS events", sos_count)
    c2.metric("Sample vessels", vessel_count)
    c3.metric("Sample events", len(SAMPLE_EVENTS))

    st.divider()
    render_sample_alerts(SAMPLE_EVENTS)
    st.divider()
    render_sample_history(SAMPLE_EVENTS)


# ---------------------------------------------------------
# Live simulation
# ---------------------------------------------------------

def initialize_simulation():
    if "sim_vessels" not in st.session_state:
        st.session_state.sim_vessels = [
            {
                "node": "VESSEL-01",
                "lat": 12.9150,
                "lon": 74.7350,
                "speed": 8.4,
                "battery": 92,
                "status": "NORMAL",
            },
            {
                "node": "VESSEL-02",
                "lat": 12.9500,
                "lon": 74.7550,
                "speed": 6.7,
                "battery": 78,
                "status": "NORMAL",
            },
            {
                "node": "VESSEL-03",
                "lat": 12.8850,
                "lon": 74.7200,
                "speed": 4.2,
                "battery": 64,
                "status": "MONITORING",
            },
            {
                "node": "VESSEL-04",
                "lat": 12.9300,
                "lon": 74.7650,
                "speed": 0.8,
                "battery": 87,
                "status": "SOS DEMO",
            },
        ]


@st.fragment(run_every="2s")
def render_live_simulation():
    """Refresh a separate simulated fleet for presentation."""
    initialize_simulation()
    vessels = st.session_state.sim_vessels

    # Move the simulated vessels within the demonstration area.
    for vessel in vessels:
        vessel["lat"] = round(
            max(12.86, min(12.98, vessel["lat"] + random.uniform(-0.0012, 0.0012))),
            6,
        )
        vessel["lon"] = round(
            max(74.68, min(74.78, vessel["lon"] + random.uniform(-0.0012, 0.0012))),
            6,
        )
        vessel["speed"] = round(
            max(0, min(18, vessel["speed"] + random.uniform(-0.7, 0.7))),
            1,
        )

    now = current_time()

    st.warning(
        "DEMO SIMULATION ACTIVE — no hardware connection is confirmed. "
        "All vessel positions, telemetry and events in this section are simulated."
    )
    st.caption(
        f"Simulation refreshes every 2 seconds · Last update: {now} · "
        "Coordinates are illustrative and are not real GPS reports."
    )

    active_sos = sum(v["status"] == "SOS DEMO" for v in vessels)
    moving = sum(v["speed"] > 1 for v in vessels)
    avg_battery = round(
        sum(v["battery"] for v in vessels) / len(vessels)
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vessels monitored", len(vessels))
    c2.metric("SOS alerts (simulated)", active_sos)
    c3.metric("Vessels moving", moving)
    c4.metric("Average battery", f"{avg_battery}%")

    st.divider()
    st.subheader("Vessel tracking map")
    st.caption("Simulated vessel locations offshore in the Arabian Sea near Mangaluru.")

    map_data = pd.DataFrame([
        {
            "lat": vessel["lat"],
            "lon": vessel["lon"],
            "vessel": vessel["node"],
        }
        for vessel in vessels
    ])

    st.map(map_data, latitude="lat", longitude="lon", size=200)

    st.subheader("Vessel telemetry")

    telemetry = [
        {
            "Vessel ID": vessel["node"],
            "Latitude": vessel["lat"],
            "Longitude": vessel["lon"],
            "Speed (knots)": vessel["speed"],
            "Battery": f'{vessel["battery"]}%',
            "Status": vessel["status"],
            "Data source": "SIMULATED",
        }
        for vessel in vessels
    ]

    st.dataframe(
        telemetry,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Recent simulated events")

    simulated_events = [
        {
            "Time": now,
            "Vessel": "VESSEL-04",
            "Event": "SOS",
            "Details": "Demonstration distress alert",
            "Source": "SIMULATED — NOT A REAL SOS",
        },
        {
            "Time": now,
            "Vessel": "VESSEL-02",
            "Event": "STATUS",
            "Details": "Position and telemetry update",
            "Source": "SIMULATED",
        },
        {
            "Time": now,
            "Vessel": "VESSEL-03",
            "Event": "SENSOR",
            "Details": "Monitoring event",
            "Source": "SIMULATED",
        },
    ]

    st.dataframe(
        simulated_events,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# Actual ESP32 USB serial data
# ---------------------------------------------------------

def drain_serial_messages():
    reader = st.session_state.get("serial_reader")
    if reader is None:
        return

    for item in reader.drain_messages():
        if item["kind"] == "state":
            st.session_state.connection_state = item["state"]
            st.session_state.connection_detail = item.get("text", "")

        elif item["kind"] == "parse_error":
            st.session_state.parse_error_count += 1
            st.session_state.last_parse_error = item["text"]

        elif item["kind"] == "queue_warning":
            st.session_state.queue_warning = item["text"]

        elif item["kind"] == "event":
            event = dict(item["event"])
            event["received_at"] = current_time()
            st.session_state.valid_message_count += 1
            st.session_state.last_message_time = event["received_at"]
            st.session_state.live_history.add(event)


@st.fragment(run_every="1s")
def render_actual_serial_data():
    drain_serial_messages()

    events = list(st.session_state.live_history.events)
    reader = st.session_state.get("serial_reader")
    state = st.session_state.connection_state

    if reader is not None and state == "Connected":
        st.success(
            f"USB serial connected · {st.session_state.get('selected_port', '')}"
        )
    else:
        st.info(
            "USB serial is not connected. The simulated fleet below remains "
            "available for presentation."
        )

    if st.session_state.connection_detail:
        st.caption(st.session_state.connection_detail)

    operational_sos = [
        event for event in events
        if event.get("event_type") == "SOS"
        and not event.get("test_mode", False)
    ]
    node_ids = {
        event.get("node_id")
        for event in events
        if event.get("node_id")
    }

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Real USB SOS packets", len(operational_sos))
    c2.metric("Real USB nodes", len(node_ids))
    c3.metric("Valid serial messages", st.session_state.valid_message_count)
    c4.metric("Parse errors", st.session_state.parse_error_count)

    st.caption(
        "These metrics count actual USB serial messages only. "
        "They do not include simulated vessels or sample SOS alerts."
    )

    if st.session_state.last_message_time:
        st.caption(
            "Last actual USB message received: "
            f"{st.session_state.last_message_time}"
        )

    if st.session_state.last_parse_error:
        st.error(f"Last parse error: {st.session_state.last_parse_error}")

    if st.session_state.queue_warning:
        st.warning(st.session_state.queue_warning)

    st.subheader("Actual USB serial history")

    if not events:
        st.info("No real USB serial messages have been received in this session.")
        return

    rows = []
    for event in events:
        rows.append({
            "Device timestamp": event.get("timestamp") or "Unavailable",
            "Dashboard receive time": event.get("received_at", "Unavailable"),
            "Node": event.get("node_id", "Unknown"),
            "Event ID": event.get("event_id", "Unavailable"),
            "Event": event.get("event_type", "Unknown"),
            "GPS": format_live_coordinates(event),
            "Test data": "Yes" if event.get("test_mode", False) else "No",
            "Source": "USB SERIAL",
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# Main app
# ---------------------------------------------------------

def main():
    defaults = {
        "serial_reader": None,
        "connection_state": "Disconnected",
        "connection_detail": "",
        "live_history": EventHistory(),
        "valid_message_count": 0,
        "parse_error_count": 0,
        "last_message_time": "",
        "last_parse_error": "",
        "queue_warning": "",
        "baud_rate": 115200,
        "selected_port": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    mode = st.radio(
        "Dashboard mode",
        ["Demo Mode", "Live ESP32"],
        horizontal=True,
        key="dashboard_mode",
    )

    st.markdown(
        """
        <div class="brand-row">
            <div class="brand-mark">⚓</div>
            <h1 style="margin:0">SeaSafe</h1>
            <span class="status-pill">SHORE MONITORING CONSOLE</span>
        </div>
        <p>Maritime safety monitoring · LEAP prototype</p>
        """,
        unsafe_allow_html=True,
    )

    if mode == "Demo Mode":
        if st.session_state.serial_reader is not None:
            stop_serial_reader()

        render_demo_mode()
        return

    st.subheader("Live ESP32 monitoring")

    ports = get_serial_ports()

    c1, c2 = st.columns([3, 1])
    with c1:
        selected_port = st.selectbox(
            "USB serial port",
            options=ports if ports else ["No serial ports found"],
            index=(
                ports.index(st.session_state.selected_port)
                if st.session_state.selected_port in ports
                else 0
            ),
            disabled=st.session_state.serial_reader is not None or not ports,
        )

    with c2:
        st.selectbox(
            "Baud rate",
            [9600, 19200, 38400, 57600, 115200, 230400],
            index=4,
            key="baud_rate",
            disabled=st.session_state.serial_reader is not None,
        )

    button1, button2 = st.columns(2)

    if st.session_state.serial_reader is None:
        if button1.button("Connect ESP32", disabled=not ports):
            try:
                reader = SerialReader(
                    selected_port,
                    st.session_state.baud_rate,
                )
                st.session_state.serial_reader = reader
                st.session_state.selected_port = selected_port
                st.session_state.connection_state = "Connecting"
                reader.start()
                st.rerun()
            except Exception as exc:
                st.error(f"Could not start serial reader: {exc}")
    else:
        if button1.button("Disconnect ESP32"):
            stop_serial_reader()
            st.rerun()

    if button2.button("Refresh serial ports"):
        st.rerun()

    if not ports:
        st.caption(
            "No USB serial ports are available to this app process. "
            "If this dashboard is hosted in the cloud, it cannot directly "
            "access the USB port on your laptop."
        )

    st.divider()
    st.subheader("Actual hardware feed")
    render_actual_serial_data()

    st.divider()
    st.subheader("Simulated fleet dashboard")
    render_live_simulation()


if __name__ == "__main__":
    main()
