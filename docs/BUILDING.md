# Building from source

The source workflow currently targets Windows x64. Use a Python 3.11+ installation, Git, CMake 3.20+, Ninja and Visual Studio 2022 C++ Build Tools. Run native builds from an x64 developer shell. The runtime requires C++23; generated game modules use C11.

```powershell
python scripts/bootstrap.py
python scripts/build_runtime.py
python -m unittest discover -s tests -v
python app/twin_snakes.py --inspect --disc1 'D:\Games\Twin Snakes Disc 1.rvz' --disc2 'D:\Games\Twin Snakes Disc 2.rvz'
python app/twin_snakes.py --prepare --disc1 'D:\Games\Twin Snakes Disc 1.rvz' --disc2 'D:\Games\Twin Snakes Disc 2.rvz'
python app/twin_snakes.py
```

The builder writes private disc-derived files under the chosen data directory. For a development checkout, use `--data .local/player`. Use `--runtime PATH` to select a staged open-source runtime; the default development location is `.local/runtime`.

Setup verifies the extracted boot executable before reusing a disc directory. Running setup again replaces a missing or damaged executable from the verified disc image. The compiled native module is reused only if it matches the SHA-256 recorded at link completion. An older install with an empty completion record rebuilds once when setup is run again. Save files and settings live under the separate `user` directory.

To build the experimental native gameplay module, add `--experimental-rel` to `--prepare` after rebuilding the source runtime. Give the experiment its own `--data` directory. The builder links the verified REL from the selected discs and selects the new build after both discs are prepared. The regular launcher install uses the boot-only module while gameplay and timing tests are pending.

`scripts/bootstrap.py` fetches the pinned upstream source trees. `scripts/build_runtime.py` compiles the recompiler, runner and disc conversion tool, then stages the runtime and the source needed to compile game modules. No retail game files are needed to build the tools.

The MSVC builds of DolRecomp and ModernGekko use a per-process UTF-8 manifest so Windows can pass paths with non-ASCII characters through setup and play. That manifest setting requires Windows 10 version 1903 or later. [Microsoft's UTF-8 code page documentation](https://learn.microsoft.com/en-us/windows/apps/design/globalizing/use-utf8-code-page#set-a-process-code-page-to-utf-8)

The regular build uses the C backend. For a separate LLVM experiment, build the patched DolRecomp source with `DOLRECOMP_ENABLE_LLVM=ON` and point `LLVM_DIR` at LLVM's CMake package. In the Windows test, DolRecomp built against LLVM 19 emitted objects with `DOLRECOMP_LLVM_TARGET=x86_64-w64-windows-gnu`, `--backend=llvm` and `--runtime=recompcore` for linking with llvm-mingw. Use the patched staged SDK and keep the generated module in a private test directory.

The local game build requires CMake, Ninja and a C compiler. `scripts/package_windows.py --tools PATH` can bundle explicit local copies of Python, CMake, Ninja and llvm-mingw with the compiled launcher and runtime. Run it from a Visual Studio developer shell or provide `--vc-runtime-dir PATH` pointing to the x64 `Microsoft.VC143.CRT` folder. The package includes the [application-local Visual C++ runtime files](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170) used by the runner and conversion tools. Supply official tool distributions with their licenses. A clean Windows account test, complete notices and corresponding-source availability remain release checks.

For a local installation test, add `--stage-only` with a new `--version`. If the workspace is synced, pass `--staging-root` pointing to a private, non-synced folder. RecompLauncher can place generated game data beside a portable build. In RecompLauncher, enable developer tools, choose **Add a build**, and select the reported folder containing `TwinSnakes.exe` and `recomplauncher.json`. Check both disc prompts, prepare a fresh data directory, and verify that the display and resolution choices persist through **Play**. Test the same setup in Big Picture before submitting a release. [RecompLauncher developer guide](https://github.com/elripalda/RecompLauncher/blob/main/docs/DEVELOPERS.md#checking-your-file)

RecompLauncher checks the GameCube disc ID before setup. The setup program checks disc order, revision, and the SHA-256 of each normalized disc. The manifest leaves whole-file dump checks to setup so RVZ and GCZ files are compared after conversion.

The display setting `fullscreen=auto` follows the launcher mode at each start. Big Picture uses borderless fullscreen and desktop mode opens a window. Explicit `true` and `false` override that behavior. The separate `resolution=auto` option chooses an integer internal scale from the output area. Existing resolution values such as `640x528` and `2560x1440` still select fixed scales.

The launcher allows one visible game per user across package folders. Setup and headless diagnostics use the lock for their own data directory. Close a running game before opening another package for interactive play.

Enable **Photo Album capture** under the launcher’s advanced video settings before taking pictures with the in-game Digital Camera. For standalone play, set `XFBToTextureEnable = False` under `[Hacks]` in the data folder’s `user/Config/GFX.ini` before starting the game. Take a new photo after enabling the setting.
