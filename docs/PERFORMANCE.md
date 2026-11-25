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

Use an idle machine and the same disc and scene for comparisons. Pass `--disc 2 --load-state PATH` for a checkpoint captured on Disc 2. The default headless run isolates the CPU path. `--offscreen Vulkan` (also `--offscreen-vulkan`) exercises rendering without a visible window or audio. `--windowed` adds display presentation and normal audio with Vulkan by default. Pass `D3D` for Direct3D 11 or `D3D12` for Direct3D 12 to either option. `--dual-core` enables separate CPU and video threads in the isolated benchmark profile. Add `--frame-times` to a windowed run for median, 95th-percentile and maximum render and vertical blank intervals after warmup. Runtime presents can include multiple presentations of the same frame. These intervals measure runtime events. Use OS-level tracing to measure when frames reach the display. Generated outputs, logs and capture files stay local.

The benchmark reports startup time from process launch to the first poll that observes a running core and an advanced frame counter. For a replay it also reports when the runtime confirms the checkpoint load. A failed load produces no replay samples. Rendered frames and runtime presents use counter changes across the full measurement window, which reduces the effect of the status-file write interval on measured rates. Use these measurements alongside game speed when comparing shader warmup or video backends.

Use `--compare-threading` to run shared and separate CPU/video threads in both orders against the same runner and checkpoint. It defaults to hybrid execution. With `--shader-cache-seed PATH`, every run starts with its own copy of the supplied local `Cache` directory. Seed from a completed run with the same backend and GPU so each case starts with the same pipeline data.

Use `--load-state PATH` to compare the same scene. Add `--dispatch-samples` to collect native dispatch counts during the replay. Benchmark profiles and logs default to a subdirectory of the system temporary directory. Use `--output PATH` to retain traces elsewhere. One run in a synced workspace failed to replace the test profile's filesystem metadata (`IOS_FS: Failed to rename temporary FST file`). Repeat runs with isolated profiles outside the synced workspace completed successfully.

A later Windows test reproduced that warning by holding the existing `fst.bin` without delete sharing. A source handle returned error 32 during an atomic replacement. A destination handle returned error 5. The runtime retries those two errors when committing IOS metadata. Releasing the destination lock after 22 ms let the game boot and shut down normally. Native controls held both kinds of lock through the retry sequence and verified that the existing and temporary files survived. [Windows file sharing](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)

To compare display settings, use `--windowed Vulkan --fullscreen --frame-times` and repeat the same checkpoint with `--internal-scale 1` and `--internal-scale 4`. Fullscreen sets the presentation surface to the current monitor's desktop size. Internal scale controls the GameCube render targets independently. The Windows test runtime opened directly with a 2560 × 1440 client area, restored its windowed geometry, and returned to a 2560 × 1440 client area. Other monitors, DPI settings, HUD placement, and graphics effects remain to be checked.

Use `--compare-module PATH` to compare a native module against the prepared module on the same runner. Add `--module PATH` to supply a different reference. Use `--compare-runner PATH` to compare two runtime executables with the same module. Both comparisons run reference, candidate, candidate, reference in separate profiles. A run that exits before the requested sampling window ends is marked incomplete even if it exits normally.

The summary includes the speed at the fifth percentile and the number of samples below 95% of the original game speed. With `--frame-times`, it also counts render and vertical blank intervals longer than 50 ms. A held scene can suppress duplicate presents while the game clock and vertical blanks continue normally.

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

A 25-second replay of the same checkpoint with graphics and audio disabled measured 99.9% median game speed and a 90.3% minimum for the linked hybrid runtime. The JIT reference measured 100.0% median speed with a 99.9% minimum. Each mode completed 101 samples.

The linked runtime also replayed the checkpoint in fullscreen Vulkan with audio enabled for 30 seconds per configuration. Each run completed 120 or 121 game-speed samples and shut down normally.

| CPU and video threads | Internal scale | Median game speed | Lowest sampled speed | 95th-percentile render interval | Longest render interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Separate | 1× | 99.9% | 94.5% | 18.09 ms | 491.75 ms |
| Separate | 4× | 99.9% | 95.7% | 18.29 ms | 489.18 ms |
| Shared | 4× | 99.9% | 70.3% | 20.30 ms | 425.75 ms |

Each separate-thread run logged one render interval exceeding 40 ms at about the same time. Vertical blank intervals continued and peaked at about 30 ms. The gap appears at both tested scales. The separate-thread profile improves the sampled speed floor in this scene. Compatibility in later scenes and audio under load still need testing before changing the default.

The matched JIT reference also logged a 502 ms render interval while maintaining 99.3% or better game speed. An isolated hybrid replay with duplicate framebuffer presentation enabled recorded 1,801 presents for 1,801 vertical blanks, and its longest render interval was 26.59 ms. The default separate-thread run recorded 1,773 presents for 1,802 vertical blanks. The half-second gap came from the renderer skipping identical framebuffers. Leave that optimization enabled so the runtime sends new frames as the game produces them.

On a saved dialogue scene, headless hybrid and JIT replays produced exactly the same 907,088 overlapping DSP stereo sample frames, spanning 28.322 seconds. The replays used the original guest clock and captured audio before it reached the Windows output backend. The hybrid sampled speed reached a low of 92.4% while the PC was in use during testing.

A matched Windows process loopback test replayed the saved dialogue scene in windowed Vulkan at 4× internal resolution. Each run captured about 18 seconds of Cubeb output and shut down normally. Windows reported no packet discontinuities or timestamp gaps larger than 2 ms. At least 21.26 seconds of the captured guest DSP output matched the JIT reference sample for sample in each hybrid run. [Windows application loopback capture](https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/)

| CPU mode | Threads | Median game speed | Lowest sampled game speed |
| --- | --- | ---: | ---: |
| JIT | Shared | 100.0% | 99.7% |
| Hybrid | Shared | 100.2% | 90.6% |
| Hybrid | Separate | 100.3% | 98.6% |

The shared-thread hybrid run still dipped below full speed. Listening for repeated or distorted audio under sustained load remains open.

The in-game Digital Camera wrote a valid photo after enabling external framebuffer copies to guest memory. A separate dock replay tested this option at 4× internal resolution with offscreen Vulkan and separate CPU and video threads. The four runs compared both settings in both orders. Median game speeds were 92.4–94.1% with the default and 96.7–96.8% with photo capture enabled. This single checkpoint showed no slowdown from the option. Its cost in other scenes and graphics backends is unmeasured.

## Late-game replays

Dev.14 replayed the Tower A alarm and ensuing guard activity, the Hind fight, and the Underground Passage flashback. Each run used an isolated Windows profile, Vulkan at 4× internal resolution, and Cubeb output. Tower A used 12-second windows and the other scenes used 22-second windows. All eight runs exited normally. Windows reported zero packet discontinuities and zero gaps over 2 ms between packets with valid timestamps. The capture measures packet delivery and cannot establish audible quality while the game clock slows.

| Scene | CPU mode and threading | Median game speed | Lowest sampled speed | 95th-percentile render interval | 95th-percentile vertical blank interval |
| --- | --- | ---: | ---: | ---: | ---: |
| Tower A alarm | Hybrid, shared | 76.2% | 72.5% | 24.26 ms | 24.22 ms |
| Tower A alarm | Hybrid, separate | 77.2% | 72.6% | 25.39 ms | 25.18 ms |
| Hind fight | Hybrid, shared | 100.0% | 98.7% | 17.74 ms | 16.69 ms |
| Hind fight | Hybrid, separate | 100.0% | 92.3% | 17.55 ms | 16.70 ms |
| Hind fight | JIT, shared | 100.0% | 100.0% | 16.74 ms | 16.69 ms |
| Underground Passage flashback | Hybrid, shared | 100.0% | 95.9% | 66.74 ms | 20.36 ms |
| Underground Passage flashback | Hybrid, separate | 100.0% | 93.0% | 66.77 ms | 20.41 ms |
| Underground Passage flashback | JIT, shared | 100.0% | 99.9% | 66.74 ms | 16.69 ms |

The flashback had nearly identical render intervals at the 95th percentile in every run, including the JIT reference at full speed. The Tower A slowdown persisted in the latter part of the replay with either threading setting.

Separate-thread headless runs of the same Tower A checkpoint reached median speeds of 81.8% with output disabled, 80.4% with offscreen Vulkan at 1×, and 78.9% with offscreen Vulkan at 4×. JIT reached 100% with output disabled and with offscreen Vulkan at 4×. Each run completed 49 samples. The hybrid CPU path accounts for most of the observed slowdown in this replay.

A separate symbolized run with output disabled collected 579 instruction-pointer samples from the busiest thread. The runner accounted for 373 samples and the compiled boot module for 135. Among named runner functions, the static recomp run loop had 85 samples, its instruction-cache invalidation handler had 44, and native address resolution and its lookup helper had 51. The JIT block-cache invalidation function had 22. These are starting points for profiling repeated invalidations and address lookup before changing frame timing.

### Cache invalidation and dispatch

The runtime now forwards the physical and effective addresses from each translated cache invalidation to the fallback JIT. Fixed-address modules use one native chunk lookup. Invalidations outside the span of the compiled chunks skip the native range search. Invalidations that touch compiled code still trigger revalidation before its next native dispatch.

The Tower A comparison used the same Disc 2 checkpoint and compiled boot module with fresh profiles, separate CPU and video threads, and 49 samples per run. Each row contains two runs per build, with the order reversed for the second pair.

| Output | Dev.14 median game speed | Patched median game speed | Dev.14 lowest sample | Patched lowest sample |
| --- | ---: | ---: | ---: | ---: |
| Graphics and audio disabled | 70.5%, 80.1% | 100.1%, 99.8% | 61.5%, 67.1% | 79.0%, 92.6% |
| Offscreen Vulkan at 4×, audio disabled | 75.2%, 77.2% | 99.9%, 98.2% | 67.0%, 70.9% | 93.0%, 75.3% |

All eight replays shut down normally. Each recorded 20 chunk verifications, six invalidations that marked chunks for revalidation, and the same single chunk rejected for a guest-code hash mismatch.

Both discs completed fresh headless boots at 100% median game speed and shut down normally. In a separate Disc 1 test, the one-chunk module for the game's virtual-memory region executed 6,702 native dispatches. The same module with a deliberately wrong expected hash was rejected and executed zero native dispatches. Both runs advanced at 100% median speed with JIT fallback available.

The windowed Tower A comparison used Vulkan at 4×, Cubeb, an 80 ms audio buffer and DSP dumping. Windows process loopback recorded 18 seconds of audio per run with zero packet discontinuities in all four runs. The patched runner still slowed below real time.

| CPU and video execution | Dev.14 median speed | Patched median speed | Dev.14 render interval p95 | Patched render interval p95 |
| --- | ---: | ---: | ---: | ---: |
| Shared thread | 74.7% | 89.9% | 26.00 ms | 22.19 ms |
| Separate threads | 75.9% | 95.9% | 25.26 ms | 21.05 ms |

A separate windowed 4× Vulkan run with the default shared-thread configuration, Cubeb and DSP dumping disabled reached 91.7% median game speed and 84.5% at its lowest sample. Its 95th-percentile render interval was 21.44 ms across 989 intervals. The next performance target is the remaining windowed slowdown with normal audio and graphics enabled.

### Windowed Tower A follow-up

In a windowed 4× Vulkan profile, 150 of 574 instruction-pointer samples landed in the compiled boot module. The busiest named runtime functions included the native run loop (36 samples), instruction fallback (33) and cache invalidation (20). The sampler suspended the CPU thread to read its instruction pointer, so speed readings from this run are excluded from the comparison.

The first trial sent native data-cache flushes directly through the static recomp cache. Each replay used the same Disc 2 state, shared CPU and video execution, Cubeb output, and 18 seconds of samples. The second pair reversed the run order.

| Runner | Median game speed | Lowest speed sample | Render interval p95 | Longest render interval |
| --- | ---: | ---: | ---: | ---: |
| Dev.15 | 88.7%, 92.7% | 70.9%, 83.2% | 22.29, 20.60 ms | 49.88, 45.55 ms |
| Direct cache hook trial | 94.6%, 92.4% | 80.2%, 78.9% | 20.71, 20.84 ms | 39.27, 108.57 ms |

JIT-only reached 100.0% median speed and a 99.8% minimum with the original shared-thread 4× Vulkan and audio settings. The hybrid trial reached 95.3% median at 1× Vulkan, 89.8% at 4× Direct3D 11, and 99.3% with separate CPU and video threads at 4× Vulkan. The separate-thread run still dipped to 92.2%. These controls point to the hybrid CPU path as the remaining bottleneck in this replay.

The next build checks native chunk coverage and the fallback JIT's physical cache-line bitset for data-cache operations when accurate data-cache emulation is disabled. The runtime translates the address first and forwards lines that can affect either code cache to the invalidation path.

Two alternating comparisons used the normal shared-thread window at 4× Vulkan with Cubeb and DSP dumping disabled. Each run completed 72 or 73 samples and shut down normally.

| Runner | Median game speed | Lowest speed sample | Render interval p95 | Longest render interval |
| --- | ---: | ---: | ---: | ---: |
| Dev.15 | 94.2%, 91.3% | 88.1%, 86.9% | 19.38, 20.95 ms | 40.62, 43.35 ms |
| Filtered cache hook | 99.9%, 99.2% | 89.6%, 95.2% | 18.66, 18.91 ms | 36.02, 36.46 ms |

Both patched runs reached near-normal median speed. Their speed floors still varied across runs. All four runs recorded 20 native chunk verifications, six invalidations that marked chunks for revalidation, and the same single guest-code hash mismatch.

The patched Hind fight replay reached 100.0% median game speed and a 99.5% minimum in the same windowed configuration. A separate Tower A capture with DSP dumping and an 80 ms audio buffer recorded 17.99 seconds of Cubeb output with zero packet discontinuities. That instrumented run reached 96.3% median game speed and dipped to 83.1%.

### Sustained dev.16 replays

The packaged runtime replayed the Heliport checkpoint on Disc 1 for 75 seconds and the Tower A alarm checkpoint on Disc 2 for 90 seconds per configuration. Each run used a 4× Vulkan window and Cubeb with the default 80 ms audio buffer. DSP dumping was off. The checkpoints ran with neutral scripted input. All four runs exited normally and Windows loopback recorded zero packet discontinuities.

| Scene and CPU setting | Median game speed | Speed p05 | Lowest speed sample | Render interval p95 | Longest render interval | Longest vertical blank interval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Heliport, hybrid shared | 100.0% | 100.0% | 98.0% | 17.37 ms | 25.37 ms | 25.01 ms |
| Tower A, hybrid shared | 96.3% | 89.2% | 71.9% | 20.38 ms | 476.26 ms | 48.85 ms |
| Tower A, hybrid separate | 100.0% | 97.8% | 92.1% | 18.08 ms | 483.82 ms | 42.07 ms |
| Tower A, JIT shared | 100.0% | 100.0% | 99.5% | 17.23 ms | 492.66 ms | 28.04 ms |

The Tower A JIT replay reached the Continue screen. The first 3,600 reported frame advances, before the late transition, took 63.21 seconds with shared-thread hybrid execution, 60.21 seconds with separate threads, and 60.19 seconds with JIT. The shared-thread hybrid recorded 84 of 251 samples below 95% game speed during that prefix. The separate-thread hybrid recorded six of 240, and JIT recorded zero of 239. The game-speed drops occur during gameplay with both the scene and output settings matched.

The half-second render gap occurred in all three Tower A configurations. A matched JIT repeat with duplicate framebuffer presentation enabled recorded 5,412 render intervals and 5,412 vertical blank intervals. The longest render interval fell from 492.66 ms to 32.74 ms, with game speed at 100.0% median in both runs. Windows loopback again recorded zero packet discontinuities. The large gap measures duplicate framebuffer suppression during the transition.

A separate host capture started 32.5 seconds into the Tower A replay at 92.6% sampled game speed. Of 768 instruction-pointer samples on the busiest thread, 237 landed in the compiled boot module. Named runtime functions included the native run loop (67), instruction fallback (38), and two register-state synchronization functions (40 combined). Use these counts to target generated code and transitions between CPU paths. The sampler paused the CPU thread to collect each instruction pointer.

### Register synchronization

A dev.16 process logged about 75 million native bursts across startup and the 90-second shared-thread Tower A replay. Each burst copies the guest register state into and out of the compiled module. The x64 trial packs or unpacks two paired floating-point registers at a time with SSE2 and gets the timebase and its cycle remainder from one tick sample. Disassembly confirmed vector shuffles in both directions. The two synchronization routines measured about half the combined reference size through their next symbol boundaries.

The packaged dev.16 runner and the candidate each completed two 90-second Tower A replays in alternating order. Both used shared threads, fresh profiles, 4× Vulkan and normal Cubeb audio. Each run collected 360 speed samples and exited normally.

| Runner | Median game speed | Speed p05 | Lowest sample | Samples below 95% | Vertical blank interval p95 | Longest vertical blank interval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dev.16 | 96.8%, 94.5% | 82.0%, 87.1% | 69.9%, 76.8% | 125, 204 | 21.82, 21.68 ms | 47.60, 47.70 ms |
| Register sync trial | 98.8%, 98.6% | 86.4%, 85.7% | 62.1%, 60.3% | 65, 68 | 20.62, 20.96 ms | 47.60, 103.24 ms |

The candidate registered fewer samples below 95% in both comparisons. Its lowest speed samples and one vertical blank interval were worse. Sustained game speed improved in this replay, and the isolated pacing dips still need investigation.

A round-trip test preserved all 65,536 test lane values, including NaN payloads and signed zeros. Headless Tower A trace and DSP captures varied between trials. The first candidate dump differed after 4.371 seconds of DSP audio, and two runs of the dev.16 reference also had different native traces. A repeated candidate run matched all 273 comparable dispatch records from the first dev.16 run, including the guest timebase and downcount. Its 22.333 seconds of overlapping DSP audio also matched sample for sample.

### Shader cache and isolated hitches

Standalone startup set the user path and enabled shader caching. A fresh profile lacked the parent cache directory. The Vulkan renderer tried to create the shader subdirectory with a single-directory operation, and the pipeline UID cache could not open its file in the missing parent. Startup now creates the full shader cache path before initializing the renderer.

The regular runner created six Vulkan cache files and a pipeline UID cache on a fresh profile. A second launch using the same directory read 34 saved pipeline UIDs. Both launches shut down normally.

Three 90-second, shared-thread Tower A diagnostic runs used the same instrumented dev.17 build, 4× Vulkan and normal audio. The first used an untouched profile. The second started with an empty cache directory and wrote about 11.6 MB of cache files. The third seeded a fresh profile with those files.

| Shader cache | Median game speed | Speed p05 | VBlank interval p95 | Longest VBlank interval | VBlank intervals over 50 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Missing directory | 100.0% | 92.0% | 18.76 ms | 55.63 ms | 1 |
| Empty writable cache | 95.9% | 83.5% | 21.85 ms | 90.10 ms | 5 |
| Populated cache | 100.0% | 90.4% | 19.39 ms | 73.66 ms | 1 |

The populated cache had fewer long intervals than the empty cache in this pair. The missing-directory run also had one long interval. These runs establish the persistence bug and show run-to-run variation in the remaining hitches.

During the warm run's 73.66 ms VBlank gap, presentation ran for 55.6 ms and the same thread spent 55.4 ms inside a Vulkan fence wait. The traced shader compile and native cache-reset events occurred outside that gap. A separate diagnostic run sampled the emulation thread in Windows' Ready state inside two gaps of about 40 ms. The snapshots identify periods when the thread was runnable and cannot measure the full time it spent waiting to run. Identify the work behind the Vulkan fence and keep checking scheduling gaps under normal playback.

Two further 90-second warm-cache Tower A runs used 4× Vulkan and normal audio. The probe distinguished fence waits for descriptor and command buffer reuse, synchronous submissions, upload buffers, and readbacks. Both runs reached 100.0% median game speed and shut down normally. The longest VBlank intervals were 34.43 and 78.91 ms. The second run's 78.91 ms gap had no overlapping probe event and Windows reported no additional emulation-thread CPU time during the gap. The only Vulkan fence waits of at least 5 ms in either run were synchronous staging-texture flushes during startup, before the measured segment. The origin of the earlier presentation fence wait remains open.

Four matched 70-second Tower A runs used the same dev.18 diagnostic runner, Disc 2 checkpoint, warm cache, windowed 4× Vulkan and Cubeb audio. Each run collected 281 speed samples and shut down normally.

| Run order | Median game speed | Speed p05 | Samples below 95% | VBlank interval p95 | Longest VBlank interval | VBlank intervals over 50 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Shared | 100.1% | 91.2% | 33 | 19.84 ms | 51.23 ms | 1 |
| Separate | 100.0% | 89.9% | 22 | 19.32 ms | 99.93 ms | 7 |
| Separate | 100.0% | 95.8% | 11 | 19.08 ms | 41.23 ms | 0 |
| Shared | 100.0% | 93.9% | 24 | 19.65 ms | 39.11 ms | 0 |

Separate threads yielded fewer samples below 95% in both run orders. One separate-thread run had seven VBlank intervals over 50 ms in a single burst about 55 seconds after loading the checkpoint. No traced Vulkan wait overlapped the burst. The launcher still defaults to shared threads. A Windows scheduling trace that covers a reproduced burst would help distinguish host scheduling from untraced blocking in the runtime.

### Windows scheduling

Windows Performance Recorder could not start the system CPU trace from the test account. A local sampler queried the game threads about every 2.57 ms. The median query took 10–20 µs. The sampler recorded whether a thread was running, ready for a processor, or waiting. These snapshots cannot establish the duration of an individual wait. [Microsoft thread state definitions](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.threadstate)

Four 85-second shared-thread Tower A replays used the same dev.18 diagnostic runner, warm cache, 4× Vulkan and Cubeb audio. For the middle two runs, the test raised just the combined CPU and video thread from normal to above-normal priority. All four exited normally.

| Thread priority | Median game speed | Speed p05 | Samples below 95% | VBlank interval p95 | Longest VBlank interval | VBlank gaps of at least 30 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Normal | 99.6% | 83.3% | 120 of 340 | 22.20 ms | 48.45 ms | 13 |
| Above normal | 100.0% | 85.6% | 56 of 340 | 20.63 ms | 35.59 ms | 6 |
| Above normal | 89.8% | 80.6% | 209 of 340 | 23.57 ms | 32.80 ms | 6 |
| Normal | 94.3% | 79.8% | 183 of 340 | 23.02 ms | 60.07 ms | 22 |

The thread was ready in 89 of 408 snapshots during gaps of at least 30 ms at normal priority, compared with 5 of 129 at above-normal priority. In both priority trials the longest gaps were shorter. Sustained speed varied, including an 89.8% median on the second above-normal replay. This limits the priority result to isolated stalls on this machine. [Microsoft scheduling priorities](https://learn.microsoft.com/en-us/windows/win32/procthread/scheduling-priorities)

A separate normal-priority replay triggered an instruction-pointer sample after sustained slowdown, at 85.1% game speed. Of 766 samples from the busiest host thread, 228 landed in the native game module and 391 in the runtime. The busiest named runtime functions were the instruction fallback hook (67), the native execution loop (54) and the two register synchronization routines (33 combined). Disassembly placed 27 of the hook samples in the code for translating data-cache flush addresses and checking the JIT block cache. The sampler briefly paused the thread for each snapshot, so these counts locate the hot path without measuring the cost of individual instructions.

### Cache-flush address translation

Upstream Dolphin's x64 JIT checks the translated block cache before invoking invalidation. It can also combine a known cache-flush loop when the instruction sequence and cycle budget permit it. The native runtime invokes a hook per flush, so the first trial reduces the cost of that hook using the runtime's existing instruction address table. Changing the loop itself would require validating its cycle and interruption behavior. [Dolphin x64 cache instruction implementation](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/PowerPC/Jit64/Jit_LoadStore.cpp)

The candidate uses the current instruction BAT table to translate cache-flush addresses with a mapped entry. Translation-disabled addresses are already physical. Addresses that miss the table still use the general MMU. The same block-validity checks and invalidation calls receive the translated address. The guest cycle charge is identical.

Four 70-second runs replayed Tower A with warm shader caches, shared CPU and video threads, windowed 4× Vulkan and Cubeb audio. All four exited normally.

| Run order | Median game speed | Speed p05 | Samples below 95% | VBlank interval p95 | Longest VBlank interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dev.18 | 97.3% | 82.9% | 115 of 280 | 22.21 ms | 48.73 ms |
| Candidate | 100.0% | 100.0% | 0 of 281 | 17.09 ms | 34.68 ms |
| Candidate | 100.0% | 99.1% | 3 of 281 | 17.62 ms | 31.84 ms |
| Dev.18 | 100.0% | 99.1% | 1 of 281 | 17.78 ms | 26.51 ms |

The first dev.18 run reproduced sustained slowdown. The second dev.18 run reached full median speed and had the shortest maximum VBlank interval in the group. The two candidate runs reached full median speed, with some variation in the lowest speed samples and longest gaps.

A diagnostic build compared every 64th cache-flush lookup against the original MMU path. The Heliport and Tower A replays matched on 3,295,835 sampled lookups, of which 3,293,252 used an instruction BAT mapping and 2,583 reported an invalid address. Both replays exited normally. Page-table misses still call the original translator.

Four 36-second, headless Tower A replays measured Windows CPU time on the emulation thread per recorded video update. In the first run order the cost fell from 16.906 to 16.178 ms per update. In the reverse order it fell from 16.647 to 16.012 ms. That frees about 4% of the thread's CPU budget in this checkpoint. The original 59.94 Hz video timing gives a wall-time budget of about 16.68 ms per update. The headless runs isolate CPU cost from window presentation.

A follow-up cached the fallback JIT block-cache pointer to avoid a virtual call in the data-cache flush hook. Four matched 36-second headless Tower A runs measured 15.517 and 15.410 ms per recorded video update for dev.19 and 15.503 and 15.359 ms for the candidate. All four reached 100% median game speed. The difference was at most 0.051 ms per update and did not justify adding lifecycle state to the hot path.

### x64 condition-register synchronization

The runtime converts Dolphin's eight internal condition-register fields to the packed PowerPC value during native register synchronization. The x64 patch packs four fields at a time using SSE2. The packed value matched the scalar rules on one million test inputs covering full-width values and zero, sign and low-word edge cases.

In four matched 36-second headless Tower A replays, CPU cost per video update fell from 15.675 to 15.197 ms in the first run order and from 15.474 to 15.259 ms in the reverse order. All runs reached 100% median game speed. The Disc 1 Underground Passage dialogue replay produced 23.448 seconds of sample-identical overlapping DSP audio on the reference and candidate, and both shut down normally. These tests establish the x64 CPU saving on this machine. Display pacing still needs separate measurement.

### Dev.19 packaged gameplay and audio

The initial dev.19 package reused an object file that still contained the cache verifier. After forcing a rebuild, the staged runner and its startup logs no longer contained the verifier. The following runs use the rebuilt package.

Four 22-second saved-scene replays used shared CPU and video threads, 4× Vulkan, Cubeb, and Windows per-process loopback capture. Each run had zero reported audio packet discontinuities and zero timestamp gaps over 2 ms among packets with valid timestamps. All four exited normally.

| Scene | Median game speed | Speed p05 | Minimum sampled speed | Longest VBlank interval | Audio packets |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tower A alarm | 100.0% | 92.89% | 85.55% | 37.47 ms | 2,199 |
| Underground Passage flashback | 100.0% | 99.77% | 96.48% | 32.59 ms | 2,200 |
| Hind fight | 100.0% | 100.0% | 99.99% | 23.49 ms | 2,199 |
| Hind fight repeat | 100.0% | 100.0% | 100.0% | 20.27 ms | 2,199 |

The 69.05 ms VBlank gap seen in the initial Hind fight capture did not recur in these two replays. The flashback had a 66.75 ms 95th-percentile render interval while its video updates continued at a median interval of 16.68 ms. The earlier JIT reference had a similar render interval in this scene. Tower A still had short drops in sampled game speed. The loopback checks measure audio delivery, and listening tests under sustained load remain open.

Three 75-second Tower A replays used the rebuilt package, warm shader caches, a Vulkan window and normal audio. The first run overlapped the end of a package-digest check, so the 1× replay was repeated after the check finished. All runs used shared CPU and video threads and exited normally.

| Internal scale in run order | Median game speed | Speed p05 | Samples below 95% | Longest VBlank interval | VBlank intervals over 50 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1× | 100.0% | 96.8% | 8 of 301 | 56.04 ms | 2 |
| 4× | 100.0% | 97.6% | 7 of 301 | 40.19 ms | 0 |
| 1× repeat | 100.0% | 98.1% | 5 of 300 | 43.92 ms | 0 |

The short speed drops persisted at both scales. This run order shows that a long gap can occur at 1× and leaves the effect of resolution on worst-case pacing open.

### Dev.19 scheduling at default internal resolution

Five 75-second Tower A diagnostic replays used the current runtime, a warm Vulkan shader cache, 1× internal resolution and normal audio. The Windows sampler queried the combined CPU and video thread every 2.57–2.58 ms. Runs 3 and 4 raised only that thread to `THREAD_PRIORITY_ABOVE_NORMAL`. All five reached 100% median game speed and shut down normally. [Windows scheduling priorities](https://learn.microsoft.com/en-us/windows/win32/procthread/scheduling-priorities)

| Run | Thread priority | Speed p05 | Samples below 95% | Longest VBlank interval | Traced VBlank gaps of at least 30 ms |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Normal | 96.2% | 11 of 300 | 42.37 ms | 14 |
| 2 | Normal | 99.5% | 3 of 300 | 38.63 ms | 6 |
| 3 | Above normal | 99.4% | 4 of 301 | 31.68 ms | 2 |
| 4 | Above normal | 100.0% | 1 of 301 | 25.39 ms | 0 |
| 5 | Normal | 100.0% | 0 of 301 | 26.72 ms | 0 |

In the first two runs, 47 of 202 snapshots during the traced gaps showed the thread ready to run. Outside those gaps, 155 of 58,983 snapshots showed the thread ready. None of the long gaps overlapped a traced Vulkan wait, shader compile, cache reset or throttle oversleep. This supports a scheduling contribution to some hitches. The snapshots cannot establish how long each scheduling delay lasted, and the 56 ms gap from the earlier packaged run did not recur in this diagnostic series.

Both above-normal trials had shorter maximum VBlank intervals than the first two normal runs. The final normal control was within 1.33 ms of the shortest maximum and had the fewest speed drops. The release profile uses normal priority. A priority change needs validation under sustained mixed workloads and on another Windows system.

### Dev.20 Tower A graphics backends

Three 75-second replays used dev.20, the same Disc 2 Tower A alarm state, shared CPU and video threads, a 4× window and Cubeb audio. The Intel i5-11400 and GeForce RTX 3060 Ti ran each backend with a populated shader cache. All three runs completed at 100% median game speed and shut down normally.

| Backend | Speed p05 | Lowest speed sample | Samples below 95% | Render interval p95 | Longest VBlank interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vulkan | 98.1% | 81.4% | 7 of 301 | 22.11 ms | 43.74 ms |
| Direct3D 11 | 99.6% | 97.3% | 0 of 301 | 17.58 ms | 34.19 ms |
| Direct3D 12 | 99.7% | 96.6% | 0 of 301 | 17.37 ms | 25.88 ms |

The 25-second cache-building replays also reached 100% median game speed with zero samples below 95% on both Direct3D backends. Those sampling windows began after startup. Warm Direct3D 12 reached the first observed running frame in 25.81 seconds. These results cover one checkpoint on one graphics card.

The dev.21 Direct3D 11 setting also passed two 22-second windowed replays at 4× with Cubeb and a warm shader cache. The Disc 1 Underground Passage flashback reached 100.0% median and 96.9% minimum game speed. The Disc 2 Hind fight reached 100.1% median and 99.7% minimum. Windows loopback reported zero packet discontinuities and zero gaps over 2 ms among packets with valid timestamps in both captures. Both runs shut down normally.

### Profile-guided C module compilation

Clang 23.1.1 instrumented the boot module using `-fprofile-generate`. Three 24-second training replays covered the Dock, Tower A and the Underground Passage flashback. I merged the profiles with the bundled `llvm-profdata` and compiled the same generated C with `-fprofile-use`. The profile, generated sources and modules stayed local. [Clang profile-guided optimization](https://clang.llvm.org/docs/UsersManual.html#profile-guided-optimization)

Eight headless replays used the dev.22 runtime and shared CPU and video threads. The Windows sampler measured emulation-thread CPU time per video update. Each pair reversed the run order. All eight runs reached 100% median game speed and shut down normally.

| Checkpoint | Measured window | Reference → PGO, reference first | Reference → PGO, PGO first |
| --- | ---: | ---: | ---: |
| Tower A | 36 s | 14.977 → 14.346 ms (4.2% lower) | 14.829 → 14.429 ms (2.7% lower) |
| Heliport, excluded from training | 30 s | 11.611 → 11.281 ms (2.8% lower) | 11.487 → 11.148 ms (3.0% lower) |

Separate headless replays matched the standard module sample for sample across 26.493 seconds of dialogue DSP output and 26.508 seconds of Hind fight DSP output. The disc streaming tracks also matched over their overlapping durations. The optimized DLL grew from 9,711,616 to 10,122,752 bytes.

The measurements isolate CPU cost on this machine. Easy Setup builds the standard module. The profile-guided build requires separate training and a second compilation.

### Native chunk lookup allocation

The runtime sizes the chunk lookup to the last mapped chunk. Existing bounds checks send addresses beyond the lookup to the usual fallback. The supported boot module uses 401,984 bytes for the lookup, down from 25,165,824 bytes. The experimental boot-plus-REL module uses about 11.64 MiB less for that lookup.

Four 32-second headless Tower A replays reached 100% median game speed with clean shutdown. Emulation-thread CPU cost ranged from 15.74 to 15.83 ms per video update across both builds. A separate Heliport replay with each runner recorded native dispatch inside the extended virtual memory region of the experimental module. Both full-module runs were below full game speed.

### Runtime launch inspection

The prepared launcher supplies an explicit native module. The runner now leaves full game and asset inspection to runtime creation on that path. Module discovery, netplay and builds with compile-time pinned checks still inspect before selecting or checking a module. Isolating this change reduced Disc 1 headless startup from 23.56 seconds to 12.54–12.57 seconds and Disc 2 from 24.31–24.56 seconds to 13.03–13.04 seconds.

Caching each asset's relative path before sorting avoids repeated filesystem resolution in the comparator. On Windows the scan also uses the operating system's SHA-256 provider when available, with the portable implementation retained as a fallback. Both retail asset manifests matched the original scan exactly. Tests also compared 13 synthetic file sizes, empty files, filenames containing non-ASCII characters and nested trees created in different orders. A standalone scan went from 11.79–11.88 seconds to 2.35–2.51 seconds in the order-reversed comparison. [Windows SHA-256 API](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcrypthash)

Paired runs on the same prepared data used dev.22 and the combined candidate. Startup measures process creation through the first poll that observes an advancing frame. Each pair reversed the run order. All headless runs reached 100% median game speed over the five-second sample and shut down normally.

| Disc and renderer | Dev.22 | Combined candidate |
| --- | ---: | ---: |
| Disc 1, Null | 24.06–24.56 s | 4.02–4.31 s |
| Disc 2, Null | 26.59–26.82 s | 4.27 s |
| Disc 1, offscreen Vulkan, warm shader cache | 24.31–27.32 s | 5.02–5.77 s |

The candidate also booted through normal module discovery and through the `STATICRECOMP_MODULE` override. Unreadable assets, malformed boot metadata and a missing game root still failed with the invalid-game exit code. An unavailable explicit module failed with the module initialization exit code.

### Dev.23 checkpoint replays

The updated benchmark waited for restoration to finish on the CPU thread. A truncated state and a tagged Disc 2 state on Disc 1 each produced zero replay samples. The tagged state loaded successfully on Disc 2. The sustained replays below used dev.23, the matching Disc 2 checkpoints, a warm cache for each backend and shared CPU and video threads. Both restored their checkpoint before sampling, used 4× offscreen rendering and exited normally.

| Checkpoint | Backend | Window | Drawn frames per second | Game speed median / minimum | Samples below 95% speed |
| --- | --- | ---: | ---: | ---: | ---: |
| Tower A alarm | Direct3D 11 | 65 s | 59.61 | 100% / 76.8% | 14 / 261 |
| Vulcan Raven fight | Vulkan | 35 s | 59.05 | 100% / 55.8% | 5 / 141 |

These runs cover different scenes, so a matched replay is needed to compare the backends. The short dips at both checkpoints remain open.

An instrumented runtime measured eight vertical blank gaps of at least 30 ms in a repeat of Tower A at 4× offscreen Direct3D 11. The longest was 38.44 ms. Windows sampled the shared CPU and video thread as running or ready throughout these gaps. The disc read, shader and Direct3D wait probes reported no events during those gaps.

The 4× offscreen Vulkan Raven replay measured 118 vertical blank gaps of at least 30 ms. All 118 overlapped waits to reuse an upload buffer. The longest gap was 52.87 ms and included 37.74 ms in the buffer wait, almost all inside the Vulkan fence call. The renderer's offscreen path skips the regular windowed backbuffer submission. This makes GPU submission cadence a variable in offscreen comparisons. The user's visible window pauses require separate validation.

### Offscreen Vulkan submission

In four warm 28-second Raven replays at 4×, the vertex upload buffer accounted for all instrumented reuse waits. Two runs used the original submission cadence and two submitted GPU work once per new frame, with the order reversed for the second pair. Every run restored the checkpoint, held 100% median game speed and shut down normally.

| Replay | Vertex upload waits of at least 5 ms | Vertical blank gaps of at least 30 ms | Longest gap |
| --- | ---: | ---: | ---: |
| Reference first | 95 | 96 | 73.07 ms |
| Candidate second | 0 | 2 | 34.25 ms |
| Candidate first | 0 | 1 | 32.57 ms |
| Reference second | 95 | 95 | 50.23 ms |

The automation status also formerly reported the internal presenter sequence number, which could advance twice within one present. The updated runner counts completed guest present callbacks directly. Estimates from the older counter measure changes in that sequence number. Rendered frame rate uses the separate unique-frame counter.

The regular build, with the submission change and no diagnostic probes, held 100% median game speed in a 35-second Raven replay at 4× and a 12-second dialogue replay at 1×. It counted 59.64 drawn frames and present callbacks per second in the fight and 30.05 per second in dialogue. Both restored their checkpoints before sampling and shut down normally.

At 4× offscreen Vulkan, the updated runner produced 23.07 seconds of sample-identical DSP audio against the reference in dialogue and 24.14 seconds in the Raven fight. A second unchanged reference ran under overlapping host compilation load and produced a shorter matching interval. The updated build matched that entire interval in each scene, 18.26 and 18.50 seconds respectively. These are guest PCM comparisons. Windows audio output is measured separately.

The dev.25 package also ran both checkpoints in normal windows with warm caches, 4× internal resolution and sound output disabled. Both confirmed the checkpoint load before sampling and shut down normally.

| Checkpoint | Backend | Window | Median game speed | Samples below 95% speed | Maximum render / vertical blank interval |
| --- | --- | ---: | ---: | ---: | ---: |
| Vulcan Raven fight | Vulkan | 38 s | 100% | 0 / 153 | 28.85 / 25.79 ms |
| Tower A alarm | Direct3D 11 | 45 s | 100% | 4 / 181 | 39.15 / 33.35 ms |

### Cold Direct3D 11 shader startup

Four clean-cache Disc 1 starts at 4× reached the first advancing frame in 29.20–29.59 seconds with automatic shader worker selection. Limiting shader precompilation to six workers took 30.64–30.88 seconds in the same order-reversed comparison. A warm Direct3D 11 run reached the first advancing frame in 4.77 seconds. The automatic worker count stays selected.

### Dev.25 Tower A with Windows audio

Both windowed runs restored the same Disc 2 Tower A alarm checkpoint before sampling. They used 4× internal resolution, warm shader caches, shared CPU and video threads, and Cubeb with an 80 ms audio buffer. Windows process loopback captured 54.99 seconds of game audio per run. Both captures contained 5,496 audible packets and reported zero packet discontinuities or timestamp gaps above 2 ms. Both runs shut down normally.

| Backend | Median / minimum game speed | Samples below 95% speed | Maximum render / vertical blank interval |
| --- | ---: | ---: | ---: |
| Vulkan | 100% / 86.09% | 12 / 220 | 41.01 / 49.75 ms |
| Direct3D 11 | 100% / 97.40% | 0 / 220 | 38.75 / 30.53 ms |

The comparison covers one matched run per backend on a GeForce RTX 3060 Ti. Listening quality and the cause of the short Vulkan dips still need separate checks.

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

PowerPC instruction fingerprints identified the matching SDK routines in the USA executable. A JIT probe measured their median call intervals in an in-engine dialogue scene and in dock gameplay, using emulated ticks with offscreen Vulkan. Both runs completed at 100% median game speed.

| Guest operation | Dialogue | Dock gameplay |
| --- | ---: | ---: |
| `GXCopyDisp` copies the rendered framebuffer | 29.95 Hz | 59.95 Hz |
| `VISetNextFrameBuffer` submits the buffer to the video interface | 29.97 Hz | 59.94 Hz |
| `PADRead` reads controller state | 59.94 Hz | 59.94 Hz |
| The traced engine viewport call sets up the draw | 29.97 Hz | 59.93 Hz |

The same engine viewport call site tracked the display-copy cadence in both scenes. Four perspective upload sites also followed roughly 30 Hz in dialogue and 60 Hz at the Dock. In a follow-up trace, one overlay call site built a view matrix into the same destination in both scenes. For that destination, the median interval was 33.369 ms across 372 calls in dialogue and 16.679 ms across 740 calls at the Dock. In dialogue the same call site also built matrices into a second destination twice per update. The USA matrix routine matches the PAL `C_MTXLookAt` symbol position relative to neighboring SDK functions and calls the expected vector normalization and cross-product helpers. Animation and camera-input update rates still need separate traces. [PAL SDK symbol reference](https://github.com/alphanu1/msg-twinsnakes-recomp/blob/d1fbfec2281042d2eaef43dbb20afedb0ae1d364/config/symbols/main.dol.symbols.txt) [libogc view-matrix API](https://github.com/devkitPro/libogc/blob/master/gc/ogc/gu.h)

Prototype rendering directly from camera and animation evaluated at the presentation cadence, where the game's data supports it. Start with a known gameplay replay and an in-engine dialogue scene. Keep the original physics and script update schedule and audio clock, and verify motion, camera cuts, and dialogue timing with repeatable input. A higher simulation rate would require validating each frame-dependent update and callback. Keep the original guest speed limit during these experiments.

The opening sequence showed about 30 rendered frames per second and 60 video updates per second in an earlier capture. Static references and a relocated function pointer identified the USA movie task on both discs. The opening playback trace recorded 322 calls with a median interval of 33.367 ms. Neither the dialogue nor the gameplay replay called this task. That interval measures the task cadence. Decoder output timestamps and dialogue sync still need verification before evaluating optional video smoothing. [PAL movie task symbols](https://github.com/alphanu1/msg-twinsnakes-recomp/blob/d1fbfec2281042d2eaef43dbb20afedb0ae1d364/config/symbols/mgso_pal.rel.symbols.txt)

Measure input, simulation, render submission and presentation timing once the render path is independent. Those markers support a Reflex comparison. Evaluate DLSS Super Resolution and DLAA after confirming that the renderer can expose scene color before the HUD, depth, motion vectors, camera jitter, and history resets for the newly rendered frames. [NVIDIA Reflex programming guide](https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuideReflex.md) [NVIDIA DLSS programming guide](https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuideDLSS.md)
