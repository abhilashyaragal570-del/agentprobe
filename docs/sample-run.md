# Sample run

A real AgentProbe run against [Nova](https://github.com/abhilashyaragal570-del/nova): 13 test cases, 10 runs per case, 130 runs in total.

- Agent configuration: `prompt=pirate`
- Dataset: `nova_live`
- Date: 2026-10-15

This run was made before AgentProbe separated errored runs from failed ones, so it uses the earlier output format. Nothing in it was an adapter error, so the numbers are the same under the current rules.

## Command

```powershell
python scripts\run_nova.py --repeats 10 --config prompt=pirate
```

## Output

```text
Run 20261015T081314Z-d8f788: 129/130 runs passed (99%), 10 runs per case
Config: prompt=pirate
  PASS  calc-001: 10/10 (10219 ms avg)
  PASS  calc-002: 10/10 (12194 ms avg)
  FLAKY files-001: 9/10 (22330 ms avg)
  PASS  memory-001: 10/10 (4752 ms avg)
  PASS  basic-001: 10/10 (6257 ms avg)
  PASS  calc-003: 10/10 (8144 ms avg)
  PASS  calc-004: 10/10 (6166 ms avg)
  PASS  calc-005: 10/10 (4977 ms avg)
  PASS  calc-006: 10/10 (2905 ms avg)
  PASS  calc-007: 10/10 (5934 ms avg)
  PASS  multi-001: 10/10 (7003 ms avg)
  PASS  files-002: 10/10 (9901 ms avg)
  PASS  notool-001: 10/10 (4634 ms avg)
    - files-001: ["wrong tools: expected ['list_files'], got []"]
```

## What the flaky case was

One of the 10 `files-001` runs failed. The saved report shows an empty answer and a latency of about 140 seconds, just under the 150-second timeout. So the call stalled and returned nothing; Nova did not pick the wrong tool. The most likely cause is the model API being slow or rate limited, but that was not confirmed.

The run was scored as `wrong tools` because AgentProbe did not yet check for empty answers. It now reports these as `empty answer` and prints the latency next to each failure.

Re-running `files-001` alone, 10 runs, gave 10/10. One stall in 130 runs is reported here as it happened, not hidden.

## How to read this

- `PASS` means every scored run of that case passed. `FLAKY` means some passed and some failed. `FAIL` means none passed. `ERROR` means every run errored, so the case was never really tested.
- The pass rate per case matters more than the overall number, because a flaky case can hide inside a high average.
- Latency is the average time per run in milliseconds.
- `memory-001` is state-dependent: it depends on what Nova has saved, so treat its result as weaker evidence than the others.
- A clean 10/10 means no failures were seen in 10 runs. It does not prove a case can never fail.
- Runs that end in an adapter error (a 429 rate limit, a timeout, a refused connection) are marked errored. They are shown separately and left out of pass rates and comparisons.

## Compare your own runs

Run the same command with `--config` set to your own agent settings, then compare two reports:

```powershell
python scripts\compare.py reports\BEFORE.json reports\AFTER.json
```

If the two runs used different settings, the compare output starts with a warning listing what changed.