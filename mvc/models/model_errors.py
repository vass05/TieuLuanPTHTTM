"""Errors that the web layer can report without inventing predictions."""


class ModelUnavailableError(RuntimeError):
    pass


class TaskConflictError(RuntimeError):
    pass
