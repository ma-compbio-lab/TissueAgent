"""A fresh installation must expose Settings before provider keys are configured."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import models
from server import main
from server.routes import chat, sessions
from server.session_manager import SessionState


@pytest.fixture
def startup(monkeypatch):
    """Isolate keys and session state without migrating the user's projects."""
    for variable in models.PROVIDER_ENV_VAR.values():
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(models, "_api_keys", {})
    monkeypatch.setattr(models, "_selection", models.Selection())
    monkeypatch.setattr(models, "_revision", 0)
    session = SessionState()
    for module in (main, chat, sessions):
        monkeypatch.setattr(module, "session", session)
    for name in (
        "reset_data_directories", "migrate_legacy_sessions", "migrate_legacy_library_layout",
        "migrate_projects_out_of_workspace", "migrate_plan_scratch_out_of_workspace",
        "migrate_chat_json_to_dotfile", "migrate_scratch_into_active_project",
        "recover_active_project", "register_ui_event_queue", "stop_r_backend",
    ):
        monkeypatch.setattr(main, name, Mock(return_value=None))
    monkeypatch.setattr(main, "_kernel_client", None)
    monkeypatch.setattr(main, "_settings_revision", None)

    def compile_graph(_kernel):
        session.agent = object()
        session.model_revision = models.get_revision()
        main._settings_revision = main.agent_settings.get_revision()

    compiled = Mock(side_effect=compile_graph)
    monkeypatch.setattr(main, "_compile_graph", compiled)
    return session, compiled


def test_settings_and_websocket_work_before_a_key_is_supplied(startup):
    """Missing keys reject a prompt without closing chat or changing the project."""
    session, compiled = startup
    with TestClient(main.app) as client:
        response = client.get("/api/models/list")
        assert response.status_code == 200
        assert response.json()["keys"]["openai"]["effective"] is False
        compiled.assert_not_called()
        with client.websocket_connect("/ws/chat") as ws:
            for _ in range(3):
                ws.receive_json()  # history, mode, metrics
            ws.send_json({"type": "send_message", "text": "Test a fresh installation"})
            error = ws.receive_json()
            assert error["type"] == "run_error"
            assert error["error_type"] == "ModelConfigurationError"
            assert "Settings" in error["detail"]
            assert "OPENAI_API_KEY" in error["detail"]
            assert session.agent_state["messages"] == []
            assert session.project_id is None
            ws.send_json({"type": "set_mode", "mode": "copilot"})
            assert ws.receive_json() == {"type": "mode_updated", "data": {"mode": "copilot"}}

        response = client.post("/api/models/keys", json={"provider": "openai", "key": "test-key"})
        assert response.json()["keys"]["openai"]["ui_set"] is True
        assert "test-key" not in response.text
        main.ensure_graph_current()
        compiled.assert_called_once()
        main.ensure_graph_current()
        compiled.assert_called_once()


def test_exported_key_preserves_eager_startup(startup, monkeypatch):
    """Existing users with exported credentials still get a compiled graph at startup."""
    _, compiled = startup
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with TestClient(main.app):
        compiled.assert_called_once()


def test_both_selected_providers_need_keys(startup):
    """Configuring one role does not conceal a missing key for the other role."""
    _, compiled = startup
    models.set_selection("gpt-5.5", "claude-sonnet-4-6")
    models.set_api_key("openai", "test-key")
    with TestClient(main.app):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            main.ensure_graph_current()
        compiled.assert_not_called()
