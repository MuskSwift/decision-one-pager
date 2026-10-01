# Decision One-Pager Engine

CLI that turns a decision **topic** plus **materials** into a one-page Markdown memo. Output is Chinese. The six H2 headings are a stable contract so reviews and diffs can key off structure.

Python **3.10+**, standard library only — no pip packages required. Licensed under MIT.

## Six H2 contract (exact, in order)

Generated memos must contain these heading strings, exactly, in this order:

1. `## 问题陈述`
2. `## 选项对比`
3. `## 推荐`
4. `## 否决或缓做`
5. `## 待核实事实`
6. `## 明确不做`

Do not translate, rephrase, retitle, or change heading level. Body wording may vary between runs.

## Install

From the repo root (no install):

```bash
python3 -m decision_one_pager --help
```

(`python -m decision_one_pager` works when `python` is 3.10+.)

Optional editable install (exposes the `decision-one-pager` console script):

```bash
pip install -e .
```

There is also a thin wrapper at `bin/decision-one-pager`.

## Authentication (bring your own)

Generation uses model **grok-4.6**. This project does not ship API keys or implement login.

**Option A — xAI HTTP API (preferred when a key is present).** Set `XAI_API_KEY` in the environment. The CLI POSTs to `https://api.x.ai/v1/chat/completions` with stdlib `urllib.request`.

```bash
export XAI_API_KEY="xai-..."
```

**Option B — grok CLI fallback.** If `XAI_API_KEY` is unset, the CLI shells out to an already-authenticated grok CLI (typically at `~/.grok/bin`):

```bash
export PATH="$HOME/.grok/bin:$PATH"
grok -p "<prompt>" -m grok-4.6 --effort high --always-approve
```

Authenticate the grok CLI yourself before running this tool. If neither a key nor `grok` is available, generation fails.

## End-to-end example

From the repo root, using the bundled fixtures:

```bash
python3 -m decision_one_pager \
  --topic "是否把内部工具开源" \
  --materials-file examples/sample-input.md \
  --taboo-file examples/taboo-sample.txt \
  --out out/oss-one-pager.md
```

On success the CLI prints the output path (`out/oss-one-pager.md`) and exits `0`. Open that file: it should start at `## 问题陈述` and include all six headings.

Positional topic is accepted:

```bash
python3 -m decision_one_pager "是否把内部工具开源" --materials "……背景……"
```

`--materials` and `--materials-file` can be combined (concatenated). At least one materials source is required. `--taboo` / `--taboo-file` are optional.

Default output path: `./out/<slug>-one-pager.md` (spaces → `-`, unsafe characters stripped; CJK kept).

## Example paths

| Path | What it is |
| --- | --- |
| [`examples/sample-input.md`](examples/sample-input.md) | Fixture with `# topic` then `# materials` |
| [`examples/taboo-sample.txt`](examples/taboo-sample.txt) | Optional taboo / forbidden-content list |
| [`examples/sample-output.md`](examples/sample-output.md) | Hand-written sample memo in the six-heading shape |

The CLI takes `--topic` and `--materials` / `--materials-file`; it does not parse the `# topic` / `# materials` fixture format. The heading-assert script does.

## Content rules

- Output **only** the markdown one-pager with those six H2 headings, in order.
- 选项对比: at most **2** options; each must include **做法 / 代价 / 风险**.
- 推荐: pick one side and give **≤3** reasons.
- 待核实事实: label unverified items; never pretend they are verified.
- Honour the taboo list when provided.
- Write in Chinese.

After generation, a wrapping markdown fence (if the model added one) is stripped, then any leading preamble **before** the first exact `## 问题陈述` is sliced off so the saved file starts at that heading (ENG-010). All six heading strings are then checked with exact match.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Memo written; all six headings present. stdout is the output path. |
| `1` | Input error, generation failure, empty output, or missing headings. Missing headings are listed on stderr; a failed output file is removed. |
| `130` | Interrupted (`Ctrl-C`). |

The `bin/decision-one-pager` wrapper exits `127` if neither `python3` nor `python` is on `PATH`.

## Re-run heading assert

From the repo root:

```bash
bash scripts/assert_stable_headings.sh
```

The script parses topic + materials from `examples/sample-input.md`, runs `python3 -m decision_one_pager` (or `python -m`) twice into temp files, and asserts that all six heading strings appear in **each** output (body wording may differ). Prints `PASS` or `FAIL` and exits `0` / `1`. Requires a working backend (`XAI_API_KEY` or authenticated `grok` CLI).

## License

[MIT](LICENSE). See [CHANGELOG.md](CHANGELOG.md) for releases.
