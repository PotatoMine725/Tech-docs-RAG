"""Qt thread-pool executor: runs the port call off the GUI thread, delivers callbacks on the GUI thread."""
from __future__ import annotations

import itertools
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _Job(QRunnable):
    def __init__(self, job_id: int, fn: Callable[[], object], owner: "QtExecutor") -> None:
        super().__init__()
        self._id, self._fn, self._owner = job_id, fn, owner

    def run(self) -> None:
        try:
            self._owner._finished.emit(self._id, self._fn(), None)
        except Exception as exc:  # noqa: BLE001 - forwarded to the view-model
            self._owner._finished.emit(self._id, None, exc)


class QtExecutor(QObject):
    """Must be created on the GUI thread; its signal is delivered there (queued) from the worker."""

    _finished = Signal(int, object, object)

    def __init__(self, pool: QThreadPool | None = None) -> None:
        super().__init__()
        self._pool = pool or QThreadPool.globalInstance()
        self._ids = itertools.count()
        self._pending: dict[int, tuple[Callable, Callable]] = {}
        self._finished.connect(self._deliver)

    def __call__(self, fn, on_ok, on_err) -> None:
        job_id = next(self._ids)
        self._pending[job_id] = (on_ok, on_err)
        self._pool.start(_Job(job_id, fn, self))

    @Slot(int, object, object)
    def _deliver(self, job_id: int, result: object, exc: object) -> None:
        on_ok, on_err = self._pending.pop(job_id)
        (on_err(exc) if exc is not None else on_ok(result))
