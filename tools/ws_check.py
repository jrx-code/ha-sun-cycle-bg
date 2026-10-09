#!/usr/bin/env python3
"""Check the sun_cycle_bg websocket commands against a live Home Assistant.

    python3 tools/ws_check.py ws://192.168.18.178:8123 ADMIN_TOKEN [USER_TOKEN]

Tokens are read from files when the argument is a path (keeps them out of the
process list). As admin: list, get, set, subscribe (an event right away and one
after a write), bad input, delete of a missing profile; the scratch profile
`ws-check` is removed at the end. With a non-admin token as well: read works,
set and delete are refused. Needs `websockets`. Exit 1 on the first failure.
"""
import asyncio
import json
import os
import sys

import websockets

PROFILE = "ws-check"


def token(arg: str) -> str:
    return open(arg).read().strip() if os.path.isfile(arg) else arg


class Conn:
    def __init__(self, ws):
        self.ws, self.n, self.events = ws, 0, []

    async def call(self, msg: dict) -> dict:
        self.n += 1
        await self.ws.send(json.dumps({"id": self.n, **msg}))
        while True:
            r = json.loads(await self.ws.recv())
            if r.get("type") == "event":
                self.events.append(r)
            elif r.get("id") == self.n:
                return r

    async def wait_event(self, sub_id: int, count: int, timeout: float = 3.0) -> list:
        async def pump():
            while len([e for e in self.events if e["id"] == sub_id]) < count:
                r = json.loads(await self.ws.recv())
                if r.get("type") == "event":
                    self.events.append(r)
        await asyncio.wait_for(pump(), timeout)
        return [e["event"] for e in self.events if e["id"] == sub_id]


async def connect(url: str, tok: str) -> Conn:
    ws = await websockets.connect(url.rstrip("/") + "/api/websocket", max_size=2**24)
    await ws.recv()
    await ws.send(json.dumps({"type": "auth", "access_token": tok}))
    r = json.loads(await ws.recv())
    if r["type"] != "auth_ok":
        raise SystemExit(f"auth failed: {r}")
    return Conn(ws)


def check(name: str, ok: bool, detail="") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f"  {detail}" if detail and not ok else ""))
    if not ok:
        raise SystemExit(1)


async def main() -> None:
    url, admin = sys.argv[1], token(sys.argv[2])
    user = token(sys.argv[3]) if len(sys.argv) > 3 else None
    a = await connect(url, admin)
    P = "sun_cycle_bg/profile/"
    r = await a.call({"type": P + "list"})
    check("list", r["success"] and "profiles" in r["result"], r)
    r = await a.call({"type": P + "subscribe", "profile": PROFILE})
    sub = a.n
    check("subscribe", r["success"], r)
    ev = await a.wait_event(sub, 1)
    check("subscribe sends the current profile", ev[0]["profile"] == PROFILE, ev)
    cfg = {"stars": {"count": 42}, "weather": {"entity": "weather.home", "leaves": "seasons"}}
    r = await a.call({"type": P + "set", "profile": PROFILE, "config": dict(cfg, type="x", profile="y")})
    check("set", r["success"], r)
    ev = await a.wait_event(sub, 2)
    check("event after set", ev[-1]["config"] == cfg, ev[-1])
    r = await a.call({"type": P + "get", "profile": PROFILE})
    check("get drops type/profile", r["success"] and r["result"]["config"] == cfg, r)
    r = await a.call({"type": P + "set", "profile": PROFILE, "config": [1]})
    check("set rejects a non-object", not r["success"], r)
    r = await a.call({"type": P + "set", "profile": "", "config": {}})
    check("set rejects an empty name", not r["success"], r)
    if user:
        u = await connect(url, user)
        r = await u.call({"type": P + "get", "profile": PROFILE})
        check("user: get", r["success"] and r["result"]["config"] == cfg, r)
        r = await u.call({"type": P + "set", "profile": PROFILE, "config": {}})
        check("user: set refused", not r["success"] and r["error"]["code"] == "unauthorized", r)
        r = await u.call({"type": P + "delete", "profile": PROFILE})
        check("user: delete refused", not r["success"] and r["error"]["code"] == "unauthorized", r)
        await u.ws.close()
    r = await a.call({"type": P + "delete", "profile": PROFILE})
    check("delete", r["success"] and r["result"]["deleted"], r)
    ev = await a.wait_event(sub, 3)
    check("event after delete: config null", ev[-1]["config"] is None, ev[-1])
    r = await a.call({"type": P + "delete", "profile": PROFILE})
    check("delete of a missing profile", r["success"] and not r["result"]["deleted"], r)
    await a.ws.close()


if __name__ == "__main__":
    asyncio.run(main())
