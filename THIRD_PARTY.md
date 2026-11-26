# Third-party components

- **ModernGekko**, GPL-3.0: https://github.com/ExpansionPak/ModernGekko
- **RecompCore**, Dolphin-derived, GPL-2.0-or-later and third-party components under their respective licenses: https://github.com/ExpansionPak/RecompCore
- **DolRecomp**, GPL-3.0: https://github.com/ExpansionPak/DolRecomp
- **Dolphin Emulator**, GPL-2.0-or-later and third-party licenses: https://github.com/dolphin-emu/dolphin

Exact dependency revisions are recorded in `dependencies.lock.json`. Bundled open-source runtime files must retain their license notices, and distributions must provide the corresponding source as required by those licenses. The runtime staging directory is private build output, not game content. Do not add generated game modules, extracted disc data or proprietary SDK/source files to a distribution.

Windows runtime staging copies notices for the linked dependencies and Vulkan headers from the pinned RecompCore tree to `runtime/licenses/RecompCore/Externals`. It includes source-file notices for the Bochs disassembler, FreeSurround and Kiss FFT.

The bundled Gecko code handler's MIT notice is in `runtime/licenses/Gecko-codehandler-MIT.txt`. The bundled GameCube fonts retain their notices in `runtime/Sys/GC/font-licenses.txt`. RecompCore carries the corresponding assembly and generation tools for the replacement DSP ROM and coefficients. [Gecko code handler source](https://github.com/ExpansionPak/RecompCore/blob/cf8ceb81b47d6172164cd0572f57aa7624719f33/docs/codehandler.s) [DSP replacement source](https://github.com/ExpansionPak/RecompCore/tree/cf8ceb81b47d6172164cd0572f57aa7624719f33/docs/DSP/free_dsp_rom)

The Windows package includes these tool distributions. Their download digests are recorded in `dependencies.lock.json`.

- Python 3.13.16, with notices in `python/LICENSE.txt`. [Python release](https://www.python.org/downloads/release/python-31316/)
- CMake 4.4.4, with notices in `tools/cmake/doc/cmake/LICENSE.rst`. [CMake release](https://github.com/Kitware/CMake/releases/tag/v4.4.4)
- Ninja 1.13.2, with its Apache 2.0 license in `tools/ninja/COPYING`. [Ninja release](https://github.com/ninja-build/ninja/releases/tag/v1.13.2)
- llvm-mingw 20260908, with notices in `tools/llvm-mingw/LICENSE.TXT` and its component directories. [llvm-mingw release](https://github.com/mstorsjo/llvm-mingw/releases/tag/20260908)

Original code in this repository is licensed under GPL-3.0-or-later; dependency licenses remain with their respective authors.
