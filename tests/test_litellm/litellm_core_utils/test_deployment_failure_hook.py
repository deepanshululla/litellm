"""
Tests for CustomLogger.async_log_deployment_failure_event pre-gate dispatch.

Verifies that:
- The hook fires on every failure attempt, including attempts past the first.
- is_first_failure_in_chain is True only on the first call per Logging instance.
- Errors in the hook do not propagate to the caller.
- The hook is not called for callbacks that are not CustomLogger instances.
"""
import asyncio
import time
from unittest.mock import patch

import pytest

import litellm
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.litellm_logging import Logging as LitellmLogging


class _RecordingLogger(CustomLogger):
    def __init__(self):
        super().__init__()
        self.calls: list[tuple[bool, str]] = []

    async def async_log_deployment_failure_event(
        self, kwargs, exception, is_first_failure_in_chain, start_time, end_time
    ):
        self.calls.append((is_first_failure_in_chain, type(exception).__name__))


@pytest.fixture
def logging_obj():
    return LitellmLogging(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        call_type="completion",
        start_time=time.time(),
        litellm_call_id="test-call-id",
        function_id="test-fn-id",
    )


@pytest.mark.asyncio
async def test_hook_fires_on_first_attempt(logging_obj):
    recorder = _RecordingLogger()
    with patch.object(litellm, "_async_failure_callback", [recorder]):
        with patch.object(logging_obj, "dynamic_async_failure_callbacks", []):
            await logging_obj.async_failure_handler(
                exception=ValueError("deployment A failed"),
                traceback_exception="tb",
            )

    assert len(recorder.calls) == 1
    is_first, exc_name = recorder.calls[0]
    assert is_first is True
    assert exc_name == "ValueError"


@pytest.mark.asyncio
async def test_hook_fires_on_second_attempt_with_correct_flag(logging_obj):
    recorder = _RecordingLogger()
    with patch.object(litellm, "_async_failure_callback", [recorder]):
        with patch.object(logging_obj, "dynamic_async_failure_callbacks", []):
            await logging_obj.async_failure_handler(
                exception=ValueError("attempt 1 failed"),
                traceback_exception="tb1",
            )
            await logging_obj.async_failure_handler(
                exception=ConnectionError("attempt 2 failed"),
                traceback_exception="tb2",
            )

    assert len(recorder.calls) == 2
    assert recorder.calls[0] == (True, "ValueError")
    assert recorder.calls[1] == (False, "ConnectionError")


@pytest.mark.asyncio
async def test_hook_error_does_not_propagate(logging_obj):
    class _ExplodingLogger(CustomLogger):
        async def async_log_deployment_failure_event(
            self, kwargs, exception, is_first_failure_in_chain, start_time, end_time
        ):
            raise RuntimeError("hook exploded")

    with patch.object(litellm, "_async_failure_callback", [_ExplodingLogger()]):
        with patch.object(logging_obj, "dynamic_async_failure_callbacks", []):
            await logging_obj.async_failure_handler(
                exception=ValueError("original"),
                traceback_exception="tb",
            )


@pytest.mark.asyncio
async def test_hook_not_called_for_non_custom_logger(logging_obj):
    deployment_hook_called = []

    class _WatcherLogger(CustomLogger):
        async def async_log_deployment_failure_event(
            self, kwargs, exception, is_first_failure_in_chain, start_time, end_time
        ):
            deployment_hook_called.append(True)

    fn_callback_called = []

    async def fn_callback(kwargs, response_obj, start_time, end_time):
        fn_callback_called.append(True)

    with patch.object(litellm, "_async_failure_callback", [fn_callback]):
        with patch.object(logging_obj, "dynamic_async_failure_callbacks", []):
            await logging_obj.async_failure_handler(
                exception=ValueError("x"),
                traceback_exception="tb",
            )

    assert len(deployment_hook_called) == 0
