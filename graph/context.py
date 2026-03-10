import logging
import re
from typing import Any

from agent_framework._sessions import BaseContextProvider, AgentSession, SessionContext
from agent_framework._types import Message

log = logging.getLogger(__name__)

_FILE_TOOLS = {"search_files", "read_file", "read_multiple_files"}


def _parse_files_from_output(text: str) -> dict[str, str]:
    """Extract {id: name} pairs from search_files output text."""
    ids = re.findall(r"^ID:\s*(.+)$", text, re.MULTILINE)
    names = re.findall(r"^Name:\s*(.+)$", text, re.MULTILINE)
    return {fid.strip(): name.strip() for fid, name in zip(ids, names)}


class DocumentContextProvider(BaseContextProvider):
    def __init__(self) -> None:
        super().__init__(source_id="document_context")

    async def before_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        doc_ctx = session.state.get("doc_context")
        if not doc_ctx:
            log.debug("[doc_ctx] before_run: no session context yet, skipping injection")
            return

        lines = ["[Session Context]"]
        if topic := doc_ctx.get("topic"):
            lines.append(f"Current topic: {topic}")
        if last_query := doc_ctx.get("last_query"):
            lines.append(f'Last search: "{last_query}"')
        if files := doc_ctx.get("files"):
            file_list = ", ".join(f"{name} ({fid})" for fid, name in files.items())
            lines.append(f"Files found: {file_list}")

        if len(lines) > 1:
            text = "\n".join(lines)
            log.info("[doc_ctx] before_run: injecting context:\n%s", text)
            context.extend_messages(self, [Message("system", [text])])

    async def after_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        if not context.response or not context.response.messages:
            log.debug("[doc_ctx] after_run: no response messages, skipping")
            return

        # First pass: collect function_call entries for our file tools.
        call_map: dict[str, dict[str, Any]] = {}  # call_id -> {name, args}
        for message in context.response.messages:
            for content in message.contents or []:
                if content.type == "function_call" and content.name in _FILE_TOOLS:
                    args = content.parse_arguments() or {}
                    log.info("[doc_ctx] after_run: saw tool call — %s(%s)", content.name, args)
                    call_map[content.call_id] = {"name": content.name, "args": args}

        if not call_map:
            log.debug("[doc_ctx] after_run: no file tool calls in this turn, skipping state update")
            return

        doc_ctx: dict[str, Any] = session.state.setdefault("doc_context", {})

        # Second pass: match function_result messages and extract state.
        for message in context.response.messages:
            for content in message.contents or []:
                if content.type != "function_result":
                    continue
                call = call_map.get(content.call_id)
                if not call:
                    continue

                tool_name: str = call["name"]
                result_text = str(content.result or "")

                if tool_name == "search_files":
                    query: str = call["args"].get("query", "")
                    doc_ctx["topic"] = query
                    doc_ctx["last_query"] = query
                    new_files = _parse_files_from_output(result_text)
                    doc_ctx.setdefault("files", {}).update(new_files)
                    log.info(
                        "[doc_ctx] after_run: search_files(query=%r) → found %d file(s): %s",
                        query,
                        len(new_files),
                        list(new_files.values()),
                    )

        log.debug("[doc_ctx] after_run: session state now: %s", doc_ctx)
