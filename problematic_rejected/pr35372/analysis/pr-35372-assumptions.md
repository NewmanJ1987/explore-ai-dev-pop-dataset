# Assumptions: PR #35372 — feat: Disable Optimize in no-db mode with fail-fast startup check

## Assumption 1: `CAMUNDA_OPTIMIZE_DATABASE` resolves to the same property key as `@ConditionalOnProperty` checks

**Claim:** `Main.java` calls `System.setProperty(CAMUNDA_OPTIMIZE_DATABASE, DatabaseConfig.NONE)` where `CAMUNDA_OPTIMIZE_DATABASE` comes from `ConfigurationServiceConstants`. `OptimizeDatabaseConfiguration` checks `@ConditionalOnProperty(prefix = "camunda.database", name = "type")` — resolving to `camunda.database.type`. For the Spring condition to be triggered by the system property set in `main()`, `CAMUNDA_OPTIMIZE_DATABASE` must equal `"camunda.database.type"`. If they differ (e.g., `"camunda.optimize.database"`), the `@ConditionalOnProperty` path is never activated via `overrideOptimizeDatabaseType()`.

**Where to look:** `optimize/util/optimize-commons/src/main/java/io/camunda/optimize/service/util/configuration/ConfigurationServiceConstants.java` — read the value of `CAMUNDA_OPTIMIZE_DATABASE`. If it is not `"camunda.database.type"`, the wiring is broken.

---

## Assumption 2: The PR description accurately describes the commit under review

**Claim:** The PR description says "Added an early startup check in `Main.java` that reads the global `camunda.database.type` configuration flag... Fails fast with a clear, actionable error message... Prevents any resource consumption." The commit diff (`e90ba640`) shows the OPPOSITE: it REMOVES `checkForNoSecondaryStorageMode()` / `System.exit(1)` from `Main.java` and REPLACES it with Spring conditional configuration (`OptimizeDatabaseConfiguration`). The description was written for an earlier commit and does not describe the refactoring in this commit.

**Where to look:** The commit diff itself directly refutes the PR description — the description is a mismatch with the actual change.

---

## Assumption 3: `getDatabaseType()` property-lookup order is correct

**Claim:** The new implementation uses:
```java
return System.getProperty("camunda.database.type", System.getenv("CAMUNDA_DATABASE_TYPE"));
```
This reads the system property first and falls back to the env var. The old code (deleted in this commit) checked env var first, then system property. The assumption is that system property should have higher priority than the env var — the same order assumed by the rest of Camunda's property resolution.

**Where to look:** Other callers of `camunda.database.type` and `CAMUNDA_DATABASE_TYPE` across the platform to confirm priority order. Also check if Spring Boot's `RelaxedBindingStrategy` for env vars means `CAMUNDA_DATABASE_TYPE` already maps to `camunda.database.type` and could be double-read.

---

## Assumption 4: `@ConditionalOnProperty` with `havingValue = DatabaseConfig.NONE` handles uppercase input

**Claim:** If an operator sets `CAMUNDA_DATABASE_TYPE=NONE` (uppercase), `getDatabaseType()` returns "NONE", `equalsIgnoreCase` in `overrideOptimizeDatabaseType()` matches it, and sets the system property to `DatabaseConfig.NONE` (presumably lowercase "none"). The `@ConditionalOnProperty(havingValue = DatabaseConfig.NONE)` then matches. The test `shouldFailStartupWhenDatabaseTypeIsNoneUpperCase` covers this path.

**Where to look:** `io/camunda/search/connect/configuration/DatabaseConfig.java` — confirm `NONE = "none"` (lowercase). Spring Boot `@ConditionalOnProperty` performs case-insensitive comparison via `havingValue`.

---

## Assumption 5: `@PostConstruct` on `OptimizeDatabaseConfiguration` fires before Optimize consumes significant resources

**Claim:** The PR claims the change "prevents any resource consumption." Using `@PostConstruct` fires during Spring context initialization — after component scanning and `@Configuration` class instantiation has begun. The check does NOT run before Spring starts; it fires mid-context-load. The `IllegalStateException` causes a `BeanCreationException` and context refresh failure, but other beans may have already been initialized.

**Where to look:** Spring Boot's bean ordering and application event lifecycle — check whether Optimize's database connections or expensive beans are initialized before or after `OptimizeDatabaseConfiguration`'s `@PostConstruct`.

---

## Assumption 6: `OptimizeNoSecondaryStorageIT` accurately tests `OptimizeDatabaseConfiguration`

**Claim:** `OptimizeNoSecondaryStorageIT` calls `Main.main()` and expects a `BeanCreationException` rooted in `IllegalStateException`. For this to work: (a) `overrideOptimizeDatabaseType()` must set the property correctly so `@ConditionalOnProperty` activates, (b) the Spring context must load `OptimizeDatabaseConfiguration`, and (c) the `@PostConstruct` must throw and propagate. If Assumption 1 is false (property name mismatch), `@ConditionalOnProperty` never activates and the test would pass a no-op — the exception would not be thrown and the test would fail.

**Where to look:** `OptimizeNoSecondaryStorageIT.java` — check the exception assertion; also confirm `Main.class` scan includes the `configuration` package where `OptimizeDatabaseConfiguration` lives.

---

## Assumption 7: `OptimizeNoSecondaryStorageFailureIT` tests the real configuration, not a proxy

**Claim:** The acceptance test (`OptimizeNoSecondaryStorageFailureIT`) uses `TestOptimizeConfiguration` — an inner static class annotated with the same `@ConditionalOnProperty` as `OptimizeDatabaseConfiguration` — loaded via `AnnotationConfigApplicationContext`. This does NOT test `OptimizeDatabaseConfiguration` itself. If `OptimizeDatabaseConfiguration` has a different condition, missing import, or different bean behavior, the acceptance test will pass while the production configuration breaks.

**Where to look:** Compare `OptimizeNoSecondaryStorageFailureIT.TestOptimizeConfiguration` annotations against `OptimizeDatabaseConfiguration` — specifically check that `DatabaseConfig.NONE` resolves identically in both.

---

## Assumption 8: Deleting `MainTest.java` leaves the new `getDatabaseType()` env-var fallback untested

**Claim:** The deleted `MainTest.java` tested the static helpers `isNoSecondaryStorageMode()` and `getDatabaseType()`. The replacement `getDatabaseType()` in `Main.java` has a new behavior: it reads `System.getenv("CAMUNDA_DATABASE_TYPE")` as fallback. No unit test covers this env-var path. `OptimizeNoSecondaryStorageIT` only sets `System.setProperty("camunda.database.type", "none")` — it never exercises the env-var branch.

**Where to look:** `OptimizeNoSecondaryStorageIT.java` and any other test file — grep for `CAMUNDA_DATABASE_TYPE` to check if the env-var fallback path is tested anywhere.
