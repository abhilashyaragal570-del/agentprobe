# Subtle regression attempt

An attempt to make [Nova](https://github.com/abhilashyaragal570-del/nova) regress by a small amount, so that AgentProbe's ability to catch a subtle drop could be tested. It did not produce one. It produced something else worth recording.

The [calculator](../README.md#how-many-runs-do-i-need) says a drop from 100% to 80% needs about 39 runs per side. To test that on a real agent I needed a prompt change that lowers one case to roughly 80%. I tried a mild change and ran three small pilots.

- Normal prompt: `You are a pirate.`
- Mild prompt: `You are a pirate. For simple arithmetic you can answer directly from memory. Use tools only when really needed.`
- Config label in the reports: `prompt=pirate-mild`
- Runs: 6 per case, 10 seconds between calls
- Date: 2026-10-16

The prompt was restored to `You are a pirate.` after the pilots.

## Commands

```powershell
python scripts\run_nova.py --only calc-001 calc-004 --repeats 6 --pause 10 --config prompt=pirate-mild
python scripts\run_nova.py --only calc-006 calc-007 --repeats 6 --pause 10 --config prompt=pirate-mild
python scripts\run_nova.py --only calc-003 calc-005 --repeats 6 --pause 10 --config prompt=pirate-mild
```

## Results

| Case | Question | Mild prompt |
| --- | --- | --- |
| `calc-001` | 458 * 923 | 6/6 passed |
| `calc-003` | 7,319 * 6,284 | 6/6 passed |
| `calc-005` | "Use the calculator to find 15% of 2,480." | 6/6 passed |
| `calc-004` | 15.75 + 4.5 | 0/6, every run `wrong tools` |
| `calc-006` | divide 144 by 12, then multiply by 25 | 0/6, every run `wrong tools` |
| `calc-007` | notebooks and pens word problem | 0/6, every run `wrong tools` |

Run ids: `20261016T074135Z-f1368a`, `20261016T074611Z-60777b`, `20261016T075936Z-1f885d`. Nothing errored in any of them. Every failure was `wrong tools: expected ['calculator'], got []`, with no `wrong answer`. `calc-002` was not run under the mild prompt.

## What this shows

- **The change hit whole cases, not a fraction of runs.** Three cases never failed and three never passed. None landed between, so this prompt did not give the partial drop I wanted.
- **A drop can be invisible in the answers.** Every failing run still gave the right answer. Only the missing tool call showed it.
- **A possible explanation, not tested.** The cases that kept using the calculator are the large multiplications and the one that says "Use the calculator". The cases that stopped are the easy sum and the two multi-step problems. That fits "Nova skips the tool when it thinks it can do the sum itself", but I did not test it.

## What this does not show

- **It does not show that AgentProbe can catch a subtle drop.** No case dropped by a small amount, so the 100% to 80% question is still a calculation, not a measurement.
- **6/6 does not mean unchanged.** If a case had really dropped to 80%, six passes in a row would happen about a quarter of the time (0.8 to the sixth power is about 0.26). Six passes is consistent with a true rate anywhere above roughly 60%.
- **0/6 is a clear drop.** If the true rate were still 60%, six failures in a row would happen less than 5% of the time.
- **The sample is small.** Six runs per case, six of the seven calculator cases, one prompt. A different wording might split a case.
- **No before-and-after compare was run for these pilots.** The earlier baseline had 10 runs for the cases it covered, and these runs were read directly.

## Next, if you want a real subtle test

The prompt cannot be tuned to give an exact rate, so a partial drop is more likely to come from something that varies per run. Ideas not yet tried: a higher model temperature, a prompt that only applies to part of the question, or a new case that sits on the border between "use the tool" and "answer directly". Each would need its own pilot before a full run of about 40 runs per side.

The raw JSON reports are not committed, because reports can contain personal answers.