from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


_ALLOWED_TRANSITIONS: set[tuple[RunStatus, RunStatus]] = {
    (RunStatus.CREATED, RunStatus.QUEUED),
    (RunStatus.QUEUED, RunStatus.RUNNING),
    (RunStatus.QUEUED, RunStatus.PAUSED),
    (RunStatus.RUNNING, RunStatus.PAUSED),
    (RunStatus.PAUSED, RunStatus.QUEUED),
    (RunStatus.RUNNING, RunStatus.COMPLETED),
    (RunStatus.RUNNING, RunStatus.FAILED),
    (RunStatus.RUNNING, RunStatus.INTERRUPTED),
    (RunStatus.RUNNING, RunStatus.CANCELLED),
    (RunStatus.INTERRUPTED, RunStatus.RUNNING),
    (RunStatus.FAILED, RunStatus.RUNNING),
}


def can_transition(current: RunStatus, target: RunStatus) -> bool:
    """判断 run 状态是否允许流转，保持任务生命周期边界清晰。"""
    return (current, target) in _ALLOWED_TRANSITIONS


def assert_transition_allowed(current: RunStatus, target: RunStatus) -> None:
    """在服务层更新状态前调用，避免非法状态被写入数据库。"""
    if not can_transition(current, target):
        raise ValueError(f"Invalid run status transition: {current.value} -> {target.value}")
