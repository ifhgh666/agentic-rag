"""Read-timeout alone cannot bound a provider's total streaming duration."""
import time

import pytest

from app.core.model_provider import ModelResult, complete_model


def test_provider_that_ignores_transport_timeout_cannot_block_total_wait():
    class SlowProvider:
        def complete(self, messages, *, tools=None, timeout_seconds=None):
            # A provider may keep delivering chunks within each read timeout.
            for _ in range(20):
                time.sleep(0.01)
            return ModelResult("late answer", "fake", "slow")
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        complete_model(SlowProvider(), [{"role": "user", "content": "test"}], timeout_seconds=0.03)
    assert time.monotonic() - started < 0.15
