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

Setup places each disc in its build directory after extraction succeeds and verifies its executable. It also records a successful native link before reusing the compiled module. Setup can retry an interrupted extraction or link from the same disc pair.

To build the experimental native gameplay module, add `--experimental-rel` to `--prepare` after rebuilding the source runtime. Give the experiment its own `--data` directory. The builder links the verified REL from the selected discs and selects the new build after both discs are prepared. The regular launcher install uses the boot-only module while gameplay and timing tests are pending.

`scripts/bootstrap.py` fetches the pinned upstream source trees. `scripts/build_runtime.py` compiles the recompiler, runner and disc conversion tool, then stages the runtime and the source needed to compile game modules. No retail game files are needed to build the tools.

The regular build uses the C backend. For a separate LLVM experiment, build the patched DolRecomp source with `DOLRECOMP_ENABLE_LLVM=ON` and point `LLVM_DIR` at LLVM's CMake package. In the Windows test, DolRecomp built against LLVM 19 emitted objects with `DOLRECOMP_LLVM_TARGET=x86_64-w64-windows-gnu`, `--backend=llvm` and `--runtime=recompcore` for linking with llvm-mingw. Use the patched staged SDK and keep the generated module in a private test directory.

The local game build requires CMake, Ninja and a C compiler. `scripts/package_windows.py --tools PATH` can bundle explicit local copies of Python, CMake, Ninja and llvm-mingw with the compiled launcher and runtime. Run it from a Visual Studio developer shell or provide `--vc-runtime-dir PATH` pointing to the x64 `Microsoft.VC143.CRT` folder. The package includes the [application-local Visual C++ runtime files](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170) used by the runner and conversion tools. Supply official tool distributions with their licenses. A clean Windows account test, complete notices and corresponding-source availability remain release checks.

For a local installation test, add `--stage-only` with a new `--version`. If the workspace is synced, pass `--staging-root` pointing to a private, non-synced folder. RecompLauncher can place generated game data beside a portable build. In RecompLauncher, enable developer tools, choose **Add a build**, and select the reported folder containing `TwinSnakes.exe` and `recomplauncher.json`. Check both disc prompts, prepare a fresh data directory, and verify that the display and resolution choices persist through **Play**. Test the same setup in Big Picture before submitting a release. [RecompLauncher developer guide](https://github.com/elripalda/RecompLauncher/blob/main/docs/DEVELOPERS.md#checking-your-file)
