from enum import Enum, auto

class VaultState(Enum):
    DOWN = auto()
    NOT_INITIALIZED = auto()
    SEALED = auto()
    UNSEALED = auto()
    STANDBY = auto()
    PERF_STANDBY = auto()
    RECOVERY = auto()
    DR_SECONDARY = auto()
    UNKNOWN = auto()
