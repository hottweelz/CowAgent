"""Version-aware defaults for model families exposed by the model catalog."""
import re

from common.const import MODEL_LIST


_MODEL_VERSION = re.compile(r"^gpt-(\d+(?:\.\d+)?)-(luna|terra|sol)$")


def newest_supported_model(family, supported_models=MODEL_LIST):
    """Return the newest catalog model in a family, excluding GPT-5.6 fallbacks.

    Version parts are compared as integers. This keeps 6.1 newer than 6 and
    avoids lexical ordering. GPT-5.6 remains available as an explicit pin only.
    """
    if family not in {'luna', 'terra', 'sol'}:
        raise ValueError(f'Unknown GPT model family: {family}')

    candidates = []
    for model in supported_models:
        match = _MODEL_VERSION.fullmatch(model)
        if not match or match.group(2) != family:
            continue
        version = tuple(int(part) for part in match.group(1).split('.'))
        if version[0] < 6:
            continue
        candidates.append((version, model))

    if not candidates:
        raise ValueError(f'No supported GPT-6 or newer {family} model is available')
    return max(candidates, key=lambda candidate: candidate[0])[1]
