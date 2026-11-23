# Performance and runtime evaluation

The first Windows run reached the title screen on an Intel Core i5-11400 and RTX 3060 Ti. The user reported about 17–18 FPS and drops to 5 FPS with audible stutter. The screen counter measures rendered frames. Runtime speed measures advancement of the GameCube clock, with `1.0` representing normal speed.

The hybrid build uses a native C module for `main.dol` and falls back for other guest code. The loader plus game module account for about 97,000 and 1,135,000 PowerPC instructions, respectively, before reachability analysis. The engine module, `mgso.rel`, needs a runtime relocation mapping so compiled code executes at the addresses the game actually loaded. Translation alone establishes neither coverage nor correct runtime behavior.

A diagnostic comparison with video and audio output disabled measured a `1.00` median speed over 13 JIT samples and a `0.16` median speed over 9 hybrid C samples. This isolates a significant slowdown to the CPU path for early boot on this machine. The comparison ran while a separate test window was open, so the exact figures need an idle-machine repeat. JIT-only mode is a diagnostic reference for original game timing.

With unused mod callbacks removed, the C module measured `0.34` median speed over 15 samples and `0.33` over 11 samples on repeat. The repeat exited cleanly with a longer shutdown timeout. An experimental LLVM 19 Windows module with the same runtime measured `0.086` over 15 samples and stopped with Windows status `0xC0000409`. The LLVM candidate is excluded from the current build.

Dispatch sampling showed that the GameCube scheduler dominated native dispatch while the dedicated idle thread repeatedly yielded. For USA revision 0, the runtime now calls its existing idle handler after that thread returns from `OSYieldThread`. This advances to the next scheduled hardware event using the original clock. The headless boot comparison measured `0.307` median speed over 23 samples before the idle fix and `0.999` over 20 samples with it, with normal shutdown on both runs. The setting is limited to the supported revision. Both discs share the same DOL.

The staged runtime ran the Disc 1 startup logos and opening video with Vulkan and Cubeb audio. It measured `1.000` median speed, `59.932` video updates per second and `29.984` rendered FPS across 46 samples. Individual clock-speed samples ranged from `0.627` to `1.573` around boot and video transitions. A separate manual test reached the main menu at about 60 FPS with clear audio, then reported frame drops, apparent speed changes and audio stutter during a cutscene. Disc 2 measured `0.999` median speed over 15 headless boot samples and exited normally.

A faster-sampled Disc 1 run with video and audio output disabled measured `1.000` median speed in both CPU modes. The JIT range was `0.976–1.027` over 193 samples and the hybrid range was `0.919–1.100` over 192 samples. These runs cover early boot and the opening video. The worst Vulkan dips were absent in this comparison. The cause of cutscene stutter and the timing of later scenes remain open.

A live Windows capture during the indoor dialogue after the submarine shot measured `21.8–32.0` rendered FPS. The busiest runtime thread was using roughly one full logical core during the worst dips. Windows reported `3.3–6.5%` 3D engine utilization for the game. A later cutscene dropped to `16.7–21.8` FPS with only one game window open and showed the same single-thread saturation.

A headless replay of a local save state from the later cutscene measured `1.000` median speed with the JIT and `0.728` with hybrid native execution over 57 samples per mode. The worst hybrid sample was `0.668`, while the JIT stayed between `1.000` and `1.002`. The scene reproduced the slowdown with no graphics or audio output. A native dispatch profile found repeated data-cache flush and invalidation loops among the busiest sites. Routing those loops to the fallback JIT reduced instruction-level fallbacks from 6.57 million to 0.17 million, with essentially the same median speed of `0.730`.

A replay starting from a later save state in the same cutscene measured `1.000` with the JIT and `0.652` with hybrid execution over 33 samples per mode. The hybrid minimum was `0.552`. Both runs exited normally.

A separate instrumented replay estimated more wall time inside the hybrid fallback JIT than in native dispatch and register-state synchronization combined. The instrumented run was slower, so use the plain replay for speed comparisons. The next CPU investigation is the cost of moving between the native module and the fallback JIT during this scene.

During gameplay with one game window running, 26 live samples ranged from `15.8` to `27.1` FPS. The same runtime thread averaged `99%` of one logical core. Replaying a gameplay save with video and audio output disabled measured `1.000` median speed for the JIT and `0.278` for the hybrid build over 41 samples per mode. The hybrid minimum was `0.171`. This slowdown also affects interactive gameplay and is consistent with the tester's report of slow motion and choppy audio.

Two private x64 experiments bypassed the native-dispatch check for guest addresses above the fixed native code range, then also allowed fallback block linking to those addresses. On the same gameplay state, they measured `0.295` and `0.300` median speed, respectively. Both trials remained far below normal speed. The development package uses the original runtime for this path.

```powershell
python scripts/benchmark_boot.py --data .local/player --runner .local/runtime/moderngekko-run.exe
```

Use an idle machine and the same disc, graphics backend and scene for comparisons. The default headless run isolates the CPU path. `--windowed` adds normal Vulkan presentation and audio output. The pinned runtime raised an ImGui context assertion during an experimental offscreen Vulkan run, so that configuration yielded no hybrid result. For gameplay, measure frame pacing and compare input response, audio timing and cutscene timing with the retail disc under Dolphin. Generated outputs, logs and capture files stay local.

Use `--load-state PATH` to compare the same scene. Add `--dispatch-samples` to collect native dispatch counts during the replay.

## Tool comparisons

| Project | What to test or reuse |
| --- | --- |
| [Skies of Arcadia Legends Recompiled](https://github.com/ogdanimal/SkiesOfArcadiaLegends-Recomp/blob/main/BUILDING.md) | DolRecomp's LLVM path, per-target CPU selection and profile-guided optimization. Establish a correct Windows x64 baseline before using profiles from representative gameplay. |
| [Medal of Honor Frontline GameCube Recomp](https://github.com/ant0-blase/MOHFrontline-GC-RECOMP) | The runtime verifies loaded guest bytes before choosing native code for multiple executable images. Twin Snakes needs a related check for its relocatable module, whose addresses may differ by session. |
| [GekkoAOT](https://github.com/ant0-blase/GekkoAOT) | An alternate runtime with direct RVZ input and REL discovery. Its v0.0.9 Windows tool found `main.dol` and `mgso.rel` on the USA Disc 1 RVZ and entered REL compilation. Gameplay compatibility is still unverified. |
| [Twin Snakes Native Port](https://github.com/alphanu1/msg-twinsnakes-recomp) and its [Switch prototype](https://github.com/ramonDias07/MGSTTS-nx) | Public PAL analysis and runtime behavior are starting points for comparisons. Validate every code layout and timing assumption independently on the USA revision. |

Once normal-speed play is reliable, compare the original rendering cadence with a render loop that runs independently of the original simulation tick. Keep movie cadence and audio timing intact. NVIDIA's [Streamline integration guide](https://developer.nvidia.com/rtx/streamline/get-started) describes the timing markers for Reflex and the scene data needed for DLSS reconstruction. Revisit GPU features after those inputs can be measured and validated.
