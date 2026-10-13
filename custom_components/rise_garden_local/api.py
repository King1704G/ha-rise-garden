"""Local TCP client for the Rise Garden controller (port 1000).

The controller is an ESP32 exposing a plaintext, newline-terminated command
server. It is fragile: it accepts a single client at a time and has a small
lwIP socket pool, so parallel connections or half-sent commands wedge the
server task (it starts sending RST and only recovers after a long idle or a
power cycle). This client therefore:

  * serialises every exchange behind an asyncio.Lock (one in flight, ever),
  * opens one short-lived connection per exchange and always closes it,
  * only ever sends complete "<verb ...>\r\n" lines,
  * enforces a minimum spacing between connections,
  * backs off on error.

Protocol (verified against fw "2012 v4.3.1"; command names from the app):
  read : bare word, e.g. "lamp 2", "wpump"   -> "OK <value...>"
  write: verb + args, e.g. "lamp 2 50", "wpump on" -> "OK ..."
  error: anything unrecognised                -> "FAIL syntax"
Some reads (e.g. ``ltimer``, ``stack``) return several lines terminated by a
final "OK". There is no "put" verb.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 1000

# Controller is single-client and slow; never hammer it.
_MIN_INTERVAL = 0.4          # seconds between connections
_CONNECT_TIMEOUT = 6.0
_READ_TIMEOUT = 3.0

# The controller silently truncates command lines after this many characters.
# A truncated 'ltimer set' can store a partial schedule, or FAIL and wipe it.
MAX_LINE = 127


class RiseLocalError(Exception):
    """Raised when the controller reports FAIL or cannot be reached."""


class RiseGardenLocal:
    """Serialised async client for one Rise Garden controller."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self._host = host
        self._port = port
        self._lock = asyncio.Lock()
        self._last_conn = 0.0

    @property
    def host(self) -> str:
        return self._host

    async def _exchange(self, line: str, *, multiline: bool = False) -> str:
        """Send one command line and return the raw reply (minus trailing CRLF)."""
        async with self._lock:
            # Space connections out so we never overrun the controller.
            gap = time.monotonic() - self._last_conn
            if gap < _MIN_INTERVAL:
                await asyncio.sleep(_MIN_INTERVAL - gap)

            writer = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=_CONNECT_TIMEOUT,
                )
                writer.write((line + "\r\n").encode())
                await writer.drain()

                buf = b""
                deadline = time.monotonic() + _READ_TIMEOUT
                while time.monotonic() < deadline:
                    try:
                        chunk = await asyncio.wait_for(
                            reader.read(4096),
                            timeout=deadline - time.monotonic(),
                        )
                    except asyncio.TimeoutError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    if multiline:
                        # multi-line dumps end with a line that is exactly "OK"
                        if buf.rstrip().split(b"\r\n")[-1] in (b"OK", b"") and buf.rstrip().endswith(b"OK"):
                            break
                    elif buf.endswith(b"\r\n"):
                        break
                return buf.decode(errors="replace").rstrip("\r\n")
            except (OSError, asyncio.TimeoutError) as err:
                raise RiseLocalError(f"{self._host}:{self._port} {err}") from err
            finally:
                self._last_conn = time.monotonic()
                if writer is not None:
                    try:
                        writer.close()
                        await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
                    except (OSError, asyncio.TimeoutError):
                        pass

    # ---- primitives -------------------------------------------------------

    async def get(self, key: str, *, multiline: bool = False) -> str:
        """Read a value. Returns the text after 'OK '. Raises on FAIL."""
        reply = await self._exchange(key, multiline=multiline)
        if reply.startswith("FAIL"):
            raise RiseLocalError(f"{key!r}: {reply}")
        if reply.startswith("OK"):
            return reply[2:].lstrip()
        # multi-line dumps: strip a trailing 'OK'
        return reply[:-2].rstrip() if reply.endswith("OK") else reply

    async def command(self, line: str) -> None:
        """Send a write command. Raises on FAIL."""
        reply = await self._exchange(line)
        if not reply.startswith("OK"):
            raise RiseLocalError(f"{line!r}: {reply}")

    async def raw(self, line: str, *, multiline: bool = False) -> str:
        """Send an arbitrary line and return the raw reply (for the service/discovery)."""
        return await self._exchange(line, multiline=multiline)

    # ---- typed helpers ----------------------------------------------------

    async def get_int(self, key: str) -> int | None:
        try:
            val = await self.get(key)
        except RiseLocalError:
            return None
        try:
            return int(val.split()[0])
        except (ValueError, IndexError):
            return None

    async def set_lamp(self, channel: int, level: int) -> None:
        """Set one lamp channel (1-3) to 0-100 %."""
        await self.command(f"lamp {channel} {max(0, min(100, level))}")

    async def set_pump(self, on: bool) -> None:
        """Turn the water pump on or off."""
        await self.command(f"wpump {'on' if on else 'off'}")

    async def set_pump_cycle(self, on_s: int, off_s: int) -> None:
        """Set the pump cycle ('wpc <on seconds> <off seconds>'), verified by readback.

        The firmware parses non-numbers as 0 and still answers OK, so both
        values are validated here before anything is sent.
        """
        if isinstance(on_s, bool) or isinstance(off_s, bool) or not (
            isinstance(on_s, int) and isinstance(off_s, int) and on_s >= 1 and off_s >= 1
        ):
            raise ValueError(f"invalid pump cycle {on_s!r}/{off_s!r}")
        await self.command(f"wpc {on_s} {off_s}")
        stored = await self.get("wpc")
        if stored.split()[:2] != [str(on_s), str(off_s)]:
            raise RiseLocalError(f"pump cycle readback mismatch: sent {on_s} {off_s}, controller has {stored!r}")

    async def set_clock(self, now_utc: datetime) -> None:
        """Set the controller clock. Only the UTC time of day can be set; the date is ignored."""
        await self.command(f"time {now_utc.astimezone(timezone.utc):%H:%M:%S}")

    async def light_schedule(self) -> list[dict] | None:
        """Parse 'ltimer': lines like ' 11:00:00 - 2400s - 25' (times are UTC)."""
        try:
            raw = await self.get("ltimer", multiline=True)
        except RiseLocalError:
            return None
        steps = []
        for line in raw.splitlines():
            parts = [p.strip() for p in line.split(" - ")]
            if len(parts) == 3 and parts[1].endswith("s"):
                try:
                    steps.append(
                        {"start_utc": parts[0], "duration_s": int(parts[1][:-1]), "level": int(parts[2])}
                    )
                except ValueError:
                    continue
        return steps

    async def set_light_schedule(self, steps: list[dict]) -> None:
        """Replace the whole light schedule, then verify it by reading it back.

        steps: [{"start_utc": "HH:MM:SS", "duration_s": int, "level": 0-100}, ...]
        """
        line = format_schedule(steps)
        await self.command(line)
        stored = await self.light_schedule()
        expected = [
            {"start_utc": _parse_time(s["start_utc"]), "duration_s": int(s["duration_s"]), "level": int(s["level"])}
            for s in steps
        ]
        if stored != expected:
            raise RiseLocalError(f"schedule readback mismatch: sent {expected}, controller has {stored}")

    async def unit_id(self) -> str | None:
        """Return the controller/kit id (the MAC-like unit id)."""
        try:
            val = await self.get("unitid")
        except RiseLocalError:
            return None
        # e.g. '"244cab137c28" 244cab137c28 0 nosb'  -> second token
        parts = val.replace('"', " ").split()
        return parts[0] if parts else None


def _parse_time(value: str) -> str:
    """Normalise 'H:MM' / 'HH:MM:SS' to 'HH:MM:SS'."""
    parts = [int(p) for p in str(value).split(":")]
    if len(parts) == 2:
        parts.append(0)
    if len(parts) != 3 or not (0 <= parts[0] < 24 and 0 <= parts[1] < 60 and 0 <= parts[2] < 60):
        raise ValueError(f"invalid time {value!r}")
    return "%02d:%02d:%02d" % tuple(parts)


def format_schedule(steps: list[dict]) -> str:
    """Build the shortest 'ltimer set' line the firmware accepts.

    Grammar (found by probing): '<H>:<MM>:<SS>[%<level>]#<seconds>' entries
    separated by spaces. The hour may drop its leading zero, minutes and
    seconds may not; the level defaults to 100 when omitted.
    """
    if not steps:
        raise ValueError("schedule needs at least one step")
    entries = []
    for step in steps:
        hh, mm, ss = _parse_time(step["start_utc"]).split(":")
        duration = int(step["duration_s"])
        level = int(step["level"])
        if duration <= 0:
            raise ValueError(f"invalid duration {duration}")
        if not 0 <= level <= 100:
            raise ValueError(f"invalid level {level}")
        entries.append(f"{int(hh)}:{mm}:{ss}{'' if level == 100 else f'%{level}'}#{duration}")
    line = "ltimer set " + " ".join(entries)
    if len(line) > MAX_LINE:
        raise ValueError(f"schedule is {len(line)} characters; the controller accepts at most {MAX_LINE}")
    return line
