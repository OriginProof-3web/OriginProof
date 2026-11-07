class BlockchainDependencyError(RuntimeError):
    """Raised when chain state cannot be read reliably."""


class BlockchainConfigurationError(ValueError):
    """Raised when an address or identifier is malformed."""
