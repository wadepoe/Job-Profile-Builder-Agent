import logging

from langchain_core.messages import SystemMessage
from langchain_core.messages.utils import count_tokens_approximately
from opentelemetry import trace

from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from agent import SampleAgent
from batch_process_tool import batch_process_tool
from datetime_tool import get_datetime_tool
from deliver_profile_tool import deliver_profile_tool
from find_similar_profiles_tool import find_similar_profiles_tool
from gap_resolution_tool import gap_resolution_tool
from generate_profile_tool import generate_profile_tool
from intake_tool import intake_tool
from link_requisition_tool import link_requisition_tool
from load_skill_resources import get_load_skill_resource_tool
from mcp_providers.agw import get_mcp_tools
from prompt_injection_detector import wrap_tool

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Custom agent tools (no MCP dependency — always available)
_AGENT_TOOLS = [
    intake_tool,
    gap_resolution_tool,
    generate_profile_tool,
    deliver_profile_tool,
    batch_process_tool,
    find_similar_profiles_tool,
    link_requisition_tool,
]


async def _run_agent(
    agent: SampleAgent,
    query: str,
    context_id: str,
    tools: list,
    updater: TaskUpdater,
) -> None:
    """
    Run the agent and stream results. Extracted from execute() so that
    OpenTelemetry spans can be applied without wrapping an async generator.
    All milestone instrumentation lives here.
    """
    with tracer.start_as_current_span("job_profile.agent_execution") as span:
        span.set_attribute("context_id", context_id)
        span.set_attribute("tool_count", len(tools))

        try:
            async for item in agent.stream(query, context_id, tools=tools):
                is_task_complete = item["is_task_complete"]
                require_user_input = item["require_user_input"]
                content = item["content"]

                # Normalise content to str in all branches — AIMessage.content
                # can be a list of dicts when the model returns multi-modal output.
                safe_content = content if isinstance(content, str) else str(content)

                if require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(safe_content, context_id, updater.task_id),
                        final=True,
                    )
                    break
                elif is_task_complete:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=safe_content))], name="agent_result"
                    )
                    await updater.complete()
                    break
                else:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(safe_content, context_id, updater.task_id),
                    )
        except Exception as e:
            span.record_exception(e)
            raise


class AgentExecutor(A2AAgentExecutor):
    def __init__(self):
        self.agent = SampleAgent()
        self.skill_tools = [get_datetime_tool(), *get_load_skill_resource_tool()]

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent and stream results back via A2A protocol.

        Business milestones M1–M6 are instrumented via structured logging in each
        tool module. OpenTelemetry spans cover the full execution and each named
        business step.

        Milestone spans:
          - job_profile.source_intake      → M1
          - job_profile.gap_resolution     → M2
          - job_profile.draft_generation   → M3
          - job_profile.human_review       → M4
          - job_profile.output_delivery    → M5
          - job_profile.batch_completion   → M6
        """
        query = context.get_user_input()
        task = context.current_task
        if not task:
            assert context.message is not None, "Cannot create task without a message"
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        # Load MCP tools from Agent Gateway
        mcp_tools = []
        try:
            mcp_tools = await get_mcp_tools()
            if not mcp_tools:
                logger.warning("No MCP tools returned from Agent Gateway")
        except Exception as e:
            logger.error("Failed to load MCP tools from Agent Gateway: %s", e)

        # Combine MCP tools, agent-specific tools, and skill tools
        all_tools = [*mcp_tools, *_AGENT_TOOLS, *self.skill_tools]

        # Wrap all tools with prompt injection scanning
        all_tools = [wrap_tool(t) for t in all_tools]

        from agent import get_system_prompt
        _system_prompt = get_system_prompt()
        _msg_tokens = count_tokens_approximately([SystemMessage(content=_system_prompt)])
        _total_tokens = count_tokens_approximately(
            [SystemMessage(content=_system_prompt)], tools=list(all_tools)
        )
        logger.info(
            "Loaded %d tool(s) (%d MCP, %d agent, %d skill); token estimate — prompt: %d, tools: %d, total: %d",
            len(all_tools),
            len(mcp_tools),
            len(_AGENT_TOOLS),
            len(self.skill_tools),
            _msg_tokens,
            _total_tokens - _msg_tokens,
            _total_tokens,
        )

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            await _run_agent(self.agent, query, task.context_id, all_tools, updater)
        except Exception as e:
            logger.exception("Agent execution error")
            raise ServerError(error=InternalError()) from e

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise ServerError(error=UnsupportedOperationError())
