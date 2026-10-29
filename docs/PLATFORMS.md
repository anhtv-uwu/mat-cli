# Platform packaging and validation

The bundle builder has no hardcoded Linux runtime path. It discovers the MAT
runtime inside either a regular distribution or a macOS app directory, and the
JRE inside either a regular directory or `Contents/Home`. Download locks, cache
keys, filenames and native launchers are selected by OS and architecture.
Cross-packaging never runs the target JVM. It copies the self-contained Java
plugin into MAT's plugins directory and registers it in `bundles.info`.

| Target | Native CI runner | Included JRE |
| --- | --- | --- |
| linux-x86_64 | ubuntu-24.04 | Temurin 21.0.13+9 |
| linux-aarch64 | ubuntu-24.04-arm | Temurin 21.0.13+9 |
| macos-x86_64 | macos-15-intel | Temurin 21.0.13+9 |
| macos-aarch64 | macos-15 (ARM64) | Temurin 21.0.13+9 |
| windows-x86_64 | windows-2025 | Temurin 21.0.12.1+1 |

The Windows JRE is pinned separately because the 21.0.13+9 release did not offer
a Windows JRE at lock creation. Its archive/version and SHA-256 are explicit in
[bundle-lock.json](../bundle-lock.json). macOS ARM64 MAT's SHA-512 was calculated
from the official Eclipse HTTPS archive; the published checksum endpoint returned
"Unable to locate sums". The other MAT hashes came from that endpoint.

The shared Java build runs the 92 existing unit tests plus five launcher/JSON
transport regression tests. Packaging tests cover host
aliases, archive layouts, path traversal rejection, unsafe links, executable
permissions and plugin registration. Each native job builds an archive, extracts
it into a new path containing spaces, verifies its per-file SHA256SUMS, removes
any OSGi cache, then runs the real-HPROF integration suite with the included JVM.
New regression cases cover embedded quotes in OQL and Unicode JSON output.
Windows additionally checks the CMD entry point and process exit status.

A target is validated only when its native job passes. An archive assembled on
another OS is not evidence of native compatibility. Workflow results for the
release commit are authoritative; the old [v0.1.0 validation](VALIDATION.md) only
covers Linux x86_64 and remains a historical record.

The matrix covers these OS/CPU combinations, not every distribution or OS
version. Linux packages use glibc, macOS bundles are not notarized installers,
and Windows ARM64 is not offered by the MAT 1.17 RCP distribution used here.

Windows uses an ASCII-only JVM bootstrap command and an explicit UTF-8/Base64
argument transport, preserving Unicode, embedded quotes, empty arguments and
the caller's original working directory. JSON escapes non-ASCII characters using
standard JSON escapes. Heap filenames and OQL Unicode values are exercised on
all five platforms. Java 21's native launcher still requires a bundle installation
path representable in its Windows code page; use an ASCII-only installation path.
