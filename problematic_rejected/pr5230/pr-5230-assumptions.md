# Assumptions: PR #5230 — feat: support my_service.py syntax for service loading

> **Note on commit vs PR diff discrepancy:** The commit SHA `0e837ef1cbb6e5c312a87ba268cee32d2b7e1f90`
> uses `s.__class__.__name__` to extract service names, while the current PR diff uses `s.inner.__name__`.
> These are different expressions with different semantics and the commit patch diverges from the PR diff.
> All assumptions below are noted with which version they apply to.

---

## Assumption 1: Branch ordering in `normalize_identifier` is safe
**Claim:** The new `.py` file branch is inserted *before* the `service.py` directory fallback,
meaning a path like `/some/dir/service.py` passed as a string would be handled by the new branch
(returning `"service"` as module name and `/some/dir` as path) rather than the directory branch.
This ordering is intentional and does not silently swallow directory-style invocations.
**Where to look:** `src/_bentoml_impl/loader.py` — the full `normalize_identifier` function,
specifically the `elif` chain. Check what other branches precede and follow the new one, and whether
any caller ever passes a `.py` path that was previously handled by a later branch.

---

## Assumption 2: `path.stem` reliably extracts a valid Python module name
**Claim:** For any `.py` file, `path.stem` (e.g. `my_service` from `my_service.py`) always
produces an importable module name. This assumes the filename has no dots before `.py` (e.g.
`foo.bar.py` would give `foo.bar`, which is not a valid module name), and that the stem is
directly used as the module identifier in downstream `import_service` calls.
**Where to look:** `src/_bentoml_impl/loader.py` — how the returned `module_name` from
`normalize_identifier` is subsequently used in `import_service` or callers; check if there is
any validation of the module name string.

---

## Assumption 3: `path.parent` is the correct `bento_path` for `.py` files
**Claim:** When no explicit `working_dir` is provided and a `.py` file is given, the PR returns
`path.parent` as the bento/working path. This assumes that the directory containing the `.py`
file is the correct root for resolving imports, configs, and other project files.
**Where to look:** `src/_bentoml_impl/loader.py` — how `bento_path` is used after
`normalize_identifier` returns; compare with how other branches (e.g. directory with
`bentofile.yaml`) set the path.

---

## Assumption 4: Service objects have a `.inner` attribute with `__name__` (PR diff version)
**Claim:** In the PR diff, `service_names = [s.inner.__name__ for s in all_services]` assumes
that every element in `all_services` has an `.inner` attribute that is the original decorated
class, and that `.__name__` on it returns the human-readable class name (e.g. `"Service1"`).
If `.inner` does not exist or is not the class itself, this will raise `AttributeError` or
produce wrong names.
**Where to look:** `src/_bentoml_impl/loader.py` — the `Service` or service-wrapper class
definition; check what type `all_services` contains and whether `.inner` is a defined attribute.
Also relevant: the test `test_import_service_multiple_services_error` which asserts `"Service1"`
and `"Service2"` appear in the error.

---

## Assumption 5: `s.__class__.__name__` is wrong for service wrappers (commit version)
**Claim:** The commit (`0e837ef1`) uses `s.__class__.__name__` instead of `s.inner.__name__`.
If service objects are instances of a generic wrapper class (e.g. `Service` or `BentoService`),
then `s.__class__.__name__` would return the wrapper's class name rather than the user-defined
class name, making the error message unhelpful or incorrect. The PR diff's `s.inner.__name__`
is the corrected version.
**Where to look:** Same as Assumption 4. If the wrapper class is named something generic,
`s.__class__.__name__` would be wrong; if it's dynamically constructed from the user class,
it could be correct.

---

## Assumption 6: Backward compatibility with directory-based and `service.py` conventions
**Claim:** The PR claims backward compatibility. The new `.py` branch is inserted before the
`service.py` directory check, so passing a *directory path* still falls through to the existing
`service.py` check unmodified. A directory with a `service.py` inside is not mistakenly matched
by the new branch (since `path.is_file()` would be `False` for a directory).
**Where to look:** `src/_bentoml_impl/loader.py` — confirm that `path.is_file()` correctly
filters out directory inputs and that no existing call site passes a `.py` filename embedded in
a directory string.

---

## Assumption 7: The test for multiple services accurately reflects runtime behavior
**Claim:** `test_import_service_multiple_services_error` writes a real `.py` file with two
`@bentoml.service`-decorated classes, then calls `import_service`. This requires that:
(a) `@bentoml.service` works without a running server/runtime environment in a test context,
(b) the module is actually imported (not mocked), and
(c) the error is raised during the `import_service` call itself, not during the decorator
application.
**Where to look:** `src/_bentoml_impl/loader.py` — `import_service` implementation; check
whether `@bentoml.service` has side effects (registration, server init) that would fail in a
unit test with `tmp_path`.
