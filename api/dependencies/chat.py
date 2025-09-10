from usecases import ChatUsecase


def get_chat_usecase() -> ChatUsecase:
    """Get the chat usecase.

    Returns:
        The chat usecase.

    """
    return ChatUsecase()
