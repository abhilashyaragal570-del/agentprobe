# AgentProbe

[![CI](https://github.com/abhilashyaragal570-del/agentprobe/actions/workflows/ci.yml/badge.svg)](https://github.com/abhilashyaragal570-del/agentprobe/actions/workflows/ci.yml)

Evaluation and regression testing for AI agents.

LLM agents give different answers on different runs, so a single passing test proves little. AgentProbe runs every test case several times, scores each run, and tells you which cases are stable, which are flaky, and whether a change to your agent made things better, worse, or just noisier.

## What it does

- Loads test cases from a JSONL dataset (input, expected answer, expected tools).
- Runs them through an adapter: a mock agent for offline tests, or a real agent over HTTP.
- Scores each run with failure reasons (`wrong answer`, `wrong tools`, `empty answer`).
- Marks runs that ended in an adapter error (rate limit, timeout, connection refused) as **errored**, and leaves them out of pass rates and comparisons.
- Repeats each case N times and reports a pass rate per case, marking cases that sometimes pass and sometimes fail as **flaky**.
- Stops early when several runs in a row error, instead of grinding on and saving a useless report.
- Saves every run as a JSON report, including the agent settings you give it.
- Compares two reports with a Fisher exact test, so a gap that could be chance is labelled `NOISE` instead of a regression.
- Warns when two compared reports used different agent settings.
- Calculates how many runs per case you need to catch a drop of a given size.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
python scripts\run_eval.py
```

`run_eval.py` uses the built-in mock agent, so it needs no server and no API key.

## Testing a real agent

The first real target is [Nova](https://github.com/abhilashyaragal570-del/nova), a FastAPI assistant that calls tools. `NovaAdapter` talks to Nova over HTTP:

- creates a fresh conversation for every case, so cases cannot influence each other
- sends the question to `POST /chat` and cuts the token trailer off the answer
- reads the names of the tools Nova used from that trailer
- retries on rate limits (HTTP 429 and 503) with a growing wait

The live dataset, `datasets/nova_live.jsonl`, has 13 cases: single and multi-step arithmetic, large numbers, decimals, percentages, a word problem, listing files, a missing file, a question that needs two tools, a question that needs none, and a memory case. A second dataset, `datasets/nova_border.jsonl`, has four mid-difficulty sums used to look for partial drops. Pick a dataset with `--dataset nova_border`. Unit tests load every dataset file and check for empty inputs, duplicate case ids and empty expected answers, so a typo is caught before a live run.

With Nova running (for example `uvicorn web.fastapi_app:app --port 8000` in the Nova folder):

```powershell
python scripts\run_nova.py --repeats 10 --config prompt=pirate
python scripts\run_nova.py --only calc-001 --repeats 10 --config prompt=pirate
```

A full run is 130 calls and takes about 25 to 30 minutes, because cases run one at a time. The script asks for `NOVA_PASSWORD` and never prints it. A mistyped password shows up as `HTTP 401` errors and triggers the early abort. Nova must be started with the same `NOVA_PASSWORD` value you give the script; setting `$env:NOVA_PASSWORD` in both windows avoids a mismatch.

## Errored runs and early abort

A run that ends in an adapter error is not a verdict on the agent: the model API may have been rate limited, the call may have timed out, or the server may not have been running. AgentProbe marks such runs `errored`, shows them separately, and excludes them from pass rates, flaky detection and comparisons. An empty answer with no error still counts as a failure, because the cause is unknown.

`run_nova.py` stops after 5 errored runs in a row and saves no report. Its message says Nova is probably down or rate limited, but the last line shows the real error (429 for a quota, 401 for a wrong password). Change the limit with `--abort-after N`, or use `0` to turn it off. If a finished run contains errored runs, it prints a warning and the error messages, and you should re-run those cases before comparing.

## Recording the agent configuration

Pass `--config key=value` (as many pairs as you like) to store the agent's settings in the report, for example `--config prompt=pirate model=some-model temperature=0`. They are saved in the report's `agent_config` field and printed at the end of the run. If you leave `--config` out, the run says the configuration was not recorded. Reports saved before this feature still load; they just have an empty configuration.

AgentProbe cannot read the agent's settings itself, so the values are whatever you type. Use the same keys and spelling every time, or the comparison will flag a difference that is only a typo.

## Matching answers

Cases default to exact matching. Set `"answer_match": "contains"` for LLM answers: the expected value must appear as a standalone value, and commas in numbers are ignored, so `422,734` matches `422734` and `50` does not match inside `500`.

## Comparing runs

```powershell
python scripts\compare.py reports\BEFORE.json reports\AFTER.json
```

Each case gets a verdict: `SAME`, `BETTER`, `WORSE`, `NOISE`, `NEW`, `REMOVED` or `INCONCLUSIVE`. `BETTER` and `WORSE` need p < 0.05 on a Fisher exact test of the pass and fail counts. `INCONCLUSIVE` means one side had no usable runs because every run errored.

Errored runs are ignored in the comparison, so a rate limit cannot show up as a regression. If the two reports recorded different configurations, `compare.py` prints a warning listing each key that changed, so a prompt or model change is not mistaken for a regression in the agent's code. If neither report recorded a configuration, it prints a note saying so.

## How many runs do I need?

A small drop needs many more runs than a large one. `runs_needed.py` works out how often `compare.py` would call a drop `WORSE`, using the same Fisher test, for a given true pass rate before and after:

```powershell
python scripts\runs_needed.py --before 1.0 --after 0.8
python scripts\runs_needed.py --before 1.0 --after 0.5
```

Results from running it:

| Drop | 10 runs per side | 20 runs | 50 runs | Runs for 80% power |
| --- | --- | --- | --- | --- |
| 100% to 80% | caught 3% of the time | 37% | 95% | 39 |
| 100% to 67% | caught 21% of the time | 84% | 100% | 19 |
| 100% to 50% | caught 62% of the time | 99% | 100% | 12 |

So a clean `SAME` or `NOISE` from a 10-run comparison does not rule out a drop from 100% to 80%: it would be missed about 97% of the time. The calculation assumes both sides have the pass rates you enter and use the same number of runs. Treat the answer as a minimum, because power does not rise perfectly smoothly with the run count.

## Sample run

A real 13-case, 10-runs-per-case run against Nova is in [docs/sample-run.md](docs/sample-run.md): 129 of 130 runs passed. One case, `files-001`, was flaky because a single call stalled for about 140 seconds and returned nothing. The page shows the exact command, the output and how to read it. The raw JSON report is not committed.

## Regression check

[docs/regression-check.md](docs/regression-check.md) shows AgentProbe catching a change I made on purpose. I told Nova never to use tools, ran three cases, and compared them with the sample run. All three (`calc-001`, `calc-002`, `files-001`) came out `WORSE`, with every failure a `wrong tools` reason and no `wrong answer`. The configuration warning named the prompt change. The page has the commands, the output and what the check does and does not show.

## Subtle regression attempt

[docs/subtle-regression.md](docs/subtle-regression.md) records an attempt to make Nova regress by only a little. I gave it a mild prompt ("answer simple arithmetic from memory") and ran three 6-run pilots. Three cases stayed at 6/6 and three fell to 0/6, with nothing in between, so the attempt did not produce a partial drop. The page lists every case, what the results do and do not show, and ideas for a real subtle test.

## Partial regression

[docs/partial-regression.md](docs/partial-regression.md) follows up with four new mid-difficulty cases. Under the same mild prompt, two of them dropped partway in a 6-run pilot. A 40-runs-per-side test of `border-002` went from 39/39 to 21/39 (100% to 54%) and compare called it `WORSE`, with the two timeouts left out. This is a partial drop caught on a real agent, but not the subtle 100% to 80% drop.

## Soft prompt pilot

[docs/soft-prompt-pilot.md](docs/soft-prompt-pilot.md) records a last try at a drop near 100% to 80%. With a softer prompt that kept the calculator as the default, a 10-run pilot of the four border cases left three at 100% and `border-004` at 7/9, with both failures empty answers and three `503` errors during the run. That looks like server trouble rather than a prompt effect, so I stopped there and did not run the full comparison. The 100% to 80% case stays untested live.

## Continuous integration

Every push to `main` and every pull request runs the unit tests and the mock-agent smoke test on Python 3.11 and 3.12 through GitHub Actions (`.github/workflows/ci.yml`). Real Nova runs are not part of CI because they need a live server and a password.

## What the Nova runs showed

- **Tool tracking works.** `calculator` and `list_files` appeared in `tools_used` once Nova's `/chat` trailer was extended to list tool names.
- **A test can be wrong, not the agent.** `memory-001` expected a `list_memories` call. Nova answered correctly from facts already in its prompt, so the expectation was changed.
- **Rate limits look like failures.** One run scored 8/15, but every failure was an HTTP 429 from the model API, not a wrong answer. That led to retries and a pause between calls, and the next run scored 14/15.
- **One slip is not a regression.** `calc-001` gave `423,734` instead of `422,734` once in 13 runs, then passed 10 of 10. A plain compare called a 100% to 67% change `WORSE`; the Fisher test labels it `NOISE`.
- **A stall can look like a tool error.** In a 130-run check, one `files-001` run took about 140 seconds and returned an empty answer, and was scored as `wrong tools`. A re-run gave 10/10. AgentProbe now reports such runs as `empty answer` and shows each failure's latency.
- **Throttling can ruin a whole run.** A later 12-run check scored 0/12, with every run failing on error 429 after about 65 seconds. AgentProbe now marks those runs as errored and stops early, so they can no longer pass for a regression. The abort stopped later attempts the same way, with no report saved.
- **A deliberate regression is caught.** With a no-tools prompt, `calc-001` and `calc-002` fell from 100% to 0% and `files-001` from 90% to 0%, all `WORSE` at p < 0.01, with no errored runs. The answers stayed correct; only the tool calls disappeared. A check that looked only at answers would have missed it.
- **A prompt change hit whole cases.** Under a mild prompt, three calculator cases stayed at 6/6 and three went to 0/6, with none in between.
- **A partial drop was caught, and the pilot overstated the pass rate.** `border-002` read 4/6 in a pilot but 21/39 (54%) over 40 runs, against 39/39 on the normal prompt. Six-run pilots find candidates; they do not measure them.
- **Occasional timeouts are normal.** One run in 40 timed out on each side of the border test. Because errored runs are excluded, they did not change either pass rate.
- **A softer prompt did not give a clean 80% case.** Three border cases stayed at 100%, and the fourth was clouded by `503` errors and empty answers.
- **The early abort catches a wrong password.** Two runs stopped with `HTTP 401: Password required` after 5 errored runs and saved no report, which is the intended behaviour.

## Limitations

- **Timeouts cannot kill a hung thread.** On timeout the case is recorded as errored and the run moves on, but a stuck call may keep running in the background. For HTTP agents the client's own timeout cancels the request properly.
- **Small samples.** With 3 runs per case, even 0/3 versus 3/3 gives p = 0.10 (`NOISE`). Ten runs catch a drop from 100% to 50% about 62% of the time, but a drop from 100% to 80% only about 3% of the time. See "How many runs do I need?".
- **State-dependent cases.** Cases such as `memory-001` depend on what the agent has saved, so they are tagged `state-dependent` and are weak tests until the agent's state is controlled.
- **Cases are sequential.** Runs are one at a time, which is slow but keeps rate limits predictable.
- **Read-only tools only.** Nova pauses tools that change things until a human approves them, so the live dataset avoids them.
- **Configuration is self-reported.** The report stores the settings you pass with `--config`; it does not check them against the running agent.
- **No drop as small as 100% to 80% has been tested live.** The largest partial drop caught was 100% to 54% on one case, with 40 runs per side. A softer prompt was tried in a 10-run pilot and did not give a usable candidate. The calculator's figure of about 39 runs per side for 100% to 80% is a calculation, not a measured result. No regression has appeared on its own: apart from occasional stalls and timeouts, every case passes on the current Nova.
- **The calculator assumes known pass rates.** It tells you how many runs a drop of a size you pick would need. It cannot tell you what drop your agent will actually have.
- **Errored runs hide real failures.** A server that fails with an error on every call looks the same as a rate limit, so check the printed error messages before trusting a run.
- **Live reports are not committed.** `reports/*.json` is in `.gitignore` because reports can contain personal answers.
- **The run scripts have no automated tests.** `run_nova.py` and `compare.py` are checked by reading their output, and the dataset tests only cover the files in `datasets/`. The comparison logic and config helpers behind `compare.py` are unit tested.

## Project layout

```text
src/agentprobe/            schemas, dataset, runner, scoring, storage, summary, compare, stats, power, configdiff
src/agentprobe/adapters/   base, mock, nova
datasets/                  nova_tools.jsonl (mock), nova_live.jsonl (13 real Nova cases), nova_border.jsonl (4 border cases)
scripts/                   run_eval.py, run_nova.py, compare.py, runs_needed.py
docs/                      sample-run.md, regression-check.md, subtle-regression.md, partial-regression.md, soft-prompt-pilot.md
tests/unit/                133 tests, no network needed
```