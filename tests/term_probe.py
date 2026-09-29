"""Sonde terminal WS : connecte, envoie echo, attend la réponse ; teste l'isolation (403).
Usage: uv run python tests/term_probe.py <http://host:port> <sid> <node>"""
import asyncio
import json
import sys

import websockets


async def probe(url: str, cookie: str | None, sid: str, node: str, expect_ok: bool) -> None:
    headers = {"Cookie": f"netsys_user={cookie}"} if cookie else {}
    ws_url = url.replace("http", "ws", 1)
    try:
        async with websockets.connect(f"{ws_url}/ws/term/{sid}/{node}", additional_headers=headers) as ws:
            await ws.send(json.dumps({"type": "input", "data": "echo QOK-$((6*7))\n"}))
            buf = b""
            try:
                async with asyncio.timeout(10):
                    while b"QOK-42" not in buf:
                        buf += await ws.recv()
            except TimeoutError:
                raise RuntimeError(f"QOK absent, reçu: {buf[:200]!r}") from None
    except websockets.exceptions.ConnectionClosed as e:
        if expect_ok and e.code == 1008:
            return
        if not expect_ok:
            print(f"refusé code={e.code} (attendu)")
            return
        raise
    if not expect_ok:
        raise RuntimeError("isolation échouée: un autre user a accès")
    print("terminal OK")


if __name__ == "__main__":
    url, sid, node = sys.argv[1], sys.argv[2], sys.argv[3]
    cookie = sys.argv[4] if len(sys.argv) > 4 else None
    asyncio.run(probe(url, cookie, sid, node, expect_ok=True))
