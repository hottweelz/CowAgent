"""Internal lifecycle control for an authenticated, freshly launched service.

This module does not retrofit an existing process and exposes no network route.
Normal startup does not install a coordinator. The private launch helper is the
only application startup path that calls these functions.
"""
from common import runtime_drain
import sys


COMPONENTS = (
    "startup", "http", "chat", "agent", "scheduler", "recovery",
    "evolution", "memory", "extensions",
)


def prepare():
    return runtime_drain.install(runtime_drain.RuntimeDrain(COMPONENTS))


def bind_initialized(coordinator, owner, channel_entries):
    """Bind normal runtime ownership; unsupported ingress stays fail closed."""
    if runtime_drain.current() is not coordinator:
        raise RuntimeError("lifecycle owner unavailable")
    coordinator.bind_owner(owner)
    for name in ("startup", "chat", "agent", "memory", "extensions"):
        coordinator.register_component(name)
    coordinator.register_component("http", _http_ready)
    for entry in channel_entries:
        channel_type = entry if isinstance(entry, str) else getattr(entry, "channel_type", None)
        if channel_type != "web":
            coordinator.mark_unsupported("non_web_ingress")


def _http_ready():
    # Read existing objects only. A probe must not construct a channel or load
    # runtime configuration, including during the startup-thread handoff.
    from common.channel_registry import get_channel_manager
    manager = get_channel_manager()
    channel = manager.get_channel("web") if manager is not None else None
    common = sys.modules.get("channel.web.core._common")
    serving = getattr(common, "SERVING", None)
    if (channel is None or getattr(channel, "_http_server", None) is None
            or serving is None or not serving.is_set()):
        return ["http_not_ready"]
    return []


def drain(owner, timeout):
    """Close a bound runtime and return evidence; never signal or restart it."""
    coordinator = runtime_drain.current()
    if (coordinator is None or coordinator._owner is None
            or coordinator._owner.owner is not owner):
        raise RuntimeError("lifecycle owner unavailable")
    coordinator._owner.validate()
    coordinator.close_admission()
    result = coordinator.wait(timeout)
    result["runtime_epoch"] = coordinator._owner.epoch
    result["registered_agents"] = sorted(
        profile.id for profile in owner.agent_registry.list(include_disabled=True)
    )
    return result
