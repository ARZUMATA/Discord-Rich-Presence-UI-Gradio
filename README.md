# Discord Rich Presence UI

A desktop application built with Gradio that allows users to set and manage their Discord Rich Presence status through a simple graphical interface.

## Overview

This tool enables you to:
- Connect to Discord using a Client ID
- Set custom `state` and `details` text for your presence
- Display elapsed time that can auto-update continuously
- Use large and small images (via Discord asset keys)
- Save and recall recent inputs for faster reuse
- Persist settings and history between sessions

The application runs locally in a browser window using Gradio's interface, and communicates directly with Discord via the `pypresence` library.

## Features

### Core Presence Controls
- **State & Details**: Text fields to define what appears in your presence (e.g., "Playing a game" and "On level 10").
- **Recent Entries Dropdowns**: Automatically saves and recalls previously used states and details.

### Time Management
- Manual input of elapsed time using hours, minutes, and seconds.
- **Auto-Update Mode**: When enabled, the elapsed time continues to increase without needing repeated updates.
- **Timer Reset**: Option to reset the elapsed time to zero.

### Image Assets
- Support for large and small images (must be pre-uploaded to your Discord application as assets).
- Optional hover text for both images.

### Persistent Storage
All settings and history are saved locally in `storage.json`, including:
- Discord Client ID
- Update interval
- Auto-update preference
- History of recent state and details entries

## Requirements

- Python 3.7 or higher
- `gradio`
- `pypresence`
- `json`, `os`, `time` (standard libraries)

Install dependencies:
```bash
pip install gradio pypresence
```

## Usage

1. Run the script:
   ```bash
   python app.py
   ```

2. Enter your Discord Application Client ID (obtained from the [Discord Developer Portal](https://discord.com/developers/applications)).

3. Click "Connect" to establish a presence session.

4. Fill in the desired presence fields and click "Update Presence".

5. Enable "Auto-Update Elapsed Time" to have the timer run continuously.

6. Close the app when done — it will automatically disconnect from Discord.

## Notes

- This app does not host or transmit any data online beyond what is required to update your own Discord presence.
- Image keys must correspond to assets uploaded to your Discord application.
- The interface is responsive and designed for local use only.