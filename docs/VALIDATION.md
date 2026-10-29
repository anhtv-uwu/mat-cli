# Validation record

Date: 2026-10-29. Platform: Linux x86_64. Build: Microsoft OpenJDK 21.0.12,
Maven 3.9.16. Runtime: bundled Temurin 21.0.13+9, Eclipse MAT 1.17.0
(build 202606011933).

## Results

- `mvn -B verify`: successful; 92 upstream unit tests, zero failures/errors/skips.
- `python3 scripts/smoke.py build/mat-cli-linux-x86_64/mat-cli`:
  27 integration checks passed against a genuine synthetic HPROF generated with
  HotSpotDiagnosticMXBean, including paths containing spaces.
- Integration checks cover info, histogram sorting/pagination/empty pages,
  dominators, object address lookup, incoming/outgoing references, GC root paths,
  threads, OQL object and scalar results, generic MAT queries, invalid arguments,
  missing/broken heaps, bad queries, help, interactive EOF and legacy full report.
- The application source was reviewed for process execution, network calls,
  credential/environment access, file writes, executable extension loading and
  build hooks. No backdoor was identified in this review. Upstream's unsafe
  cleanup script was omitted, automatic install/uninstall hooks removed,
  argument parsing and interactive snapshot disposal/EOF handling corrected.
- Runtime dependency archive inspected: no JUnit, Mockito, Byte Buddy or test
  classes. Those frameworks run only during development/testing.
- OSV querybatch lookup returned no advisories for `commons-cli:commons-cli`
  1.8.0, `commons-io:commons-io` 2.21.0, `org.apache.commons:commons-text` 1.15.0,
  and its transitive dependency `org.apache.commons:commons-lang3` 3.20.0.
- MAT download SHA-512 matched the value returned by Eclipse's official
  `downloads/sums.php` endpoint. Temurin checksum pinned from Adoptium metadata.
- A successful `info` invocation on the synthetic heap was observed using
  `strace -f -e trace=network`: no AF_INET/AF_INET6 connect, send or receive
  calls. The JVM created probe sockets and attempted local AF_UNIX nscd access.
  This observation applies to this invocation, not every possible MAT query.

- The final archive was extracted to a different directory, every SHA256SUMS
  entry verified, and the extracted OSGi cache removed. All 27 integration
  checks passed again on that relocated copy using its bundled JRE.

## Limits

This is not a full security audit of Eclipse, Java, Maven or all transitive
binary components, nor an antivirus scan or proof that malware cannot exist.
No claim that upstream has a backdoor is established. Only Linux x86_64 is
bundled and tested. Very large/corrupt/production heap coverage is not exhaustive.
Use trusted expressions/plugins, keep dumps private and apply process limits.
