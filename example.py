"""
Example script demonstrating how to use the SmartLockerClient class programmatically.

This example shows how to:
1. Create a SmartLockerClient instance
2. Request a locker
3. Open a locker with a stored code
"""

import asyncio
from smart_locker_ble import SmartLockerClient

async def request_new_locker():
    """Example of requesting a new locker."""
    print("Example: Requesting a new locker")

    # Create client instance
    client = SmartLockerClient()

    # Request a locker
    print("Requesting a locker...")
    success = await client.request_locker()
    if not success:
        print("Failed to request locker")
        await client.disconnect()
        return

    # Wait for notification with the locker code
    print("Waiting for locker assignment...")
    try:
        # Wait for a notification (timeout after 30 seconds)
        await asyncio.sleep(30)
    except asyncio.CancelledError:
        pass

    # Disconnect
    await client.disconnect()

    if client.locker_code:
        print(f"Locker assigned with code: {client.locker_code}")
        print("You can now place your items in the locker.")
    else:
        print("No locker code received. Please try again later.")

async def retrieve_items_with_code(code):
    """Example of retrieving items using a stored code."""
    print(f"Example: Retrieving items with code: {code}")

    # Create client instance
    client = SmartLockerClient()

    # Connect to device
    print("Connecting to SmartLocker device...")
    connected = await client.connect()
    if not connected:
        print("Failed to connect to SmartLocker device")
        return

    # Subscribe to notifications
    print("Subscribing to notifications...")
    subscribed = await client.subscribe_to_notifications()
    if not subscribed:
        print("Failed to subscribe to notifications")
        await client.disconnect()
        return

    # Send the code to the serial communication characteristic
    print(f"Sending code to serial communication...")
    success = await client.send_to_serial(code)
    if success:
        print(f"Locker opened with code: {code}")
        client.clear_locker_code()
        print("Code cleared. Ready for a new locker request.")
    else:
        print("Failed to open locker")

    # Disconnect
    await client.disconnect()

async def main():
    """Main function demonstrating both examples."""
    # Example 1: Request a new locker
    await request_new_locker()

    print("\n" + "-" * 50 + "\n")

    # Example 2: Retrieve items with a stored code
    # Replace "123456" with an actual code you received
    await retrieve_items_with_code("123456")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample terminated by user")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
