# Verification Verdict: PR #35372

## Assumption 1: `CAMUNDA_OPTIMIZE_DATABASE` resolves to the same property key as `@ConditionalOnProperty` checks
**Verdict:** ❌ Refuted
**Evidence:** `ConfigurationServiceConstants.java` defines `CAMUNDA_OPTIMIZE_DATABASE = "CAMUNDA_OPTIMIZE_DATABASE"` (the uppercase string literal, not `"camunda.database.type"`). `Main.java` calls `System.setProperty(CAMUNDA_OPTIMIZE_DATABASE, DatabaseConfig.NONE)` — i.e., `System.setProperty("CAMUNDA_OPTIMIZE_DATABASE", "none")`. However, `OptimizeDatabaseConfiguration.java` uses `@ConditionalOnProperty(prefix = "camunda.database", name = "type", havingValue = "none")`, which checks the property key `"camunda.database.type"`. These two keys are different, so `overrideOptimizeDatabaseType()` in `Main.java` sets a property that the `@ConditionalOnProperty` condition never reads. The wiring is broken.

---

## Assumption 2: The PR description accurately describes the commit under review
**Verdict:** ❌ Refuted
**Evidence:** The PR description states "Added an early startup check in `Main.java`... Fails fast with a clear, actionable error message... Prevents any resource consumption." The actual commit diff adds `overrideOptimizeDatabaseType()` to `Main.java` (which calls `System.setProperty`) and introduces a `@PostConstruct` on `OptimizeDatabaseConfiguration` that throws `IllegalStateException`. The description implies a simple early/pre-Spring check (like `System.exit(1)`), but the actual mechanism fires mid-Spring-context via `@PostConstruct` — after bean scanning has started. Additionally, as established in Assumption 1, the system property set in `Main.java` does not actually activate the `@ConditionalOnProperty`. The description is materially misleading about both the mechanism and its correctness.

---

## Assumption 3: `getDatabaseType()` property-lookup order is correct
**Verdict:** ✅ Confirmed (for the new code's internal logic, but see Assumption 1 for a wiring issue)
**Evidence:** `Main.java` diff shows: `return System.getProperty("camunda.database.type", System.getenv("CAMUNDA_DATABASE_TYPE"));` — system property has higher priority than the env var fallback. The order within `getDatabaseType()` itself is internally consistent. Whether this matches the rest of the platform's priority order is outside the scope of the changed files; within scope, the logic is coherent.

---

## Assumption 4: `@ConditionalOnProperty` with `havingValue = DatabaseConfig.NONE` handles uppercase input
**Verdict:** ✅ Confirmed (for the test's direct property path; the `overrideOptimizeDatabaseType()` path is broken per Assumption 1)
**Evidence:** `DatabaseConfig.java` confirms `NONE = "none"` (lowercase). `OptimizeDatabaseConfiguration.java` uses `havingValue = DatabaseConfig.NONE` = `"none"`. Spring Boot's `@ConditionalOnProperty` performs case-insensitive comparison, so `"NONE"` would match. `OptimizeNoSecondaryStorageIT.java` contains `shouldFailStartupWhenDatabaseTypeIsNoneUpperCase` which sets `System.setProperty("camunda.database.type", "NONE")` directly — bypassing `Main.main()` — so the test exercises the Spring condition path directly and avoids the broken `overrideOptimizeDatabaseType()` path.

---

## Assumption 5: `@PostConstruct` on `OptimizeDatabaseConfiguration` fires before Optimize consumes significant resources
**Verdict:** ❓ Unverifiable
**Evidence:** The changed files confirm that the check mechanism is `@PostConstruct` on `OptimizeDatabaseConfiguration.java`, which fires during Spring context refresh (mid-context-load, not pre-Spring). Whether Optimize's resource-heavy beans (database connections, import jobs, etc.) are initialized before or after this `@PostConstruct` depends on bean dependency order and `@DependsOn` annotations in beans outside the changed files. This cannot be determined from the two changed files and their direct imports alone.

---

## Assumption 6: `OptimizeNoSecondaryStorageIT` accurately tests `OptimizeDatabaseConfiguration`
**Verdict:** ❌ Refuted
**Evidence:** `OptimizeNoSecondaryStorageIT.java` sets `System.setProperty("camunda.database.type", "none")` directly in the test setup — it does NOT call `Main.main()` for the property-setting path, it calls `Main.main(new String[]{})` only to trigger the Spring startup. This means the test bypasses `overrideOptimizeDatabaseType()` in `Main.java` entirely. The test is testing that Spring's `@ConditionalOnProperty` on `"camunda.database.type"` works — which it would — but it does NOT test the actual `Main.main()` flow where `System.setProperty(CAMUNDA_OPTIMIZE_DATABASE, ...)` is called with the wrong key. If `overrideOptimizeDatabaseType()` is the only mechanism to set the property (e.g., when only the env var `CAMUNDA_DATABASE_TYPE` is set), the test gives false confidence that the end-to-end flow works.

---

## Assumption 7: `OptimizeNoSecondaryStorageFailureIT` tests the real configuration, not a proxy
**Verdict:** ✅ Confirmed (the assumption's concern is valid; the test uses a proxy)
**Evidence:** `OptimizeNoSecondaryStorageFailureIT.java` uses `TestOptimizeConfiguration` — an inner `@Configuration` class with identical `@ConditionalOnProperty(prefix = "camunda.database", name = "type", havingValue = DatabaseConfig.NONE)` annotation — loaded via `AnnotationConfigApplicationContext`. It does NOT load `OptimizeDatabaseConfiguration` itself. `TestOptimizeConfiguration`'s constructor directly throws `IllegalStateException` (not via `@PostConstruct`). If `OptimizeDatabaseConfiguration` had an error (wrong annotation, missing import, different condition), this acceptance test would still pass. The test validates the Spring conditional mechanism in isolation, not the production configuration class.

---

## Assumption 8: Deleting `MainTest.java` leaves the new `getDatabaseType()` env-var fallback untested
**Verdict:** ✅ Confirmed
**Evidence:** `MainTest.java` does not appear in the repo tree at commit `e90ba640` (confirmed deleted). `OptimizeNoSecondaryStorageIT.java` uses `System.setProperty("camunda.database.type", ...)` in both tests — neither test sets `CAMUNDA_DATABASE_TYPE` as an environment variable. No other test file for `Main.java`'s `getDatabaseType()` is present within the changed files or their direct test counterparts. The env-var fallback branch in `getDatabaseType()` is untested.

---

## Summary

The patch has a critical wiring bug (Assumption 1): `CAMUNDA_OPTIMIZE_DATABASE` constant equals the string `"CAMUNDA_OPTIMIZE_DATABASE"` — not `"camunda.database.type"` — so `System.setProperty(CAMUNDA_OPTIMIZE_DATABASE, DatabaseConfig.NONE)` in `Main.java` sets the wrong system property and never activates the `@ConditionalOnProperty` on `OptimizeDatabaseConfiguration`. The integration tests (`OptimizeNoSecondaryStorageIT`) inadvertently mask this bug by setting `"camunda.database.type"` directly, bypassing `Main.main()`'s broken `overrideOptimizeDatabaseType()` method entirely. Additionally, `MainTest.java` was deleted and the env-var fallback path has zero test coverage. Overall confidence in the patch is low: the core env-var-triggered startup-failure path is non-functional at the commit under review.
