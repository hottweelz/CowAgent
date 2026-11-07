"""Bounded startup consumer for durable native worker tasks."""
import threading
from concurrent.futures import ThreadPoolExecutor

from common.log import logger


class RecoveryService:
    def __init__(self, bridge, store, max_workers=3):
        self.bridge, self.store = bridge, store
        self._stop = threading.Event()
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="task-recovery")
        self._capacity = max_workers
        self._futures = {}
        self._thread = None
        self.last_error = None

    def scan_once(self):
        """Reconcile only abandoned locks, then dispatch queued tasks once."""
        from agent.recovery.runtime import execute_task
        for key, future in list(self._futures.items()):
            if future.done():
                # Surface storage failures rather than silently dropping them.
                del self._futures[key]
                future.result()
        self.store.reconcile()
        remaining = self._capacity - len(self._futures)
        if remaining <= 0:
            return
        for task in self.store.list_tasks(states=['queued'], limit=remaining, oldest_first=True):
            key = task['task_id']
            if key not in self._futures:
                self._futures[key] = self._pool.submit(
                    execute_task, self.store, key, bridge=self.bridge, cancel_event=self._stop,
                    wait_for_existing=False)

    def _run(self):
        while not self._stop.is_set():
            try:
                self.scan_once()
                self.last_error = None
            except Exception:
                self.last_error = 'Recovery journal or dispatch unavailable'
                logger.error('[Recovery] Journal or dispatch unavailable; no untracked fallback')
            self._stop.wait(1.0)

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="task-recovery-dispatch", daemon=True)
            self._thread.start()
        return self

    def close(self, wait=False):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._pool.shutdown(wait=wait, cancel_futures=True)


def start_recovery_service(agent_bridge):
    existing = getattr(agent_bridge, 'recovery_service', None)
    if existing is not None:
        return existing
    from agent.recovery.runtime import get_task_store
    from agent.subagent.runner import SubagentSettings
    service = RecoveryService(agent_bridge.bridge, get_task_store(),
                              max_workers=SubagentSettings.from_config().max_concurrent)
    agent_bridge.recovery_service = service.start()
    return service
