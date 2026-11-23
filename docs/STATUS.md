# Compatibility and validation

The Windows prototype reaches the title screen with a native boot module. The USA revision 0 idle fix restored normal speed in the early-boot benchmark. The local disc pair has been identified and hashed.

| Area | Evidence |
| --- | --- |
| Public source project | Available on GitHub with source CI. |
| Recompiler/runtime build | DolRecomp, ModernGekko, the disc conversion tool and Windows launcher built locally. |
| Disc identity and revision validation | Both discs: GGSEA4, revision 0; main executables have identical SHA-256. Full normalized-disc hashes recorded in supported-builds.json. |
| Native game module | Local setup built one shared native boot module. Both discs share the same main REL. The reconstructed REL executable bytes matched seven local checkpoints and fresh boots of both discs. A local runner executed one verified REL chunk natively and refused the same chunk with an incorrect hash. Source builds can generate the combined input with `--experimental-rel`. The full native REL build and gameplay comparison remain pending. |
| Boot / gameplay | Disc 1 reached the main menu at about 60 FPS with the idle fix. Disc 2 advanced at normal speed in a headless boot test. Disc 1 entered gameplay, with a pre-fix live capture ranging from 15.8 to 27.1 FPS. After the x64 fallback memory fix, two gameplay checkpoints reached 65–67% of normal speed in headless replays. The main REL still uses JIT fallback. |
| Audio / cutscenes / codec | The updated main menu had clear audio. The tester reported choppy audio during slow cutscenes and gameplay. Matched save-state replays reproduced the CPU slowdown with audio output disabled. The later cutscene checkpoint runs at full speed in headless replays with the x64 fallback memory fix. Audible playback, codec conversations and later scenes still need verification. |
| Controller | The fixed Windows runtime automatically assigns a physical XInput controller to port 1. The trace captured Start, A, B and D-pad presses, and the tester confirmed an in-game response. A later Windows test showed the game falling back to the keyboard on disconnect and reassigning the controller to port 1 on reconnect without a restart. Other controller types still need hardware testing. |
| Save / load / disc transition | Local save-state replay works. In-game memory-card save/load and the disc transition still need testing. |
| Complete playthrough | Not tested |
| RecompLauncher schema | Passes the official current schema; separate disc inputs and prepare/start entry points. |
| RecompLauncher installed-package test | The Windows launcher completed fresh setup and reported progress using bundled tools with a system-only `PATH`. A repeat reused the build. The same launcher booted the prepared game headlessly and exited normally. In-launcher installation and testing on a clean Windows account remain pending. |
| Monitor-native fullscreen / higher internal resolution | Runtime settings are wired in the manifest. Output size, effects and performance still need verification. |
| Unlocked frame rate | Planned; no patch enabled |

Do not interpret an instruction translation percentage, a successful host build, a boot screen or a launcher schema check as full game compatibility.
