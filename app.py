import gradio as gr
from pypresence import Presence
import time
import json
import os

# File for persistent storage
STORAGE_FILE = "storage.json"

# Default settings
DEFAULT_STORAGE = {
    "client_id": "",
    "state_history": [],
    "details_history": [],
    "update_interval": 300,  # Default update interval in seconds
    "history_limit": 10,
    "auto_update_enabled": False
}

# Load or initialize storage
def load_storage():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            try:
                data = json.load(f)
                # Ensure required fields exist
                for key, default in DEFAULT_STORAGE.items():
                    if key not in data:
                        data[key] = default
                return data
            except json.JSONDecodeError:
                pass
    return DEFAULT_STORAGE.copy()

def save_storage(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Initialize
storage = load_storage()
RPC = None
connected = False
last_update_time = None  # Time when presence was last updated
manual_start_offset = 5  # Elapsed seconds at time of update

def update_storage_field(key, value):
    storage[key] = value
    save_storage(storage)


def add_to_history(field: str, value: str):
    """Add value to history if not blank, trim to limit."""
    if not value or not value.strip():
        return []
    key = f"{field}_history"
    items = storage[key]
    limit = storage["history_limit"]
    if value not in items:
        items.insert(0, value)
    else:
        items.remove(value)
        items.insert(0, value)
    storage[key] = items[:limit]
    save_storage(storage)
    return items[:limit]  # Return list for updating dropdown choices


def connect_discord(client_id):
    global RPC, connected
    try:
        RPC = Presence(client_id)
        RPC.connect()
        connected = True
        update_storage_field("client_id", client_id)
        return "Connected to Discord!"
    except Exception as e:
        connected = False
        return f"Failed to connect: {e}"

def disconnect():
    global RPC, connected, last_update_time
    if RPC:
        try:
            RPC.close()
        except:
            pass
    RPC = None
    connected = False
    last_update_time = None
    return "Disconnected.", "00:00:00"


def total_seconds_to_hms(seconds):
    """Convert total seconds to (h, m, s)"""
    seconds = int(max(seconds, 0))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return h, m, s


def hms_to_total_seconds(h, m, s):
    """Convert h, m, s to total seconds"""
    return h * 3600 + m * 60 + s

def update_presence_auto(state, details,
                         hours, minutes, seconds,  # HH MM SS inputs
                         large_image, large_text, small_image, small_text,
                         enable_auto, update_interval, client_id_input):
    global RPC, connected, last_update_time, manual_start_offset

    # Handle reconnection if client ID changes
    if connected and client_id_input != storage.get("client_id", ""):
        disconnect()
    if not connected and client_id_input.strip():
        connect_discord(client_id_input)

    if not connected or RPC is None:
        return "Not connected to Discord. Please check Client ID.", "00:00:00"

    current_time = time.time()
    new_elapsed = 0

    # Preserve current elapsed time or resume auto
    if enable_auto and last_update_time is not None:
        # Continue auto-updating from previous elapsed
        elapsed_since_update = current_time - last_update_time
        new_elapsed = manual_start_offset + elapsed_since_update
    elif last_update_time is not None:
        # Manual update: keep last computed elapsed (don't reset)
        elapsed_since_update = current_time - last_update_time
        new_elapsed = manual_start_offset + elapsed_since_update
    else:
        # First update ever: use user input
        new_elapsed = hms_to_total_seconds(hours, minutes, seconds)

    # Update internal tracker
    manual_start_offset = new_elapsed
    last_update_time = current_time

    try:
        RPC.update(
            state=state,
            details=details,
            start=int(current_time - new_elapsed),
            large_image=large_image or None,
            large_text=large_text or None,
            small_image=small_image or None,
            small_text=small_text or None,
        )
        # Save to history
        add_to_history("state", state)
        add_to_history("details", details)
        status_msg = "Presence updated!"
    except Exception as e:
        status_msg = f"Update failed: {e}"

    # Save auto mode state
    update_storage_field("auto_update_enabled", bool(enable_auto))

    # Format current elapsed time as HH:MM:SS string for display
    h, m, s = total_seconds_to_hms(new_elapsed)
    display_time = f"{h:02d}:{m:02d}:{s:02d}"

    # Return updated elapsed to UI (preserved)
    return status_msg, display_time


def reset_timer():
    """Reset the timer to 00:00:00"""
    return 0, 0, 0, "00:00:00"


def on_state_select(choice):
    return choice  # Only called if choice is valid


def on_details_select(choice):
    return choice


# Load initial choices
state_choices = storage["state_history"]
details_choices = storage["details_history"]

# Default values if empty
initial_state = state_choices[0] if state_choices else "Doing something fun"
initial_details = details_choices[0] if details_choices else "An important detail"

with gr.Blocks(title="Discord Rich Presence UI") as demo:
    gr.Markdown("# Discord Rich Presence UI")
    gr.Markdown("Set your custom presence with optional auto-updating elapsed time.")

    with gr.Row():
        client_id = gr.Textbox(
            label="Client ID",
            value=storage.get("client_id", ""),
            placeholder="1234567890"
        )
        connect_btn = gr.Button("Connect")
        disconnect_btn = gr.Button("Disconnect")

    status = gr.Textbox(label="Status", value="Not connected")
    current_elapsed_display = gr.Textbox(
        label="Current Elapsed Time (auto-updated)",
        value="00:00:00",
        interactive=False  # Display-only
    )

    gr.Markdown("## Presence Status")
    
    # State: Textbox + Dropdown
    gr.Markdown("### State")
    state = gr.Textbox(
        label="Enter State",
        value=initial_state,
        placeholder="e.g., Playing a game"
    )
    state_dropdown = gr.Dropdown(
        label="Recent States (click to load)",
        choices=state_choices,
        interactive=True,
        allow_custom_value=False
    )
    state_dropdown.change(fn=on_state_select, inputs=state_dropdown, outputs=state)

    # Details
    gr.Markdown("### Details")
    details = gr.Textbox(
        label="Enter Details",
        value=initial_details,
        placeholder="e.g., On level 10"
    )
    details_dropdown = gr.Dropdown(
        label="Recent Details (click to load)",
        choices=details_choices,
        interactive=True,
        allow_custom_value=False
    )
    details_dropdown.change(fn=on_details_select, inputs=details_dropdown, outputs=details)

    gr.Markdown("## Elapsed Time (HH:MM:SS)")
    with gr.Row():
        hours = gr.Number(label="Hours", value=0, precision=0, minimum=0)
        minutes = gr.Number(label="Minutes", value=0, precision=0, minimum=0)
        seconds = gr.Number(label="Seconds", value=5, precision=0, minimum=0)

    reset_btn = gr.Button("Reset Timer to 00:00:00", variant="secondary")

    gr.Markdown("## Art Assets (must be uploaded to Discord first)")
    with gr.Row():
        large_image = gr.Textbox(label="Large Image Key", placeholder="e.g., play_icon")
        large_text = gr.Textbox(label="Large Image Text", placeholder="Hover text for large image")

    with gr.Row():
        small_image = gr.Textbox(label="Small Image Key", placeholder="e.g., logo")
        small_text = gr.Textbox(label="Small Image Text", placeholder="Hover text for small image")

    gr.Markdown("## Auto-Update Settings")
    enable_auto = gr.Checkbox(
        label="Enable Auto-Update Elapsed Time",
        value=storage.get("auto_update_enabled", False)
    )
    update_interval = gr.Slider(
        minimum=0.5, maximum=10, value=storage.get("update_interval", 300), step=0.5,
        label="Update Interval (seconds)"
    )
    update_interval.change(lambda x: update_storage_field("update_interval", x), inputs=update_interval)
    enable_auto.change(lambda x: update_storage_field("auto_update_enabled", x), inputs=enable_auto)

    update_btn = gr.Button("Update Presence")

    # Connect events
    connect_btn.click(fn=connect_discord, inputs=client_id, outputs=status)
    disconnect_btn.click(fn=disconnect, outputs=[status, current_elapsed_display])

    # Update presence
    result = update_btn.click(
        fn=update_presence_auto,
        inputs=[
            state, details,
            hours, minutes, seconds,
            large_image, large_text, small_image, small_text,
            enable_auto, update_interval, client_id
        ],
        outputs=[status, current_elapsed_display]
    )

    # After update, refresh dropdown choices (not values!)
    result.then(
        fn=lambda: gr.update(choices=storage["state_history"]),
        inputs=None,
        outputs=state_dropdown
    ).then(
        fn=lambda: gr.update(choices=storage["details_history"]),
        inputs=None,
        outputs=details_dropdown
    ).then(
        # Sync back current elapsed to HH:MM:SS inputs
        fn=lambda display: [
            gr.update(value=int(display.split(':')[0])),
            gr.update(value=int(display.split(':')[1])),
            gr.update(value=int(display.split(':')[2]))
        ],
        inputs=current_elapsed_display,
        outputs=[hours, minutes, seconds]
    )

    # Reset timer to 0
    reset_btn.click(
        fn=reset_timer,
        inputs=None,
        outputs=[hours, minutes, seconds, current_elapsed_display]
    )

    demo.queue()
    demo.launch()