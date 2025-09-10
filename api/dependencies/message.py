from usecases import MessageUsecase


def get_message_usecase() -> MessageUsecase:
    """Get the message usecase.

    Returns:
        The message usecase.

    """
    return MessageUsecase()
