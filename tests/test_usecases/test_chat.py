from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPart, TextPartDelta

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
