from __future__ import annotations


def diff_configs(before: str, after: str) -> list[str]:
    before_lines = set(before.splitlines())
    after_lines = set(after.splitlines())
    added = sorted(after_lines - before_lines)
    removed = sorted(before_lines - after_lines)
    return [f"+ {line}" for line in added] + [f"- {line}" for line in removed]


def apply_fragment(config_text: str, fragment_text: str) -> str:
    config = config_text.splitlines()
    for line in fragment_text.splitlines():
        if line and line not in config:
            config.append(line)
    return "\n".join(config) + "\n"
