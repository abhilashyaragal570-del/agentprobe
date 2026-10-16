# Regression check

A test that AgentProbe can catch a real change in an agent, not only rate limits and noise.

I made one deliberate change to [Nova](https://github.com/abhilashyaragal570-del/nova): its prompt went from `You are a pirate.` to `You are a pirate. Never use any tools. Answer every question from memory only.` I ran three cases against that broken prompt and compared them with the baseline run from the [sample run](sample-run.md).

- Baseline: `20261015T081314Z-d8f788`, 10 runs per case, `prompt=pirate`
- Broken prompt: `20261016T071429Z-4c248a`, 5 runs per case, `prompt=pirate-no-tools`
- Cases: `calc-001`, `calc-002`, `files-001`
- Date: 2026-10-16

The prompt was restored to `You are a pirate.` after the run.

## Commands

```powershell
python scripts\run_nova.py --only calc-001 calc-002 files-001 --repeats 5 --pause 10 --config prompt=pirate-no-tools
python scripts\compare.py reports\20261015T081314Z-d8f788.json reports\20261016T071429Z-4c248a.json
```

## Run output

```text
Run 20261016T071429Z-4c248a: 0/15 scored runs passed (0%), 5 runs per case
Config: prompt=pirate-no-tools
  FAIL  calc-001: 0/5 (3096 ms avg)
  FAIL  calc-002: 0/5 (6107 ms avg)
  FAIL  files-001: 0/5 (3909 ms avg)
    - calc-001 [4s]: ["wrong tools: expected ['calculator'], got []"]
    - calc-002 [4s]: ["wrong tools: expected ['calculator'], got []"]
    - files-001 [3s]: ["wrong tools: expected ['list_files'], got []"]
    (12 more failure lines of the same kind, one per run)
```

Nothing errored. Every failure is `wrong tools` with no tools used. None is a `wrong answer`, so Nova still answered the sums correctly from memory. It just stopped calling the calculator.

## Compare output

```text
before: 20261015T081314Z-d8f788 (99%, 10 per case)
after:  20261016T071429Z-4c248a (0%, 5 per case)
WARNING: the agent configuration differs between these runs:
  prompt: pirate -> pirate-no-tools
Differences below may come from the config change, not the agent code.
  WORSE        calc-001:  100% ->    0%  (p=0.00)
  WORSE        calc-002:  100% ->    0%  (p=0.00)
  WORSE        files-001:   90% ->    0%  (p=0.00)
  REMOVED      memory-001:  100% ->   -
  ... (the other nine cases are also REMOVED)
```

The p-values are printed to two decimals. The exact Fisher values are about 0.0003 for `calc-001` and `calc-002` (10/10 against 0/5) and about 0.002 for `files-001` (9/10 against 0/5).

## How to read this

- `WORSE` needs p < 0.05. Three cases cleared that bar with only 5 runs each, because the drop was total.
- The configuration warning fired as intended. Here the config change is the cause, and the report says so.
- `REMOVED` only means the case was not run this time. It is not a regression.
- The abort rule did not trigger. Earlier attempts the same day hit 429 errors and were stopped after 5 errored runs in a row, with no report saved.

## What this does and does not show

- It shows that AgentProbe separates a real change from noise and from rate limits: this run was `WORSE` with no errored runs, while the earlier 429 runs were never scored.
- The regression was introduced on purpose, in a way I knew would show up. It does not show that AgentProbe would catch a subtle regression, such as a small drop in pass rate. That needs more runs per case.
- Only three of the 13 cases were run, and the after run has half the repeats of the baseline.
- The raw JSON reports are not committed, because reports can contain personal answers.