# Partial regression

The first time AgentProbe caught a drop that was neither total nor tiny. The [subtle regression attempt](subtle-regression.md) only produced all-or-nothing drops, so I wrote four new cases that sit between an easy sum and a big multiplication, and looked for one that splits.

## Setup

- New dataset: `datasets/nova_border.jsonl`, four calculator cases (`border-001` to `border-004`) such as "What is 256 + 389?".
- Normal prompt: `You are a pirate.`
- Mild prompt: `You are a pirate. For simple arithmetic you can answer directly from memory. Use tools only when really needed.`
- Date: 2026-10-16

## Pilots (6 runs per case)

| Case | Normal prompt | Mild prompt |
| --- | --- | --- |
| `border-001` | 6/6 | 6/6 |
| `border-002` | 6/6 | 4/6 |
| `border-003` | 6/6 | 2/5 (1 run errored) |
| `border-004` | 6/6 | 6/6 |

Two cases dropped partway. I picked `border-002` for a full run. Choosing the case that looked partial in a small sample tends to pick one that looks more extreme than it is, so the pilot rate was not trusted.

## Full run (40 runs per side, `border-002` only)

```powershell
python scripts\run_nova.py --dataset nova_border --only border-002 --repeats 40 --pause 10 --config prompt=pirate-mild
python scripts\run_nova.py --dataset nova_border --only border-002 --repeats 40 --pause 10 --config prompt=pirate
python scripts\compare.py reports\20261016T091808Z-f8063d.json reports\20261016T085315Z-063456.json
```

```text
before: 20261016T091808Z-f8063d (100%, 40 per case)
after:  20261016T085315Z-063456 (54%, 40 per case)
WARNING: the agent configuration differs between these runs:
  prompt: pirate -> pirate-mild
  WORSE        border-002:  100% ->   54%  (p=0.00)  [errored: 1 before, 1 after]
```

- Normal prompt: 39 of 39 scored runs passed. One run timed out and was left out.
- Mild prompt: 21 of 39 scored runs passed. One run timed out and was left out. All 18 failures were `wrong tools` with no tools used, none a wrong answer.
- The verdict was `WORSE` with p far below 0.05. The pilot's 4/6 had suggested about 67%; the larger sample gave 54%.

## What this shows

- AgentProbe caught a partial drop on a real agent: a case that still worked about half the time, and passed every time before.
- Nova skipped the calculator on roughly half the runs of this case, while still answering correctly. Only the tool calls showed it.
- The two timeouts did not count toward either pass rate, and the compare line shows them as `[errored: 1 before, 1 after]`.

## What this does not show

- **It is not a subtle drop.** The drop is 100% to about 54%. The calculator says a drop of that size needs about 12 runs per side, so 40 was more than enough. A drop from 100% to 80% needs about 39 per side and has still not been tested live.
- **One case, one prompt, one day.** Two of four border cases split, and only one got a full run.
- **Pilot rates were unreliable.** 4/6 became 54% at 40 runs. Six-run pilots are good for finding candidates, not for measuring them.
- **The cause is unconfirmed.** The mild prompt plausibly makes Nova answer sums directly, but I did not inspect why it skipped the tool.
- The raw JSON reports are not committed, because reports can contain personal answers.