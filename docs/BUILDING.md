# Building from source

The source workflow currently targets Windows x64. Use a Python 3.11+ installation, Git, CMake 3.20+, Ninja and Visual Studio 2022 C++ Build Tools. Run native builds from an x64 developer shell. The runtime requires C++23; generated game modules use C11.

```powershell
python scripts/bootstrap.py
python scripts/build_runtime.py
cmake -S . -B .local/build/launcher -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build .local/build/launcher
python -m unittest discover -s tests -v
python app/twin_snakes.py --inspect --disc1 'D:\Games\Twin Snakes Disc 1.rvz' --disc2 'D:\Games\Twin Snakes Disc 2.rvz'
python app/twin_snakes.py --prepare --disc1 'D:\Games\Twin Snakes Disc 1.rvz' --disc2 'D:\Games\Twin Snakes Disc 2.rvz'
python app/twin_snakes.py
```

The builder writes private disc-derived files under the chosen data directory. For a development checkout, use `--data .local/player`. Use `--runtime PATH` to select a staged open-source runtime; the default development location is `.local/runtime`.

Setup can reuse extracted disc directories across runner updates when the normalized disc hashes and extractor hash match. It checks each cached boot executable and gameplay module before reuse. Running setup again re-extracts a missing or damaged disc cache from the verified image. The compiled native module is reused only if it matches the SHA-256 recorded at link completion. An older install with an empty completion record rebuilds once when setup is run again. Save files and settings live under the separate `user` directory.

Play checks the setup record, both prepared boot executables and the native module. When a check fails, the launcher keeps the previous setup record as `prepared.needs-repair.json`. In RecompLauncher, close the error and press Play again to reopen Easy Setup. Standalone players can reopen `TwinSnakes.exe` to select the disc images again. Setup can regenerate a damaged completion record using the verified files already in the cache.

Run `TwinSnakes.exe --experimental-vector-routing` to try routing three vector routines through the PowerPC JIT on the verified USA boot profile. The updated runtime precomputes aligned fallback ranges for fixed-address modules. [Replay measurements](PERFORMANCE.md#precomputed-fallback-dispatch) Run `--experimental-cache-loops` to test the separate cache-maintenance ranges. The diagnostic `STATICRECOMP_FALLBACK_RANGES` environment variable takes precedence, followed by a nonempty `StaticRecompFallbackRanges` runtime setting.

To build the experimental native gameplay module, add `--experimental-rel` to `--prepare` after rebuilding the source runtime. Give the experiment its own `--data` directory. The builder links the verified REL from the selected discs and selects the new build after both discs are prepared. The regular launcher install uses the boot-only module while gameplay and timing tests are pending.

`scripts/bootstrap.py` fetches the pinned upstream source trees. `scripts/build_runtime.py` compiles the recompiler, runner and disc conversion tool, then stages the runtime and the source needed to compile game modules. No retail game files are needed to build the tools.

For a fresh native build, you can pass the same short, local `--source PATH` to both scripts. This keeps deeply nested upstream files out of the synced workspace. The source checkout includes the nested Git submodules at their pinned revisions.

The MSVC builds of DolRecomp and ModernGekko use a per-process UTF-8 manifest so Windows can pass paths with non-ASCII characters through setup and play. That manifest setting requires Windows 10 version 1903 or later. [Microsoft's UTF-8 code page documentation](https://learn.microsoft.com/en-us/windows/apps/design/globalizing/use-utf8-code-page#set-a-process-code-page-to-utf-8)

The regular build uses the C backend. For a separate LLVM experiment, build the patched DolRecomp source with `DOLRECOMP_ENABLE_LLVM=ON` and point `LLVM_DIR` at LLVM's CMake package. In the Windows test, DolRecomp built against LLVM 19 emitted objects with `DOLRECOMP_LLVM_TARGET=x86_64-w64-windows-gnu`, `--backend=llvm` and `--runtime=recompcore` for linking with llvm-mingw. Use the patched staged SDK and keep the generated module in a private test directory.

The portable package bundles Python, CMake, Ninja and llvm-mingw for setup. Run `python scripts/bootstrap.py --windows-tools PATH` with a new local directory, then pass the same directory as `--tools PATH` to `scripts/package_windows.py`. Bootstrap verifies the official archives and Ninja's license against the SHA-256 pins in `dependencies.lock.json` before it publishes the finished tool directory. If you supply another tool directory for development, include each distribution's license, with Ninja's `COPYING` beside `ninja.exe`.

Run the packager from a Visual Studio developer shell or provide `--vc-runtime-dir PATH` pointing to the x64 `Microsoft.VC143.CRT` folder. The package includes the application-local Visual C++ runtime files used by the runner and conversion tools. A clean Windows account test, complete runtime notices and corresponding-source availability remain release checks. [Microsoft Visual C++ redistribution documentation](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170)

Use the runtime staging directory from `build_runtime.py` as the package input. The packager checks it before copying and checks the assembled package before writing its inventory. Player directories, generated runtime code, disc and save files, and diagnostic output cause packaging to stop.

The portable package includes CMake's command-line help and license notices. Its generated HTML manual is omitted. The bundled compiler retains the x64 Windows target and drops the separate ARM64, ARMv7 and x86 target directories.

The Windows package includes the built-in game settings matched by `supported-builds.json`. Dolphin Qt themes and the Qt debugger's symbol database are omitted. Shared runtime data, including the GameCube and on-screen fonts and their notices, are included.

For a local installation test, add `--stage-only` with a new `--version`. If the workspace is synced, pass `--staging-root` pointing to a private, non-synced folder. RecompLauncher can place generated game data beside a portable build. In beta 68, open Settings, choose **Bring Your Games**, then **Pick a Folder**, and select the reported folder containing `TwinSnakes.exe` and `recomplauncher.json`. Choose **Go Through Them** and **Add Without Updates**. The **Add a build** screen in developer mode is also available. Check both disc prompts, prepare a fresh data directory, and verify that the display and resolution choices persist through **Play**. Test the same setup in Big Picture before submitting a release. [RecompLauncher developer guide](https://github.com/elripalda/RecompLauncher/blob/main/docs/DEVELOPERS.md#checking-your-file)

RecompLauncher checks the GameCube disc ID before setup. The setup program checks disc order, revision, and the SHA-256 of each normalized disc. The manifest leaves whole-file dump checks to setup so RVZ and GCZ files are compared after conversion.

The Windows dev.21 runtime reads the Direct3D 11 choice from RecompLauncher’s Game Settings. For a standalone development build, the same choice is `backend = D3D` in `user/config.ini`. The first run with a new backend builds its shader cache.

The display setting `fullscreen=auto` follows the launcher mode at each start. Big Picture uses borderless fullscreen and desktop mode opens a window. Explicit `true` and `false` override that behavior. The separate `resolution=auto` option chooses an integer internal scale from the output area. Existing resolution values such as `640x528` and `2560x1440` still select fixed scales.

The launcher allows one visible game per user across package folders. Setup and headless diagnostics use the lock for their own data directory. Close a running game before opening another package for interactive play.

New Twin Snakes save states record the disc mounted at save time. Load a state with that disc mounted. For a local Disc 2 test, run `TwinSnakes.exe --boot-disc 2`. Older states lack disc metadata and require selecting the matching disc yourself. In-game memory-card saves still trigger the story’s automatic disc change.

The runtime’s debug automation reports `load_state` as processed after the CPU completes the load. Wait for that result before measuring or sending dependent input. A rejected load appears in the failed command directory and `last_error`.

For timing comparisons with a source-built runner, `command=pad_fields` holds controller input for the requested number of emulated video fields. Supply `port`, `fields` and any controls you want to hold. The hold starts at the next field boundary, and the command completes after the last field. `pad_frames` remains available for scripts timed to newly drawn frames.

The automation status reports `guest_ticks` and `throttle_clock_hz` from emulated video fields. The throttle clock is the active limit in guest cycles per host second. A value of zero after fields have advanced means the limiter is disabled. A save-state load restores the guest clock, so `guest_ticks` can decrease across a load. For comparable replays, start from the same checkpoint and align the benchmark samples by `guest_ticks`. The benchmark keeps host time, new draws and presentation callbacks in each sample, and includes the throttle rate when the runner reports it.

Dev.37 enables **Codec and Photo Album accuracy** by default for standalone and RecompLauncher profiles without a saved choice. If you previously turned it off, turn it back on under the launcher's advanced video settings and restart. For standalone profiles with an explicit override, the matching value is `XFBToTextureEnable = False` under `[Hacks]` in the data folder’s `user/Config/GFX.ini`. On dev.35 and earlier, the option is called **Photo Album capture**. Take a new photo after enabling the setting if a previous capture was incorrect.
