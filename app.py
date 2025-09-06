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
    "history_limit": 10
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
    """Add value to history if not already present, trim to limit."""
    if not value:
        return
    items = storage[f"{field}_history"]
    limit = storage["history_limit"]
    if value not in items:
        items.insert(0, value)
    else:
        # Move to top if already exists
        items.remove(value)
        items.insert(0, value)
    storage[f"{field}_history"] = items[:limit]
    save_storage(storage)
    return items[:limit]

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
    return "Disconnected.", [], []


def update_presence_auto(state, details, start, large_image, large_text, small_image, small_text,
                         enable_auto, update_interval, client_id_input):
    global RPC, connected, last_update_time, manual_start_offset

    # Handle reconnection if client ID changes
    if connected and client_id_input != storage.get("client_id", ""):
        disconnect()
    if not connected and client_id_input.strip():
        connect_discord(client_id_input)

    if not connected or RPC is None:
        return "Not connected to Discord. Please check Client ID.", start, [], []

    current_time = time.time()
    # Compute elapsed time
    if enable_auto and last_update_time is not None:
        elapsed_since_update = current_time - last_update_time
        new_elapsed = manual_start_offset + elapsed_since_update
    else:
        new_elapsed = float(start) if start else 0
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
        state_choices = storage["state_history"]
        details_choices = storage["details_history"]
        status_msg = "Presence updated!"
    except Exception as e:
        status_msg = f"Update failed: {e}"
        state_choices = storage["state_history"]
        details_choices = storage["details_history"]

    return status_msg, new_elapsed, state_choices, details_choices

# Load initial choices
state_choices = storage["state_history"]
details_choices = storage["details_history"]

with gr.Blocks(title="Discord Rich Presence") as demo:
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
    current_elapsed = gr.Number(
        label="Current Elapsed Time (auto-updated)",
        value=0,
        interactive=False  # Display-only, user cannot edit
    )

    gr.Markdown("## Presence Status")
    state = gr.Dropdown(
        label="State (type or select)",
        choices=state_choices,
        value="Doing something fun",
        allow_custom_value=True
    )
    details = gr.Dropdown(
        label="Details (type or select)",
        choices=details_choices,
        value="An important detail",
        allow_custom_value=True
    )

    start = gr.Number(label="Initial Elapsed Time (seconds)", value=5)

    gr.Markdown("## Art Assets (must be uploaded to Discord first)")
    with gr.Row():
        large_image = gr.Textbox(label="Large Image Key", placeholder="e.g., play_icon")
        large_text = gr.Textbox(label="Large Image Text", placeholder="Hover text for large image")

    with gr.Row():
        small_image = gr.Textbox(label="Small Image Key", placeholder="e.g., logo")
        small_text = gr.Textbox(label="Small Image Text", placeholder="Hover text for small image")

    gr.Markdown("## Auto-Update Settings")
    enable_auto = gr.Checkbox(label="Enable Auto-Update Elapsed Time", value=False)
    update_interval = gr.Slider(
        minimum=0.5, maximum=10, value=storage.get("update_interval", 300), step=0.5,
        label="Update Interval (seconds)"
    )
    update_interval.change(lambda x: update_storage_field("update_interval", x), inputs=update_interval)

    update_btn = gr.Button("Update Presence")

    # Connect events
    connect_btn.click(fn=connect_discord, inputs=client_id, outputs=status)
    disconnect_btn.click(fn=disconnect, outputs=[status, state, details])

    update_btn.click(
        fn=update_presence_auto,
        inputs=[
            state, details, start, large_image, large_text,
            small_image, small_text, enable_auto, update_interval, client_id
        ],
        outputs=[status, current_elapsed, state, details]
    )

    # Auto-refresh
    demo.queue()
    demo.launch()