from pydantic import BaseModel


class RunQualityCheck(BaseModel):
    id: str
    title: str
    status: str
    summary: str
    score_delta: int
    details: dict


class RunQualityResponse(BaseModel):
    run_id: str
    score: int
    status: str
    checks: list[RunQualityCheck]
