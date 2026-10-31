"""Local implementation of ai-shifu/detect-agent 0.1.9 (MIT).

Specification attribution (MIT License):
Copyright (c) 2026 ai-shifu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping


SPEC_VERSION = "0.1.9"
SPEC_COMMIT = "1da565572418fd88da8b782ebbda53f2a321d310"

# Product spelling is also the bounded CLI display-name contract. Context-only
# products are reportable only when explicitly declared, not from a context hint.
AGENT_DISPLAY_NAMES = {
    "crush": "Crush",
    "hermes-agent": "Hermes Agent",
    "kilo-code": "Kilo Code",
    "trae": "TRAE",
    "vtcode": "VT Code",
    "workbuddy": "WorkBuddy",
    "grok-bot": "Grok Bot",
    "qwenwork": "QwenWork",
    "cue": "Cue",
    "muse": "Muse",
    "manus": "Manus",
    "doubao-work": "Doubao Work",
    "kimi": "Kimi Code",
    "grok-build": "Grok Build",
    "gemini-cli": "Gemini CLI",
    "cline": "Cline",
    "codex": "Codex",
    "antigravity": "Antigravity",
    "augment-cli": "Augment CLI",
    "opencode": "opencode",
    "goose": "Goose",
    "junie": "Junie",
    "pi": "Pi",
    "cowork": "Claude Cowork",
    "claude-code": "Claude Code",
    "cursor-cli": "Cursor CLI",
    "kiro": "Kiro",
    "openclaw": "OpenClaw",
    "github-copilot": "GitHub Copilot",
    "replit": "Replit",
    "devin": "Devin",
    "instinct": "Instinct",
    "lingguang": "Lingguang",
    "cursor": "Cursor",
    "zed": "Zed",
    "hi": "hi",
    "sandbase-harness": "SandBase Harness",
}

_DECLARATION_ALIASES = {
    "codex_cli": "codex",
    "claude_code": "claude-code",
    "gemini_cli": "gemini-cli",
    "open_code": "opencode",
    "grok": "grok-build",
}
_ASCII_TRIM = "\t\n\v\f\r "
_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")

# Each row is OR over alternatives; each alternative is AND over predicates.
# None means non-empty, while a string is an exact case-sensitive value.
# The order is the specification's first-match policy, not ancestry inference.
_RUNTIME_RULES = (
    ("crush", ((("CRUSH", None),),)),
    ("hermes-agent", ((("HERMES_SESSION_ID", None),), (("HERMES_AGENT", None),))),
    ("kilo-code", ((("KILOCODE_FEATURE", None),),)),
    ("trae", ((("TRAE_AI_SHELL_ID", None),),)),
    ("vtcode", ((("VTCODE", None),),)),
    ("workbuddy", ((("WORKBUDDY_APPLICATION_NAME", None),), (("WORKBUDDY_APP_NAME", None),))),
    ("grok-bot", (
        (("SAND_AGENT", None),),
        (("CURSOR_AGENT", None), ("SAND_MANIFEST_V2", None), ("SAND_SUPERVISOR_ENABLED", None)),
    )),
    ("qwenwork", ((("QODER_WORK_INTEGRATION_PRODUCT", None),),)),
    ("cue", ((("MANUS_LONG_DESKTOP_WORKER", None),), (("MANUS_OPERATOR_PLATFORM", None),))),
    ("muse", ((("JARVIS_IS_ASSIGNED", None),), (("JARVIS_TOOL_CALL_ID", None),))),
    ("manus", ((("MANUS_ADDON_RUNTIME_SPEC_PATH", None),), (("MANUS_ADDON_RUNTIME_SPECS_REVISION", None),))),
    ("doubao-work", ((("DOUBAO_OFFICE_AGENT_NAME", None),),)),
    ("kimi", ((("KIMI_PLUGIN_ROOT", None),),)),
    ("grok-build", ((("GROK_AGENT", "1"),), (("GROK_PLUGIN_ROOT", None),), (("GROK_PLUGIN_DATA", None),))),
    ("gemini-cli", ((("GEMINI_CLI", None),),)),
    ("cline", ((("CLINE_ACTIVE", None),),)),
    ("codex", (
        (("CODEX_SANDBOX", None),), (("CODEX_CI", None),),
        (("CODEX_THREAD_ID", None),), (("CODEX_SANDBOX_NETWORK_DISABLED", None),),
    )),
    ("antigravity", ((("ANTIGRAVITY_AGENT", None),), (("ANTIGRAVITY_CLI_ALIAS", None),))),
    ("augment-cli", ((("AUGMENT_AGENT", None),),)),
    ("opencode", ((("OPENCODE_CLIENT", None),), (("OPENCODE", None),))),
    ("goose", ((("GOOSE_TERMINAL", None),),)),
    ("junie", ((("JUNIE_SHIM_PATH", None),),)),
    ("pi", ((("PI_CODING_AGENT", None),),)),
    ("cowork", (
        (("CLAUDE_CODE_IS_COWORK", None), ("CLAUDECODE", None)),
        (("CLAUDE_CODE_IS_COWORK", None), ("CLAUDE_CODE", None)),
    )),
    ("claude-code", ((("CLAUDECODE", None),), (("CLAUDE_CODE", None),))),
    ("cursor-cli", ((("CURSOR_AGENT", None),), (("CURSOR_EXTENSION_HOST_ROLE", "agent-exec"),))),
    ("kiro", ((("AGENT_CONTEXT_OUT", None),),)),
    ("openclaw", ((("OPENCLAW_SHELL", None),),)),
    # Nested agent CLI markers take precedence over inherited command environments.
    ("devin", ((("DEVIN_DIR", None),), (("DEVIN_DISABLE_HISTEXPAND", None),))),
    ("instinct", (
        (("INSTINCT_OUTER_TOOL_USE_ID", None),),
        (("INSTINCT_OUTER_TOOL_USE_STARTED_AT", None),),
        (("INSTINCT_OUTER_TOOL_USE_TIMEOUT_SECONDS", None),),
    )),
    ("lingguang", ((("EXEC_FROM", None),),)),
)


def _matches(environment: Mapping[str, str], key: str, expected: str | None) -> bool:
    value = environment.get(key)
    return bool(value) if expected is None else value == expected


def _result(agent_id: str | None, evidence: str) -> dict[str, str | None]:
    return {"agent_id": agent_id, "evidence": evidence}


def detect_agent(
    environment: Mapping[str, str],
    *,
    filesystem_probe: Callable[[str], bool] | None = None,
    stdout_is_tty: bool | None = None,
    path_separator: str = os.pathsep,
) -> dict[str, str | None]:
    """Detect through fixed lookups, preserving the supplied provider semantics.

    Probes are optional caller capabilities. No native environment, filesystem,
    terminal state, subprocess, or network is consulted by this function.
    """
    for key in ("AI_AGENT", "AGENT"):
        raw = environment.get(key)
        if raw is None:
            continue
        declaration = raw.strip(_ASCII_TRIM)
        if declaration:
            normalized = declaration.translate(_ASCII_LOWER)
            agent_id = _DECLARATION_ALIASES.get(normalized, normalized)
            return _result(agent_id if agent_id in AGENT_DISPLAY_NAMES else None, "declared")

    for agent_id, alternatives in _RUNTIME_RULES:
        if any(all(_matches(environment, key, expected) for key, expected in group) for group in alternatives):
            return _result(agent_id, "runtime-marker")

    path = environment.get("PATH", "")
    for entry in path.split(path_separator):
        components = entry.replace("\\", "/").split("/")
        if any(left == ".pi" and right == "agent" for left, right in zip(components, components[1:])):
            return _result("pi", "context-hint")
    if "kiro" in environment.get("TERM_PROGRAM", "") and stdout_is_tty is False:
        return _result("kiro", "context-hint")
    if _matches(environment, "GOOSE_PROVIDER", None):
        return _result("goose", "context-hint")
    if any(_matches(environment, key, None) for key in ("COPILOT_MODEL", "COPILOT_ALLOW_ALL", "COPILOT_GITHUB_TOKEN")):
        return _result("github-copilot", "context-hint")
    if _matches(environment, "REPL_ID", None):
        return _result("replit", "context-hint")
    if filesystem_probe is not None:
        try:
            if filesystem_probe("/opt/.devin"):
                return _result("devin", "context-hint")
        except OSError:
            # Unavailable filesystem access supplies no evidence.
            pass
    if _matches(environment, "CURSOR_TRACE_ID", None):
        return _result("cursor", "context-hint")
    if _matches(environment, "ZED_TERM", None):
        return _result("zed", "context-hint")
    return _result(None, "none")
