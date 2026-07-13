class DeepOrbitError(Exception):
    """Expected user-facing failure."""

    code = "DEEPORBIT_ERROR"


class ConfigError(DeepOrbitError):
    code = "CONFIG_ERROR"


class TaskNotFoundError(DeepOrbitError):
    code = "TASK_NOT_FOUND"
