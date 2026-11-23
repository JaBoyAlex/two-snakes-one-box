# Compatibility and validation

The Windows prototype reaches the title screen with a native boot module and falls below normal game speed. The local USA revision 0 disc pair has been identified and hashed.

| Area | Evidence |
| --- | --- |
| Public source project | Available on GitHub. Source CI passed on the initial commit. |
| Recompiler/runtime build | DolRecomp, ModernGekko, the disc conversion tool and Windows launcher built locally. |
| Disc identity and revision validation | Both discs: GGSEA4, revision 0; main executables have identical SHA-256. Full normalized-disc hashes recorded in supported-builds.json. |
| Native game module | Local setup extracted both RVZ discs and built one shared native boot module. The main game REL was translated in a separate experiment, with runtime integration outstanding. |
| Title screen / gameplay | Disc 1 reached the title screen using the native DOL and runtime fallback. Gameplay and disc 2 boot remain unverified. |
| Audio / cutscenes / codec | Audio output started. The first play test reported stutter during the slowdown. Audio timing at normal speed remains unverified. |
| Controller | Rebuilt runtime detected an XInput controller and assigned it to port 1 without a config file. In-game response and reconnection still need verification. |
| Save / load / disc transition | Not tested |
| Complete playthrough | Not tested |
| RecompLauncher schema | Passes the official current schema; separate disc inputs and prepare/start entry points. |
| RecompLauncher installed-package test | Private Windows ZIP built with manifest, local compiler tools and MSVC runtime files. Ran its launcher and disc inspection locally. Actual in-launcher installation and a clean Windows test remain pending. |
| Monitor-native fullscreen / higher internal resolution | Runtime settings are wired in the manifest. Output size, effects and performance still need verification. |
| Unlocked frame rate | Planned; no patch enabled |

Do not interpret an instruction translation percentage, a successful host build, a boot screen or a launcher schema check as full game compatibility.
