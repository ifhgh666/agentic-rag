"""Legacy deadline APIs remain testable; reference online execution ignores them."""
import pytest
from pydantic import ValidationError
from app.config import Settings
from app.core.model_call import ModelCallBudget
from tests.fakes.reference_helpers import make_service, run_turn

def test_request_timeout_defaults_to_five_minutes_and_rejects_larger_config():
    assert Settings(_env_file=None).request_timeout_seconds == 300
    for value in (0, -1, 301):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, request_timeout_seconds=value)


def test_request_budget_keeps_api_deadline_instead_of_resetting_clock(monkeypatch):
    monkeypatch.setattr("app.core.model_call.time.monotonic", lambda: 100.0)
    budget = ModelCallBudget(8, 12, {})
    budget.start("r", deadline=105.0)
    assert budget.remaining_seconds("r") == 5



def test_reference_execution_does_not_enter_legacy_deadline_or_call_runner(settings, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Old model deadline/runner entered")
    monkeypatch.setattr("app.core.model_call.ModelCallRunner.invoke", forbidden)
    monkeypatch.setattr("app.core.model_call.owned_call_context", forbidden)
    poisoned = settings.model_copy(update={"max_simple_llm_calls": 0, "max_llm_calls_per_request": 0,
        "llm_timeout_seconds": .001, "request_timeout_seconds": .001, "max_context_tokens": 1,
        "llm_max_output_tokens": 1})
    service, model, _ = make_service(poisoned)
    final, _ = run_turn(service)
    assert not final["pending"] and len(model.calls) == 4
    assert len(final["state"]["messages"][-1].content) > 1

def test_thread_lock_is_released_after_model_transport_failure(settings):
    def broken(*_):
        raise TimeoutError("SDK transport timeout")
    service, model, _ = make_service(settings, resolver=broken)
    with pytest.raises(TimeoutError):
        run_turn(service)
    with service.request("test"):
        with pytest.raises(RuntimeError, match="THREAD_BUSY"):
            with service.request("test"):
                pytest.fail("Same thread was not excluded")
    with service.request("test"):
        assert "test" in service._active
