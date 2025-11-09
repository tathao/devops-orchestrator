
class OrchestratorException(Exception):
    pass

class CommandError(OrchestratorException):
    def __init__(self, message, stdout, stderr):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr

class ServiceNotFound(OrchestratorException):
    pass

class TemplateNotFound(OrchestratorException):
    pass

class ServiceAlreadyExists(OrchestratorException):
    pass

class VaultError(OrchestratorException):
    pass

class ConfigError(OrchestratorException):
    pass