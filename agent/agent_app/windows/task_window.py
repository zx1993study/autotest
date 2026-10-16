from __future__ import annotations

import asyncio
import json
import logging
import time
from uuid import uuid4

from agent_app.windows.local_control import window_path, write_json
from agent_app.windows.native import NativeBrowserWindow


class TaskBrowserWindow:
    def __init__(self, config, api, task_id, lease_token, name):
        self.config, self.api = config, api
        self.task_id, self.lease_token = task_id, lease_token
        self.window_id = uuid4().hex
        self.label = f"Autotest #{task_id} | {str(name)[:60]}"
        self.native = NativeBrowserWindow(self.label) if config is not None and api is not None else None
        self.phase, self.focus, self.command_id = "starting", "idle", ""
        self.page, self.loop = None, None
        self.local_loop = None
        self.activation_lock = asyncio.Lock()
        self.done = False
        self._local_id = ""
        self.revision = time.time_ns()

    def state(self):
        return {"window_id": self.window_id, "label": self.label, "status": "closed" if self.done else self.native.status if self.native else "unavailable",
                "browser_name": self.native.browser_name if self.native else "", "phase": self.phase,
                "focus": self.focus, "command_id": self.command_id}

    async def attach(self, page):
        self.page = page
        if not self.native:
            return
        self.native.start()
        self.loop = asyncio.create_task(self._control_loop())
        self.local_loop = asyncio.create_task(self._local_loop())
        await asyncio.to_thread(self.native.ready.wait, 7)
        await self.activate()

    async def activate(self, command_id=""):
        async with self.activation_lock:
            if command_id:
                self.command_id = command_id
            self.focus = "failed"
            if self.page and not self.page.is_closed() and self.native and self.native.status == "open":
                try:
                    await self.page.bring_to_front()
                    self.focus = await asyncio.to_thread(self.native.focus)
                except Exception:  # noqa: BLE001 - window focus failure must not replay or fail a business action.
                    self.focus = "failed"

    async def set_phase(self, phase, activate=False):
        self.phase = phase
        if self.native:
            self.native.phase = phase
        if activate:
            await self.activate()

    def _local_command(self):
        path = window_path(self.config).with_suffix(".show")
        try:
            command = json.loads(path.read_text(encoding="utf-8"))
            if command.get("id") != self._local_id and command.get("window_id") == self.window_id and 0 <= time.time() - command.get("created_at", 0) < 12:
                self._local_id = command["id"]
                return True
        except (OSError, ValueError, TypeError):
            pass
        return False

    async def _exchange(self):
        method = getattr(self.api, "browser_window_exchange", None)
        if not method:
            return {}
        self.revision += 1
        return await asyncio.to_thread(method, self.task_id, self.lease_token, {**self.state(), "revision": self.revision})

    async def _control_loop(self):
        while not self.done:
            try:
                response = await self._exchange()
                command = (response or {}).get("command")
                if isinstance(command, dict) and command.get("window_id") == self.window_id and command.get("id") != self.command_id:
                    await self.activate(command["id"])
                    await self._exchange()
            except Exception as exc:  # noqa: BLE001 - local controls stay available during a platform outage.
                logging.getLogger(__name__).debug("Browser window exchange: %s", type(exc).__name__)
            await asyncio.sleep(1)

    async def _local_loop(self):
        while not self.done:
            if self.page.is_closed():
                self.native.status = "closed"
            try:
                write_json(window_path(self.config), {"task_id": self.task_id, "window": self.state(), "updated_at": time.time()})
                if self._local_command():
                    await self.activate()
            except OSError:
                logging.getLogger(__name__).debug("Browser local control unavailable")
            await asyncio.sleep(.5)

    async def close(self):
        self.done, self.phase = True, "finished"
        if self.native:
            await asyncio.to_thread(self.native.close)
        for loop in (self.loop, self.local_loop):
            if not loop:
                continue
            loop.cancel()
            try:
                await loop
            except asyncio.CancelledError:
                pass
        if self.native is not None:
            write_json(window_path(self.config), {"task_id": self.task_id, "window": self.state(), "updated_at": time.time()})
        if self.api is not None:
            try:
                await self._exchange()
            except Exception as exc:  # noqa: BLE001 - final report also closes the task's window lifecycle.
                logging.getLogger(__name__).debug("Final browser window exchange: %s", type(exc).__name__)
