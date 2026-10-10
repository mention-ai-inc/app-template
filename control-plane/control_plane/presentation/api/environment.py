from enum import StrEnum


class ComponentType(StrEnum):
    SERVER = "server"
    LISTENER = "listener"
    EXECUTOR = "executor"
    JOB = "job"
    TRIGGER = "trigger"
