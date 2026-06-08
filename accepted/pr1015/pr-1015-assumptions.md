# Assumptions: PR #1015 — Refactor createKnowledgeSuggestionTask to reduce payload parameters

## Assumption 1: Every projectId has a matching project in the database
**Claim:** When `processCreateKnowledgeSuggestion` is called, the `projectId` in the payload always resolves to an existing row via `prisma.project.findUnique`. If a project has been deleted or the ID is stale, the function now throws an error instead of silently propagating the caller-supplied values.
**Where to look:** Call sites that enqueue `createKnowledgeSuggestionTask` — specifically `generateDocsSuggestionTask` in `frontend/packages/jobs/src/trigger/jobs.ts` — to confirm `projectId` is always sourced from a DB-validated context before being passed.

## Assumption 2: Every project has at least one repositoryMapping with a populated repository
**Claim:** `project.repositoryMappings[0]?.repository` is non-null for every project that will ever reach this function. The guard `throw new Error('Repository information not found...')` is treated as an exceptional case, not a normal runtime path.
**Where to look:** The `repositoryMappings` relation definition in the Prisma schema, and whether there is any application flow that creates a project without a repository mapping before this task can be triggered.

## Assumption 3: take: 1 always selects the correct repository
**Claim:** Each project has exactly one relevant repository mapping. Using `take: 1` (with no `orderBy`) means the result is deterministic only if projects have at most one mapping. If a project can have multiple mappings, the first one returned depends on DB insertion order, which may not be the intended one.
**Where to look:** The Prisma schema for `repositoryMappings` relation cardinality, and whether any project in production has more than one mapping.

## Assumption 4: repository.installationId is safely castable to Number()
**Claim:** `installationId` is stored in the DB as a type that `Number()` converts without loss (e.g. a numeric string or a BigInt). If it is `null`, `undefined`, or a non-numeric string, `Number()` produces `NaN` or `0`, which would silently corrupt downstream behaviour rather than throwing.
**Where to look:** The Prisma schema field type for `repository.installationId`, and how the downstream `installationId` value is used after this function (e.g. passed to a GitHub API call that requires a valid integer).

## Assumption 5: repository.owner and repository.name are never null
**Claim:** The `owner` and `name` fields on the `repository` model are non-nullable, so `repositoryFullName` constructed as `${repositoryOwner}/${repositoryName}` is always a valid string. If either is nullable in the schema, the string could silently become `"null/undefined"`.
**Where to look:** The Prisma schema `Repository` model field definitions for `owner` and `name`.

## Assumption 6: Removing the three fields from generateDocsSuggestionTask's trigger call doesn't break its payload contract
**Claim:** `generateDocsSuggestionTask` previously passed `repositoryOwner`, `repositoryName`, and `installationId` to `createKnowledgeSuggestionTask.trigger()`. Removing them requires that the trigger's payload type has also been updated to not expect those fields — otherwise TypeScript would catch this, but a runtime schema mismatch (e.g. in Trigger.dev's payload validation) could silently fail.
**Where to look:** The updated `createKnowledgeSuggestionTask` payload type definition in `jobs.ts` and whether Trigger.dev performs runtime payload validation on top of TypeScript types.

## Assumption 7: The prisma client is already imported in processCreateKnowledgeSuggestion
**Claim:** The new DB query uses `prisma` directly, so the module must import a configured Prisma client instance. If the import was not added, the function throws a ReferenceError at runtime.
**Where to look:** The import section at the top of `frontend/packages/jobs/src/functions/processCreateKnowledgeSuggestion.ts`.
