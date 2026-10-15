# AgentProbe

[![CI](https://github.com/abhilashyaragal570-del/agentprobe/actions/workflows/ci.yml/badge.svg)](https://github.com/abhilashyaragal570-del/agentprobe/actions/workflows/ci.yml)

Evaluation and regression testing for AI agents.

LLM agents give different answers on different runs, so a single passing test proves little. AgentProbe runs every test case several times, scores each run, and tells you which cases are stable, which are flaky, and whether a change to your agent made things better, worse, or just noisier.

## What it does

- Loads test cases from a JSONL dataset (input, expected answer, expected tools).
- Runs them through an adapter: a mock agent for offline tests, or a real agent over HTTP.
- Scores each run with failure reasons (`wrong answer`, `wrong tools`, `adapter error`).
- Repeats each case N times and reports a pass rate per case, marking cases that sometimes pass and sometimes fail as **flaky**.
- Saves every run as a JSON report, including the agent settings you give it.
- Compares two reports with a Fisher exact test, so a gap that could be chance is labelled `NOISE` instead of a regression.
- Warns when two compared reports used different agent settings.

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

With Nova running:

```powershell
python scripts\run_nova.py --repeats 3 --config prompt=pirate
python scripts\run_nova.py --only calc-001 --repeats 10 --config prompt=pirate
```

The script asks for `NOVA_PASSWORD` and never prints it.

## Recording the agent configuration

Pass `--config key=value` (as many pairs as you like) to store the agent's settings in the report, for example `--config prompt=pirate model=some-model temperature=0`. They are saved in the report's `agent_config` field and printed at the end of the run. If you leave `--config` out, the run says the configuration was not recorded. Reports saved before this feature still load; they just have an empty configuration.

AgentProbe cannot read the agent's settings itself, so the values are whatever you type. Use the same keys and spelling every time, or the comparison will flag a difference that is only a typo.

## Matching answers

Cases default to exact matching. Set `"answer_match": "contains"` for LLM answers: the expected value must appear as a standalone value, and commas in numbers are ignored, so `422,734` matches `422734` and `50` does not match inside `500`.

## Comparing runs

```powershell
python scripts\compare.py reports\BEFORE.json reports\AFTER.json
```

Each case gets a verdict: `SAME`, `BETTER`, `WORSE`, `NOISE`, `NEW` or `REMOVED`. `BETTER` and `WORSE` need p < 0.05 on a Fisher exact test of the pass and fail counts.

If the two reports recorded different configurations, `compare.py` prints a warning listing each key that changed, so a prompt or model change is not mistaken for a regression in the agent's code. If neither report recorded a configuration, it prints a note saying so.

## Continuous integration

Every push to `main` and every pull request runs the unit tests and the mock-agent smoke test on Python 3.11 and 3.12 through GitHub Actions (`.github/workflows/ci.yml`). Real Nova runs are not part of CI because they need a live server and a password.

## What the Nova runs showed

- **Tool tracking works.** `calculator` and `list_files` appeared in `tools_used` once Nova's `/chat` trailer was extended to list tool names.
- **A test can be wrong, not the agent.** `memory-001` expected a `list_memories` call. Nova answered correctly from facts already in its prompt, so the expectation was changed.
- **Rate limits look like failures.** One run scored 8/15, but every failure was an HTTP 429 from the model API, not a wrong answer. That led to retries and a pause between calls, and the next run scored 14/15.
- **One slip is not a regression.** `calc-001` gave `423,734` instead of `422,734` once in 13 runs, then passed 10 of 10. A plain compare called a 100% to 67% change `WORSE`; the Fisher test labels it `NOISE`.

## Limitations

- **Timeouts cannot kill a hung thread.** On timeout the case is recorded as failed and the run moves on, but a stuck call may keep running in the background. For HTTP agents the client's own timeout cancels the request properly.
- **Small samples.** With 3 runs per case, even 0/3 versus 3/3 gives p = 0.10 (`NOISE`). Use more repeats to detect differences. Ten or more is a sensible start.
- **State-dependent cases.** Cases such as `memory-001` depend on what the agent has saved, so they are tagged `state-dependent` and are weak tests until the agent's state is controlled.
- **Cases are sequential.** Runs are one at a time, which is slow but keeps rate limits predictable.
- **Read-only tools only.** Nova pauses tools that change things until a human approves them, so the live dataset avoids them.
- **Configuration is self-reported.** The report stores the settings you pass with `--config`; it does not check them against the running agent.
- **Live reports are not committed.** `reports/*.json` is in `.gitignore` because reports can contain personal answers.

## Project layout

```text
src/agentprobe/            schemas, dataset, runner, scoring, storage, summary, compare, stats, configdiff
src/agentprobe/adapters/   base, mock, nova
datasets/                  nova_tools.jsonl (mock), nova_live.jsonl (real Nova)
scripts/                   run_eval.py, run_nova.py, compare.py
tests/unit/                81 tests, no network needed
```