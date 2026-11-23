# Compatibility and validation

Status: development tooling bring-up. The local USA revision 0 disc pair has been identified and hashed; gameplay is untested.

| Area | Evidence |
| --- | --- |
| Public source project | Being prepared |
| Recompiler/runtime build | Pending |
| Disc identity and revision validation | Both discs: GGSEA4, revision 0; main executables have identical SHA-256. Full normalized-disc hashes recorded in supported-builds.json. |
| Native game module | Not built |
| Title screen / gameplay | Not tested |
| Audio / cutscenes / codec | Not tested |
| Save / load / disc transition | Not tested |
| Complete playthrough | Not tested |
| RecompLauncher schema | Passes the official current schema; separate disc inputs and prepare/start entry points. |
| RecompLauncher installed-package test | Not tested |
| Monitor-native fullscreen / higher internal resolution | Planned |
| Unlocked frame rate | Planned; no patch enabled |

Do not interpret an instruction translation percentage, a successful host build, a boot screen or a launcher schema check as full game compatibility.
