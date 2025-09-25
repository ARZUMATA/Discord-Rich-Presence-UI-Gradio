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

    # Compute what the current UI input is (in seconds)
    ui_elapsed = hms_to_total_seconds(hours, minutes, seconds)

    # If we already have a running timer, use it unless UI inputs were manually changed
    if last_update_time is not None:
        if enable_auto:
            # Continue auto-updating from last known elapsed
            elapsed_since_update = current_time - last_update_time
            new_elapsed = manual_start_offset + elapsed_since_update
        else:
            # Manual mode: still continue from last elapsed (don't reset!)
            # But: check if user manually changed the HH:MM:SS fields
            current_h, current_m, current_s = total_seconds_to_hms(manual_start_offset)
            # If UI does NOT match current internal elapsed → user changed it
            if not (abs(ui_elapsed - manual_start_offset) < 1):  # Allow 1s tolerance
                new_elapsed = ui_elapsed  # Accept manual override
            else:
                # No change in UI → keep accumulating
                elapsed_since_update = current_time - last_update_time
                new_elapsed = manual_start_offset + elapsed_since_update
    else:
        # First update ever: use UI input
        new_elapsed = ui_elapsed

    # Update internal tracker
    manual_start_offset = new_elapsed
    last_update_time = current_time

    try:
        RPC.update(
            state=state,
            details=details,
            # party_size=[0,0],
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

    return status_msg, display_time

def reset_timer():
    """Reset the timer to 00:00:00"""
    global manual_start_offset, last_update_time
    manual_start_offset = 0
    last_update_time = time.time()  # So next update starts from 0
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

with gr.Blocks(
    title="Discord Rich Presence UI",
    css="""
    .gradio-container {
        max-width: 800px !important;
        margin: 0 auto !important;
        padding: 20px;
    }
    """
) as demo:
    with gr.Row():
        with gr.Column():
            gr.Markdown("# Discord Rich Presence UI")
            gr.Markdown("Set your custom presence with optional auto-updating elapsed time.")

        with gr.Column(scale=1):
            # Avatar with decoration and links
            avatar_html = '''
            <div style="display: flex; justify-content: flex-end; align-items: center; height: 100%;">
                <div style="position: relative; display: inline-block; margin-right: 10px;" title="ARZUMATA">
                    <img src="https://avatars.githubusercontent.com/u/54457203?v=4" 
                            alt="Avatar" 
                            style="border-radius: 50%; width: 64px; height: 64px;">
                    <img src="https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/50a92b90-66fd-44ed-926a-5f936e7078a1/original=true/user%20avatar%20decoration.gif" 
                            alt="Avatar Decoration" 
                            style="position: absolute; top: 0px; scale: 120%">
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <a href="https://github.com/ARZUMATA" target="_blank" style="text-decoration: none; font-size: 18px;">
                        <svg width="32" height="32" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
                        </svg>
                    </a>
                    <a href="https://civitai.com/user/ARZUMATA" target="_blank" style="text-decoration: none;">
                        <img src="https://civitai.com/favicon.ico" alt="Civitai" style="width: 32px; height: 32px;">
                    </a>
                    <a href="https://huggingface.co/ARZUMATA" target="_blank" style="text-decoration: none;">
                        <img src="https://huggingface.co/favicon.ico" alt="Hugging Face" style="width: 32px; height: 32px;">
                    </a>
                </div>
            </div>
            '''
            gr.HTML(avatar_html)

    with gr.Row():
        with gr.Column():
            show_id = gr.Checkbox(label="Show Client ID", value=False)
            client_id = gr.Textbox(
                label="Client ID",
                value=storage.get("client_id", ""),
                type="password",
                placeholder="1234567890"
            )
        with gr.Column():
            connect_btn = gr.Button("Connect")
            disconnect_btn = gr.Button("Disconnect")

    with gr.Row():
        status = gr.Textbox(label="Status", value="Not connected")
        current_elapsed_display = gr.Textbox(
            label="Current Elapsed Time (auto-updated)",
            value="00:00:00",
            interactive=False  # Display-only
        )
        
    show_id.change(
            lambda show: gr.update(type="text" if show else "password"),
            inputs=show_id,
            outputs=client_id
        )

    gr.Markdown("## Presence Status")
    
    with gr.Row():

        # Details
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Details (first row)")
            with gr.Column():

                details = gr.Textbox(
                    label="Enter Details",
                    value=initial_details,
                    placeholder="e.g., On level 10"
                )
            with gr.Column():
                details_dropdown = gr.Dropdown(
                    label="Recent Details (click to load)",
                    choices=details_choices,
                    interactive=True,
                    allow_custom_value=False
                )
                details_dropdown.change(fn=on_details_select, inputs=details_dropdown, outputs=details)
                
        # State: Textbox + Dropdown
        with gr.Row():
            with gr.Column():
                gr.Markdown("### State (second row)")
            with gr.Column():
                state = gr.Textbox(
                    label="Enter State",
                    value=initial_state,
                    placeholder="e.g., Playing a game"
                )
            with gr.Column():
                state_dropdown = gr.Dropdown(
                    label="Recent States (click to load)",
                    choices=state_choices,
                    interactive=True,
                    allow_custom_value=False
                )
                state_dropdown.change(fn=on_state_select, inputs=state_dropdown, outputs=state)

    update_btn = gr.Button("Update Presence")

    gr.Markdown("## Elapsed Time (HH:MM:SS)")
    with gr.Row():
        hours = gr.Number(label="Hours", value=0, precision=0, minimum=0)
        minutes = gr.Number(label="Minutes", value=0, precision=0, minimum=0)
        seconds = gr.Number(label="Seconds", value=5, precision=0, minimum=0)

    reset_btn = gr.Button("Reset Timer to 00:00:00", variant="secondary")

    # Detect if the user edits HH:MM:SS without clicking Update
    def on_time_edit(h, m, s):
        global manual_start_offset, last_update_time
        total = hms_to_total_seconds(h, m, s)
        # Update internal state so next "Update" uses this as base
        manual_start_offset = total
        last_update_time = time.time()
        display = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
        return display  # Update display field

    # Sync whenever time fields change
    # Register event for all three inputs
    gr.on(
        triggers=[hours.change, minutes.change, seconds.change],
        fn=on_time_edit,
        inputs=[hours, minutes, seconds],
        outputs=current_elapsed_display
    )

    gr.Markdown("## Art Assets (must be uploaded to Discord first)")
    with gr.Accordion("Show/Hide Image & Text Settings", open=False):
        with gr.Row():
            with gr.Row():
                with gr.Column():
                    large_image = gr.Textbox(label="Large Image Key", placeholder="e.g., play_icon")
                    large_text = gr.Textbox(label="Large Image Text", placeholder="Hover text for large image")

            with gr.Row():
                with gr.Column():
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
    demo.launch(
    share=False,
    debug=True,
    server_port=7870,
    inbrowser=True,
)