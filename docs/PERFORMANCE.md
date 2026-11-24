# Performance and runtime evaluation

The first Windows run reached the title screen on an Intel Core i5-11400 and RTX 3060 Ti. The user reported about 17–18 FPS and drops to 5 FPS with audible stutter. The window title can display rendered FPS and game speed separately. `100% speed` means the GameCube clock is advancing normally.

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

The tester reported better pacing, including intervals close to normal speed, with major slowdowns still present. That agrees with the game clock measured during the live checkpoint.

```powershell
python scripts/benchmark_boot.py --data .local/player --runner .local/runtime/moderngekko-run.exe
```

Use an idle machine and the same disc and scene for comparisons. The default headless run isolates the CPU path. `--offscreen Vulkan` (also `--offscreen-vulkan`) exercises rendering without a visible window or audio. `--windowed` adds display presentation and normal audio with Vulkan by default. Pass `D3D` for Direct3D 11 or `D3D12` for Direct3D 12 to either option. `--dual-core` enables separate CPU and video threads in the isolated benchmark profile. Add `--frame-times` to a windowed run for median, 95th-percentile and maximum render and vertical blank intervals after warmup. The runtime render counter includes repeated presents when they are enabled. These intervals measure runtime events. Use OS-level tracing to measure when frames reach the display. Generated outputs, logs and capture files stay local.

Use `--load-state PATH` to compare the same scene. Add `--dispatch-samples` to collect native dispatch counts during the replay. Benchmark profiles and logs default to a subdirectory of the system temporary directory. Use `--output PATH` to retain traces elsewhere. One run in a synced workspace failed to replace the test profile's filesystem metadata (`IOS_FS: Failed to rename temporary FST file`). Repeat runs with isolated profiles outside the synced workspace completed successfully.

To compare display settings, use `--windowed Vulkan --fullscreen --frame-times` and repeat the same checkpoint with `--internal-scale 1` and `--internal-scale 4`. Fullscreen sets the presentation surface to the current monitor's desktop size. Internal scale controls the GameCube render targets independently. The Windows test runtime opened directly with a 2560 × 1440 client area, restored its windowed geometry, and returned to a 2560 × 1440 client area. Other monitors, DPI settings, HUD placement, and graphics effects remain to be checked.

Use `--compare-module PATH` to compare a native module against the prepared module on the same runner. Add `--module PATH` to supply a different reference. The benchmark runs reference, candidate, candidate, reference in separate profiles to expose run-order effects. A run that exits before the requested sampling window ends is marked incomplete even if it exits normally.

Use a regular windowed launch for physical controller checks. `--automation-dir` installs scripted input overrides, including when it is added only to capture timing. During a manual test the launcher detected the XInput pad and assigned it to port 1 after resuming the saved session without those overrides. The tester confirmed that the controller responded, reported around 30 FPS in the replayed cutscene, and saw around 50 FPS in the first 15 seconds of gameplay. The game clock was unavailable in the window title on that build.

The tester subsequently reported gameplay drops. Thirteen nearby live samples ranged from 35.0 to 47.0 rendered FPS while the busiest runtime thread averaged 99.6% of one logical CPU. Six concurrent samples put 3D GPU engine usage between 7.8% and 8.2%. A local save state from that part of gameplay is available for comparing the CPU paths with the same starting state.

A private x64 trial linked fallback JIT blocks directly when the destination could not belong to the fixed native module. The dispatcher still checks destinations inside native code ranges. In the first matched headless replay of the new checkpoint, the reference measured `0.837` median speed and `0.780` minimum speed. The trial measured `1.000` median and `0.999` minimum. Both runs completed 21 samples, recorded native dispatches, and shut down normally. Repeat runs and windowed gameplay are pending.

During a subsequent windowed test of the x64 trial, the tester reported a recurring slowdown in another area and saved a checkpoint there. In 24 nearby samples, the title displayed 53.3–62.4 FPS and game speed as low as 86%. The busiest runtime thread averaged 98.9% of one logical CPU. Nine samples put 3D GPU engine usage between 9.1% and 18.9%. Replaying this checkpoint with output disabled and with offscreen Vulkan can test whether the remaining slowdown requires the renderer.

Replaying the new checkpoint with output disabled measured `0.837` median speed for the reference and `0.998` with fallback linking enabled. The linked build's minimum was `0.956`. With offscreen Vulkan and the same linked build, the median was `0.921` and the minimum was `0.813`. These runs collected 28–29 samples each and shut down normally. The renderer adds enough work in this checkpoint to reproduce part of the live slowdown.

The same Vulkan replay reached `1.000` median speed with separate CPU and video threads. The first 29 samples had a minimum of `0.955`. The full 49-sample run dipped to `0.909` and exited normally. The thread names confirmed that the setting took effect. The separate threads are available in an isolated test profile for live validation.

The tester reported that the separate-thread profile played smoothly in a later live session. A subsequent renderer comparison replayed the same F1 checkpoint with the linked runtime and separate threads, on one machine with a single game process. Two offscreen runs per backend, alternating the order, reached median game speeds of `1.000–1.002`. The lowest sampled speeds were `0.941` for Vulkan and `0.923` for Direct3D 11 across 66 samples per backend.

Both backends ran with sound enabled in the six-second windowed comparison at 640 × 528. Each completed 25 game-speed samples and logged 361 render intervals.

| Backend | Median game speed | Lowest sampled speed | Median render interval | 95th-percentile interval | Longest interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vulkan | 100.0% | 99.6% | 16.683 ms | 17.133 ms | 23.108 ms |
| Direct3D 11 | 100.0% | 98.4% | 16.689 ms | 17.274 ms | 23.072 ms |

Keep Vulkan for the current test profile. This replay covers one gameplay checkpoint at baseline resolution. Longer sessions across cutscenes, room transitions, fresh shader caches, and monitor-native output are still needed. The runtime already enables hybrid ubershaders and shader caching. Compare cold and warm playback before prioritizing shader changes. [Dolphin performance guide](https://dolphin-emu.org/docs/guides/performance-guide/)

The display-patch test runner replayed the same checkpoint with sound enabled for nine seconds per setting on a 2560 × 1440 desktop at 165 Hz. Each run collected 37 game-speed samples and shut down normally.

| Output | Internal scale | Median game speed | 95th-percentile render interval | Longest render interval |
| --- | ---: | ---: | ---: | ---: |
| Fullscreen Vulkan | 1× | 96.2% | 18.932 ms | 24.692 ms |
| Fullscreen Vulkan | 4× | 96.1% | 18.924 ms | 29.495 ms |
| Windowed Vulkan | 1× | 97.2% | 19.950 ms | 29.901 ms |
| Fullscreen Direct3D 11 | 1× | 97.5% | 18.595 ms | 23.961 ms |

The 1× and 4× runs had similar median speed and 95th-percentile render intervals. Both window modes and both backends still showed slowdown in these short runs. Keep the original scale as the default while checking repeatability, remaining CPU and renderer costs, and visual correctness at higher scales.

A pre-patch windowed Vulkan reference reached 99.7% median speed with an 18.37 ms 95th-percentile render interval. Rebuilding the display patch without the JIT timing probe gave 99.0% and 22.15 ms in the same windowed replay. The rebuilt runner reached 97.2% and 19.13 ms in fullscreen at 4×. These short runs still show pacing dips and warrant repeated comparisons before qualifying the display change for wider testing.

In a later interactive test at 4× fullscreen, the tester reported slow motion. Live samples showed 85–94% game speed with the busiest thread using roughly one logical CPU. The tester's replay was restarted at the same checkpoint at 1× fullscreen. A later interactive sample ranged from 91% to 100%, with 18 of 19 samples at 97% or better. These captures include live input and cover different intervals after loading. Longer matched captures are needed to measure how much of the slowdown comes from rendering at higher scale.

After the tester reported minimizing and restoring, Windows reported a maximized window with a menu and a 2556 × 1345 client area on the 2560 × 1440 desktop. The profile still requested 1×. The renderer recalculates the internal scale on resize only in its automatic scale mode. This observation verifies the smaller presentation area. A controlled minimize and restore is needed to identify how fullscreen was left. A new local save state from this session is available for matched replays.

Three controlled minimize and restore cycles on the same display retained the exact 2560 × 1440 fullscreen client area at 4× internal scale. This test used the Windows minimize command and restore API. The earlier transition to a maximized window remains unexplained.

At the new F1 checkpoint, the display runner reached 79.7% median speed with graphics and audio disabled. The JIT reference reached 100.0% under the same conditions. The display runner was missing the earlier fallback block-linking change. Rebuilding with that change produced the following results over the same eight-second span, using separate CPU and video threads and 33 game-speed samples per run.

| Test | Before linking | With linking | Render interval at the 95th percentile |
| --- | ---: | ---: | ---: |
| Graphics and audio disabled | 79.7% | 98.6% | — |
| Vulkan fullscreen at 1× | 82.1% | 95.0% | 23.54 → 20.32 ms |
| Vulkan fullscreen at 4× | 82.6% | 98.6% | 23.00 → 19.36 ms |

The rebuilt runner exited normally in each replay and in a cold Disc 1 boot at 100% median speed. The 1× run still had a 137 ms render interval. These brief runs identify a CPU improvement. Repeat across longer replays before drawing conclusions about scale or worst-case pacing.

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

The complete REL has the same SHA-256 on both supported discs. Its executable section starts at `0x7F0080EC` in the runtime's GameCube virtual memory region. Its zero-initialized data is allocated separately in main RAM. Applying the relocation records from the disc with that section placement reproduced all 4,540,760 executable bytes in seven saved checkpoints and a fresh headless boot of each disc. The fresh boots used separate profiles and stopped normally.

The experimental builder joins the boot executable and the relocated on-disc sections as compiler input. It reproduced the same input byte for byte from either disc, with the section placement recorded in the supported-build profile. The runtime extends its existing per-chunk verification to code in the virtual memory region. A one-chunk smoke test executed 6,746 native dispatches from the REL and shut down normally. Repeating the cold boot with a deliberately wrong expected hash rejected the chunk, executed zero native dispatches, and also shut down normally. Both tests used the JIT for code outside this chunk and measured a median `1.000` game speed in the opening sequence.

The full module linked successfully and executed REL code at multiple addresses during gameplay. The first matched headless gameplay replay measured median speed of `0.561` with the boot-only module and `0.397` with the full module over 41 samples each. Both exited normally. The full module's runtime reported about 15 million instruction fallback calls in that replay. A second gameplay comparison was stopped early when work paused. The later cutscene replay measured median speed of `1.004` with the boot-only module and `0.990` with the full module over 41 samples each. The full module dipped to `0.837` during that replay. The main module remains experimental.

Repeating the early gameplay comparison with the currently staged Windows runner and alternating the module order measured `0.745` and `0.739` for the boot-only build and `0.417` and `0.422` for the full module. Each run completed the requested sampling window, collected 29 samples, and exited normally. The boot-only module stays selected for regular launches.

In a later profile of the same checkpoint, 9,568 of 9,570 sampled instruction fallback calls were PowerPC data-cache flush or invalidate operations. Two call sites accounted for nearly all of those samples. The runtime continues to process those operations through its cache-coherency path.

A private cache-line trial reused the fallback JIT's single-line invalidation path and skipped searching native chunks for lines outside the small set of compiled ranges. The full module's gameplay replay improved from `0.395` to `0.437` over 41 samples per build. Reversing test order measured `0.429` with the trial and `0.418` with the comparison build over 33 samples each. Gameplay remains below real time. The trial stayed local while the larger native dispatch cost remains unresolved.

A Windows instruction-pointer sample of the busiest thread during the same headless gameplay replay landed inside the full native module 408 times out of 574. Paired-single load, store, and multiply-add helpers were among the busiest named symbols. The stock JIT reached `1.000` median speed on that replay. The full C module reached `0.420` in an uninstrumented repeat and `0.413` with the sampler attached. Runtime profiles, binaries, and instruction addresses stayed local.

A private trial replaced the module's CRT fused multiply-add call with a hardware FMA instruction on the i5-11400. Two runs per build in alternating order measured `0.423` and `0.421` for the reference and `0.419` and `0.406` for the trial, with 33 samples per run and clean exits. Keep the existing floating-point path. The profile points to several hot helpers and large generated chunks. Evaluate code layout and register-state traffic before tuning individual floating-point calls further.

GekkoAOT already compiles secondary modules and translates between compile-time and live addresses. Its standalone ABI is different from the current runtime's. The local DOL passed its ABI probe. REL linking and gameplay are still unverified in that tool.

### Experimental LLVM backend on Windows

Replaying the early gameplay checkpoint with the earlier LLVM boot module reproduced `0xC0000409` on shutdown. The debugger traced the abort to the CPU manager joining its play-time tracking thread. The LLVM build changed `XMM7` across the CPU run loop, and the caller had kept the thread handle in that register. The C reference preserved the register and shut down normally. The ABI requires functions to restore `XMM7` before returning. [Windows x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention#callercallee-saved-registers)

The Windows RecompCore LLVM path now returns through generated function frames so they restore the caller's registers. The rebuilt module preserved `XMM7` and shut down normally in the same debugger replay. The build also supplies the SDK's native-region check, which permits native chaining when no host-call hook is installed.

The module linked against the SDK from a fresh runtime staging run. On the same runner without the debugger, the early gameplay checkpoint measured `0.718` median speed with C and `0.486` with the experimental LLVM boot module. The later cutscene reached `0.727` median speed with LLVM. Each headless replay completed 29 samples and shut down normally. The LLVM gameplay run logged more than nine million native dispatches. The regular launcher selects the C build.

## Frame-rate investigation

The pinned runtime derives game speed from emulated CPU ticks and wall time. `VideoInterface` counts vertical blanks, and `Core::Callback_FramePresented` counts host presentations, including repeated frames when enabled. The audio interface schedules samples using the emulated CPU clock. To measure game work directly, a private JIT probe recorded function entries and indirect calls against emulated CPU ticks. The task scheduler ran at a median 29.95 Hz over 346 passes in a dialogue replay and 59.96 Hz over 677 passes in gameplay. These passes dispatched 53 and 115 distinct callbacks, respectively. Both replays maintained the original guest clock. Map camera, animation, and draw callbacks before changing their rates. [PAL task scheduler analysis](https://github.com/alphanu1/msg-twinsnakes-recomp/blob/d1fbfec2281042d2eaef43dbb20afedb0ae1d364/config/symbols/mgso_pal.rel.symbols.txt)

Prototype rendering directly from camera and animation evaluated at the presentation cadence, where the game's data supports it. Start with a known gameplay replay and an in-engine dialogue scene. Keep the original physics and script update schedule and audio clock, and verify motion, camera cuts, and dialogue timing with repeatable input. A higher simulation rate would require validating each frame-dependent update and callback. Keep the original guest speed limit during these experiments.

The opening sequence showed about 30 rendered frames per second and 60 video updates per second in an earlier capture. Static references and a relocated function pointer identified the USA movie task on both discs. The opening playback trace recorded 322 calls with a median interval of 33.367 ms. Neither the dialogue nor the gameplay replay called this task. That interval measures the task cadence. Decoder output timestamps and dialogue sync still need verification before evaluating optional video smoothing. [PAL movie task symbols](https://github.com/alphanu1/msg-twinsnakes-recomp/blob/d1fbfec2281042d2eaef43dbb20afedb0ae1d364/config/symbols/mgso_pal.rel.symbols.txt)

Measure input, simulation, render submission and presentation timing once the render path is independent. Those markers support a Reflex comparison. Evaluate DLSS Super Resolution and DLAA after confirming that the renderer can expose scene color before the HUD, depth, motion vectors, camera jitter, and history resets for the newly rendered frames. [NVIDIA Reflex programming guide](https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuideReflex.md) [NVIDIA DLSS programming guide](https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuideDLSS.md)
