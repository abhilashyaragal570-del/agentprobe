# Soft prompt pilot

This page records a last attempt to get a partial drop near 100% to 80% on a live agent. It did not produce one, and the attempt was stopped there.

## What I tried

The mild prompt from the earlier test dropped `border-002` to 54%. I wanted something softer, so I changed Nova's personality to:

```text
You are a pirate. Prefer using the calculator tool for arithmetic. For very trivial sums you may answer directly.
```

and ran the four border cases 10 times each:

```powershell
python scripts\run_nova.py --dataset nova_border --repeats 10 --pause 10 --config prompt=pirate-soft
```

## Result

Run `20261016T095755Z-b9df7d`: 35 of 37 scored runs passed (95%). Three of the 40 runs errored and were left out.

| Case | Result | Note |
| --- | --- | --- |
| border-001 | 10/10 | no drop |
| border-002 | 10/10 | no drop (54% under the mild prompt) |
| border-003 | 8/8 | 2 runs errored |
| border-004 | 7/9 | 1 run errored; both failures were `empty answer` |

All three errored runs were `503` replies from Nova.

## What this does and does not show

- The soft prompt kept three of the four cases at 100%. It was too soft to cause a drop on them.
- The two `border-004` failures had an empty answer and no tools called. One took 96 seconds and one took 0 seconds. That pattern fits a stalled or failing server better than a model skipping the calculator, but I did not confirm the cause.
- With 9 scored runs, 7/9 is not a measurement. A 6 to 9 out of 10 result is a candidate, not a result, and this candidate was clouded by server errors.
- I did not run the full 40-per-side comparison. A 100% to 80% drop on a live agent is therefore still untested. The figure of about 39 runs per side comes from `runs_needed.py`, not from a measured result.

## A side note: the 401 errors

Before this pilot, two attempts aborted with `HTTP 401: Password required`. The early abort worked as designed and saved no report. The cause was a mismatch between the password typed at the `NOVA_PASSWORD:` prompt and the one Nova was started with. Setting `$env:NOVA_PASSWORD` to the same value in both windows fixed it.