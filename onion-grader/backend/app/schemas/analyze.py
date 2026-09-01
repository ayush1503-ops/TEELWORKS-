"""Pydantic response models (API contract)."""
from pydantic import BaseModel, Field


class ImageInfo(BaseModel):
    filename: str
    format: str
    width: int
    height: int
    size_bytes: int
    megapixels: float
    aspect_ratio: float


class AnalyzeResponse(BaseModel):
    analysis_id: str
    created_at: str
    status: str
    analysis_available: bool
    image: ImageInfo
    detection: dict = Field(default_factory=dict)
    features: dict = Field(default_factory=dict)
    defects: list[dict] = Field(default_factory=list)
    quality_score: dict | None = None
    grade: dict = Field(default_factory=dict)
    grade_probabilities: dict | None = None
    predicted_class: dict | None = None
    analysis_confidence: dict = Field(default_factory=dict)
    model: dict = Field(default_factory=dict)
    capture_warnings: dict = Field(default_factory=dict)
    disclaimers: list[str] = Field(default_factory=list)
    phase: int
    app_version: str


class BatchItem(BaseModel):
    index: int
    filename: str
    ok: bool
    analysis_id: str | None = None
    found: bool = False
    quality_score: int | None = None
    grade: str | None = None
    defects_detected: list[str] = Field(default_factory=list)
    error: str | None = None


class BatchResponse(BaseModel):
    batch_id: str
    created_at: str
    total_files: int
    analysed_ok: int
    onions_found: int
    undetermined: int
    distribution: dict = Field(default_factory=dict)   # grade → {count, pct}
    avg_quality_score: float | None = None
    defect_tally: dict = Field(default_factory=dict)
    items: list[BatchItem] = Field(default_factory=list)
    report_url: str | None = None
    note: str = Field(default="")
    disclaimers: list[str] = Field(default_factory=list)


class EvalResponse(BaseModel):
    filename: str
    actual: str
    predicted: str
    confidence: float
    correct: bool
    quality_score: int | None = None
    grade: str | None = None
    analysis_id: str | None = None
    top_defects: list[str] = Field(default_factory=list)
