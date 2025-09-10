from usecases import SessionUsecase


def get_session_usecase() -> SessionUsecase:
    """Get the session usecase.

    Returns:
        The session usecase.

    """
    return SessionUsecase()
