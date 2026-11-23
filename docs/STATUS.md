# Compatibility and validation

The Windows prototype reaches the title screen with a native boot module. The USA revision 0 idle fix restored normal speed in the early-boot benchmark. The local disc pair has been identified and hashed.

| Area | Evidence |
| --- | --- |
| Public source project | Available on GitHub with source CI. |
| Recompiler/runtime build | DolRecomp, ModernGekko, the disc conversion tool and Windows launcher built locally. |
| Disc identity and revision validation | Both discs: GGSEA4, revision 0; main executables have identical SHA-256. Full normalized-disc hashes recorded in supported-builds.json. |
| Native game module | Local setup extracted both RVZ discs and built one shared native boot module. The main game REL was translated in a separate experiment, with runtime integration outstanding. |
| Boot / gameplay | Disc 1 reached the main menu at about 60 FPS with the idle fix. Disc 2 advanced at normal speed in a headless boot test. Gameplay and the disc transition still need verification. |
| Audio / cutscenes / codec | The updated main menu had clear audio. Frame drops and audio stutter still occur during a cutscene. Codec conversations and gameplay audio still need verification. |
| Controller | The initial SDL mapping detected the controller but discarded presses because INI values were converted to booleans. The fixed Windows runtime automatically mapped a physical XInput controller to port 1 with a fresh profile. The trace captured Start, A, B and D-pad presses, and the tester confirmed an in-game response. Reconnect and other controller types still need hardware testing. |
| Save / load / disc transition | Not tested |
| Complete playthrough | Not tested |
| RecompLauncher schema | Passes the official current schema; separate disc inputs and prepare/start entry points. |
| RecompLauncher installed-package test | Private Windows ZIP built with manifest, local compiler tools and MSVC runtime files. Ran its launcher and disc inspection locally. Actual in-launcher installation and a clean Windows test remain pending. |
| Monitor-native fullscreen / higher internal resolution | Runtime settings are wired in the manifest. Output size, effects and performance still need verification. |
| Unlocked frame rate | Planned; no patch enabled |

Do not interpret an instruction translation percentage, a successful host build, a boot screen or a launcher schema check as full game compatibility.
