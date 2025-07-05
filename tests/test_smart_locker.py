import asyncio
import pytest
from unittest.mock import AsyncMock

from smart_locker_ble import SmartLockerClient, BLEConfig, BLEConnectionError

class FakeClient:
    def __init__(self, config: BLEConfig, code=b"CODE123", door=b"1", avail=b"5"):
        self.config = config
        self.is_connected = True
        self._code = code
        self._door = door
        self._avail = avail
    async def read_gatt_char(self, uuid: str):
        if uuid == self.config.locker_code_uuid:
            return self._code
        if uuid == self.config.door_char_uuid:
            return self._door
        if uuid == self.config.available_char_uuid:
            return self._avail
        return b""
    async def write_gatt_char(self, uuid: str, data: bytes):
        # No-op for tests
        return

def make_client(monkeypatch, fake):
    async def fake_connect(self, timeout=20):
        self.client = fake
    async def fake_disconnect(self):
        pass
    monkeypatch.setattr(SmartLockerClient, "_connect", fake_connect)
    monkeypatch.setattr(SmartLockerClient, "_disconnect", fake_disconnect)
    monkeypatch.setattr(SmartLockerClient, "_save_stored", lambda self: None)

@pytest.mark.asyncio
async def test_request_locker_success(monkeypatch):
    config = BLEConfig()
    fake = FakeClient(config, code=b"TEST", door=b"3", avail=b"8")
    make_client(monkeypatch, fake)

    write_mock = AsyncMock()
    monkeypatch.setattr(SmartLockerClient, "_write", write_mock)

    client = SmartLockerClient(config)
    code = await client.request_locker()

    write_mock.assert_awaited_once_with(config.write_char_uuid, b"\xA4")
    assert code == "TEST"
    assert client.last_door == "3"
    assert client.available_count == 8

@pytest.mark.asyncio
async def test_request_locker_device_not_found(monkeypatch):
    async def fake_connect(self, timeout=20):
        raise BLEConnectionError("Device not found")
    monkeypatch.setattr(SmartLockerClient, "_connect", fake_connect)

    client = SmartLockerClient()
    with pytest.raises(BLEConnectionError):
        await client.request_locker()

@pytest.mark.asyncio
async def test_request_locker_read_timeout(monkeypatch):
    config = BLEConfig()
    fake = FakeClient(config)
    async def timeout_read(uuid):
        raise asyncio.TimeoutError
    fake.read_gatt_char = timeout_read
    make_client(monkeypatch, fake)
    write_mock = AsyncMock()
    monkeypatch.setattr(SmartLockerClient, "_write", write_mock)

    client = SmartLockerClient(config)
    with pytest.raises(asyncio.TimeoutError):
        await client.request_locker()
