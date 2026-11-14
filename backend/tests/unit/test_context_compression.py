from app.core.legacy_cache import dynamic_token_threshold
from app.core.model_provider import estimate_tokens


def test_dynamic_token_threshold_uses_configured_base_and_growth():
    assert dynamic_token_threshold(2000, 0.9, 1) == 2000
    assert dynamic_token_threshold(2000, 0.9, 2) == 3800
    assert dynamic_token_threshold(2000, 0.9, 3) == 5600


def test_token_estimate_is_available_for_window_guards():
    assert estimate_tokens("") == 0
    assert estimate_tokens("PX-200 16 A") > 0
