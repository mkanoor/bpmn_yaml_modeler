"""
Message Queue - In-memory message correlation for receive tasks
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class MessageQueue:
    """In-memory message queue for workflow message correlation"""

    def __init__(self):
        # Message queues by correlation key
        # Format: {correlation_key: [messages...]}
        self.messages: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Waiting receive tasks
        # Format: {correlation_key: [(task_id, future, timeout)...]}
        self.waiting_tasks: Dict[str, List[tuple]] = defaultdict(list)

        # Lock for thread safety
        self.lock = asyncio.Lock()

    async def publish_message(
        self,
        message_ref: str,
        correlation_key: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Publish a message to the queue

        Args:
            message_ref: Message reference/topic
            correlation_key: Correlation key to match receive tasks
            payload: Message data

        Returns:
            True if message was delivered to waiting task, False if queued
        """
        async with self.lock:
            message = {
                'messageRef': message_ref,
                'correlationKey': correlation_key,
                'payload': payload,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Publishing message: {message_ref}, correlation: {correlation_key}")

            # Check if there's a waiting receive task
            if correlation_key in self.waiting_tasks and self.waiting_tasks[correlation_key]:
                # Deliver to first waiting task
                task_id, future, timeout_handle = self.waiting_tasks[correlation_key].pop(0)

                # Cancel timeout
                if timeout_handle:
                    timeout_handle.cancel()

                # Deliver message
                if not future.done():
                    future.set_result(message)
                    logger.info(f"Message delivered to waiting task: {task_id}")
                    return True

            # No waiting task, queue the message
            self.messages[correlation_key].append(message)
            logger.info(f"Message queued for correlation key: {correlation_key}")
            return False

    async def wait_for_message(
        self,
        task_id: str,
        message_ref: str,
        correlation_key: str,
        timeout_seconds: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for a message matching correlation key

        Args:
            task_id: Receive task ID
            message_ref: Expected message reference
            correlation_key: Correlation key to match
            timeout_seconds: Timeout in seconds

        Returns:
            Message dict if received, None if timeout

        Raises:
            asyncio.TimeoutError if timeout expires
        """
        async with self.lock:
            # Check if message already in queue
            if correlation_key in self.messages and self.messages[correlation_key]:
                # Check for matching message ref
                for i, msg in enumerate(self.messages[correlation_key]):
                    if msg['messageRef'] == message_ref or not message_ref:
                        # Found matching message
                        message = self.messages[correlation_key].pop(i)
                        logger.info(f"Message retrieved from queue for task: {task_id}")
                        return message

            # No message in queue, wait for it
            logger.info(f"Task {task_id} waiting for message: {message_ref}, correlation: {correlation_key}")

            # Create future
            future = asyncio.Future()

            # Setup timeout
            timeout_handle = None

            async def timeout_handler():
                await asyncio.sleep(timeout_seconds)
                async with self.lock:
                    # Remove from waiting list
                    if correlation_key in self.waiting_tasks:
                        self.waiting_tasks[correlation_key] = [
                            (tid, fut, th) for tid, fut, th in self.waiting_tasks[correlation_key]
                            if tid != task_id
                        ]

                    # Set timeout exception
                    if not future.done():
                        future.set_exception(asyncio.TimeoutError(
                            f"Timeout waiting for message: {message_ref}"
                        ))

            timeout_handle = asyncio.create_task(timeout_handler())

            # Add to waiting list
            self.waiting_tasks[correlation_key].append((task_id, future, timeout_handle))

        # Wait for message (outside lock)
        try:
            message = await future
            logger.info(f"Task {task_id} received message")
            return message
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_id} timed out waiting for message")
            raise

    async def get_queued_messages(self, correlation_key: str) -> List[Dict[str, Any]]:
        """Get all queued messages for a correlation key"""
        async with self.lock:
            return list(self.messages.get(correlation_key, []))

    async def get_waiting_tasks(self, correlation_key: str) -> List[str]:
        """Get all tasks waiting for messages with correlation key"""
        async with self.lock:
            return [task_id for task_id, _, _ in self.waiting_tasks.get(correlation_key, [])]

    async def clear_messages(self, correlation_key: str):
        """Clear all messages for a correlation key"""
        async with self.lock:
            if correlation_key in self.messages:
                del self.messages[correlation_key]
                logger.info(f"Cleared messages for correlation key: {correlation_key}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        async with self.lock:
            return {
                'total_queued_messages': sum(len(msgs) for msgs in self.messages.values()),
                'total_waiting_tasks': sum(len(tasks) for tasks in self.waiting_tasks.values()),
                'correlation_keys': list(set(list(self.messages.keys()) + list(self.waiting_tasks.keys())))
            }


# Global message queue instance
_message_queue: Optional[MessageQueue] = None


def get_message_queue() -> MessageQueue:
    """Get or create global message queue"""
    global _message_queue
    if _message_queue is None:
        _message_queue = MessageQueue()
    return _message_queue
