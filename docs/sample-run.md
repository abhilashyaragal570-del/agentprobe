# Sample run

A real AgentProbe run against [Nova](https://github.com/abhilashyaragal570-del/nova), 10 runs per case.

- Agent configuration: `prompt=pirate`
- Dataset: `nova_live`
- Date: 2026-10-15

## Command

```powershell
python scripts\run_nova.py --repeats 10 --config prompt=pirate
```

## Output

```text
Run 20261015T071406Z-cf6336: 50/50 runs passed (100%), 10 runs per case
Config: prompt=pirate
  PASS  calc-001: 10/10 (9050 ms avg)
  PASS  calc-002: 10/10 (10139 ms avg)
  PASS  files-001: 10/10 (7521 ms avg)
  PASS  memory-001: 10/10 (2413 ms avg)
  PASS  basic-001: 10/10 (3733 ms avg)
```

## How to read this

- `PASS` means every run of that case passed. `FLAKY` means some runs passed and some failed. `FAIL` means none passed.
- The pass rate per case matters more than the overall number, because a flaky case can hide inside a high average.
- Latency is the average time per run in milliseconds.
- `memory-001` is state-dependent: it depends on what Nova has saved, so treat its result as weaker evidence than the others.
- A clean 10/10 means no failures were seen in 10 runs. It does not prove the case can never fail. Earlier runs of `calc-001` showed a single wrong answer in 13 runs.

## Compare your own runs

Run the same command with `--config` set to your own agent settings, then compare two reports:

```powershell
python scripts\compare.py reports\BEFORE.json reports\AFTER.json
```

If the two runs used different settings, the compare output starts with a warning listing what changed.