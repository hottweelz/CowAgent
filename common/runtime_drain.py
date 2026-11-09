"""Process-owned admission and drain accounting for supported runtime work.

This module has no effect until a coordinator is explicitly installed.
"""
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from functools import wraps
import os
import re
import threading
import time
import uuid


class AdmissionClosed(RuntimeError):
    """New work cannot be admitted by this runtime."""


_active = ContextVar("runtime_drain_lease", default=None)
_installed = None
_install_lock = threading.Lock()
_PUBLIC = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")


def _label(value):
    if not isinstance(value, str) or not _PUBLIC.fullmatch(value):
        raise ValueError("expected a public identifier")
    return value


def install(coordinator):
    global _installed
    if not isinstance(coordinator, RuntimeDrain):
        raise TypeError("coordinator must be a RuntimeDrain")
    coordinator._check_process()
    with _install_lock:
        if _installed is not None and _installed is not coordinator:
            raise RuntimeError("a runtime drain coordinator is already installed")
        _installed = coordinator
    return coordinator


def current():
    coordinator = _installed
    if coordinator is not None:
        coordinator._check_process()
    return coordinator


class _Lease:
    def __init__(self, coordinator, category, agent_id):
        self._coordinator = coordinator
        self.category = category
        self.agent_id = agent_id
        self._running = 0
        self._released = False

    @contextmanager
    def activate(self):
        coordinator = self._coordinator
        if coordinator is not None:
            with coordinator._condition:
                coordinator._check_process()
                if not coordinator._valid(self):
                    raise AdmissionClosed("lease is not active")
                self._running += 1
                coordinator._generation += 1
        token = _active.set(self) if coordinator is not None else None
        try:
            yield self
        finally:
            if token is not None:
                _active.reset(token)
                with coordinator._condition:
                    self._running -= 1
                    coordinator._generation += 1
                    if self._released and not self._running:
                        coordinator._leases.pop(id(self), None)
                        coordinator._condition.notify_all()

    def run(self, target, *args, **kwargs):
        try:
            with self.activate():
                return target(*args, **kwargs)
        finally:
            self.release()

    def release(self):
        coordinator = self._coordinator
        if coordinator is not None:
            with coordinator._condition:
                coordinator._check_process()
                if coordinator._owns(self) and not self._released:
                    self._released = True
                    coordinator._generation += 1
                    if not self._running:
                        del coordinator._leases[id(self)]
                    coordinator._condition.notify_all()


def _validate_owner(owner):
    # Import only at explicit owner binding, never on the default no-op path.
    from agent.discovery.initialized_runtime import InitializedRuntime
    return InitializedRuntime(owner)


class RuntimeDrain:
    def __init__(self, required_components=()):
        self.pid = os.getpid()
        self.epoch = uuid.uuid4().hex
        self._condition = threading.Condition()
        self._leases = {}
        self._closed = False
        self._generation = 0
        self._required = frozenset(_label(name) for name in required_components)
        self._components = {}
        self._unsupported = set()
        self._owner = None

    def _check_process(self):
        if os.getpid() != self.pid:
            raise RuntimeError("runtime drain belongs to another process")

    def _owns(self, lease):
        record = self._leases.get(id(lease)) if lease is not None else None
        return record is not None and record[0] is lease

    def _valid(self, lease):
        return self._owns(lease) and not lease._released

    def reserve(self, category, agent_id=""):
        category = _label(category)
        if agent_id:
            agent_id = _label(agent_id)
        with self._condition:
            self._check_process()
            parent = _active.get()
            if self._closed and not self._valid(parent):
                raise AdmissionClosed("runtime admission is closed")
            lease = _Lease(self, category, agent_id)
            self._leases[id(lease)] = (lease, category, agent_id)
            self._generation += 1
            self._condition.notify_all()
            return lease

    @contextmanager
    def work(self, category, agent_id=""):
        lease = self.reserve(category, agent_id)
        try:
            with lease.activate():
                yield lease
        finally:
            lease.release()

    def register_component(self, name, probe=None):
        name = _label(name)
        if probe is not None and not callable(probe):
            raise TypeError("probe must be callable")
        with self._condition:
            self._check_process()
            if self._closed:
                raise AdmissionClosed("coverage is frozen")
            if name in self._components:
                raise ValueError("component already registered")
            self._components[name] = probe

    def mark_unsupported(self, code):
        with self._condition:
            self._check_process()
            self._unsupported.add(_label(code))
            self._condition.notify_all()

    def bind_owner(self, owner):
        if owner is None:
            raise ValueError("owner is required")
        runtime = _validate_owner(owner)
        with self._condition:
            self._check_process()
            if self._closed or self._owner is not None:
                raise RuntimeError("owner already bound or admission closed")
            self._owner = runtime

    def close_admission(self):
        with self._condition:
            self._check_process()
            if not self._closed:
                self._closed = True
                self._generation += 1
            self._condition.notify_all()

    def _receipt(self, deadline):
        with self._condition:
            self._check_process()
            leases = list(self._leases.values())
            closed = self._closed
            blockers = set(self._unsupported)
            blockers.update("missing_component:" + name for name in self._required - self._components.keys())
            if self._owner is None:
                blockers.add("missing_owner")
            if not closed:
                blockers.add("admission_open")
            generation = self._generation
            if closed and not leases:
                probes = list(self._components.items())
            else:
                probes = []
                blockers.add("probe_stale")
            owner = self._owner
        if owner is not None:
            try:
                owner.validate()
            except Exception:
                blockers.add("invalid_owner")
        # A probe must not hold the coordinator lock, or exceed the caller's deadline.
        results = {}
        threads = []
        def run_probe(name, probe):
            try:
                result = probe()
                if not isinstance(result, (list, tuple)):
                    raise ValueError("probe must return a sequence")
                results[name] = [_label(code) for code in result]
            except Exception:
                results[name] = ["probe_error:" + name]
        for name, probe in probes:
            if probe is not None:
                thread = threading.Thread(target=run_probe, args=(name, probe), daemon=True)
                try:
                    thread.start()
                except Exception:
                    blockers.add("probe_error:" + name)
                else:
                    threads.append((name, thread))
        for name, thread in threads:
            thread.join(max(0, deadline - time.monotonic()))
            if thread.is_alive():
                blockers.add("probe_pending:" + name)
            else:
                blockers.update(results.get(name, ["probe_error:" + name]))
        # Close and active counts must be checked after the probes, under the same lock.
        with self._condition:
            self._check_process()
            leases = list(self._leases.values())
            blockers.update(self._unsupported)
            if self._generation != generation:
                blockers.add("probe_stale")
            active = dict(sorted(Counter(category for _, category, _ in leases).items()))
            agents = dict(sorted(Counter(agent for _, _, agent in leases if agent).items()))
            return {"drained": self._closed and not leases and not blockers,
                    "pid": self.pid, "epoch": self.epoch,
                    "required_components": sorted(self._required),
                    "registered_components": sorted(self._components),
                    "closed": self._closed, "active": active, "agents": agents,
                    "blockers": sorted(blockers)}

    def snapshot(self):
        return self._receipt(time.monotonic() + 0.05)

    def wait(self, timeout):
        self._check_process()
        deadline = time.monotonic() + max(0, timeout)
        with self._condition:
            active = _active.get()
            if self._owns(active):
                receipt = None
            else:
                while self._leases:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self._condition.wait(remaining)
                receipt = True
        result = self._receipt(deadline)
        if receipt is None:
            result["drained"] = False
            result["blockers"] = sorted(set(result["blockers"]) | {"self_wait"})
        return result


def reserve(category, agent_id=""):
    coordinator = current()
    return coordinator.reserve(category, agent_id) if coordinator else _Lease(None, category, agent_id)


@contextmanager
def work(category, agent_id=""):
    lease = reserve(category, agent_id)
    try:
        with lease.activate():
            yield lease
    finally:
        lease.release()


def start_thread(category, target, *, args=(), kwargs=None, daemon=True, name=None):
    lease = reserve(category)
    try:
        thread = threading.Thread(target=lease.run, args=(target, *args), kwargs=kwargs or {}, daemon=daemon, name=name)
        thread.start()
    except BaseException:
        lease.release()
        raise
    return thread


def submit(executor, category, target, *args, **kwargs):
    lease = reserve(category)
    try:
        future = executor.submit(lease.run, target, *args, **kwargs)
        future.add_done_callback(lambda done: lease.release() if done.cancelled() else None)
        return future
    except BaseException:
        lease.release()
        raise


def tracked(category):
    def decorate(target):
        @wraps(target)
        def wrapped(*args, **kwargs):
            with work(category):
                return target(*args, **kwargs)
        return wrapped
    return decorate


def tracked_generator(category):
    def decorate(target):
        @wraps(target)
        def wrapped(*args, **kwargs):
            def iterate():
                lease = reserve(category)
                context = copy_context()
                def invoke(method, value):
                    with lease.activate():
                        return method(value)
                def close_generator(generator):
                    with lease.activate():
                        generator.close()
                try:
                    generator = target(*args, **kwargs)
                    method, value = generator.send, None
                    while True:
                        try:
                            item = context.run(invoke, method, value)
                        except StopIteration as stop:
                            return stop.value
                        try:
                            value = yield item
                            method = generator.send
                        except GeneratorExit:
                            context.run(close_generator, generator)
                            raise
                        except BaseException as exc:
                            method, value = generator.throw, exc
                finally:
                    lease.release()
            return iterate()
        return wrapped
    return decorate


def register_component(name, probe=None):
    coordinator = current()
    if coordinator is not None:
        coordinator.register_component(name, probe)


def mark_unsupported(code):
    coordinator = current()
    if coordinator is not None:
        coordinator.mark_unsupported(code)
