# PR #115854, Commit `065d3cb` — Verified Assumptions

**Verification date**: 2026-06-06  
**Commit inspected**: `065d3cb3398041dc4c8bcd0488fa065be7191580`  
**Sources**: commit patch via `gh api`, `readytorun.h` and `corcompile.h` content at commit state, `ReadyToRunConstants.cs` from crossgen2 tooling, PR inline review comments.

---

## Assumption 1 — `READYTORUN_FIXUP_ModuleOverride = 0x80` correctly represents `ENCODE_MODULE_OVERRIDE = 0x80`

**Verdict: CONFIRMED**

Evidence:
- `corcompile.h` at parent commit (17c8a712) explicitly declares `ENCODE_MODULE_OVERRIDE = 0x80`.
- The patch to `readytorun.h` adds `READYTORUN_FIXUP_ModuleOverride = 0x80` with an identical comment describing the high-bit flag semantics.
- The crossgen2 C# tooling (`ReadyToRunConstants.cs`) already had `ModuleOverride = 0x80` independently defined — confirming the value was established in the R2R specification before this rename.
- All four usage sites (`genericdict.cpp` ×4, `prestub.cpp` ×4, `jitinterface.cpp` ×2) change from `ReadyToRunFixupKind::ModuleOverride` to `READYTORUN_FIXUP_ModuleOverride` in `& / &~` patterns that are structurally identical before and after.
- No numeric disagreement exists at any level.

---

## Assumption 2 — Deleting `case READYTORUN_FIXUP_Module:` (i.e., not mapping `ENCODE_MODULE_HANDLE = 0x50`) is correct

**Verdict: CONFIRMED**

Evidence:
- The crossgen2 C# `ReadyToRunFixupKind` enum in `ReadyToRunConstants.cs` (the definitive R2R image writer) has no entry in the range `0x50–0x7F`. After `Verify_IL_Body = 0x36`, the next entry is `ModuleOverride = 0x80`. There is no `Module = 0x50` fixup kind defined.
- The `readytorun.h` C++ enum at this commit likewise has no entry at `0x50`.
- jkotas's inline review comment at the relevant `jitinterface.cpp` line 13787 is explicit: *"Fragile NGen leftovers. No longer used."*
- `ENCODE_MODULE_HANDLE = 0x50` was the first entry of the explicitly-separated 0x50-block in `CORCOMPILE_FIXUP_BLOB_KIND` (separated from the 0x10–0x36 range that became `ReadyToRunFixupKind` by the comment gap and explicit `= 0x50` assignment), confirming it was never part of the R2R format.
- The crossgen2 outerloop CI run (triggered by jkotas: `/azp run runtime-coreclr crossgen2 outerloop`) passed, meaning no exercised R2R image emitted kind `0x50` and hit the now-absent case.

---

## Assumption 3 — Deleting `ENCODE_SYNC_LOCK` (0x51), `ENCODE_PROFILING_HANDLE` (0x52), and `ENCODE_VARARGS_*` (0x53–0x55) cases is correct

**Verdict: CONFIRMED**

Evidence:
- The crossgen2 `ReadyToRunFixupKind` enum in `ReadyToRunConstants.cs` has no entries at `0x51–0x55`. Values appearing at 0x50–0x55 in `ReadyToRunConstants.cs` are in the `ReadyToRunHelper` enum (e.g. `GetString = 0x50`, `LogMethodEnter = 0x51`) — these are helper *IDs* dispatched through `READYTORUN_FIXUP_Helper = 0x1A`, not standalone fixup kinds.
- jkotas's inline review comment (line 13914 of `jitinterface.cpp`) on `ENCODE_PROFILING_HANDLE` states: *"This was a left-over from the special NGen image flavor with prolog/epilog profiler callouts. We do not have those anymore. If the profiler wants callouts, we fallback to JIT."*
- jkotas's review comment at line 13787 covers all the 0x50-block cases as a group: *"Fragile NGen leftovers. No longer used."*
- The crossgen2 outerloop CI passed — no R2R image exercised the deleted cases.

---

## Assumption 4 — `ENCODE_READYTORUN_HELPER = 0x1A` and `READYTORUN_FIXUP_Helper = 0x1A` are numerically identical

**Verdict: CONFIRMED**

Evidence:
- `readytorun.h` at this commit: `READYTORUN_FIXUP_Helper = 0x1A` (explicit assignment, confirmed in the grep output).
- `corcompile.h` at parent commit: `ENCODE_TYPE_HANDLE = 0x10` starts the sequence; counting sequentially through `ENCODE_METHOD_HANDLE`, `ENCODE_FIELD_HANDLE`, `ENCODE_METHOD_ENTRY`, `ENCODE_METHOD_ENTRY_DEF_TOKEN`, `ENCODE_METHOD_ENTRY_REF_TOKEN`, `ENCODE_VIRTUAL_ENTRY`, `ENCODE_VIRTUAL_ENTRY_DEF_TOKEN`, `ENCODE_VIRTUAL_ENTRY_REF_TOKEN`, `ENCODE_VIRTUAL_ENTRY_SLOT` (= 0x19 implicit) gives `ENCODE_READYTORUN_HELPER = 0x1A`.
- No explicit override interrupts the sequence between 0x10 and 0x1A.
- `ReadyToRunConstants.cs` corroborates: `Helper = 0x1A`.

---

## Assumption 5 — All non-`ModuleOverride` values in `ReadyToRunFixupKind` are below `0x80`

**Verdict: CONFIRMED** (for current state; latent risk is prospective)

Evidence:
- `readytorun.h` at commit `065d3cb`: highest non-`ModuleOverride` entry is `READYTORUN_FIXUP_Verify_IL_Body = 0x36`. Values `0x37–0x7F` are completely unallocated.
- `ReadyToRunConstants.cs` confirms the same: enum ends at `Verify_IL_Body = 0x36`, then jumps to `ModuleOverride = 0x80`.
- No existing fixup kind has bit 7 set except `READYTORUN_FIXUP_ModuleOverride`. The flag-stripping logic is correct for the current enum.
- The latent risk identified in the analysis — a future addition in `0x40–0x7F` silently colliding with the flag bit — is real but lies outside the scope of this commit. No `static_assert` guarding the invariant was added.

---

## Assumption 6 — `IsInstructionSetSupported` is only called from code compiled inside `#ifdef FEATURE_READYTORUN`

**Verdict: CONFIRMED**

Evidence:
- The commit patch shows `#endif // FEATURE_READYTORUN` was removed from immediately before `IsInstructionSetSupported`'s definition and re-added after `LoadDynamicInfoEntry`'s closing brace. Both functions are now guarded by the outer `#ifdef FEATURE_READYTORUN`.
- `IsInstructionSetSupported` takes a `ReadyToRunInstructionSet` parameter and calls `InstructionSetFromR2RInstructionSet` — both are R2R-specific types. A non-R2R call site would have been a semantic error even before this move.
- The PR built and was merged without link errors in any CI configuration.
- The crossgen2 outerloop CI (exercising R2R compilation paths most thoroughly) ran and passed.
- Two senior maintainers (jkotas and AaronRobinsonMSFT) reviewed and approved.
- Residual caveat: specialised stripped-down build configurations that compile `jitinterface.cpp` with `FEATURE_READYTORUN` undefined were not explicitly tested in this PR's CI runs, but no such configuration is known to exist in the runtime repo.

---

## Assumption 7 — Removing `SBuffer` and `PEDecoder` forward declarations from `corcompile.h` does not break any downstream translation unit

**Verdict: CONFIRMED**

Evidence:
- The commit patch removes `SBuffer`, `SigBuilder`, `PEDecoder`, and `GCRefMapBuilder` forward declarations from `corcompile.h`.
- `SigBuilder` is re-declared in `zapsig.h` (visible in the `zapsig.h` patch: `class SigBuilder;` added).
- `GCRefMapBuilder` is re-declared in `frames.h` (visible in the `frames.h` patch: `class GCRefMapBuilder;` added).
- `SBuffer` and `PEDecoder` are dropped entirely — their only consumers were the fragile NGen code paths also deleted in this PR.
- The PR compiled and all CI builds passed. A missing forward declaration would have produced a hard compile error in any translation unit that included `corcompile.h` and named these types; no such error occurred.

---

## Assumption 8 — `kZapProfilingHandleImportValueIndex*` constants are used exclusively in the deleted `ENCODE_PROFILING_HANDLE` case

**Verdict: CONFIRMED**

Evidence:
- The `corcompile.h` patch deletes the entire anonymous enum containing `kZapProfilingHandleImportValueIndexFixup` through `kZapProfilingHandleImportValueIndexCount`.
- The `jitinterface.cpp` patch deletes the `ENCODE_PROFILING_HANDLE` case, which contains all six uses of these constants (`kZapProfilingHandleImportValueIndexClientData`, `kZapProfilingHandleImportValueIndexEnterAddr`, `kZapProfilingHandleImportValueIndexLeaveAddr`, `kZapProfilingHandleImportValueIndexTailcallAddr`).
- The PR compiled successfully. Since C++ generates a hard compile error for any reference to an undeclared identifier, the successful build proves no surviving code references these constants.
- The `kZap*` prefix marks NGen-era infrastructure; jkotas confirmed the profiling handle mechanism it supported no longer exists.

---

## Summary Table

| # | Assumption | Verdict | Key Evidence |
|---|---|---|---|
| 1 | `READYTORUN_FIXUP_ModuleOverride = 0x80` matches `ENCODE_MODULE_OVERRIDE = 0x80` | **CONFIRMED** | Both explicitly = 0x80 in header files; crossgen2 C# enum independently corroborates |
| 2 | Deleting `case READYTORUN_FIXUP_Module:` (0x50) is correct | **CONFIRMED** | crossgen2 `ReadyToRunFixupKind` has no 0x50 entry; jkotas: "Fragile NGen leftovers"; crossgen2 outerloop CI passed |
| 3 | Deleting `ENCODE_SYNC_LOCK/PROFILING_HANDLE/VARARGS_*` (0x51–0x55) is correct | **CONFIRMED** | Same: no 0x51–0x55 in `ReadyToRunFixupKind`; jkotas confirmed dead NGen code; CI passed |
| 4 | `ENCODE_READYTORUN_HELPER` and `READYTORUN_FIXUP_Helper` both = 0x1A | **CONFIRMED** | Sequential count from 0x10 yields 0x1A; explicit `= 0x1A` in readytorun.h and ReadyToRunConstants.cs |
| 5 | All non-`ModuleOverride` R2R fixup kinds < 0x80 | **CONFIRMED** | Highest is 0x36; gap 0x37–0x7F unallocated in both C++ and C# enums |
| 6 | `IsInstructionSetSupported` only called inside `FEATURE_READYTORUN` | **CONFIRMED** | Build succeeded; R2R-specific parameter type; CI passed; maintainer approval |
| 7 | Removing `SBuffer`/`PEDecoder` from `corcompile.h` safe | **CONFIRMED** | Build succeeded; both moved to appropriate headers or had no remaining consumers |
| 8 | `kZapProfilingHandleImportValueIndex*` used only in deleted case | **CONFIRMED** | Build succeeded (compile error would occur if any live code referenced them) |
