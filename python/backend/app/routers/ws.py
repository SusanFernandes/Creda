"""
WebSocket endpoint for real-time push notifications.
Clients connect and receive nudges/alerts in real time.
"""
import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

logger = logging.getLogger("creda.ws")

router = APIRouter()

# Active WebSocket connections: user_id -> set of websockets
_connections: Dict[str, Set[WebSocket]] = {}


async def broadcast_to_user(user_id: str, message: dict):
    """Send a message to all WebSocket connections for a given user."""
    if user_id in _connections:
        dead = set()
        payload = json.dumps(message)
        for ws in _connections[user_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        _connections[user_id] -= dead
        if not _connections[user_id]:
            del _connections[user_id]


async def broadcast_nudge(user_id: str, nudge: dict):
    """Broadcast a new nudge to connected clients."""
    await broadcast_to_user(user_id, {
        "type": "nudge",
        "data": nudge,
    })


async def broadcast_market_alert(user_id: str, alert: dict):
    """Broadcast a market alert to connected clients."""
    await broadcast_to_user(user_id, {
        "type": "market_alert",
        "data": alert,
    })


def get_connected_users() -> list[str]:
    """Return list of user IDs with active WebSocket connections."""
    return list(_connections.keys())


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: str = Query(default=""),
):
    """
    WebSocket endpoint for real-time notifications.
    Client connects with ?user_id=<uuid> query parameter.
    Receives JSON messages with type: nudge | market_alert | heartbeat
    """
    if not user_id:
        await websocket.close(code=4001, reason="user_id required")
        return

    await websocket.accept()
    logger.info("WS connected: user=%s", user_id[:8])

    # Register connection
    if user_id not in _connections:
        _connections[user_id] = set()
    _connections[user_id].add(websocket)

    try:
        # Send initial pending nudges
        try:
            from app.database import async_session_factory
            async with async_session_factory() as db:
                from app.models import Nudge
                result = await db.execute(
                    select(Nudge)
                    .where(Nudge.user_id == user_id, Nudge.is_read == False)  # noqa: E712
                    .order_by(Nudge.sent_at.desc())
                    .limit(10)
                )
                nudges = result.scalars().all()
                if nudges:
                    await websocket.send_text(json.dumps({
                        "type": "initial_nudges",
                        "data": [
                            {
                                "id": str(n.id),
                                "title": n.title,
                                "body": n.body,
                                "nudge_type": n.nudge_type,
                                "sent_at": n.sent_at.isoformat() if n.sent_at else "",
                            }
                            for n in nudges
                        ],
                    }))
        except Exception as e:
            logger.debug("WS initial nudge load failed: %s", e)

        # Keep connection alive with heartbeat
        while True:
            try:
                # Wait for client messages (ping/pong or commands)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif msg.get("type") == "mark_read":
                    # Mark nudge as read via WS
                    nudge_id = msg.get("nudge_id")
                    if nudge_id:
                        try:
                            from app.database import async_session_factory
                            from app.models import Nudge
                            async with async_session_factory() as db:
                                result = await db.execute(
                                    select(Nudge).where(Nudge.id == nudge_id, Nudge.user_id == user_id)
                                )
                                nudge = result.scalar_one_or_none()
                                if nudge:
                                    nudge.is_read = True
                                    await db.commit()
                                    await websocket.send_text(json.dumps({
                                        "type": "nudge_read",
                                        "nudge_id": nudge_id,
                                    }))
                        except Exception:
                            pass
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_text(json.dumps({"type": "heartbeat"}))
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WS error: %s", e)
    finally:
        # Unregister connection
        if user_id in _connections:
            _connections[user_id].discard(websocket)
            if not _connections[user_id]:
                del _connections[user_id]
        logger.info("WS disconnected: user=%s", user_id[:8])
