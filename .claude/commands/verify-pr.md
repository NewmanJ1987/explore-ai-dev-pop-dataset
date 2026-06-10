# /verify-pr

Runs a two-phase assumption analysis on a pull request, then generates an HTML report.

**Usage:** `/verify-pr <PR_NUMBER> <COMMIT_SHA>`

**Output folder:** `analysis/pr_<PR_NUMBER>_<SHORT_SHA>/` where `SHORT_SHA` is the first 7 characters of `COMMIT_SHA`.

---

## Phase 1 — Assumption Extraction

**Scope is strictly limited to:**
- The PR title and description (`gh pr view $PR_NUMBER --json title,body`)
- The PR diff (`gh pr diff $PR_NUMBER`)
- The commit message and patch (`git show $COMMIT_SHA`)

**Do not** read PR comments, review threads, linked issues, commit history beyond `$COMMIT_SHA`, or any files in the codebase. Do not fetch additional context to fill gaps — if the description is vague or incomplete, reflect that in the assumptions. Work only with what is explicitly in the PR description and diff.

1. Fetch the PR title and description using `gh pr view $PR_NUMBER --json title,body`
2. Fetch the PR diff using `gh pr diff $PR_NUMBER`
3. Fetch the commit details using `git show $COMMIT_SHA`
4. Run this analysis against only the above:

   > Read the PR description and see what it claims to do. Assume it may be
   > incorrect — enumerate the assumptions that must hold for this patch to be
   > correct. Take a look at the behavior of existing functions it calls, the
   > state it expects, the control flow it modifies, and the relationship between
   > the change and the stated issue. For each assumption, specify what evidence
   > in the codebase would confirm or refute it.

5. Write the output to `analysis/pr_$PR_NUMBER_$SHORT_SHA/assumptions.md` in this format:

```
# Assumptions: PR #<PR_NUMBER> — <PR title>

## Assumption 1: <short label>
**Claim:** <what must be true for the patch to be correct>
**Where to look:** <specific files, functions, or test locations that would confirm or refute this>

## Assumption 2: ...
```

---

## Phase 2 — Assumption Verification (subagent)

Spawn a subagent using Task() with the following instructions. Pass it the PR number, the short SHA, and the path to the assumptions file.

**Subagent instructions:**

You are verifying assumptions about a pull request. You have a strict scope — do not explore the full repository.

**Allowed scope only:**
- Files changed in the PR (get the list with `gh pr diff $PR_NUMBER --name-only`)
- Direct imports / dependencies of those changed files (one level deep only — do not follow transitive dependencies)
- Test files that directly test the changed files

**For each assumption in `analysis/pr_$PR_NUMBER_$SHORT_SHA/assumptions.md`:**

1. Identify which changed file(s) and their direct dependencies are relevant to this assumption
2. Read only those files
3. Check if any tests directly cover the relevant behavior
4. Classify the assumption as one of:
   - ✅ **Confirmed** — the code or tests provide clear evidence the assumption holds
   - ❌ **Refuted** — the code or tests contradict the assumption
   - ❓ **Unverifiable** — the changed files and their immediate dependencies do not contain enough information; do not speculate or explore further

**Do not** chase transitive dependencies, search the broader codebase, or mark an assumption Confirmed/Refuted based on inference alone. If the evidence isn't in scope, it's Unverifiable.

Write the verdict to `analysis/pr_$PR_NUMBER_$SHORT_SHA/verdict.md` in this format:

```
# Verification Verdict: PR #<PR_NUMBER>

## Assumption 1: <label>
**Verdict:** ✅ Confirmed / ❌ Refuted / ❓ Unverifiable
**Evidence:** <specific file + line or test that supports the verdict, or a one-line explanation of why it's unverifiable>

## Assumption 2: ...

---
## Summary
<2–3 sentences: overall confidence in the patch, any refuted assumptions that need attention>
```

---

## Phase 3 — HTML Report Generation

After Phase 2 completes, generate an HTML report by reading both output files and writing `analysis/pr_$PR_NUMBER_$SHORT_SHA/review.html`.

The HTML must follow this exact structure and dark-theme style:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>PR #<PR_NUMBER> — Assumption Verification Report</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #c9d1d9; line-height: 1.6; padding: 2rem; }
  header { max-width: 1100px; margin: 0 auto 2rem; border-bottom: 1px solid #30363d; padding-bottom: 1.5rem; }
  header h1 { font-size: 1.4rem; font-weight: 600; color: #e6edf3; margin-bottom: 0.4rem; }
  header .meta { font-size: 0.85rem; color: #8b949e; display: flex; gap: 1.5rem; flex-wrap: wrap; margin-top: 0.5rem; }
  .summary-box { max-width: 1100px; margin: 0 auto 2rem; background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 1.25rem; }
  .summary-box h3 { font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #8b949e; margin-bottom: 0.75rem; }
  .score-row { display: flex; gap: 1.25rem; margin-bottom: 1rem; flex-wrap: wrap; }
  .score-pill { display: flex; align-items: center; gap: 0.5rem; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 0.4rem 0.85rem; font-size: 0.8rem; font-weight: 600; }
  .score-pill .n { font-size: 1.1rem; font-weight: 700; }
  .score-pill.confirmed .n { color: #3fb950; }
  .score-pill.refuted .n { color: #f85149; }
  .score-pill.unverifiable .n { color: #e3b341; }
  .summary-box p { font-size: 0.875rem; color: #c9d1d9; line-height: 1.65; }
  .assumptions { max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; overflow: hidden; transition: border-color 0.15s; }
  .card:hover { border-color: #58a6ff; }
  .card-header { display: flex; align-items: center; gap: 0.75rem; padding: 0.9rem 1.25rem; border-bottom: 1px solid #30363d; background: #0d1117; cursor: pointer; user-select: none; }
  .card-header:hover { background: #161b22; }
  .card-header .num { font-size: 0.7rem; font-weight: 700; background: #21262d; border: 1px solid #30363d; border-radius: 4px; padding: 0.15rem 0.5rem; color: #8b949e; flex-shrink: 0; }
  .card-header h2 { font-size: 0.95rem; font-weight: 600; color: #e6edf3; flex: 1; }
  .badge { font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.65rem; border-radius: 20px; flex-shrink: 0; white-space: nowrap; }
  .badge-confirmed  { background: #0d4429; color: #3fb950; border: 1px solid #238636; }
  .badge-refuted    { background: #3d0914; color: #f85149; border: 1px solid #da3633; }
  .badge-unverifiable { background: #1c2128; color: #e3b341; border: 1px solid #9e6a03; }
  .chevron { color: #8b949e; font-size: 0.8rem; transition: transform 0.2s; flex-shrink: 0; }
  .card.open .chevron { transform: rotate(90deg); }
  .card-body { display: none; padding: 1.25rem; }
  .card.open .card-body { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
  @media (max-width: 720px) { .card.open .card-body { grid-template-columns: 1fr; } }
  .pane { display: flex; flex-direction: column; gap: 0.5rem; }
  .pane-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #8b949e; display: flex; align-items: center; gap: 0.4rem; }
  .pane-label .dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
  .pane-label .dot-blue   { background: #388bfd; }
  .pane-label .dot-green  { background: #3fb950; }
  .pane-label .dot-red    { background: #f85149; }
  .pane-label .dot-yellow { background: #e3b341; }
  .pane-content { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 0.9rem 1rem; font-size: 0.85rem; color: #c9d1d9; flex: 1; }
  .pane-content p { margin-bottom: 0.6rem; }
  .pane-content p:last-child { margin-bottom: 0; }
  .pane-content code { background: #21262d; border: 1px solid #30363d; border-radius: 4px; padding: 0.1rem 0.35rem; font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.8rem; color: #d2a8ff; }
  .pane-content .where { margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #21262d; font-size: 0.8rem; color: #8b949e; }
  .verdict-section { display: flex; flex-direction: column; gap: 0.3rem; }
  .verdict-section-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #8b949e; }
  .verdict-section-body { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 0.75rem 1rem; font-size: 0.85rem; color: #c9d1d9; }
  .verdict-section-body code { background: #21262d; border: 1px solid #30363d; border-radius: 4px; padding: 0.1rem 0.35rem; font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.8rem; color: #d2a8ff; }
</style>
</head>
<body>

<header>
  <h1>PR #<PR_NUMBER> — <PR_TITLE></h1>
  <div class="meta">
    <span>🔀 <a href="<PR_URL>" target="_blank" style="color:#58a6ff;text-decoration:none;">Pull Request #<PR_NUMBER> ↗</a></span>
    <span>🔑 Commit <code style="background:#21262d;border:1px solid #30363d;border-radius:4px;padding:0.1rem 0.35rem;font-size:0.8rem;color:#d2a8ff"><SHORT_SHA></code></span>
    <span>📄 Files changed: <FILES_LIST></span>
  </div>
</header>

<div class="summary-box">
  <h3>Overall Summary</h3>
  <div class="score-row" id="score-row"></div>
  <p id="summary-text"></p>
</div>

<div class="assumptions" id="assumptions"></div>

<script>
const data = [
  // One object per assumption, in order:
  {
    id: 1,
    label: "<assumption label>",
    verdict: "confirmed",          // "confirmed" | "refuted" | "unverifiable"
    claim: `<claim text — use <code> tags for identifiers>`,
    where: `<where-to-look text>`,
    evidence: `<evidence text — use <code> tags for identifiers>`,
  },
  // ... repeat for each assumption
];

const summaryText = `<2-3 sentence overall summary from verdict.md>`;

const verdictMeta = {
  confirmed:    { label: "✅ Confirmed",    cls: "badge-confirmed",    dot: "dot-green"  },
  refuted:      { label: "❌ Refuted",      cls: "badge-refuted",      dot: "dot-red"    },
  unverifiable: { label: "❓ Unverifiable", cls: "badge-unverifiable", dot: "dot-yellow" },
};

function buildCard(item) {
  const vm = verdictMeta[item.verdict];
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `
    <div class="card-header" onclick="toggleCard(this)">
      <span class="num">A${item.id}</span>
      <h2>${item.label}</h2>
      <span class="badge ${vm.cls}">${vm.label}</span>
      <span class="chevron">▶</span>
    </div>
    <div class="card-body">
      <div class="pane">
        <div class="pane-label"><span class="dot dot-blue"></span>Phase 1 — Assumption</div>
        <div class="pane-content">
          <p>${item.claim}</p>
          <div class="where"><strong>Where to look:</strong> ${item.where}</div>
        </div>
      </div>
      <div class="pane">
        <div class="pane-label"><span class="dot ${vm.dot}"></span>Phase 2 — Verdict</div>
        <div class="verdict-section">
          <div class="verdict-section-label">Evidence</div>
          <div class="verdict-section-body">${item.evidence}</div>
        </div>
      </div>
    </div>
  `;
  return card;
}

function toggleCard(header) { header.closest(".card").classList.toggle("open"); }

const container = document.getElementById("assumptions");
data.forEach(item => container.appendChild(buildCard(item)));

const counts = { confirmed: 0, refuted: 0, unverifiable: 0 };
data.forEach(d => counts[d.verdict]++);
const scoreRow = document.getElementById("score-row");
[{ key: "confirmed", label: "Confirmed" }, { key: "refuted", label: "Refuted" }, { key: "unverifiable", label: "Unverifiable" }].forEach(({ key, label }) => {
  const pill = document.createElement("div");
  pill.className = `score-pill ${key}`;
  pill.innerHTML = `<span class="n">${counts[key]}</span><span>${label}</span>`;
  scoreRow.appendChild(pill);
});
document.getElementById("summary-text").innerHTML = summaryText;
document.querySelectorAll(".card")[0]?.classList.add("open");
</script>
</body>
</html>
```

**Instructions for filling in the template:**

- Replace `<PR_NUMBER>`, `<PR_TITLE>`, `<PR_URL>`, `<SHORT_SHA>`, `<FILES_LIST>` in the header with real values fetched earlier.
- Populate the `data` array with one object per assumption, cross-referencing `assumptions.md` (for `claim` and `where`) and `verdict.md` (for `verdict` and `evidence`).
- Map verdict text to the `verdict` field: "✅ Confirmed" → `"confirmed"`, "❌ Refuted" → `"refuted"`, "❓ Unverifiable" → `"unverifiable"`.
- Set `summaryText` to the Summary paragraph from `verdict.md`.
- Use `<code>` HTML tags (not backticks) for inline identifiers inside `claim`, `where`, and `evidence` strings.
- Write the completed file to `analysis/pr_$PR_NUMBER_$SHORT_SHA/review.html`.
