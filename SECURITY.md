# Security scope

No software can honestly be guaranteed 100% malware-free. This fork does not
establish that upstream contains a backdoor. Review findings and actual test
results are recorded in docs/VALIDATION.md.

The application source contains no network client, telemetry, shell command
execution, auto-update, credential collection or remote-control feature.
Build tools download dependencies; runtime works offline. Launchers start the included JVM; the Windows CMD entry point first invokes
the Windows-provided PowerShell script. Eclipse MAT, Equinox, JRE and Maven dependencies remain
part of the trust boundary; a source review is not a proof about every binary.

The bundle pins official MAT and Temurin downloads and checks cryptographic
hashes before extraction. MAT hashes are pinned per platform; the macOS ARM64 hash was computed from
the official HTTPS archive because Eclipse's checksum endpoint did not provide
one. Other MAT hashes were checked against Eclipse's published checksums.
JRE hashes come from Adoptium/GitHub release metadata. Provenance is recorded
in the lock file. Build on a
trusted machine and verify the generated SHA256SUMS before first use.

Heap dumps and JSON/results can contain secrets. MAT writes indexes and thread
sidecars beside the dump; the legacy report writes results there as well.
Use a private writable copy of each dump. Do not analyze the same dump from
multiple processes concurrently. Keep bundle files writable for Equinox state.
MAT, its parsers, extension plugins and query engine are trusted executable code.
Only run trusted OQL/MAT expressions and install trusted plugins. Pagination
bounds output rows, not the CPU/memory cost of parsing or executing queries.
Use an OS/container memory limit and process timeout for untrusted dumps.

The four CLI runtime Maven libraries were checked against OSV; see the dated
validation record. No antivirus engine or exhaustive dependency vulnerability
audit of the full MAT/JRE bundle is claimed.
Report a reproducible security problem privately to the repository owner;
never include a real heap dump or credentials in a public issue.
