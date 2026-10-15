def parse_config_pairs(pairs: list[str] | None) -> dict[str, str]:
    """Turn ["model=x", "prompt=pirate"] into {"model": "x", "prompt": "pirate"}."""
    config: dict[str, str] = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        key = key.strip()
        if not sep or not key:
            raise ValueError(f"Expected key=value, got {pair!r}")
        config[key] = value.strip()
    return config


def config_differences(
    before: dict[str, str], after: dict[str, str]
) -> dict[str, tuple[str | None, str | None]]:
    """Keys whose value differs between two configs. None means 'not recorded'."""
    diffs: dict[str, tuple[str | None, str | None]] = {}
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old != new:
            diffs[key] = (old, new)
    return diffs