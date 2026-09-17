"""Tenant-separated Redis alert transport. Payloads contain no packet data."""
import json
import os
import time
import redis
from redis import asyncio as async_redis
from starlette.websockets import WebSocketDisconnect


def channel(tenant_id):
    return f"neomnix:alerts:{tenant_id}"


def publish_critical_alert(tenant_id, job_id):
    with redis.Redis.from_url(os.environ["REDIS_URL"], socket_timeout=3) as client:
        client.publish(channel(tenant_id), json.dumps({
            "type": "critical_data_leak", "job_id": job_id,
        }))


async def stream_alerts(websocket, tenant_id):
    client = async_redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=3)
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel(tenant_id))
        await websocket.accept()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20)
            if message and message["type"] == "message":
                await websocket.send_text(message["data"].decode())
            else:
                await websocket.send_json({"type": "heartbeat"})
        # Reconnect requires a fresh user/tenant/revocation check.
        await websocket.close(code=1000, reason="Revalidate session")
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.aclose()
        await client.aclose()
