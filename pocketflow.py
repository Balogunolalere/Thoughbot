from __future__ import annotations
import asyncio
from typing import Any, Mapping, Sequence, TypedDict
from dataclasses import dataclass

# ---------- Public API ----------
class Context(TypedDict, total=False):
    """Shared immutable context visible to every node."""
    ...


@dataclass(slots=True)
class Params:
    """Frozen parameters for a single run."""
    data: Mapping[str, Any]


class Node:
    """Base node.  Must implement __call__."""
    async def __call__(self, ctx: Context, p: Params) -> tuple[str, Any]:
        """
        Returns (action, value) where
          action: routing key for the next node
          value : actual payload
        """
        raise NotImplementedError


class Flow:
    """Concurrent depth-first traversal of a DAG."""
    def __init__(self, start: Node) -> None:
        self._start = start
        self._edges: dict[str, Node] = {}

    def edge(self, action: str, node: Node) -> None:
        self._edges[action] = node

    async def run(
        self,
        ctx: Context,
        params: Params | None = None,
        *,
        semaphore: asyncio.Semaphore | None = None,
    ) -> Any:
        """
        Run the graph once.
        If semaphore is given, at most that many nodes execute concurrently.
        """
        sem = semaphore or asyncio.Semaphore(1_000_000)
        params = params or Params({})

        async def _visit(node: Node) -> Any:
            async with sem:
                action, value = await node(ctx, params)
                next_node = self._edges.get(action)
                return (await _visit(next_node)) if next_node else value

        return await _visit(self._start)


class BatchFlow:
    """Run the same graph with different parameters, concurrently."""
    def __init__(self, start: Node) -> None:
        self._flow = Flow(start)

    async def run(
        self,
        ctx: Context,
        params_list: Sequence[Params],
        *,
        max_parallel: int | None = None,
    ) -> list[Any]:
        semaphore = asyncio.Semaphore(max_parallel) if max_parallel else None
        coros = [self._flow.run(ctx, p, semaphore=semaphore) for p in params_list]
        return await asyncio.gather(*coros)


# ---------- Retry wrapper ----------
class Retry(Node):
    def __init__(
        self,
        inner: Node,
        *,
        tries: int = 3,
        backoff: float = 0.1,
        jitter: bool = True,
    ) -> None:
        self._inner = inner
        self.tries = max(tries, 1)
        self.backoff = backoff
        self.jitter = jitter

    async def __call__(self, ctx: Context, p: Params) -> tuple[str, Any]:
        delay = self.backoff
        for attempt in range(self.tries):
            try:
                return await self._inner(ctx, p)
            except Exception as exc:
                if attempt == self.tries - 1:
                    raise
                await asyncio.sleep(delay)
                if self.jitter:
                    delay *= 1.5 * (0.5 + 0.5 * hash((id(self), attempt)) % 1)