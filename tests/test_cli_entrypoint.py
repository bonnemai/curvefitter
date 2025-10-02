"""Tests for the CLI entrypoint in ``app.__main__``."""

from __future__ import annotations

import os
from typing import Any

import pytest

from app import __main__ as cli


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, False),
        ("", False),
        ("0", False),
        ("false", False),
        ("TRUE", True),
        ("Yes", True),
        ("1", True),
    ],
)
def test_env_true_handles_common_truthy_strings(value: str | None, expected: bool) -> None:
    assert cli._env_true(value) is expected


def test_should_run_local_defaults_to_true_when_not_lambda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_LAMBDA_RUNTIME_API", raising=False)
    monkeypatch.delenv("CURVE_FITTER_LOCAL_SERVER", raising=False)

    assert cli._should_run_local() is True


def test_should_run_local_requires_opt_in_when_in_lambda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_LAMBDA_RUNTIME_API", "localhost")
    monkeypatch.delenv("CURVE_FITTER_LOCAL_SERVER", raising=False)

    assert cli._should_run_local() is False

    monkeypatch.setenv("CURVE_FITTER_LOCAL_SERVER", "true")
    assert cli._should_run_local() is True


def test_main_raises_when_not_permitted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_LAMBDA_RUNTIME_API", raising=False)
    monkeypatch.setenv("CURVE_FITTER_LOCAL_SERVER", "no")

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert "requires CURVE_FITTER_LOCAL_SERVER=true" in str(exc.value)


def test_main_invokes_uvicorn_with_expected_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_LAMBDA_RUNTIME_API", raising=False)
    monkeypatch.setenv("CURVE_FITTER_LOCAL_SERVER", "yes")
    monkeypatch.setenv("CURVE_FITTER_LOCAL_HOST", "127.0.0.1")
    monkeypatch.setenv("CURVE_FITTER_LOCAL_PORT", "9999")
    monkeypatch.setenv("CURVE_FITTER_LOCAL_RELOAD", "TRUE")
    monkeypatch.setenv("CURVE_FITTER_LOCAL_LOG_LEVEL", "debug")

    captured: dict[str, Any] = {}

    def _fake_run(*args: Any, **kwargs: Any) -> None:
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(cli.uvicorn, "run", _fake_run)

    cli.main()

    assert captured["args"] == ("app.main:app",)
    assert captured["kwargs"] == {
        "host": "127.0.0.1",
        "port": 9999,
        "reload": True,
        "log_level": "debug",
    }

    # Local environment variables should not leak into subsequent tests
    for key in (
        "CURVE_FITTER_LOCAL_SERVER",
        "CURVE_FITTER_LOCAL_HOST",
        "CURVE_FITTER_LOCAL_PORT",
        "CURVE_FITTER_LOCAL_RELOAD",
        "CURVE_FITTER_LOCAL_LOG_LEVEL",
    ):
        monkeypatch.delenv(key, raising=False)
        assert os.getenv(key) is None
