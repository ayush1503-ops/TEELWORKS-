"""API schemas - the single OnionResult[] contract consumed by the UI."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x: float = Field(..., description="normalized 0..1, left")
    y: float = Field(..., description="normalized 0..1, top")
    width: float
    height: float


class RegionPoint(BaseModel):
    x: float
    y: float
    r: float


class Finding(BaseModel):
    kind: Literal[
        "Surface Discoloration",
        "Surface Damage",
        "Possible Mold-Like Growth",
        "Shriveling",
        "Sprouting",
    ]
    confidence: float = Field(..., description="visual-evidence strength 0..1; NOT food safety")
    evidence: str


class OnionMetrics(BaseModel):
    darkRatio: float
    saturationStd: float
    greenTop: float
    detectorConfidence: float
    verifierConfidence: Optional[float] = None


class OnionResult(BaseModel):
    id: str
    bbox: BBox
    status: Literal["GREEN", "YELLOW", "RED"]
    statusLabel: Literal["NO OBVIOUS VISIBLE DAMAGE", "NEEDS REVIEW", "VISIBLE DAMAGE"]
    confidence: float
    findings: List[Finding]
    regions: List[RegionPoint]
    metrics: OnionMetrics
    modelName: str
    notes: str = ""
    signals: Optional[dict] = None


class AnalyzeRequest(BaseModel):
    imageBase64: str
    sourceMode: Literal["camera", "upload", "demo"] = "upload"


class AnalyzeResponse(BaseModel):
    engine: str
    engineDetail: str
    imageWidth: int
    imageHeight: int
    results: List[OnionResult]
    meta: dict
