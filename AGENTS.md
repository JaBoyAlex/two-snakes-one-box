# Twin Snakes Recomp development

- The user's objective is a stable native recomp with easy RecompLauncher installation, followed by monitor-native output and a validated unlocked-framerate mode.
- Keep retail disc data, extracted assets, saves, generated game code, game modules and raw diagnostic logs private in ignored storage. Publish source/tooling only.
- Pin open-source dependencies. Preserve their notices and corresponding-source obligations when packaging a runtime.
- Report observed compatibility. Separate host compilation, title-screen boot, native execution, interpreter fallback and complete gameplay validation.
- Keep original gameplay timing until baseline compatibility is established. A speed-limit change is not an unlocked-frame-rate implementation.
- Update docs/STATUS.md with measured results and remaining blockers. Do not publish a playable or stable release until the applicable gates in docs/ROADMAP.md have been verified.
- Source checks: `python -m unittest discover -s tests -v`; `python scripts/check_manifest.py` with jsonschema installed. Native build instructions are in docs/BUILDING.md.
