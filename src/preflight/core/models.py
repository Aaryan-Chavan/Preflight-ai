from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4

from .enums import RiskLevel, Severity, Decision, PushOutcome, ChangeKind, Language

class Hunk(BaseModel):
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    content: str = Field(..., description="The unified diff content of the hunk")

class Symbol(BaseModel):
    name: str
    kind: str = Field(..., description="e.g., 'function', 'class', 'method'")
    start_line: int
    end_line: int
    change_kind: ChangeKind
    complexity_delta: int = 0
    fan_in: int = 0  
    semantic_flags: List[str] = Field(default_factory=list)

class FileChange(BaseModel):
    old_path: Optional[str] = None
    new_path: Optional[str] = None
    change_kind: ChangeKind
    language: Language
    hunks: List[Hunk] = Field(default_factory=list)
    symbols: List[Symbol] = Field(default_factory=list)
    is_test_file: bool = False

class ChangeSet(BaseModel):
    repo_path: str
    repo_name: str
    branch: str
    local_sha: str
    remote_sha: str
    files: List[FileChange] = Field(default_factory=list)
    ml_risk_result: dict | None = None

class Finding(BaseModel):
    tool: str
    rule_id: str
    severity: Severity
    file_path: str
    line_number: int
    message: str
    category: str

class FeatureVector(BaseModel):
    files_modified: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    hunks_count: int = 0
    entropy: float = 0.0
    author_experience_commits: int = 0
    file_age_days_avg: float = 0.0
    complexity_delta_total: int = 0
    findings_critical: int = 0
    findings_error: int = 0
    findings_warning: int = 0
    modifies_auth: int = 0
    modifies_security: int = 0
    modifies_db_schema: int = 0
    modifies_api: int = 0
    modifies_dependencies: int = 0
    modifies_tests: int = 0

class CriticalFunction(BaseModel):
    name: str
    file_path: str
    severity: Severity
    reason: str = Field(..., description="Deterministic reason, rephrased by LLM")

class RiskResult(BaseModel):
    level: RiskLevel
    probability: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    critical_functions: List[CriticalFunction] = Field(default_factory=list)
    prediction_reasons: List[str] = Field(default_factory=list)

class PopupPayload(BaseModel):
    repo_name: str
    branch: str
    files_modified_count: int
    risk_level: RiskLevel
    confidence_percentage: int
    critical_functions: List[CriticalFunction]
    impact_summary: List[str]
    verification_checklist: List[str]
    ai_recommendation: str
    commit_message: str = "Commit details unavailable"

class ReportMetadata(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    install_id: str
    uid: Optional[str] = None
    repo_name: str
    branch: str
    local_sha: str
    remote_sha: str
    decision: Decision = Decision.PENDING
    outcome: PushOutcome = PushOutcome.PENDING
    analysis_ms: int = 0
    pipeline_version: str = "0.1.0"
    sync_status: str = "pending"
# testing
class Report(BaseModel):
    meta: ReportMetadata
    popup: PopupPayload
    detailed_markdown: Optional[str] = None