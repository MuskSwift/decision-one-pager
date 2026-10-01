"""Generation backends and prompt template for Decision One-Pager Engine v0."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request

from .validate import REQUIRED_HEADINGS

XAI_API_URL = "https://api.x.ai/v1/chat/completions"
XAI_MODEL = "grok-4.6"
GROK_BIN_DIR = os.path.join(os.path.expanduser("~"), ".grok", "bin")

HEADING_BLOCK = "\n".join(REQUIRED_HEADINGS)

SYSTEM_PROMPT = f"""你是「决策一页纸」生成器。只输出一份 Markdown 决策一页纸，不要任何前言、后记、解释、问候或标题以外的内容。

必须且只能使用以下 6 个 H2 标题，顺序固定，文字必须完全一致（不得翻译、改写、增删标点或换成别的级别）：

{HEADING_BLOCK}

内容规则：
- 全文使用中文。
- 不要用 markdown 代码围栏（```）把整篇文档包起来。
- 「选项对比」最多 2 个选项。每个选项必须包含三块：做法 / 代价 / 风险。
- 「推荐」只选择其中一侧，并给出不超过 3 条理由。
- 「待核实事实」列出尚未核实的信息，每条标明「未核实」；禁止把猜测写成已证实事实。
- 「否决或缓做」写明本次不选或暂缓的选项及原因。
- 「明确不做」列出明确排除的动作或范围。
- 若用户提供了禁忌清单，输出中不得出现清单禁止的内容。
"""

USER_TEMPLATE = """请根据以下输入生成决策一页纸。

# 主题
{topic}

# 材料
{materials}

# 禁忌
{taboo}
"""


def build_user_prompt(topic: str, materials: str, taboo: str) -> str:
    taboo_text = taboo.strip() if taboo and taboo.strip() else "（无）"
    return USER_TEMPLATE.format(
        topic=topic.strip(),
        materials=materials.strip(),
        taboo=taboo_text,
    )


def combined_prompt(topic: str, materials: str, taboo: str) -> str:
    return SYSTEM_PROMPT + "\n\n" + build_user_prompt(topic, materials, taboo)


def strip_wrapping_fences(text: str) -> str:
    """Remove a single markdown fence wrapping the whole document, if present."""
    body = text.strip()
    if not body.startswith("```"):
        return body
    lines = body.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def strip_leading_preamble(markdown: str) -> str:
    """Slice from the first exact ``## 问题陈述`` so the file starts at that heading."""
    marker = "## 问题陈述"
    idx = markdown.find(marker)
    if idx == -1:
        return markdown
    return markdown[idx:].lstrip()


def generate(topic: str, materials: str, taboo: str = "") -> str:
    """Generate markdown via xAI API (if XAI_API_KEY) or grok CLI fallback."""
    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if api_key:
        return _generate_via_api(topic, materials, taboo, api_key)
    return _generate_via_grok_cli(topic, materials, taboo)


def _generate_via_api(topic: str, materials: str, taboo: str, api_key: str) -> str:
    payload = {
        "model": XAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(topic, materials, taboo)},
        ],
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        XAI_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"xAI API HTTP {exc.code}: {err_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"xAI API request failed: {exc}") from exc

    try:
        body = json.loads(raw)
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"xAI API returned unexpected payload: {raw[:2000]}") from exc

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("xAI API returned empty content")
    return content


def _generate_via_grok_cli(topic: str, materials: str, taboo: str) -> str:
    env = os.environ.copy()
    env["PATH"] = GROK_BIN_DIR + os.pathsep + env.get("PATH", "")
    prompt = combined_prompt(topic, materials, taboo)
    cmd = [
        "grok",
        "-p",
        prompt,
        "-m",
        XAI_MODEL,
        "--effort",
        "high",
        "--always-approve",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=300,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "grok CLI not found. Set XAI_API_KEY or install grok at ~/.grok/bin"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("grok CLI timed out") from exc

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"grok CLI failed (exit {result.returncode}): {err}")

    stdout = (result.stdout or "").strip()
    if not stdout:
        raise RuntimeError("grok CLI returned empty stdout")
    return stdout
