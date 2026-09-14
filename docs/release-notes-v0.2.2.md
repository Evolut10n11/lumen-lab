# Lumen 0.2.2

Lumen 0.2.2 completes the automatic recovery of Russian text saved by older Windows builds.

## What changed

- Short one-character Cyrillic words such as `Я` are restored even when they touch punctuation in quoted or unquoted localized mission text. A v0.2.1 backup enables this only when it exactly proves that the live file is the corresponding incompletely repaired state.
- Intrinsically ambiguous byte-reversible Russian spans such as `Рё`, `Рё, Рё`, and `РёРё` are left unchanged instead of being treated as stronger evidence merely because they repeat. When an exact v0.2.1 backup proves an upgrade path, v0.2.2 applies unresolved weak repairs to the proven live payload rather than rebuilding from historical bytes, so text that v0.2.1 already repaired is never reverted.
- Recovery now repairs every independent high-confidence damaged fragment in one run without treating valid quoted letters such as `«Р»` or `«С»` as damaged text.
- All Lumen JSON writers share a cross-process lock with a bounded deadline, and recovery verifies the exact source bytes before replacement so concurrent Lumen saves are serialized safely.
- The first valid pre-repair backup remains immutable, and on POSIX its directory entry is flushed before live state changes. Invalid partial backups left by v0.2.1 are replaced atomically, while later distinct source versions receive content-addressed snapshots.
- Unchanged workspaces are skipped after their first scan, and fragment detection is linear rather than cubic for long healthy text.

## Compatibility

This patch keeps dashboard schema version 5 and all v0.2.x user-state formats. Installing it over v0.2.0 or v0.2.1 preserves the user's profile, missions, progress, feedback, companion, and XP.
