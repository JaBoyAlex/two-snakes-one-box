# Two Snakes, One Box

A work-in-progress native recompilation project for **Metal Gear Solid: The Twin Snakes** on GameCube, with local-disc setup and RecompLauncher integration.

**Development status.** The Windows prototype uses a locally compiled native boot module and JIT fallback for the main gameplay module. It includes the early save-state rendering fix, the faster fallback dispatcher, in-session controller port switching and a Windows focus-loss fix. Codec and Photo Album accuracy is on by default. The regular launcher uses shared CPU and video threads. RecompLauncher beta 68 prepared both discs through Easy Setup with an earlier portable build. A private update using the beta 68 installer preserved prepared data, settings and saves. A complete playthrough and a clean Windows account install remain release gates.

The dev.21 Windows build adds Direct3D 11 under **Game Settings → Graphics backend**. Its first launch may spend time compiling shaders.

Players will provide both **USA revision 0** discs matching `supported-builds.json`. Commercial game data and generated game code are never included in this repository or release downloads.

<a href="https://recomplauncher.com"><picture><source media="(prefers-color-scheme: dark)" srcset="https://recomplauncher.com/assets/press/launcher/badge-light.svg"><img alt="Get it on RecompLauncher" src="https://recomplauncher.com/assets/press/launcher/badge-dark.svg" height="48"></picture></a>

## Intended player experience

1. Install the Windows package from GitHub Releases or RecompLauncher once a tested build is available.
2. Select **Disc 1** and **Disc 2** separately. ISO, RVZ and GCZ are the target formats.
3. Setup validates the disc pair and recompiles the game locally.
4. Press Play. The same `TwinSnakes.exe` handles setup and playing; settings, builds and saves live in one movable data folder.

To import a local build in RecompLauncher beta 68, open Settings and choose **Bring Your Games**, **Pick a Folder**, **Go Through Them**, then **Add Without Updates**. Catalog availability follows the release gates.

## Approach

[DolRecomp](https://github.com/ExpansionPak/DolRecomp) translates the PowerPC executable to C. A normal host compiler builds the native game module. [ModernGekko](https://github.com/ExpansionPak/ModernGekko) provides the Dolphin-derived graphics, audio, input and hardware runtime. Exact dependency commits are in `dependencies.lock.json`.

This is a recompilation with a hardware compatibility runtime. Native code generation alone does not establish gameplay compatibility, increased performance or accurate timing. Interpreter fallback, if used during diagnosis, must be reported separately from native execution.

## Development

See [BUILDING.md](docs/BUILDING.md) for the source workflow, [STATUS.md](docs/STATUS.md) for measured results and [ROADMAP.md](docs/ROADMAP.md) for release gates.

Standalone and RecompLauncher launches use the same controller setup. The Windows runtime automatically maps the first recognized SDL gamepad to port 1, uses a saved GameCube controller profile if one exists, and falls back to the keyboard when no gamepad is available. Physical XInput buttons and automatic reassignment after reconnect have been verified on Windows. Other controller types still need hardware testing.

On Windows dev.34 and later, press **F2** or choose **File → Controller Port 1 / 4** to move the current mapping between ports during play. The shortcut needs a standard emulated GameCube controller on port 1 and an available port 4. Each new session starts with the configured port assignments.

Windows x64 is the first target. Linux and macOS packaging will follow verified builds on those platforms.

## Resolution and frame rate

The development build offers higher internal render scales and borderless fullscreen at the monitor's desktop resolution. The display tests still need broader monitor, DPI, HUD and effects coverage. Uncapped rendering follows baseline stability and must preserve movement speed, animation, physics, audio and cutscene timing. NVIDIA Reflex, DLSS and DLAA follow the renderer work. [Performance measurements and tool comparisons](docs/PERFORMANCE.md)

## Files and saves

`--data PATH` moves all generated content, saves, settings and logs together. RecompLauncher's `RECOMPLAUNCHER_DATA` is honored. Standalone installs with `portable.txt` use `recompdata` beside the program; otherwise the normal per-user application-data directory is used. Never upload that data directory when reporting an issue.

This is an unofficial project, unaffiliated with Konami, Silicon Knights or Nintendo. Names identify the original game. See [THIRD_PARTY.md](THIRD_PARTY.md) for dependency licensing.
