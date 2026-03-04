import sys


try:
    import aiohttp
except ImportError:
    print("=" * 52)
    print("  ERROR: 'aiohttp' is not installed.")
    print("  Fix:   python install.py")
    print("=" * 52)
    input("\nPress Enter to exit...")
    sys.exit(1)

try:
    import config
except ImportError:
    print("=" * 52)
    print("  ERROR: config.py not found.")
    print("  Make sure config.py is in the same folder.")
    print("=" * 52)
    input("\nPress Enter to exit...")
    sys.exit(1)

import asyncio
import itertools
import logging
import random
import signal
import traceback
from typing import Optional


_handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
if getattr(config, "LOG_FILE", None):
    try:
        _handlers.append(logging.FileHandler(config.LOG_FILE, encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] Could not open log file: {e}")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=_handlers,
)
log = logging.getLogger("CustomStatusRotator")


DISCORD_GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"
DISCORD_API     = "https://discord.com/api/v10"



def validate_config() -> bool:
    errors = []
    if not hasattr(config, "STATUSES") or not config.STATUSES:
        errors.append("  - STATUSES list is missing or empty")
    if not hasattr(config, "ROTATION_INTERVAL"):
        errors.append("  - ROTATION_INTERVAL is missing")
    elif not isinstance(config.ROTATION_INTERVAL, (int, float)) or config.ROTATION_INTERVAL < 1:
        errors.append("  - ROTATION_INTERVAL must be a number >= 1")
    if not hasattr(config, "STATUS_TYPE"):
        errors.append("  - STATUS_TYPE is missing")
    elif config.STATUS_TYPE not in ("online", "idle", "dnd", "invisible"):
        errors.append(f"  - STATUS_TYPE '{config.STATUS_TYPE}' invalid. Use: online, idle, dnd, invisible")
    for i, s in enumerate(getattr(config, "STATUSES", [])):
        if not isinstance(s, dict) or "text" not in s:
            errors.append(f"  - STATUSES[{i}] must be a dict with at least a 'text' key")
    if errors:
        print("\n[CONFIG ERROR]")
        for e in errors:
            print(e)
        return False
    return True



async def validate_token(session: aiohttp.ClientSession, token: str) -> Optional[str]:
    try:
        async with session.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": token},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return f"{data['username']}#{data.get('discriminator', '0')}"
            elif resp.status == 401:
                return None
            else:
                log.warning("Unexpected HTTP %d during token validation", resp.status)
                return None
    except aiohttp.ClientConnectorError:
        print("\n[ERROR] No internet connection or Discord is unreachable.")
        return None
    except Exception as e:
        print(f"\n[ERROR] Token validation error: {e}")
        return None



async def set_custom_status(
    session: aiohttp.ClientSession,
    token: str,
    entry: dict,
    status_type: str,
) -> bool:
    """
    PATCHes /users/@me/settings to set the custom status.
    This is the only reliable way to update the custom status text + emoji.
    """
    emoji_raw = entry.get("emoji")
    text      = entry.get("text", "")

    custom_status: dict = {"text": text}
    if emoji_raw:
        custom_status["emoji_name"] = emoji_raw

    payload = {
        "status":        status_type,
        "custom_status": custom_status,
    }

    headers = {
        "Authorization": token,
        "Content-Type":  "application/json",
    }

    try:
        async with session.patch(
            f"{DISCORD_API}/users/@me/settings",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                return True
            else:
                body = await resp.text()
                log.warning("PATCH /users/@me/settings returned %d: %s", resp.status, body)
                return False
    except Exception as e:
        log.error("Failed to set custom status: %s", e)
        return False



class CustomStatusRotator:
    def __init__(self, token: str, session: aiohttp.ClientSession):
        self.token    = token
        self._session = session
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._heartbeat_interval = 41.25
        self._sequence: Optional[int] = None
        self._running   = True
        self._connected = False
        self._tasks: list[asyncio.Task] = []

        statuses = list(config.STATUSES)
        if getattr(config, "SHUFFLE", False):
            random.shuffle(statuses)
        self._cycle = itertools.cycle(statuses)

    

    async def _send(self, payload: dict) -> None:
        try:
            if self._ws and not self._ws.closed:
                await self._ws.send_json(payload)
        except Exception as e:
            log.warning("Send error: %s", e)

   

    async def _identify(self) -> None:
        await self._send({
            "op": 2,
            "d": {
                "token": self.token,
                "properties": {
                    "os":      "Windows",
                    "browser": "Discord",
                    "device":  "Discord",
                },
                "intents": 0,
            },
        })
        log.info("IDENTIFY sent")

   

    async def _heartbeat_loop(self) -> None:
        await asyncio.sleep(random.uniform(0, self._heartbeat_interval))
        while self._running and self._connected:
            await self._send({"op": 1, "d": self._sequence})
            log.debug("Heartbeat sent (seq=%s)", self._sequence)
            await asyncio.sleep(self._heartbeat_interval)

   

    async def _rotation_loop(self) -> None:
        await asyncio.sleep(2)   
        log.info("Status rotation started.")
        while self._running:
            entry = next(self._cycle)
            label = f"{entry.get('emoji') or ''} {entry.get('text', '')}".strip()

            success = await set_custom_status(
                self._session, self.token, entry, config.STATUS_TYPE
            )
            if success:
                log.info("Custom status → %s", label)
            else:
                log.warning("Failed to set status: %s — will retry next cycle", label)

            await asyncio.sleep(config.ROTATION_INTERVAL)

    

    async def _handle(self, msg: aiohttp.WSMessage) -> None:
        if msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
            log.warning("WS event: %s", msg.type)
            self._connected = False
            return
        if msg.type != aiohttp.WSMsgType.TEXT:
            return

        try:
            data = msg.json()
        except Exception:
            return

        op = data.get("op")
        s  = data.get("s")
        if s is not None:
            self._sequence = s

        if op == 10:       
            self._heartbeat_interval = data["d"]["heartbeat_interval"] / 1000
            log.info("HELLO — heartbeat every %.2fs", self._heartbeat_interval)
            self._connected = True
            
            for t in self._tasks:
                t.cancel()
            self._tasks.clear()
            self._tasks.append(asyncio.ensure_future(self._heartbeat_loop()))
            self._tasks.append(asyncio.ensure_future(self._rotation_loop()))
            await self._identify()

        elif op == 11:    
            log.debug("Heartbeat ACK")

        elif op == 1:      
            await self._send({"op": 1, "d": self._sequence})

        elif op == 7:      
            log.warning("Discord requested reconnect.")
            self._connected = False
            if self._ws and not self._ws.closed:
                await self._ws.close()

        elif op == 9:       
            log.error("Invalid session (op 9). Reconnecting in 5s...")
            self._connected = False
            await asyncio.sleep(5)
            if self._ws and not self._ws.closed:
                await self._ws.close()

        elif op == 0:     
            t = data.get("t")
            if t == "READY":
                u = data["d"]["user"]
                log.info("Logged in as %s#%s", u["username"], u.get("discriminator", "0"))
            elif t == "RESUMED":
                log.info("Session resumed.")

  

    async def run(self) -> None:
        backoff = 2
        while self._running:
            try:
                log.info("Connecting to Gateway...")
                async with self._session.ws_connect(
                    DISCORD_GATEWAY,
                    heartbeat=None,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as ws:
                    self._ws = ws
                    backoff  = 2
                    async for msg in ws:
                        await self._handle(msg)
                        if not self._running:
                            break

                if not self._running:
                    break

                log.warning("Connection dropped. Reconnecting in %ds...", backoff)

            except aiohttp.ClientConnectorError as e:
                log.error("Connection error: %s", e)
            except asyncio.TimeoutError:
                log.error("Connection timed out.")
            except Exception:
                log.error("Unexpected error:\n%s", traceback.format_exc())

            if self._running:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

        log.info("Shut down cleanly.")

    def stop(self) -> None:
        self._running   = False
        self._connected = False
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()
        if self._ws:
            asyncio.ensure_future(self._ws.close())


async def main() -> None:
    print("=" * 52)
    print("    Siebe Custom Status Rotator")
    print("=" * 52)

    if not validate_config():
        input("\nPress Enter to exit...")
        sys.exit(1)

    print("\nPaste your Discord token below and press Enter:")
    print("(the token will be visible while typing)\n")
    token = input("  Token: ").strip()

    if not token:
        print("\n[ERROR] No token entered.")
        input("Press Enter to exit...")
        sys.exit(1)

    
    session = aiohttp.ClientSession()

    print("\nValidating token...")
    username = await validate_token(session, token)
    if username is None:
        print("[ERROR] Invalid or expired token.")
        await session.close()
        input("\nPress Enter to exit...")
        sys.exit(1)

    print(f"Logged in as:  {username}")
    print(f"Statuses:      {len(config.STATUSES)} entries")
    print(f"Interval:      every {config.ROTATION_INTERVAL}s")
    print(f"Presence dot:  {config.STATUS_TYPE}")
    print("Press Ctrl+C to stop.\n")

    rotator = CustomStatusRotator(token, session)

    loop = asyncio.get_running_loop()
    def _shutdown(sig):
        log.info("Signal %s — stopping...", sig.name)
        rotator.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown, sig)
        except (NotImplementedError, AttributeError):
            pass

    await rotator.run()
    await session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception:
        print("\n[FATAL ERROR]")
        traceback.print_exc()
    finally:
        input("\nPress Enter to exit...")
