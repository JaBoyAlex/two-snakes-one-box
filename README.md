# Twin Snakes Recomp

A work-in-progress native recompilation project for **Metal Gear Solid: The Twin Snakes** on GameCube, with local-disc setup and RecompLauncher integration.

**Development status: the Windows prototype reaches the title screen and currently runs below normal speed.**

Players will provide both **USA revision 0** discs matching `supported-builds.json`. Commercial game data and generated game code are never included in this repository or release downloads.

<a href="https://recomplauncher.com"><picture><source media="(prefers-color-scheme: dark)" srcset="https://recomplauncher.com/assets/press/launcher/badge-light.svg"><img alt="Get it on RecompLauncher" src="https://recomplauncher.com/assets/press/launcher/badge-dark.svg" height="48"></picture></a>

## Intended player experience

1. Install the Windows package from GitHub Releases or RecompLauncher once a tested build is available.
2. Select **Disc 1** and **Disc 2** separately. ISO, RVZ and GCZ are the target formats.
3. Setup validates the disc pair and recompiles the game locally.
4. Press Play. The same `TwinSnakes.exe` handles setup and playing; settings, builds and saves live in one movable data folder.

RecompLauncher metadata in this repository is an integration under development. It is not a claim of catalog listing, approved launcher support, or an available playable release.

## Approach

[DolRecomp](https://github.com/ExpansionPak/DolRecomp) translates the PowerPC executable to C. A normal host compiler builds the native game module. [ModernGekko](https://github.com/ExpansionPak/ModernGekko) provides the Dolphin-derived graphics, audio, input and hardware runtime. Exact dependency commits are in `dependencies.lock.json`.

This is a recompilation with a hardware compatibility runtime. Native code generation alone does not establish gameplay compatibility, increased performance or accurate timing. Interpreter fallback, if used during diagnosis, must be reported separately from native execution.

## Development

See [BUILDING.md](docs/BUILDING.md) for the source workflow, [STATUS.md](docs/STATUS.md) for measured results and [ROADMAP.md](docs/ROADMAP.md) for release gates.

The Windows prototype automatically maps the first recognized SDL gamepad to port 1 when there is no custom GameCube controller profile. There is a keyboard fallback. Physical play and reconnect still need verification.

Windows x64 is the first target. Linux and macOS packaging will follow verified builds on those platforms.

## Resolution and frame rate

The first compatibility target preserves the game's original timing and aspect ratio. Higher internal rendering resolutions and fullscreen output at the monitor's desktop resolution are planned. Uncapped rendering is a later update that must preserve movement speed, animation, physics, audio and cutscene timing. NVIDIA Reflex, DLSS and DLAA are optional experiments after baseline play is stable. See [PERFORMANCE.md](docs/PERFORMANCE.md) for the current measurements and tool comparisons.

## Files and saves

`--data PATH` moves all generated content, saves, settings and logs together. RecompLauncher's `RECOMPLAUNCHER_DATA` is honored. Standalone installs with `portable.txt` use `recompdata` beside the program; otherwise the normal per-user application-data directory is used. Never upload that data directory when reporting an issue.

This is an unofficial project, unaffiliated with Konami, Silicon Knights or Nintendo. Names identify the original game. See [THIRD_PARTY.md](THIRD_PARTY.md) for dependency licensing.
