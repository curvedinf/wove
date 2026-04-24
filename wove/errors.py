class UnresolvedSignatureError(NameError):
    """
    Raised when a task's signature contains parameters that cannot be resolved
    from the available dependencies.
    """
    pass


class MissingDispatchFeatureError(RuntimeError):
    """
    Raised when a dispatch feature is used without optional dispatch dependencies.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(
            "Wove dispatch features require cloudpickle.\n\n"
            'Install with: pip install "wove[dispatch]"\n\n'
            f"Required because: {reason}"
        )
