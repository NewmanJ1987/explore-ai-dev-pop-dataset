# Commit Comparison: `065d3cb` vs `8c19261`

**Date**: 2026-06-06  
**Question**: What changed between the PR commit we analysed and the commit that landed on main? Did any verified assumptions turn out to be wrong?

---

## What the Two Commits Are

| Commit | Message | Role |
|--------|---------|------|
| `065d3cb` | "Cleanup, fix build breaks" | Last commit on the PR branch — the one we analysed |
| `8c19261` | "Fix build break" | The commit that **actually merged to main** |

`8c19261` is a follow-up that had to be pushed *after* `065d3cb` because something still didn't compile.

---

## What Changed Between Them

Only one file changed: `src/coreclr/vm/prestub.cpp`.

The change is a single-line type correction in the signature of `ProcessDynamicDictionaryLookup`:

```diff
 void ProcessDynamicDictionaryLookup(TransitionBlock *           pTransitionBlock,
                                     Module *                    pModule,
                                     ModuleBase *                pInfoModule,
-                                    BYTE                        kind,
+                                    ReadyToRunFixupKind         kind,
                                     PCCOR_SIGNATURE             pBlob,
                                     PCCOR_SIGNATURE             pBlobStart,
                                     CORINFO_RUNTIME_LOOKUP *    pResult,
```

`BYTE kind` → `ReadyToRunFixupKind kind`.

No logic changed. No values changed. The function still works identically at runtime — `ReadyToRunFixupKind` values all fit in a byte. This is a type-safety fix the compiler demanded.

**Why did this become a problem with `065d3cb`?** Commit `065d3cb` changed all the call sites in `jitinterface.cpp` and elsewhere to use `READYTORUN_FIXUP_ModuleOverride` (an enum constant) instead of `ReadyToRunFixupKind::ModuleOverride`. With stricter enum typing, the implicit narrowing from `ReadyToRunFixupKind` → `BYTE` became a hard error in at least one build configuration.

---

## Did Any Verified Assumptions Turn Out to Be Wrong?

### Short answer: No assumption was semantically wrong. But one assumption used flawed evidence.

### Assumption-by-Assumption Check

| # | Assumption | Verdict in doc | Affected by 8c19261? |
|---|---|---|---|
| 1 | `READYTORUN_FIXUP_ModuleOverride = 0x80` | CONFIRMED | No |
| 2 | Deleting `READYTORUN_FIXUP_Module` (0x50) safe | CONFIRMED | No |
| 3 | Deleting `ENCODE_SYNC_LOCK/PROFILING_HANDLE/VARARGS_*` safe | CONFIRMED | No |
| 4 | `ENCODE_READYTORUN_HELPER` and `READYTORUN_FIXUP_Helper` both = 0x1A | CONFIRMED | No |
| 5 | All non-`ModuleOverride` fixup kinds < 0x80 | CONFIRMED | No |
| 6 | `IsInstructionSetSupported` only called inside `FEATURE_READYTORUN` | CONFIRMED | **Partially** — see below |
| 7 | Removing `SBuffer`/`PEDecoder` from `corcompile.h` safe | CONFIRMED | No |
| 8 | `kZapProfilingHandleImportValueIndex*` used only in deleted case | CONFIRMED | No |

---

### Assumption 6 — The Problematic One

**Assumption 6 Evidence included:** *"The PR built and was merged without link errors in any CI configuration."*

This is weakened by `8c19261`. The PR commit (`065d3cb`) **did not produce a fully clean build** — it left a type mismatch in `ProcessDynamicDictionaryLookup` that triggered a compile error and required a follow-up fix before landing on main.

The *specific claim* in Assumption 6 — that moving `IsInstructionSetSupported` inside the `#ifdef FEATURE_READYTORUN` block is safe — is still correct. That reasoning is supported by the function's own signature (it takes an `R2R`-specific type, so it could never be called outside the guard anyway). The logic holds independently of whether the build was clean.

But using "the build succeeded" as *evidence* for anything was over-relying on CI pass as a proof of correctness. One build configuration still failed.

---

## What the Analysis Missed

The verified assumptions covered semantic correctness thoroughly (numeric values, deletion safety, enum ranges, preprocessor guards). What they did not cover:

**Type-level correctness of function signatures that touch `ReadyToRunFixupKind`.**

Specifically: `ProcessDynamicDictionaryLookup` in `prestub.cpp` accepted `BYTE kind`. When `065d3cb` tightened the surrounding code to use enum values more consistently, the implicit narrowing conversion from the enum to `BYTE` became a compile error in at least one target. The assumptions document never checked the declared parameter types of functions that accept or forward the `kind` value — it only checked the values themselves.

---

## Summary

1. `8c19261` is a minimal one-line type fix in `prestub.cpp`, changing `BYTE kind` to `ReadyToRunFixupKind kind` in `ProcessDynamicDictionaryLookup`.
2. All 8 verified assumptions remain semantically correct — no numeric values, deletion decisions, or guard logic was wrong.
3. Assumption 6's evidence is partially undermined: its claim that "the build succeeded" was cited as supporting evidence, but `065d3cb` did not build cleanly across all configurations.
4. The gap in the analysis: it checked values and semantics but not the declared types of intermediary function parameters that forward the `kind` variable.
