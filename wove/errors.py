class UnresolvedSignatureError(NameError):
    """
    Raised when a task's signature contains parameters that cannot be resolved
    from the available dependencies.
    """
    pass
