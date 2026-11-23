# Performance and runtime evaluation

The first Windows run reached the title screen on an Intel Core i5-11400 and RTX 3060 Ti. The user reported about 17–18 FPS and drops to 5 FPS with audible stutter. The screen counter measures rendered frames. Runtime speed measures advancement of the GameCube clock, with `1.0` representing normal speed.

The hybrid build uses a native C module for `main.dol` and falls back for other guest code. The loader plus game module account for about 97,000 and 1,135,000 PowerPC instructions, respectively, before reachability analysis. The engine module, `mgso.rel`, needs a runtime relocation mapping so compiled code executes at the addresses the game actually loaded. Translation alone establishes neither coverage nor correct runtime behavior.

A diagnostic comparison with video and audio output disabled measured a `1.00` median speed over 13 JIT samples and a `0.16` median speed over 9 hybrid C samples. This isolates a significant slowdown to the CPU path for early boot on this machine. The comparison ran while a separate test window was open, so the exact figures need an idle-machine repeat. JIT-only mode is a diagnostic reference for original game timing.

```powershell
python scripts/benchmark_boot.py --data .local/player --runner .local/runtime/moderngekko-run.exe
```

Use an idle machine and the same disc, graphics backend and scene for comparisons. The headless run isolates the CPU path. `--windowed` adds normal Vulkan and audio output. For gameplay, measure frame pacing and compare input response, audio timing and cutscene timing with the retail disc under Dolphin. Generated outputs, logs and capture files stay local.

## Tool comparisons

| Project | What to test or reuse |
| --- | --- |
| [Skies of Arcadia Legends Recompiled](https://github.com/ogdanimal/SkiesOfArcadiaLegends-Recomp/blob/main/BUILDING.md) | DolRecomp's LLVM path, per-target CPU selection and profile-guided optimization. Establish a correct Windows x64 baseline before using profiles from representative gameplay. |
| [Medal of Honor Frontline GameCube Recomp](https://github.com/ant0-blase/MOHFrontline-GC-RECOMP) | The runtime verifies loaded guest bytes before choosing native code for multiple executable images. Twin Snakes needs a related check for its relocatable module, whose addresses may differ by session. |
| [GekkoAOT](https://github.com/ant0-blase/GekkoAOT) | An alternate runtime with direct RVZ input and REL discovery. The v0.0.9 Windows tool read the USA Disc 1 RVZ and found two executables. This establishes disc inspection only. |
| [Twin Snakes Native Port](https://github.com/alphanu1/msg-twinsnakes-recomp) and its [Switch prototype](https://github.com/ramonDias07/MGSTTS-nx) | Public PAL analysis and runtime behavior are starting points for comparisons. Validate every code layout and timing assumption independently on the USA revision. |

Once normal-speed play is reliable, compare the original rendering cadence with a render loop that runs independently of the original simulation tick. Keep movie cadence and audio timing intact. NVIDIA's [Streamline integration guide](https://developer.nvidia.com/rtx/streamline/get-started) describes the timing markers for Reflex and the scene data needed for DLSS reconstruction. Revisit GPU features after those inputs can be measured and validated.
