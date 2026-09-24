from __future__ import annotations

import argparse
import asyncio
from types import SimpleNamespace

import pytest

from matic_sdk import macos
from matic_sdk.enrollment import TOKEN_SERVICE_UUID, BleCandidate, EnrollmentError


def candidate(name: str, service: bool = True) -> BleCandidate:
    return BleCandidate(
        "test-uuid", name, (TOKEN_SERVICE_UUID,) if service else (), -40, object()
    )


def test_requires_unambiguous_robot() -> None:
    robots = (candidate("matic-one"), candidate("matic-two"))
    with pytest.raises(EnrollmentError, match="Multiple"):
        macos.choose(robots, None)
    assert macos.choose(robots, "matic-two").name == "matic-two"
    with pytest.raises(EnrollmentError, match="No matching"):
        macos.choose(robots, "matic-three")


def test_name_alone_does_not_prove_pairing_service() -> None:
    with pytest.raises(EnrollmentError, match="No matching"):
        macos.choose((candidate("matic-one", False),), "matic-one")


@pytest.mark.parametrize(
    "message,expected",
    [
        ("BLE is unsupported", "physical Mac"),
        ("BLE is not authorized", "Privacy & Security"),
        ("Bluetooth device is turned off", "Turn Bluetooth on"),
    ],
)
def test_actionable_bluetooth_diagnostics(message, expected) -> None:
    assert expected in macos.diagnostic(RuntimeError(message))


async def test_pair_timeout_bounds_gatt_wait(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(macos.sys, "platform", "darwin")

    async def scan(**kwargs):
        return (candidate("matic-one"),)

    async def enroll(*args, **kwargs):
        await asyncio.Future()

    monkeypatch.setattr(macos, "scan", scan)
    monkeypatch.setattr(macos, "enroll", enroll)
    args = argparse.Namespace(
        command="pair",
        alias="test",
        credential_root=tmp_path,
        scan_timeout=1,
        timeout=0.01,
        name="matic-one",
    )
    with pytest.raises(TimeoutError):
        await macos.run(args)
    assert "timed out" in macos.diagnostic(TimeoutError())


async def test_existing_enrollment_does_not_scan(monkeypatch) -> None:
    monkeypatch.setattr(macos.sys, "platform", "darwin")
    monkeypatch.setattr(
        macos, "CredentialStore", lambda *a, **k: SimpleNamespace(enrolled=True)
    )

    async def unexpected_scan(**kwargs):
        pytest.fail("existing enrollment must not trigger Bluetooth activity")

    monkeypatch.setattr(macos, "scan", unexpected_scan)
    with pytest.raises(EnrollmentError, match="already paired"):
        await macos.run(
            argparse.Namespace(command="pair", alias="test", credential_root=None)
        )
