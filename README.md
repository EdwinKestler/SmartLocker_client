# SmartLocker BLE Client

A Python application that connects to a SmartLocker BLE device (ESP32), subscribes to notifications, and handles the locker access workflow.

## Overview

This application implements a client for a SmartLocker system that uses Bluetooth Low Energy (BLE) for communication. The application allows users to:

1. Request a locker by sending the command byte `0xA4`
2. Receive a unique code via BLE notifications
3. Store the code for later use
4. Use the stored code to open the same locker when returning

## Application Flow

1. **Automatic Connection:**
   - When the app starts, it automatically scans for and connects to the SmartLocker device
   - It automatically subscribes to notifications from the device

2. **Requesting a Locker:**
   - If no stored code is found, the app prompts the user to press Enter to request a new locker
   - When the user presses Enter, the app explores all available BLE services and characteristics
   - It then sends the command byte `0xA4` to the write characteristic (WRITE_CHAR_UUID)
   - The device assigns a locker and sends a unique code via notification to NOTIFICATION_CHAR_UUID
   - The app stores this code for later use
   - The user can now place items in the assigned locker

3. **Retrieving Items:**
   - When the user returns and opens the app, it automatically connects to the device
   - If a stored code is found, the app shows the code as a button
   - When the user presses the button, it sends the stored code to TX_SERIAL_CHAR_UUID
   - The device opens the same locker
   - After successful retrieval, the code is cleared
   - The app is ready to start a new cycle

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd PythonBLEProject
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   source .venv/bin/activate  # On macOS/Linux
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Command-Line Interface

1. Make sure your SmartLocker device (ESP32) is powered on and in range.

2. Run the command-line application:
   ```
   python smart_locker_ble.py
   ```

3. Follow the on-screen prompts to either request a new locker or retrieve items from an existing locker.

### Graphical User Interface

The application also provides a graphical user interface using Tkinter:

1. Make sure your SmartLocker device (ESP32) is powered on and in range.

2. Run the GUI application:
   ```
   python smart_locker_ui.py
   ```

3. Use the GUI to interact with the SmartLocker device:
   - Click the "Connect" button to connect to the device
   - If no code is stored, the "Request Locker" button will be enabled after connection
   - If a code is stored, the "Retrieve Items" button will be enabled after connection
   - The status area shows the current state of the application
   - The log area shows detailed information about operations
   - The locker code is displayed prominently when assigned

## Configuration

The application is already configured with the correct UUIDs for the SmartLocker device. Here are the UUIDs used in the application:

```python
# UUIDs from the ESP32 SmartLocker device
SERVICE_UUID = "567890AB-1234-1234-3412-341278563412"
READ_CHAR_UUID = "9ABCDEF0-5678-1234-7856-3412ABEFCDAB"
WRITE_CHAR_UUID = "76543210-BA98-FEDC-1032-547698BADCFE"
NOTIFICATION_CHAR_UUID = "DEADDEAD-4444-3333-2222-ADDEADDEADDE"
TX_SERIAL_CHAR_UUID = "44556677-3333-2222-1111-111177665544"
DOOR_CHAR_UUID = "7B8B8715-0627-40A4-8D58-09AD6C7972EB"
AVAILABLE_CHAR_UUID = "D4C3B2A1-F6E5-2211-3344-556699887766"
```

The `DOOR_CHAR_UUID` corresponds to the new `CHAR_DOOR` characteristic for
assigning lockers to specific doors, while `AVAILABLE_CHAR_UUID` exposes the
`AVAILABLE` characteristic that reports the remaining free lockers.

You may also need to adjust the `DEVICE_NAME` constant if your device uses a different name:

```python
DEVICE_NAME = "SmartLocker"
```

Pairing uses a six-digit passkey. Unless you changed it on the device, the
default passkey is `123456`.

## Dependencies

- Python 3.7 or higher
- bleak: For BLE communication
- asyncio: For asynchronous operations (included in Python standard library)
- tkinter: For the graphical user interface (included in Python standard library)

## Notes

- The application stores the last locker information in `locker_code.json` in the same directory as the script. The JSON file contains the assigned code along with the most recent barcode, door number, and available count.
- If the application fails to connect to the device, make sure Bluetooth is enabled on your computer and the device is in range.
- The application waits up to 30 seconds for a notification with the locker code. If no code is received within this time, it disconnects and reports failure.
  - The application uses an exploratory approach to discover and interact with BLE services. When requesting a locker, it first explores all available services and characteristics, and then sends the `0xA4` command to the write characteristic. This approach helps ensure compatibility with different BLE devices and provides useful debugging information.

## Windows Compatibility

This application has been updated to work properly on Windows systems. The following considerations have been made:

- Added timeout parameters to BLE operations to prevent connection issues
- Enhanced error handling to catch Windows-specific exceptions, particularly the `'_bleak_winrt_Windows_Foundation.IAsyncOperation' object has no attribute 'add_done_callback'` error
- Implemented fallback mechanisms for all BLE operations that automatically try alternative approaches when Windows-specific errors occur
- Added small delays between operations to ensure connection stability on Windows
- If you encounter any issues on Windows, make sure you have the latest version of the Bleak library installed:
  ```
  pip install --upgrade bleak
  ```
- Windows users may need to ensure Bluetooth services are running and that the device is properly paired in Windows Bluetooth settings before using the application
- If you continue to experience issues, try running the application with administrator privileges or restarting your Bluetooth service
