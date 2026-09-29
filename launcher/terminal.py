"""Terminal web : WebSocket <-> docker exec PTY (bash) dans le conteneur du nœud."""
import asyncio
import contextlib
import errno
import json

import docker


async def serve(client: "docker.DockerClient", cname: str, ws) -> None:
    """Relie la WebSocket `ws` (protocole JSON, cf. static/app.js) au PTY bash du nœud."""
    api = client.api
    try:
        exec_id = api.exec_create(cname, ["/bin/bash", "-i"], stdin=True, tty=True, workdir="/root")["Id"]
        sock = api.exec_start(exec_id, socket=True, tty=True)._sock
    except Exception as e:  # noqa: BLE001
        await ws.send_text(json.dumps({"type": "error", "data": f"exec impossible: {e}"}))
        return
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    out_q: asyncio.Queue[bytes | None] = asyncio.Queue()

    def on_readable() -> None:
        try:
            data = sock.recv(65536)
        except (BlockingIOError, InterruptedError):
            return
        except OSError as e:
            if e.args[0] not in (errno.EAGAIN, errno.EWOULDBLOCK):
                out_q.put_nowait(None)
            return
        out_q.put_nowait(data or None)

    loop.add_reader(sock, on_readable)
    try:
        async def writer() -> None:
            while True:
                data = await out_q.get()
                if data is None:
                    await ws.send_text(json.dumps({"type": "closed"}))
                    return
                await ws.send_bytes(data)

        w = asyncio.create_task(writer())
        try:
            async for raw in ws.iter_text():
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "input":
                    with contextlib.suppress(OSError):
                        sock.sendall(msg.get("data", "").encode())
                elif msg.get("type") == "resize":
                    with contextlib.suppress(Exception):
                        api.exec_resize(exec_id, height=msg.get("rows", 24), width=msg.get("cols", 80))
        finally:
            w.cancel()
            with contextlib.suppress(Exception):
                sock.close()
    finally:
        loop.remove_reader(sock)
