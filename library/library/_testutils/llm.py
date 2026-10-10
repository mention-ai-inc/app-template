from collections.abc import Awaitable, Callable

from pydantic_ai import AgentRunResult


async def passthrough_run_llm[OutputT](
    *, agent_run: Callable[[], Awaitable[AgentRunResult[OutputT]]], **_: object
) -> AgentRunResult[OutputT]:
    """Test helper. Replaces `run_llm` so it just invokes the underlying `agent.run`
    thunk, skipping the span and the publish call. Use as `mocker.patch(...,
    side_effect=passthrough_run_llm)` so call args are still recorded for assertions.

    Must be `async` because `mocker.patch` autodetects `run_llm` as async and uses
    `AsyncMock`, which awaits the side_effect when it's a coroutine function."""
    return await agent_run()
