"""
app/services/queue_service.py
───────────────────────────────
Trade message queue.

LOCAL mode (SQS_QUEUE_URL not set):
  Uses an in-process asyncio.Queue.  The SQS worker still reads from it — 
  the entire pipeline works identically offline.

PRODUCTION mode (SQS_QUEUE_URL set):
  Uses boto3 to send/receive messages on the real Amazon SQS queue.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Local in-process queue (used when SQS not configured) ────────────────────
_local_queue: asyncio.Queue = asyncio.Queue()


# ── SQS client (lazy init) ────────────────────────────────────────────────────
_sqs_client = None


def _get_sqs():
    global _sqs_client
    if _sqs_client is None:
        import boto3
        kwargs = {"region_name": settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        _sqs_client = boto3.client("sqs", **kwargs)
    return _sqs_client


# ── Public API ────────────────────────────────────────────────────────────────

async def enqueue_trade(trade_id: int, trade_code: str) -> None:
    """
    Put a trade processing task onto the queue (SQS in production, in-process locally).
    """
    message = json.dumps({
        "message_type": "TRADE_EVENT",
        "trade_id": trade_id,
        "trade_code": trade_code,
    })

    if settings.use_sqs:
        try:
            sqs = _get_sqs()
            sqs.send_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                MessageBody=message,
            )
            logger.info("Enqueued trade %s to SQS", trade_code)
        except Exception as exc:
            logger.error("Failed to enqueue to SQS: %s — falling back to local queue", exc)
            await _local_queue.put(message)
    else:
        await _local_queue.put(message)
        logger.debug("Enqueued trade %s to local queue (SQS not configured)", trade_code)


async def dequeue_trade() -> Optional[dict]:
    """
    Pull the next message from the queue.
    Returns parsed dict or None if queue is empty (non-blocking).
    """
    if settings.use_sqs:
        try:
            sqs = _get_sqs()
            resp = sqs.receive_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=1,  # short-poll
            )
            messages = resp.get("Messages", [])
            if not messages:
                return None
            msg = messages[0]
            # Delete from queue immediately (at-least-once processing)
            sqs.delete_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                ReceiptHandle=msg["ReceiptHandle"],
            )
            return json.loads(msg["Body"])
        except Exception as exc:
            logger.error("SQS receive error: %s", exc)
            return None
    else:
        try:
            raw = _local_queue.get_nowait()
            return json.loads(raw)
        except asyncio.QueueEmpty:
            return None
