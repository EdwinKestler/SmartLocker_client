# smart_locker_ble.py

import asyncio
import logging
import os
import json
from dataclasses import dataclass
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class BLEConfig:
    service_uuid: str           = "567890AB-1234-1234-3412-341278563412"
    write_char_uuid: str        = "76543210-BA98-FEDC-1032-547698BADCFE"
    locker_code_uuid: str       = "DEADDEAD-4444-3333-2222-ADDEADDEADDE"  # Read+Notify server‐side
    door_char_uuid: str         = "7B8B8715-0627-40A4-8D58-09AD6C7972EB"
    available_char_uuid: str    = "D4C3B2A1-F6E5-2211-3344-556699887766"
    tx_serial_char_uuid: str = "44556677-3333-2222-1111-111177665544"
    device_name: str            = "SmartLocker"

class BLEConnectionError(Exception):
    pass

class SmartLockerClient:
    def __init__(self, config: BLEConfig = BLEConfig()):
        self.config = config
        self.client: BleakClient | None = None
        self.device = None

        # state
        self.locker_code: str | None = None
        self.last_door: str | None = None
        self.available_count: int | None = None

        # callbacks
        self.code_callback: callable | None = None
        self.door_callback: callable | None = None
        self.available_callback: callable | None = None

        # storage
        self.storage_path = os.path.join(os.path.dirname(__file__), "locker_code.json")
        self._load_stored()

    def _load_stored(self):
        try:
            with open(self.storage_path, "r") as f:
                d = json.load(f)
            self.locker_code    = d.get("code")
            self.last_door      = d.get("door")
            self.available_count= d.get("available")
            logger.info(f"Loaded: code={self.locker_code}, door={self.last_door}, av={self.available_count}")
        except:
            logger.info("No stored data")

    def _save_stored(self):
        try:
            with open(self.storage_path, "w") as f:
                json.dump({
                    "code":      self.locker_code,
                    "door":      self.last_door,
                    "available": self.available_count
                }, f)
            logger.info("State persisted")
        except Exception as e:
            logger.error(f"Persist failed: {e}")

    # registration
    def register_code_callback(self, cb):
        self.code_callback = cb
        if cb and self.locker_code is not None:
            cb(self.locker_code)

    def register_door_callback(self, cb):
        self.door_callback = cb
        if cb and self.last_door is not None:
            cb(self.last_door)

    def register_available_callback(self, cb):
        self.available_callback = cb
        if cb and self.available_count is not None:
            cb(self.available_count)

    async def retrieve_items(self, data: bytes) -> bool:
        """
        Send raw bytes to the TX_SERIAL characteristic,
        wait 1 second for the locker to process, then disconnect.
        Returns True on success.
        """
        # Ensure we’re connected
        await self._connect()

        # Write to the TX_SERIAL UUID
        await self._write(self.config.tx_serial_char_uuid, data)

        # Give the server a moment to handle it
        await asyncio.sleep(1)

        # Clean up
        await self._disconnect()
        return True

    # --- BLE plumbing ---
    async def _connect(self, timeout=20):
        # Scan
        for _ in range(3):
            devs = await BleakScanner.discover()
            for d in devs:
                if d.name and self.config.device_name in d.name:
                    self.device = d
                    break
            if self.device:
                break
            await asyncio.sleep(1)
        if not self.device:
            raise BLEConnectionError("Device not found")

        # Connect
        self.client = BleakClient(self.device.address)
        try:
            await asyncio.wait_for(self.client.connect(), timeout=timeout)
            if not self.client.is_connected:
                raise BLEConnectionError("Connect failed")
            logger.info("Connected")
            # Pair if possible (skipped if fails)
            if hasattr(self.client, "pair"):
                try:
                    await asyncio.wait_for(self.client.pair(), timeout=10)
                    logger.info("Paired")
                except:
                    logger.warning("Pair skipped")
        except (asyncio.TimeoutError, BleakError) as e:
            raise BLEConnectionError(f"BLE error: {e}")

    async def _disconnect(self):
        if self.client:
            try:
                await self.client.disconnect()
                logger.info("Disconnected")
            except:
                pass
            finally:
                self.client = None

    async def _write(self, uuid: str, data: bytes, timeout=10):
        if not self.client or not self.client.is_connected:
            raise BLEConnectionError("Not connected")
        await asyncio.wait_for(self.client.write_gatt_char(uuid, data), timeout=timeout)
        logger.info(f"Wrote {data!r} to {uuid}")

    async def request_locker(self) -> str:
        """Main flow: connect, send 0xA4, wait 2s, then read code/door/available."""
        await self._connect()

        #--- 1) Send request ---
        await self._write(self.config.write_char_uuid, b"\xA4")

        #--- 2) Wait 2 seconds for the server to generate its code ---
        await asyncio.sleep(2)

        #--- 3) Read locker code (the READ side of your Read+Notify char) ---
        raw = await asyncio.wait_for(
            self.client.read_gatt_char(self.config.locker_code_uuid),
            timeout=10,
        )
        code = raw.decode(errors="ignore").strip()
        self.locker_code = code
        logger.info(f"Locker code read: {code}")
        if self.code_callback:
            self.code_callback(code)

        #--- 4) Read door ID ---
        raw_d = await asyncio.wait_for(
            self.client.read_gatt_char(self.config.door_char_uuid),
            timeout=10,
        )
        door = raw_d.decode(errors="ignore").strip()
        self.last_door = door
        logger.info(f"Door read: {door}")
        if self.door_callback:
            self.door_callback(door)

        #--- 5) Read available count ---
        raw_a = await asyncio.wait_for(
            self.client.read_gatt_char(self.config.available_char_uuid),
            timeout=10,
        )
        try:
            av = int(raw_a.decode(errors="ignore").strip())
        except:
            av = None
        self.available_count = av
        logger.info(f"Available read: {av}")
        if self.available_callback:
            self.available_callback(av)

        #--- 6) Persist + clean up + return ---
        self._save_stored()
        await self._disconnect()
        return code

# If you want a quick CLI:
if __name__ == "__main__":
    import asyncio
    async def cli():
        c = SmartLockerClient()
        code = await c.request_locker()
        print("Code:", code)
        print("Door:", c.last_door)
        print("Available:", c.available_count)
    asyncio.run(cli())
