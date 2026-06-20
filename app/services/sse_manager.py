import asyncio
import json
from typing import Dict, List
from collections import defaultdict


class SSEManager:
    def __init__(self):
        self._connections: Dict[int, List[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, company_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._connections[company_id].append(queue)
        return queue

    def unsubscribe(self, company_id: int, queue: asyncio.Queue):
        if queue in self._connections[company_id]:
            self._connections[company_id].remove(queue)

    async def broadcast(self, company_id: int, event_type: str, data: dict):
        payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        dead = []
        for queue in self._connections[company_id]:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(queue)
        for q in dead:
            self.unsubscribe(company_id, q)

    async def event_generator(self, company_id: int):
        queue = self.subscribe(company_id)
        try:
            yield "data: {\"type\": \"connected\"}\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            self.unsubscribe(company_id, queue)


sse_manager = SSEManager()
