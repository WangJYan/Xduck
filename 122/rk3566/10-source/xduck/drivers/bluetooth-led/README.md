# Bluetooth LED display on device 122

Imported from the running 122 LED manager on 2026-11-13. The independent service owns the BLE connection, serializes GIF uploads, reconnects, and replays the persistent selection. It does not load voice recognition or dialogue code. Device-specific address is in `led_transport.py`.

Runtime: Python with bleak and dbus-fast. State: `/var/lib/xiaolong-led`; socket: `/run/xiaolong-led/control.sock`. The 122 unit uses the already provisioned Python environment; no speech models are loaded. Source and initial eyes GIF ship in the signed release under `addons/bluetooth-led/`.

`show_gif.py --status` reads connection status. Run `python -m unittest test_led_manager.py` with this directory on PYTHONPATH to check reconnect and serialization without hardware.
