from bobthebot.backends.base import NullBackend
from bobthebot.config import BotConfig
from bobthebot.engine import BotEngine
from bobthebot.models import ActionResult, EntityRef, Observation, RuntimeStatus
from bobthebot.tasks import Task


def test_engine_status_defaults_to_idle(tmp_path):
    engine = BotEngine(BotConfig(root=tmp_path), NullBackend())

    status = engine.status()

    assert status["running"] is False
    assert status["task"] == "idle"
    assert status["backend"]["backend"] == "null"


def test_set_unknown_task_raises(tmp_path):
    engine = BotEngine(BotConfig(root=tmp_path), NullBackend())

    try:
        engine.set_task("woodcutting")
    except ValueError as exc:
        assert "Unknown task" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_engine_rejects_task_when_backend_lacks_capability(tmp_path):
    engine = BotEngine(BotConfig(root=tmp_path), NullBackend())

    try:
        engine.set_task("mining")
    except ValueError as exc:
        assert "semantic_interact" in str(exc)
    else:
        raise AssertionError("expected ValueError")


class SemanticBackend:
    name = "semantic"
    capabilities = ("observe", "semantic_interact")

    def __init__(self):
        self.targets = []

    def status(self):
        return RuntimeStatus(backend=self.name, ready=True)

    def observe(self):
        return Observation(source=self.name)

    def click(self, x, y, button=1):
        return ActionResult(True, "click")

    def type_text(self, text):
        return ActionResult(True, "type_text")

    def press_key(self, key):
        return ActionResult(True, "press_key")

    def interact(self, target: EntityRef):
        self.targets.append(target)
        return ActionResult(True, "interact", target=target.name)


def test_mining_task_uses_entity_ref_against_semantic_backend(tmp_path):
    backend = SemanticBackend()
    engine = BotEngine(BotConfig(root=tmp_path), backend)
    engine.set_task("mining", target_name="Copper rock", cooldown=0)

    assert engine.task.execute(engine) is True
    assert backend.targets == [EntityRef(kind="object", name="Copper rock", action="Mine", radius=15)]
    assert engine.last_result["ok"] is True


class ExplodingTask(Task):
    def __init__(self):
        super().__init__(name="explode")

    def execute(self, engine):
        raise RuntimeError("boom")


def test_engine_pauses_and_records_task_exceptions(tmp_path):
    engine = BotEngine(BotConfig(root=tmp_path, tick_rate=0.01), NullBackend())
    engine.task = ExplodingTask()

    engine.start()
    import time

    time.sleep(0.05)
    engine.stop()

    assert engine.paused is True
    assert engine.last_result == {"error": "boom"}
