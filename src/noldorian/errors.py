"""Public exceptions raised by the Noldorian client."""


class BrokerError(RuntimeError):
    """The local broker rejected or could not complete a safe request."""
