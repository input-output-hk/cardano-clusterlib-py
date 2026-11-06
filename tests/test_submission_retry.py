"""Unit tests for bounded mempool submission retries."""

import subprocess
import types
from unittest import mock

import pytest

from cardano_clusterlib import clusterlib_klass
from cardano_clusterlib import exceptions
from cardano_clusterlib import structs
from cardano_clusterlib import transaction_group


@pytest.fixture
def submission(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """Provide a transaction group with a fake CLI and monotonic clock."""
    clock = types.SimpleNamespace(now=0.0)

    def sleep(delay: float) -> None:
        clock.now += delay

    sleeper = mock.Mock(side_effect=sleep)
    monkeypatch.setattr(
        transaction_group,
        "time",
        types.SimpleNamespace(monotonic=lambda: clock.now, sleep=sleeper),
    )
    jitter = mock.Mock(side_effect=lambda _low, high: high)
    monkeypatch.setattr(transaction_group, "random", types.SimpleNamespace(uniform=jitter))
    cli = mock.Mock(return_value=structs.CLIOut(stdout=b'{"txhash": "hash"}', stderr=b""))
    cluster = types.SimpleNamespace(
        genesis={"protocolParams": {"minFeeB": 1}}, magic_args=[], socket_args=[], cli=cli
    )
    return types.SimpleNamespace(
        group=transaction_group.TransactionGroup(cluster),
        cli=cli,
        clock=clock,
        sleep=sleeper,
        jitter=jitter,
    )


def test_submission_success(submission: types.SimpleNamespace) -> None:
    """Return successful output without sleeping or retrying."""
    assert submission.group.submit_tx_bare("tx.signed") == "hash"
    assert submission.cli.call_count == 1
    expected_timeout = 180
    assert submission.cli.call_args.kwargs["timeout"] == expected_timeout
    submission.sleep.assert_not_called()


def test_exponential_backoff(submission: types.SimpleNamespace) -> None:
    """Increase jittered delays to the cap, including beyond five attempts."""
    rejection = exceptions.CLIError("MempoolTxTooSlow (2s)")
    submission.cli.side_effect = [rejection] * 7 + [submission.cli.return_value]
    assert submission.group.submit_tx_bare("tx.signed", retry_max_delay=5) == "hash"
    assert submission.sleep.call_args_list == [mock.call(d) for d in (2, 4, 5, 5, 5, 5, 5)]
    assert submission.jitter.call_args_list == [mock.call(d / 2, d) for d in (2, 4, 5, 5, 5, 5, 5)]
    assert [c.kwargs["timeout"] for c in submission.cli.call_args_list] == [
        180,
        178,
        174,
        169,
        164,
        159,
        154,
        149,
    ]


def test_retry_budget(submission: types.SimpleNamespace) -> None:
    """Stop rather than sleep beyond the budget, retaining the last rejection."""
    rejection = exceptions.CLIError("MempoolTxTooSlow (last rejection)")
    submission.cli.side_effect = rejection
    with pytest.raises(exceptions.CLIError, match=r"3 attempts.*7s retry budget") as excinfo:
        submission.group.submit_tx_bare("tx.signed", retry_timeout=7)
    assert excinfo.value.__cause__ is rejection
    assert "last rejection" in str(excinfo.value)
    assert submission.sleep.call_args_list == [mock.call(2), mock.call(4)]
    assert submission.clock.now == sum((2, 4))


def test_default_backoff_cap(submission: types.SimpleNamespace) -> None:
    """Stop increasing the delay at the default thirty-second cap."""
    submission.cli.side_effect = [exceptions.CLIError("MempoolTxTooSlow")] * 8 + [
        submission.cli.return_value
    ]
    assert submission.group.submit_tx_bare("tx.signed") == "hash"
    assert submission.sleep.call_args_list == [mock.call(d) for d in (2, 4, 8, 16, 30, 30, 30, 30)]


@pytest.mark.parametrize("cap", [0.5, 30])
def test_lower_jitter_bound(submission: types.SimpleNamespace, cap: float) -> None:
    """Keep equal jitter above zero and respect caps smaller than the initial delay."""
    submission.jitter.side_effect = lambda low, _high: low
    submission.cli.side_effect = [exceptions.CLIError("MempoolTxTooSlow")] * 3 + [
        submission.cli.return_value
    ]
    assert submission.group.submit_tx_bare("tx.signed", retry_max_delay=cap) == "hash"
    assert submission.sleep.call_args_list == [mock.call(min(d, cap) / 2) for d in (2, 4, 8)]


def test_slow_attempt_consumes_budget(submission: types.SimpleNamespace) -> None:
    """Count time inside the CLI and do not launch another attempt after expiry."""

    def reject(*_args: object, **_kwargs: object) -> None:
        submission.clock.now += 7
        msg = "MempoolTxTooSlow"
        raise exceptions.CLIError(msg)

    submission.cli.side_effect = reject
    with pytest.raises(exceptions.CLIError, match="1 attempts"):
        submission.group.submit_tx_bare("tx.signed", retry_timeout=7)
    assert submission.cli.call_count == 1
    submission.sleep.assert_not_called()


def test_oversleep_consumes_budget(submission: types.SimpleNamespace) -> None:
    """Recheck the deadline after waking up late."""
    submission.cli.side_effect = exceptions.CLIError("MempoolTxTooSlow")
    submission.sleep.side_effect = lambda _delay: setattr(submission.clock, "now", 1000)
    with pytest.raises(exceptions.CLIError, match="1 attempts"):
        submission.group.submit_tx_bare("tx.signed")
    assert submission.cli.call_count == 1


@pytest.mark.parametrize(
    "error",
    [exceptions.CLIError("BadInputsUTxO"), subprocess.TimeoutExpired("cardano-cli", 3)],
)
def test_other_errors_propagate(submission: types.SimpleNamespace, error: Exception) -> None:
    """Never retry validation failures or ambiguous transport timeouts."""
    submission.cli.side_effect = error
    with pytest.raises(type(error)) as excinfo:
        submission.group.submit_tx_bare("tx.signed")
    assert excinfo.value is error
    assert submission.cli.call_count == 1
    submission.sleep.assert_not_called()


def test_request_timeout_cap(submission: types.SimpleNamespace) -> None:
    """Preserve the per-invocation timeout cap for larger retry budgets."""
    submission.group.submit_tx_bare("tx.signed", retry_timeout=900)
    expected_timeout = 300
    assert submission.cli.call_args.kwargs["timeout"] == expected_timeout


@pytest.mark.parametrize("setting", ["retry_timeout", "retry_max_delay"])
@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_invalid_settings(submission: types.SimpleNamespace, setting: str, value: float) -> None:
    """Reject invalid retry settings before submitting anything."""
    with pytest.raises(ValueError, match=f"{setting} must be finite and positive"):
        submission.group.submit_tx_bare("tx.signed", **{setting: value})
    submission.cli.assert_not_called()


@pytest.fixture
def real_cli_submission(
    submission: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> types.SimpleNamespace:
    """Exercise the real CLI retry loop with only subprocesses and time replaced."""
    cluster = object.__new__(clusterlib_klass.ClusterLib)
    cluster.command_era = "latest"
    cluster._cli_log = ""
    cluster.genesis = {"protocolParams": {"minFeeB": 1}}
    cluster.magic_args = []
    cluster.socket_args = []
    submission.group = transaction_group.TransactionGroup(cluster)
    submission.cluster = cluster
    submission.popen = mock.Mock()
    monkeypatch.setattr(clusterlib_klass, "time", transaction_group.time)
    monkeypatch.setattr(
        clusterlib_klass,
        "subprocess",
        types.SimpleNamespace(
            Popen=submission.popen,
            PIPE=subprocess.PIPE,
            TimeoutExpired=subprocess.TimeoutExpired,
        ),
    )
    return submission


def _process(clock: types.SimpleNamespace, duration: float, stderr: bytes = b"") -> mock.MagicMock:
    """Simulate a subprocess honoring its communicate timeout and supporting cleanup."""
    process = mock.MagicMock()
    process.__enter__.return_value = process
    process.returncode = 1 if stderr else 0

    def communicate(timeout: float | None = None) -> tuple[bytes, bytes]:
        if not process.kill.called:
            if timeout is not None and duration > timeout:
                clock.now += timeout
                exc = subprocess.TimeoutExpired("cardano-cli", timeout)
                raise exc
            clock.now += duration
        return b'{"txhash": "hash"}', stderr

    process.communicate.side_effect = communicate
    return process


def test_internal_retry_shares_budget(real_cli_submission: types.SimpleNamespace) -> None:
    """Reduce the second subprocess timeout by the first attempt and its backoff."""
    submission = real_cli_submission
    failed = _process(submission.clock, 0.2, b"resource vanished (Broken pipe)")
    slow = _process(submission.clock, 0.8)
    submission.popen.side_effect = [failed, slow]
    with pytest.raises(subprocess.TimeoutExpired):
        submission.group.submit_tx_bare("tx.signed", retry_timeout=1)
    assert failed.communicate.call_args.kwargs["timeout"] == pytest.approx(1)
    assert slow.communicate.call_args_list[0].kwargs["timeout"] == pytest.approx(0.4)
    assert submission.clock.now == pytest.approx(1)
    slow.kill.assert_called_once()
    expected_communicate_calls = 2  # Timed-out attempt, followed by cleanup after killing it.
    assert slow.communicate.call_count == expected_communicate_calls
    assert submission.popen.call_count == len((failed, slow))


def test_internal_backoff_shares_budget(real_cli_submission: types.SimpleNamespace) -> None:
    """Do not sleep past the deadline or launch a retry without time remaining."""
    submission = real_cli_submission
    submission.popen.return_value = _process(submission.clock, 0.9, b"resource exhausted")
    with pytest.raises(subprocess.TimeoutExpired):
        submission.group.submit_tx_bare("tx.signed", retry_timeout=1)
    assert submission.clock.now == pytest.approx(1)
    assert submission.sleep.call_args.args[0] == pytest.approx(0.1)
    assert submission.popen.call_count == 1


def test_internal_retry_success(real_cli_submission: types.SimpleNamespace) -> None:
    """Allow a resource-error retry when both attempts fit within the deadline."""
    submission = real_cli_submission
    failed = _process(submission.clock, 0.1, b"resource vanished")
    successful = _process(submission.clock, 0.1)
    submission.popen.side_effect = [failed, successful]
    assert submission.group.submit_tx_bare("tx.signed", retry_timeout=1) == "hash"
    assert successful.communicate.call_args.kwargs["timeout"] == pytest.approx(0.5)
    assert submission.clock.now == pytest.approx(0.6)


def test_internal_retry_without_timeout(real_cli_submission: types.SimpleNamespace) -> None:
    """Keep unlimited calls working and avoid sleeping after the last failed attempt."""
    submission = real_cli_submission
    processes = [_process(submission.clock, 1, b"resource vanished") for _ in range(3)]
    submission.popen.side_effect = processes
    with pytest.raises(exceptions.CLIError, match="resource vanished"):
        submission.cluster.cli(["query", "tip"])
    assert submission.sleep.call_args_list == [mock.call(0.4), mock.call(0.4)]
    for process in processes:
        process.communicate.assert_called_once_with(timeout=None)


def test_internal_retry_oversleep(real_cli_submission: types.SimpleNamespace) -> None:
    """Check the deadline again if internal retry backoff wakes up late."""
    submission = real_cli_submission
    submission.popen.return_value = _process(submission.clock, 0.1, b"resource vanished")
    submission.sleep.side_effect = lambda _delay: setattr(submission.clock, "now", 2)
    with pytest.raises(subprocess.TimeoutExpired):
        submission.group.submit_tx_bare("tx.signed", retry_timeout=1)
    assert submission.popen.call_count == 1
