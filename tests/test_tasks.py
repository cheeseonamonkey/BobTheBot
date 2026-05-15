from bobthebot.tasks import InteractTask, MiningTask, default_task_registry


def test_task_registry_describes_schema():
    registry = default_task_registry()

    schema = registry.schema_for("mining")

    assert schema["properties"]["target_name"]["default"] == "rock"
    assert schema["properties"]["radius"]["maximum"] == 100


def test_interact_task_schema():
    registry = default_task_registry()
    schema = registry.schema_for("interact")
    assert schema["properties"]["kind"]["enum"] == ["npc", "object", "grounditem"]
    assert schema["properties"]["target_name"]["default"] == ""


def test_task_registry_rejects_unknown_config():
    registry = default_task_registry()

    try:
        registry.create("mining", {"unknown": True})
    except ValueError as exc:
        assert "unexpected config" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_task_registry_rejects_invalid_config_type():
    registry = default_task_registry()

    try:
        registry.create("mining", {"radius": "near"})
    except ValueError as exc:
        assert "radius must be an integer" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_task_registry_creates_configured_task():
    registry = default_task_registry()

    task = registry.create("mining", {"target_name": "Tin rocks", "radius": 9, "cooldown": 0})

    assert isinstance(task, MiningTask)
    assert task.target_name == "Tin rocks"
    assert task.radius == 9
    assert task.cooldown == 0


def test_task_registry_creates_interact_task():
    registry = default_task_registry()

    task = registry.create("interact", {"kind": "npc", "target_name": "Goblin", "action": "Attack"})

    assert isinstance(task, InteractTask)
    assert task.kind == "npc"
    assert task.target_name == "Goblin"
    assert task.action == "Attack"
