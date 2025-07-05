import os
import sys
sys.path.append(os.path.dirname(__file__))

import asyncio
import threading
import tkinter as tk
from tkinter import messagebox

from smart_locker_ble import SmartLockerClient, BLEConnectionError


class SmartLockerUI:
    def __init__(self):
        # Main window
        self.root = tk.Tk()
        self.root.title("Smart Locker Controller")

        # Entry for manual code send
        tk.Label(self.root, text="Enter code:").pack(pady=(10, 0))
        self.code_entry_var = tk.StringVar()
        self.code_entry = tk.Entry(self.root, textvariable=self.code_entry_var)
        self.code_entry.pack(pady=(0, 10))

        # Buttons frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        # Send Code button
        self.send_btn = tk.Button(btn_frame, text="Send Code", command=self.send_code)
        self.send_btn.pack(side=tk.LEFT, padx=5)

        # Request Locker button
        self.request_btn = tk.Button(btn_frame, text="Request Locker", command=self.request_locker)
        self.request_btn.pack(side=tk.LEFT, padx=5)

        # Status and info labels
        self.status_label    = tk.Label(self.root, text="Status: Ready")
        self.status_label.pack(pady=(10, 0))
        self.available_label = tk.Label(self.root, text="Available: N/A")
        self.available_label.pack()
        self.info_label      = tk.Label(self.root, text="Info: N/A")
        self.info_label.pack(pady=(0, 10))

        # --- Door grid (1-16) ---
        self.door_labels: dict[int, tk.Label] = {}
        door_frame = tk.Frame(self.root)
        door_frame.pack(pady=(0, 10))
        for row in range(8):
            left_num = row + 1
            right_num = row + 9
            left_lbl = tk.Label(
                door_frame,
                text=str(left_num),
                width=4,
                height=2,
                relief="ridge",
                borderwidth=2,
                bg="green",
                fg="white",
            )
            left_lbl.grid(row=row, column=0, padx=2, pady=2)
            self.door_labels[left_num] = left_lbl

            right_lbl = tk.Label(
                door_frame,
                text=str(right_num),
                width=4,
                height=2,
                relief="ridge",
                borderwidth=2,
                bg="green",
                fg="white",
            )
            right_lbl.grid(row=row, column=1, padx=2, pady=2)
            self.door_labels[right_num] = right_lbl

        # Close button
        self.close_btn = tk.Button(self.root, text="Close", command=self.on_close)
        self.close_btn.pack(pady=(0, 10))

        # Asyncio loop + BLE client
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_loop, daemon=True).start()
        self.ble_client = SmartLockerClient()
        # Callbacks for door & available updates
        self.ble_client.register_door_callback(lambda d: self.root.after(0, self._on_door_event, d))
        self.ble_client.register_available_callback(lambda a: self.root.after(0, self._update_available, a))

        # Clean shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def disable_buttons(self):
        self.send_btn.config(state=tk.DISABLED)
        self.request_btn.config(state=tk.DISABLED)
        self.close_btn.config(state=tk.DISABLED)

    def enable_buttons(self):
        self.send_btn.config(state=tk.NORMAL)
        self.request_btn.config(state=tk.NORMAL)
        self.close_btn.config(state=tk.NORMAL)

    def _update_status(self, text: str):
        self.status_label.config(text=f"Status: {text}")

    def _update_available(self, count):
        txt = "N/A" if count is None else str(count)
        self.available_label.config(text=f"Available: {txt}")

    def _update_info(self):
        # show door if present, else show last locker code
        info = self.ble_client.last_door or self.ble_client.locker_code or "N/A"
        self.info_label.config(text=f"Info: {info}")

    def _set_door_state(self, door: str | int, used: bool):
        try:
            num = int(door)
        except (TypeError, ValueError):
            return
        lbl = self.door_labels.get(num)
        if lbl:
            lbl.config(bg="red" if used else "green")

    def _on_door_event(self, door):
        self._update_info()
        self._set_door_state(door, True)

    #
    # --- Send Code flow ---
    #
    def send_code(self):
        code = self.code_entry_var.get().strip()
        if not code:
            messagebox.showwarning("Input needed", "Please enter a code to send")
            return
        self.disable_buttons()
        self._update_status("Sending code…")
        fut = asyncio.run_coroutine_threadsafe(self._send_code_coro(code), self.loop)
        fut.add_done_callback(lambda f: self.root.after(0, self._on_send_done, f))

    async def _send_code_coro(self, code: str) -> bool:
        try:
            # Wrap with space + CRLF
            framed = f" {code}\r\n".encode("utf-8")
            await self.ble_client.retrieve_items(framed)
            return True
        except BLEConnectionError as e:
            return False

    def _on_send_done(self, fut):
        success = fut.result()
        if success:
            messagebox.showinfo("Sent", f"Code '{self.code_entry_var.get()}' sent")
            self._update_status("Code sent")
            if self.ble_client.last_door:
                self._set_door_state(self.ble_client.last_door, False)
        else:
            messagebox.showerror("Failed", "Failed to send code")
            self._update_status("Error sending code")
        self.enable_buttons()

    #
    # --- Request Locker flow (existing) ---
    #
    def request_locker(self):
        self.disable_buttons()
        self._update_status("Requesting locker…")
        fut = asyncio.run_coroutine_threadsafe(self._request_locker_coro(), self.loop)
        fut.add_done_callback(lambda f: self.root.after(0, self._on_request_done, f))

    async def _request_locker_coro(self) -> str:
        return await self.ble_client.request_locker()

    def _on_request_done(self, fut):
        try:
            code = fut.result()
            messagebox.showinfo(
                "Success",
                f"Locker code: {code}\n"
                f"Door: {self.ble_client.last_door}\n"
                f"Available: {self.ble_client.available_count}"
            )
            self._update_status("Locker assigned")
            self.code_entry_var.set(code)
            self._update_info()
            if self.ble_client.last_door:
                self._set_door_state(self.ble_client.last_door, True)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self._update_status("Error occurred")
        finally:
            self.enable_buttons()

    def on_close(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.root.destroy()


def main():
    SmartLockerUI().root.mainloop()


if __name__ == "__main__":
    main()
