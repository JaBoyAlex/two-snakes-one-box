# Release gates

Work through the gates in order. Runtime fixes and installer tests can overlap once they can use the same pinned build. [STATUS.md](STATUS.md) tracks the latest evidence.

| Order | Work | Exit evidence |
| --- | --- | --- |
| Now | Stabilize the Windows runtime at original timing. Start with sustained CPU cost in Tower A, then replay the affected gameplay and dialogue checkpoints with normal audio. Investigate intermittent long gaps and the earlier guest CPU fault. | Repeatable speed and pacing results on both discs, with crash and timing findings resolved for the release profile. |
| Next | Validate a complete playthrough and test the installer in RecompLauncher on a clean Windows account. | A full run through both discs, persistent saves across the disc swap and restart, controller reconnect, and install, update and repair inside RecompLauncher. |
| First stable release | Stage the verified build and check the portable package and release assets. | Completed gameplay and install gates, clean source and license audit, and recorded compatibility limits. |
| Display update | Finish monitor-native output and validate higher internal resolution. | Matching aspect ratio, HUD, movie and effect behavior across the supported display settings. |
| Frame-rate update | Unlock independent scene rendering for gameplay and real-time cutscenes. | Repeatable comparisons show original simulation, script and audio timing with new renders above the original cadence. |
| PC graphics follow-ups | Evaluate Reflex and then DLSS Super Resolution or DLAA once the renderer can supply their inputs. | Measured latency or image-quality results on supported hardware. |

## 1. Reproducible bring-up

- Pin the recompiler, runtime and build inputs.
- Build the runtime and validate both disc identities, revisions and content hashes locally.
- Translate and compile the original game executable.
- Reach the title screen through a loaded native module. Record native/fallback execution evidence.

## 2. Gameplay compatibility

- Verify controls, rumble, analog inputs, menus, loading and room transitions.
- Verify that a controller connected before startup works on port 1 without setup, and that disconnecting and reconnecting it after boot restores input.
- Verify codec conversations, movies, music and sound effects against the original timing.
- Verify memory-card creation, save/load, process restart and update persistence.
- Verify both discs, the disc transition, boss encounters and a complete playthrough.
- Investigate crashes and rendering errors before calling a release stable.

## 3. Easy installation

- One portable executable for setup and play, with a standalone file picker.
- RecompLauncher named inputs for both discs, visible setup progress and useful failure messages.
- Test the packaged release on a clean Windows account without developer tools.
- Test cancellation, paths with spaces and non-ASCII characters, interrupted builds and retries.
- Validate installation and settings inside RecompLauncher, including Big Picture.
- Publish only open-source tooling and runtime files, with required license/source notices.

## 4. Display improvements

- Fullscreen output follows the selected monitor's desktop resolution.
- Higher internal resolution preserves aspect ratio, HUD placement, movies and effects.
- Measure GPU cost and test more than one graphics backend.

## 5. Frame-rate work

Read-only timing traces can run alongside baseline testing. The first private prototype should render the Dock at 120 Hz while keeping the original simulation schedule. Use the same checkpoint and input for the original and candidate runs, then extend the test to an in-engine dialogue scene. Before exposing the mode, verify the stable playthrough and display gates above.

- Trace gameplay updates, animation, physics, camera transforms, input sampling and decoder frame timing using replays at the original game speed.
- Prototype direct rendering from camera and animation evaluated at the presentation cadence. Compare gameplay state, script timing, and audio against the original run.
- Verify that additional draws leave authoritative gameplay state unchanged and produce a new scene render. Compare matched guest simulation ticks and report repeated presentations separately.
- Include real-time cutscenes. Compare camera cuts, animation cues and dialogue timing with the original. Preserve source cadence and audio sync for prerecorded footage before evaluating optional smoothing.
- Keep the original frame-rate mode available.
- Test fixed 60/120/144 Hz and variable refresh at monitor-native output without changing game speed or audio timing.
- Expose an unlocked option in RecompLauncher only after those tests pass.
- Validate that world simulation, game timers, DSP/audio mixing, dialogue and movies advance at the same rate with the cap removed. Report simulation ticks, scene renders, repeated presents and video playback cadence separately.

## 6. Optional PC graphics features

- Evaluate Reflex after presentation pacing is stable. Record input, simulation, submission and present markers and measure input-to-present latency with the feature on and off on supported hardware.
- Evaluate DLSS Super Resolution and DLAA if the renderer can supply scene color before the HUD, depth, motion vectors, jitter and frame history resets. Check camera cuts, HUD, movies and effects for ghosting. Keep a baseline display path for other GPUs.

## 7. Other platforms and extras

Linux/Steam Deck and macOS need native builds and hardware validation. Recomp Achievements is a later integration once reliable gameplay events are known.
