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

Two private x64 experiments bypassed the native-dispatch check for guest addresses above the fixed native code range, then also allowed fallback block linking to those addresses. On the same gameplay state, they measured `0.295` and `0.300` median speed, respectively. Both trials remained far below normal speed and were dropped.

The x64 runtime now allows the fallback JIT to use Dolphin's fast memory mappings. The active CPU core selects the fallback's RAM mapping and forwards memory faults to the existing JIT backpatcher. The hybrid runtime continues to use the game's original timing. In headless replays with video and audio output disabled, the revised build measured `0.647` and `0.671` median speed at two gameplay checkpoints, and `1.004` at the later cutscene checkpoint. The later cutscene stayed within `0.992–1.021` across 33 samples. Repeating the first gameplay checkpoint in the same test session gave `0.332` for the old hybrid runtime, `0.658` with the fix and `1.000` for the JIT reference over 41 samples each. A cold boot on the revised runtime measured `1.000` over 29 samples. Live Vulkan frame pacing and audio at these checkpoints still need verification.

On the first gameplay checkpoint, recompiling the native C module with `-O3 -march=x86-64-v3` moved the median from `0.647` to `0.657` with the fixed runtime. The minimum fell from `0.585` to `0.548`, so the development build keeps its existing compiler settings. A separate experiment to reuse an active CPU timing slice also slowed the gameplay replay when combined with fast memory.

A later gameplay checkpoint ran with Vulkan and normal audio output at a median `45.9` rendered FPS and `0.769` of original game speed over 48 samples. It ranged from `42.1` to `47.7` FPS and `0.706` to `0.801` of original speed. This was a separate checkpoint and provides no matched comparison to the earlier live capture. The telemetry launch disabled automatic controller selection, so the controller test used a regular windowed launch.

```powershell
python scripts/benchmark_boot.py --data .local/player --runner .local/runtime/moderngekko-run.exe
```

Use an idle machine and the same disc, graphics backend and scene for comparisons. The default headless run isolates the CPU path. `--windowed` adds normal Vulkan presentation and audio output. The pinned runtime raised an ImGui context assertion during an experimental offscreen Vulkan run, so that configuration yielded no hybrid result. For gameplay, measure frame pacing and compare input response, audio timing and cutscene timing with the retail disc under Dolphin. Generated outputs, logs and capture files stay local.

Use `--load-state PATH` to compare the same scene. Add `--dispatch-samples` to collect native dispatch counts during the replay. Benchmark profiles and logs default to a subdirectory of the system temporary directory. Use `--output PATH` to retain traces elsewhere. One run in a synced workspace failed to replace the test profile's filesystem metadata (`IOS_FS: Failed to rename temporary FST file`). Repeat runs with isolated profiles outside the synced workspace completed successfully.

## Tool comparisons

I compared public GitHub release asset downloads on November 23, 2026. These totals count binary and installer downloads across available versions and platforms. They exclude source archives, resource packs, and projects whose releases use another platform's game executable. Repeated downloads are possible. The figures describe the sampled projects and exclude distribution outside GitHub.

| GameCube recomp | Downloads in the sample | Performance changes |
| --- | ---: | --- |
| [Luigi's Mansion Recompiled](https://github.com/rob646464/luigis-mansion-recompiled/releases) | 26,308 | Fixed redundant rendering work in the original 30 FPS mode, which had slowed cutscenes and desynchronized sound. Later releases reduced shader preparation work and freed unused textures, render targets, and shader memory. |
| [Skies of Arcadia Legends Recompiled](https://github.com/ogdanimal/SkiesOfArcadiaLegends-Recomp/releases/tag/v0.91.0-beta) | 12,092 | Replaced the earlier Dolphin-derived runtime with a standalone GameCube hardware layer. Its developers measured 1.46× original speed versus 0.88× on one low-power PC core. The project also prepares shaders ahead of play and documents LLVM profile-guided builds in its [build guide](https://github.com/ogdanimal/SkiesOfArcadiaLegends-Recomp/blob/main/BUILDING.md). |
| [Eternal Darkness Recomp](https://github.com/griches/EternalDarknessRecomp) | 8,817 | Runs native code through GXRuntime with host SDK services and native graphics backends. Its high-refresh presentation adds intermediate frames independently of the original game cadence. |

Our save-state slowdown reproduces with graphics and audio output disabled. The Skies runtime comparison is the closest match for current CPU and hardware-layer work. Once gameplay holds its original clock, the Luigi's Mansion work gives us specific tests for redundant per-frame work and shader preparation.

| Project | What to test or reuse |
| --- | --- |
| [Medal of Honor Frontline GameCube Recomp](https://github.com/ant0-blase/MOHFrontline-GC-RECOMP) | The runtime verifies loaded guest bytes before choosing native code for multiple executable images. Twin Snakes needs a related check for its relocatable module, whose addresses may differ by session. |
| [GekkoAOT](https://github.com/ant0-blase/GekkoAOT) | An alternate runtime with direct RVZ input and REL discovery. Its v0.0.9 Windows tool found `main.dol` and `mgso.rel` on the USA Disc 1 RVZ and entered REL compilation. Gameplay compatibility is still unverified. |
| [Twin Snakes Native Port](https://github.com/alphanu1/msg-twinsnakes-recomp) and its [Switch prototype](https://github.com/ramonDias07/MGSTTS-nx) | Public PAL analysis and runtime behavior are starting points for comparisons. Validate every code layout and timing assumption independently on the USA revision. |

### Main game module

On the supported revision, `mgso.rel` has 111,582 relocation records that affect executable instructions. Most materialize addresses within the same REL. There are also 8,238 branch relocations into the main DOL. Native dispatch needs to translate both guest addresses and control flow at the game's actual section placement. An address-range check alone cannot validate this, and fixed-address chunk hashes need to account for relocations before they can match loaded code.

GekkoAOT is the first comparison because it already compiles secondary modules and translates between compile-time and live addresses. Its standalone ABI is different from the current runtime's. The local DOL passed its ABI probe. REL linking and gameplay are still unverified. For the current runtime, capture the live section addresses and compare relocation-adjusted code with guest memory before enabling native dispatch. Keep unverified code on the existing fallback, then compare the same gameplay and cutscene checkpoints against the JIT reference at the original game clock.

Once normal-speed play is reliable, compare the original rendering cadence with a render loop that runs independently of the original simulation tick. Keep movie cadence and audio timing intact. NVIDIA's [Streamline integration guide](https://developer.nvidia.com/rtx/streamline/get-started) describes the timing markers for Reflex and the scene data needed for DLSS reconstruction. Revisit GPU features after those inputs can be measured and validated.
