# Release gates

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

- Trace gameplay updates, animation, physics, camera transforms, input sampling and decoder frame timing using replays at the original game speed.
- Prototype higher-rate rendering from interpolated camera and object state while retaining the original simulation and audio clocks. Check that interpolating a scene causes no gameplay state changes.
- Include real-time cutscenes. Compare camera cuts, animation cues and dialogue timing with the original. Preserve source cadence and audio sync for prerecorded footage before evaluating optional smoothing.
- Keep the original frame-rate mode available.
- Test fixed 60/120/144 Hz and variable refresh at monitor-native output without changing game speed or audio timing.
- Expose an unlocked option in RecompLauncher only after those tests pass.
- Validate that world simulation, game timers, DSP/audio mixing, dialogue and movies advance at the same rate with the cap removed. Report simulation ticks, scene renders (including renders from interpolated state), repeated presents and video interpolation separately.

## 6. Optional PC graphics features

- Evaluate Reflex after presentation pacing is stable. Record input, simulation, submission and present markers and measure input-to-present latency with the feature on and off on supported hardware.
- Evaluate DLSS Super Resolution and DLAA if the renderer can supply scene color before the HUD, depth, motion vectors, jitter and frame history resets. Check camera cuts, HUD, movies and effects for ghosting. Keep a baseline display path for other GPUs.

## 7. Other platforms and extras

Linux/Steam Deck and macOS need native builds and hardware validation. Recomp Achievements is a later integration once reliable gameplay events are known.
