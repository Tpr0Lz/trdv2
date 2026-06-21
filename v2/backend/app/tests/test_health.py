from threading import Event

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class BlockingStartupManager:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()

    def mark_running_runs_interrupted_on_startup(self) -> None:
        self.started.set()
        self.release.wait(timeout=5)


def test_health_does_not_wait_for_startup_recovery():
    manager = BlockingStartupManager()

    with TestClient(create_app(run_manager=manager)) as client:
        assert manager.started.wait(timeout=1)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        manager.release.set()
