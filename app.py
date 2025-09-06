import gradio as gr
from pypresence import Presence
import time

# Global variables
RPC = None
connected = False
last_update_time = None  # Time when presence was last updated
manual_start_offset = 5  # Elapsed seconds at time of update
auto_increment = False   # Whether auto-updating is enabled
auto_update_interval = 300  # Default update interval in seconds

def connect_discord(client_id):
    global RPC, connected
    try:
        RPC = Presence(client_id)
        RPC.connect()
        connected = True
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
    return "Disconnected."

def update_presence_auto(state, details, start, large_image, large_text, small_image, small_text,
                         enable_auto, update_interval):
    global RPC, connected, last_update_time, manual_start_offset, auto_update_interval

    if not connected or RPC is None:
        return "Not connected to Discord. Please connect first.", start

    # On first update or manual override, set the base
    current_time = time.time()
    if enable_auto and last_update_time is not None:
        # Auto mode: increment elapsed time based on real time passed
        elapsed_since_update = current_time - last_update_time
        new_elapsed = manual_start_offset + elapsed_since_update
    else:
        # Manual mode or first update: use user input
        new_elapsed = float(start) if start else 0
        manual_start_offset = new_elapsed
        last_update_time = current_time

    # Update Discord presence
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
        last_update_time = current_time
        auto_update_interval = update_interval
        status_msg = "Presence updated!"
    except Exception as e:
        status_msg = f"Update failed: {e}"

    return status_msg, new_elapsed

# Wrap the function for periodic updates if auto is enabled
def create_auto_updater():
    def auto_update(*args):
        while True:
            yield update_presence_auto(*args)
            time.sleep(args[-1])  # Last arg is update_interval
    return auto_update

auto_update_fn = create_auto_updater()

with gr.Blocks(title="Discord Rich Presence") as demo:
    gr.Markdown("# Discord Rich Presence UI")
    gr.Markdown("Set your custom presence with optional auto-updating elapsed time.")

    with gr.Row():
        client_id = gr.Textbox(label="Client ID", placeholder="1234567890")
        connect_btn = gr.Button("Connect")
        disconnect_btn = gr.Button("Disconnect")

    status = gr.Textbox(label="Status", value="Not connected")
    current_elapsed = gr.Number(label="Current Elapsed Time (auto-updated)", value=0)

    connect_btn.click(fn=connect_discord, inputs=client_id, outputs=status)
    disconnect_btn.click(fn=disconnect, outputs=[status, current_elapsed])

    gr.Markdown("## Presence Details")
    with gr.Row():
        state = gr.Textbox(label="State", value="Doing something fun")
        details = gr.Textbox(label="Details", value="An important detail")

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
    update_interval = gr.Slider(minimum=0.5, maximum=10, value=1, step=0.5,
                                label="Update Interval (seconds)")

    update_btn = gr.Button("Update Presence")

    # Use queue to allow background auto-updates
    demo.load = None  # Reset any auto-load
    update_btn.click(
        fn=update_presence_auto,
        inputs=[state, details, start, large_image, large_text, small_image, small_text,
                enable_auto, update_interval],
        outputs=[status, current_elapsed]
    )

    # Auto-update loop (only runs if enable_auto is True)
    demo.queue()
    demo.launch()