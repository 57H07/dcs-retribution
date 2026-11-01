# The handler moved to game.applog (WEB-08.2) so that the server can read the log;
# this name stays for custom resources/logging.yaml files that reference it.
from game.applog import HookableInMemoryHandler

__all__ = ["HookableInMemoryHandler"]
