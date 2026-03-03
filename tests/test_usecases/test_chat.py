from pydantic_ai.messages import (
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolReturnPart,
)

from enums import ToolId
from usecases.chat import ChatUsecase


class TestChatUsecase:
    def test_extract_text_chunk_returns_part_start_text(self) -> None:
        event = PartStartEvent(index=0, part=TextPart(content="П"))

        result = ChatUsecase._extract_text_chunk(event=event)

        assert result == "П"

    def test_extract_text_chunk_returns_part_delta_text(self) -> None:
        event = PartDeltaEvent(index=0, delta=TextPartDelta(content_delta="ривет"))

        result = ChatUsecase._extract_text_chunk(event=event)

        assert result == "ривет"

    def test_extract_tool_result_chunk_for_deep_think(self) -> None:
        event = FunctionToolResultEvent(
            result=ToolReturnPart(tool_name=str(ToolId.DEEP_THINK), content="analysis")
        )

        result = ChatUsecase._extract_tool_result_chunk(
            event=event, tool_id=ToolId.DEEP_THINK
        )

        assert result == "analysis"

    def test_extract_tool_result_chunk_for_web_search(self) -> None:
        event = FunctionToolResultEvent(
            result=ToolReturnPart(
                tool_name=str(ToolId.WEB_SEARCH), content={"items": [1, 2]}
            )
        )

        result = ChatUsecase._extract_tool_result_chunk(
            event=event, tool_id=ToolId.WEB_SEARCH
        )

        assert result == '{"items": [1, 2]}'

    def test_extract_tool_result_chunk_for_retrieve(self) -> None:
        event = FunctionToolResultEvent(
            result=ToolReturnPart(tool_name=str(ToolId.RETRIEVE), content=b"chunk")
        )

        result = ChatUsecase._extract_tool_result_chunk(
            event=event, tool_id=ToolId.RETRIEVE
        )

        assert result == "chunk"

    def test_extract_tool_result_chunk_ignores_other_tool(self) -> None:
        event = FunctionToolResultEvent(
            result=ToolReturnPart(tool_name=str(ToolId.DEEP_THINK), content="analysis")
        )

        result = ChatUsecase._extract_tool_result_chunk(
            event=event, tool_id=ToolId.RETRIEVE
        )

        assert result is None

    def test_merge_stream_text_accumulates_multiple_tool_calls(self) -> None:
        merged = ""
        merged = ChatUsecase._merge_stream_text(current_text=merged, chunk_text="first")
        merged = ChatUsecase._merge_stream_text(
            current_text=merged, chunk_text="\n\nsecond"
        )

        assert merged == "first\n\nsecond"
