"""Experimental macOS enrollment helper. Never sends movement commands."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from matic_sdk.credentials import CredentialStore
from matic_sdk.enrollment import BleCandidate, EnrollmentError, enroll, scan


def choose(candidates: tuple[BleCandidate, ...], name: str | None) -> BleCandidate:
    matches = [
        c
        for c in candidates
        if c.exposes_token_service and (name is None or c.name == name)
    ]
    if not matches:
        raise EnrollmentError(
            "No matching Matic is advertising its token service. In the Matic app, "
            "open Settings > Connectivity > Add another user, enable pairing mode, "
            "and keep the Mac close to the robot."
        )
    if len(matches) != 1:
        raise EnrollmentError(
            "Multiple Matics found; use --name with the exact scan name."
        )
    return matches[0]


def diagnostic(error: Exception) -> str:
    message = str(error)
    if "unsupported" in message.lower():
        return (
            "CoreBluetooth reports no supported Bluetooth controller in this process. "
            "Run the helper in Terminal on the physical Mac. A VM or restricted "
            "execution environment may not expose the controller."
        )
    if "authorized" in message.lower():
        return (
            "Bluetooth access is denied. Enable access for the requesting app in "
            "System Settings > Privacy & Security > Bluetooth, then restart it."
        )
    if "turned off" in message.lower():
        return "Turn Bluetooth on in System Settings, then retry."
    if isinstance(error, TimeoutError):
        return "Pairing timed out. Re-enable pairing mode on Matic and retry."
    return message or type(error).__name__


async def run(args: argparse.Namespace) -> None:
    if sys.platform != "darwin":
        raise EnrollmentError(
            "This helper targets macOS; use the upstream matic CLI on Linux."
        )
    if args.command == "pair":
        store = CredentialStore(args.alias, root=args.credential_root)
        if store.enrolled:
            raise EnrollmentError(
                "This alias is already paired; existing credentials were preserved."
            )
    candidates = await scan(timeout=args.scan_timeout)
    if args.command in ("doctor", "scan"):
        print("CoreBluetooth scan completed successfully.")
        for c in candidates:
            print(
                f"{c.name or '(unnamed)'}  signal={c.rssi} dBm  "
                f"token_service={c.exposes_token_service}"
            )
        if not candidates:
            print(
                "No Matic advertisements found. "
                "Enable Add another user pairing mode to discover it."
            )
        return
    candidate = choose(candidates, args.name)
    print(
        f"Connecting to {candidate.name}. "
        "Complete the macOS Bluetooth prompt with the code on Matic.",
        flush=True,
    )
    # Includes protected GATT reads/writes, which can wait for a macOS pairing dialog.
    async with asyncio.timeout(args.timeout):
        result = await enroll(
            store,
            candidate=candidate,
            timeout=args.timeout,
        )
    print(
        f"Paired as {result.device_alias!r}. "
        f"Private credentials saved to {result.token_path}"
    )
    print(
        "Enrollment succeeded; authenticated Wi-Fi access still needs "
        "a verified TLS fingerprint."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("doctor", "scan", "pair"))
    parser.add_argument(
        "--name",
        help="Exact robot name from scan; required if multiple robots advertise.",
    )
    parser.add_argument("--alias", default="my-matic")
    parser.add_argument("--credential-root", type=Path, default=None)
    parser.add_argument("--scan-timeout", type=float, default=10)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    if args.scan_timeout <= 0 or args.timeout <= 0:
        parser.error("timeouts must be positive")
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except Exception as error:
        print(diagnostic(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
