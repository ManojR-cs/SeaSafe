"""SeaSafe shore-monitoring dashboard (sample data only)."""

from datetime import datetime

import streamlit as st

from serial_reader import SerialReader
from serial_history import EventHistory
from sample_events import SAMPLE_EVENTS


def format_coordinates(event):
    """Show coordinates only when the packet contains a valid GPS fix."""
    latitude = event["latitude"]
    longitude = event["longitude"]
    if not event["gps_valid"] or latitude is None or longitude is None:
        return "Unavailable — no valid GPS fix"
    return f"{latitude:.4f}, {longitude:.4f}"


def get_event_style(event_type):
    """Return a readable label and color category for an event type."""
    styles = {
        "SOS": ("EMERGENCY · SOS", "emergency"),
        "STATUS": ("VESSEL STATUS", "status"),
        "IMPACT_CANDIDATE": ("POSSIBLE IMPACT", "candidate"),
        "TILT_CANDIDATE": ("POSSIBLE TILT", "candidate"),
    }
    return styles.get(event_type, (event_type.replace("_", " "), "status"))


def render_emergency_alerts(events):
    """Render SOS packets with the details needed for shore triage."""
    st.subheader("Emergency alerts")
    sos_events = [event for event in events if event["event_type"] == "SOS"]

    if not sos_events:
        st.info("No simulated SOS events in the current sample.")
        return

    for event in sos_events:
        label, _ = get_event_style(event["event_type"])
        st.markdown(
            f'<div class="alert-card"><div class="alert-heading">'
            f'<span class="alert-label">{label}</span>'
            f'<span class="event-id">{event["event_id"]}</span></div>'
            f'<div class="alert-vessel">{event["vessel_id"]}</div>'
            f'<div class="alert-message">{event["message"]}</div></div>',
            unsafe_allow_html=True,
        )
        left, middle, right = st.columns(3)
        left.markdown(f"**Timestamp**  \n{event['timestamp']}")
        middle.markdown(f"**Coordinates**  \n{format_coordinates(event)}")
        right.markdown(
            f"**GPS validity**  \n{'Valid fix' if event['gps_valid'] else 'Invalid / unavailable'}"
        )
        delivery, acknowledgement = st.columns(2)
        delivery.markdown(f"**Delivery**  \n{event['delivery_status']}")
        acknowledgement.markdown(f"**Acknowledgement**  \n{event['ack_status']}")
        st.divider()


def render_event_history(events):
    """Display the latest sample packets in a compact table."""
    st.subheader("Event history")
    rows = []
    for event in events:
        label, _ = get_event_style(event["event_type"])
        rows.append(
            {
                "Time (UTC)": event["timestamp"],
                "Vessel": event["vessel_id"],
                "Event ID": event["event_id"],
                "Event": label,
                "Coordinates": format_coordinates(event),
                "Delivery": event["delivery_status"],
                "Ack": event["ack_status"],
            }
        )
    # Use a semantic table instead of Streamlit's canvas-based dataframe grid.
    st.table(rows)
    st.caption(
        "SOS events are simulated examples. Candidate events indicate possible sensor triggers, not confirmed incidents."
    )


def available_serial_ports():
    """Return the ports currently reported by PySerial."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    return sorted(port.device for port in list_ports.comports())


def stop_reader():
    """Stop and forget the current reader when leaving Live mode."""
    reader = st.session_state.get("serial_reader")
    if reader is not None:
        reader.stop()
        st.session_state.serial_reader = None
    st.session_state.connection_state = "Disconnected"


def drain_live_messages():
    """Move reader-thread messages into bounded Streamlit session state."""
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
            event = item["event"]
            st.session_state.valid_message_count += 1
            received_at = datetime.now().astimezone().strftime(
                "%Y-%m-%d %H:%M:%S %Z"
            )
            st.session_state.last_message_time = received_at
            received_event = dict(event)
            received_event["received_at"] = received_at
            st.session_state.live_history.add(received_event)


def format_live_coordinates(event):
    if not event["gps_valid"]:
        return "Unavailable — no valid GPS fix"
    return f"{event['lat']:.5f}, {event['lon']:.5f}"


def render_live_alerts(events):
    st.subheader("Emergency alerts")
    alerts = [
        event
        for event in events
        if event["event_type"] == "SOS" and not event["test_mode"]
    ]
    if not alerts:
        st.info("No operational SOS messages received in this live session.")
        return

    for event in alerts:
        st.markdown(
            f'<div class="alert-card"><div class="alert-heading">'
            f'<span class="alert-label">SOS PACKET · DELIVERY NOT CONFIRMED</span>'
            f'<span class="event-id">{event["event_id"]}</span></div>'
            f'<div class="alert-vessel">{event["node_id"]}</div>'
            f'<div class="alert-message">Received over USB serial; this does not confirm radio reception or emergency delivery.</div></div>',
            unsafe_allow_html=True,
        )
        left, middle, right = st.columns(3)
        device_timestamp = event["timestamp"] or "Unavailable (not provided by device)"
        left.markdown(f"**Device event timestamp**  \n{device_timestamp}")
        middle.markdown(f"**Coordinates**  \n{format_live_coordinates(event)}")
        right.markdown(
            f"**GPS validity**  \n{'Valid fix' if event['gps_valid'] else 'Invalid / unavailable'}"
        )
        st.markdown(
            f"**RSSI:** {event['rssi'] if event['rssi'] is not None else 'Unavailable'}  "
            f"**SNR:** {event['snr'] if event['snr'] is not None else 'Unavailable'}  "
            "**Acknowledgement:** Unavailable"
        )
        st.divider()


def render_live_history(events):
    st.subheader("Live event history")
    if not events:
        st.info("Waiting for valid messages from the selected serial port. No demo events are shown in Live mode.")
        return

    rows = []
    for event in events:
        event_label = event["event_type"]
        if event["test_mode"]:
            event_label = f"HARDWARE TEST DATA · {event_label}"
        rows.append(
            {
                "Device timestamp": event["timestamp"] or "Unavailable",
                "Dashboard received at": event.get("received_at", "Unavailable"),
                "Node": event["node_id"],
                "Event ID": event["event_id"],
                "Event": event_label,
                "GPS": format_live_coordinates(event),
                "RSSI": event["rssi"] if event["rssi"] is not None else "Unavailable",
                "SNR": event["snr"] if event["snr"] is not None else "Unavailable",
                "Hops": event["hop_count"],
            }
        )
    # Keep the same table view without exposing the canvas grid's fallback labels.
    st.table(rows)
    st.caption("USB serial receipt only. This feed does not confirm LoRa reception, acknowledgements, or emergency delivery.")


@st.fragment(run_every="1s")
def render_live_dashboard():
    """Poll the thread queue once per second without blocking serial reads."""
    drain_live_messages()
    state = st.session_state.connection_state
    selected_port = st.session_state.get("selected_port", "None") or "None"
    baud_rate = st.session_state.get("baud_rate", 115200)
    if state == "Connected":
        st.success(f"Serial connection: {selected_port} at {baud_rate} baud · USB only")
    elif state in ("Reconnecting", "Reader error; reconnecting"):
        st.warning(f"Serial connection: {state}. The reader will retry this port.")
    else:
        st.info(f"Serial connection: {state} · Selected port: {selected_port}")

    if st.session_state.connection_detail:
        st.caption(st.session_state.connection_detail)
    st.caption("No live data is substituted with demo events. Current ESP32 event support is reported as STATUS only.")

    summary = st.columns(5)
    live_events = list(st.session_state.live_history.events)
    operational_sos = [
        event for event in live_events
        if event["event_type"] == "SOS" and not event["test_mode"]
    ]
    vessels = {event["node_id"] for event in live_events}
    summary[0].metric("Operational SOS packets", len(operational_sos))
    summary[1].metric("Distinct nodes", len(vessels))
    summary[2].metric("Acknowledgements", "Unavailable")
    summary[3].metric("Valid messages", st.session_state.valid_message_count)
    summary[4].metric("Parse errors", st.session_state.parse_error_count)

    detail_columns = st.columns(2)
    detail_columns[0].markdown(f"**Selected port:** {selected_port} · **Baud:** {baud_rate}")
    detail_columns[1].markdown(
        f"**Last dashboard receive time:** {st.session_state.last_message_time or 'None yet'}"
    )
    if st.session_state.live_history.duplicate_count:
        st.caption(f"Duplicate messages ignored: {st.session_state.live_history.duplicate_count}")
    if st.session_state.last_parse_error:
        st.error(f"Last parse error: {st.session_state.last_parse_error}")
    if st.session_state.queue_warning:
        st.warning(st.session_state.queue_warning)

    st.divider()
    render_live_alerts(live_events)
    render_live_history(live_events)


def main():
    st.set_page_config(page_title="SeaSafe | Shore Console", page_icon="⚓", layout="wide")
    st.markdown(
        """
        <style>
        .stApp { background: #f3f6f8; color: #142b3b; }
        .block-container { max-width: 1280px; padding-top: 1.4rem; padding-bottom: 2rem; }
        .stApp h1, .stApp h2, .stApp h3 { color: #12344a; }
        .stApp [data-testid="stMarkdownContainer"] { color: #142b3b; }
        .topline { display:flex; align-items:center; gap:14px; margin-bottom:0; }
        .brand-mark { background:#0e4057; color:white; border-radius:10px; padding:9px 13px; font-size:22px; }
        .demo-pill { background:#fff0cd; color:#805100; border:1px solid #e4b84c; border-radius:20px; padding:6px 12px; font-weight:800; letter-spacing:.06em; font-size:12px; }
        .subtitle { color:#577080; margin-top:4px; }
        .connection { background:#e4f2ee; color:#126147; border:1px solid #b9ddcf; padding:10px 14px; border-radius:8px; font-weight:600; }
        .alert-card { background:#fff5f2; border:1px solid #e8b5a8; border-left:5px solid #c43d32; border-radius:9px 9px 0 0; padding:14px 16px 10px; margin-top:5px; }
        .alert-heading { display:flex; justify-content:space-between; gap:8px; }
        .alert-label { color:#a52e26; font-weight:800; letter-spacing:.04em; }
        .event-id { color:#60727c; font-size:13px; }
        .alert-vessel { color:#18364a; font-size:20px; font-weight:750; margin-top:7px; }
        .alert-message { color:#6a4a45; margin-top:3px; }
        .stApp [data-testid="stMetric"] { background:#ffffff; color:#142b3b; border:1px solid #dce5e9; border-radius:10px; padding:14px 16px; }
        .stApp [data-testid="stMetricLabel"], .stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricDelta"] { color:#142b3b; }
        .stApp [data-testid="stWidgetLabel"] { color:#334f60; }
        .stApp [data-testid="stRadio"] label { color:#142b3b; }
        .stApp [data-baseweb="select"] > div { background:#ffffff; border-color:#8197a4; }
        .stApp [data-baseweb="select"] span { color:#142b3b; }
        .stApp [data-testid="stTextInput"] input { background:#ffffff; color:#142b3b; border-color:#8197a4; }
        .stApp [data-testid="stButton"] > button { background:#0e4057; color:#ffffff; border-color:#0e4057; }
        .stApp [data-testid="stButton"] > button:hover { background:#17536d; color:#ffffff; border-color:#17536d; }
        .stApp [data-testid="stButton"] > button:focus { outline:3px solid #d59b2d; outline-offset:2px; }
        .stApp [data-testid="stAlert"] { color:#142b3b; }
        .stApp [data-testid="stAlert"] p, .stApp [data-testid="stAlert"] div { color:#142b3b; }
        .stApp [data-testid="stTable"] { display:block; max-width:100%; overflow-x:auto; background:#ffffff; color:#142b3b; }
        .stApp [data-testid="stTable"] table { background:#ffffff; color:#142b3b; }
        .stApp [data-testid="stTable"] th { background:#e8eff3; color:#12344a; }
        .stApp [data-testid="stTable"] td { background:#ffffff; color:#142b3b; }
        </style>
        """,
        unsafe_allow_html=True,
    )

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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    selected_mode = st.radio(
        "Data source", ["Demo Mode", "Live ESP32"], horizontal=True, key="data_source"
    )
    st.markdown(
        '<div class="topline"><span class="brand-mark">⚓</span>'
        '<h1 style="margin:0">SeaSafe</h1>'
        f'<span class="demo-pill">{"DEMO MODE" if selected_mode == "Demo Mode" else "LIVE ESP32"}</span></div>'
        '<div class="subtitle">Shore monitoring console · Local prototype</div>',
        unsafe_allow_html=True,
    )

    if selected_mode == "Demo Mode":
        if st.session_state.serial_reader is not None:
            stop_reader()
        st.markdown(
            '<div class="connection">● Receiver: simulated data · No ESP32 hardware connected</div>',
            unsafe_allow_html=True,
        )
        sos_events = [event for event in SAMPLE_EVENTS if event["event_type"] == "SOS"]
        vessels_heard = {event["vessel_id"] for event in SAMPLE_EVENTS}
        pending_acknowledgements = [
            event for event in SAMPLE_EVENTS if event["ack_status"] == "Pending"
        ]
        metric_columns = st.columns(3)
        metric_columns[0].metric("Active SOS events", len(sos_events), help="Simulated SOS packets in the sample feed")
        metric_columns[1].metric("Distinct vessels heard", len(vessels_heard))
        metric_columns[2].metric("Pending acknowledgements", len(pending_acknowledgements))
        st.divider()
        render_emergency_alerts(SAMPLE_EVENTS)
        render_event_history(SAMPLE_EVENTS)
        return

    available_ports = available_serial_ports()
    if (
        st.session_state.serial_reader is None
        and st.session_state.get("selected_port")
        and st.session_state.selected_port not in available_ports
    ):
        st.session_state.pop("selected_port")
    if not available_ports:
        st.warning("No serial ports detected. Connect the ESP32 and refresh the port list. Live mode will not use demo data.")
    selected_port = st.selectbox(
        "Serial port",
        available_ports,
        index=available_ports.index(st.session_state.selected_port)
        if st.session_state.get("selected_port") in available_ports
        else 0,
        disabled=not available_ports or st.session_state.serial_reader is not None,
        key="selected_port",
    ) if available_ports else None
    st.selectbox(
        "Baud rate",
        [9600, 19200, 38400, 57600, 115200, 230400],
        index=4,
        disabled=st.session_state.serial_reader is not None,
        key="baud_rate",
    )
    control_columns = st.columns(2)
    if st.session_state.serial_reader is None:
        if control_columns[0].button("Connect", disabled=selected_port is None, type="primary"):
            reader = SerialReader(selected_port, st.session_state.baud_rate)
            st.session_state.serial_reader = reader
            st.session_state.connection_state = "Connecting"
            reader.start()
            st.rerun()
    elif control_columns[0].button("Disconnect", type="primary"):
        stop_reader()
        st.rerun()
    if control_columns[1].button("Refresh ports"):
        st.rerun()

    if st.session_state.serial_reader is None:
        st.session_state.selected_port = selected_port or ""
    render_live_dashboard()


if __name__ == "__main__":
    main()
