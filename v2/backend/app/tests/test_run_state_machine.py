import pytest

from app.core.run_states import RunStatus, assert_transition_allowed, can_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
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
    ],
)
def test_allows_expected_run_status_transitions(current, target):
    assert can_transition(current, target) is True


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RunStatus.COMPLETED, RunStatus.RUNNING),
        (RunStatus.CANCELLED, RunStatus.RUNNING),
        (RunStatus.COMPLETED, RunStatus.CANCELLED),
        (RunStatus.CREATED, RunStatus.COMPLETED),
        (RunStatus.PAUSED, RunStatus.COMPLETED),
    ],
)
def test_rejects_invalid_run_status_transitions(current, target):
    assert can_transition(current, target) is False


def test_assert_transition_allowed_names_invalid_transition():
    with pytest.raises(ValueError, match="completed -> running"):
        assert_transition_allowed(RunStatus.COMPLETED, RunStatus.RUNNING)
