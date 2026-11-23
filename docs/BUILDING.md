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

`scripts/bootstrap.py` fetches the pinned upstream source trees. `scripts/build_runtime.py` compiles the recompiler, runner and disc conversion tool, then stages the runtime and the source needed to compile game modules. No retail game files are needed to build the tools.

The local game build requires CMake, Ninja and a C compiler. `scripts/package_windows.py --tools PATH` can bundle explicit local copies of Python, CMake, Ninja and llvm-mingw with the compiled launcher/runtime, so setup needs no tool downloads or developer installation. Supply official tool distributions with their licenses. Packaging is not yet a clean-machine installation guarantee; runtime redistributables, complete notices and corresponding-source availability must be reviewed before a public binary release.
