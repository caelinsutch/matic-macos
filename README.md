# Matic macOS adapter

Experimental macOS Bluetooth enrollment for the [Unofficial Matic SDK](https://github.com/Burgess-Software/unofficial-matic-sdk). This repository preserves the upstream SDK and MIT license, and adds a macOS helper and Terminal launcher. It is not affiliated with Matic Robots.

## Status

Software tests cover platform-specific connection options, token exchange, device selection, private credential storage, and timeout handling. **Real Matic pairing on macOS has not yet been verified.** The development execution environment reports CoreBluetooth `unsupported`; a scan must be tried from Terminal on the physical Mac. Passing simulated tests is not evidence of successful hardware pairing.

## Why this can work

The upstream SDK uses Bleak but blocks non-Linux platforms. Bleak already implements a CoreBluetooth backend. On macOS, accessing a protected GATT characteristic triggers the system pairing prompt; explicit BlueZ pairing is omitted. The robot's token protocol is unchanged. The helper limits the complete enrollment exchange to 180 seconds and refuses ambiguous device selection.

References: [Bleak macOS backend](https://bleak.readthedocs.io/en/latest/backends/macos.html), [Matic smart-home setup](https://support.maticrobots.com/how-to-connect-matic-to-home-assistant).

## Install and diagnose

Requires a physical Mac with Bluetooth, Python 3.11+, and a nearby Matic you own. Use **Terminal on that Mac**, rather than a remote shell or a VM without Bluetooth passthrough.

```sh
cd ~/Projects/matic-macos
bash scripts/setup-macos.sh
.venv/bin/matic-macos doctor
```

The setup script installs into this repository's `.venv`. It looks for Python 3.11+ on PATH, then the bundled Codex Python runtime if present. Override with `MATIC_PYTHON=/absolute/path/to/python3`. It does not install system packages.

Grant Bluetooth permission to the application macOS identifies when prompted. If access is denied, use System Settings → Privacy & Security → Bluetooth, then restart the requesting application.

## Pair

1. In the Matic app, open **Settings → Connectivity → Add another user** and enable pairing mode. This is the SDK enrollment flow, distinct from **Connect to Smart Home App**.
2. Keep the Mac near Matic and run:

   ```sh
   .venv/bin/matic-macos scan
   .venv/bin/matic-macos pair --name matic-YOUR-ROBOT --alias my-matic
   ```

   Use the exact name printed by `scan`. With one advertising robot, `--name` may be omitted. With multiple robots it is required.
3. Complete the macOS pairing prompt using the six-digit code displayed on Matic.

Alternatively, double-click **Pair Matic.command** in Finder. It sets up the environment if needed, waits for you to enable pairing mode, and runs the same helper. If macOS prevents opening it, use the Terminal commands above; no security setting changes are needed.

The helper only scans and enrolls. It does not move, clean, dock, or change schedules. Credentials are stored by the upstream SDK in `~/.local/share/matic-sdk/`, using owner-only directories and files. An existing enrollment is never overwritten. Never commit that directory or share a token.

## Verify authenticated network access

Enrollment success proves the Bluetooth token exchange, not authenticated Wi-Fi control. Follow the upstream identity and TLS verification steps before using a token:

```sh
.venv/bin/matic probe --host ROBOT_HOSTNAME --insecure-read-only
.venv/bin/matic tls fingerprint --host ROBOT_HOSTNAME
```

Compare the reported robot serial with the physical label or trusted app information. Record the fingerprint only after verifying the device. Then:

```sh
export MATIC_DEVICE_ALIAS=my-matic
export MATIC_HOST=ROBOT_HOSTNAME
export MATIC_CERT_SHA256=VERIFIED_SHA256_FINGERPRINT
.venv/bin/matic status
```

`probe --insecure-read-only` sends no enrolled credential. Do not bypass certificate verification for authenticated commands. See [upstream usage](UPSTREAM_README.md) for SDK functionality beyond enrollment.

## Troubleshooting

- **BLE is unsupported:** this process cannot see a supported controller. Compare `system_profiler SPBluetoothDataType` from your own Terminal with the execution environment. This is distinct from a permission denial or Bluetooth being turned off.
- **Access denied:** enable the requesting application's Bluetooth permission and restart it.
- **No matching Matic:** re-enable Add another user pairing mode, move the Mac closer, and scan again.
- **Multiple Matics:** select an exact advertised name with `--name`.
- **Timed out:** re-enable pairing mode and complete the system prompt promptly. A valid token must be returned before enrollment is considered successful.

## Development

```sh
.venv/bin/python -m pip install pytest pytest-asyncio ruff mypy build '.[all]'
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy src/matic_sdk
```

CI runs the offline suite on Linux and macOS. It does not exercise real Bluetooth hardware. Upstream's PyPI publishing workflow is removed from this fork.
