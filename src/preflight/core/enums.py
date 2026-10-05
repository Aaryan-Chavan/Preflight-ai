from enum import Enum

class RiskLevel(str, Enum):
    """The final calculated risk level of the Git push."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    UNKNOWN = "Unknown"   # no analysis was produced

class Severity(str, Enum):
    """Severity levels for static analysis findings and critical functions."""
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"
    CRITICAL = "Critical"

class Decision(str, Enum):
    """The developer's choice in the PySide6 popup."""
    CONTINUE = "Continue Push"
    CANCEL = "Cancel Push"
    PENDING = "Pending"

class PushOutcome(str, Enum):
    """The actual result of the Git push operation captured by the detached watcher."""
    CANCELLED = "cancelled"
    PUSH_CONFIRMED = "push_confirmed"
    PUSH_UNCONFIRMED = "push_unconfirmed"  # Timeout occurred while watching
    BYPASSED = "bypassed"                  # Developer used --no-verify
    HOOK_ERROR_FAILOPEN = "hook_error_failopen" # Pipeline crashed, but push allowed
    PENDING = "pending"

class ChangeKind(str, Enum):
    """The type of modification applied to a file or symbol."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"

class Language(str, Enum):
    """Programming languages supported by Tree-sitter and the LSP."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    UNKNOWN = "unknown"

class SyncStatus(str, Enum):
    """Status of the report in the SQLite to Firestore sync outbox."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"