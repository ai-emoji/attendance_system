"""core.threads

Tiện ích chạy tác vụ nền bằng QThread cho PySide6.

Mục tiêu:
- Không block UI khi load dữ liệu nặng.
- Chuẩn hoá cancel + cleanup để giảm copy/paste ở controllers.
- Tránh lỗi Shiboken với typed Signal khi payload là dict/list -> dùng Signal(object).

Lưu ý:
- Cancel ở đây là "best-effort" (không thể ngắt query DB đang chạy), nhưng runner sẽ
  coalesce kết quả: chỉ apply kết quả của request mới nhất.
"""

from __future__ import annotations

import logging
import inspect
from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

try:
    from shiboken6 import isValid as _is_valid  # type: ignore
except Exception:  # pragma: no cover

    def _is_valid(_obj: object) -> bool:  # type: ignore
        return True


logger = logging.getLogger(__name__)


_CANCELLED = object()


class _FnWorker(QObject):
    finished = Signal(object, int)  # result, generation
    failed = Signal(str, int)  # message, generation
    progress = Signal(int, str, int)  # percent, message, generation
    progress_items = Signal(int, int, str, int)  # done, total, message, generation

    def __init__(self, fn: Callable[..., object], generation: int) -> None:
        super().__init__()
        self._fn = fn
        self._generation = int(generation)
        self._cancelled = False

    def _emit_progress(self, percent: int, message: str | None = None) -> None:
        try:
            p = max(0, min(100, int(percent)))
        except Exception:
            p = 0
        try:
            self.progress.emit(p, str(message or ""), self._generation)
        except Exception:
            pass

    def _emit_progress_items(
        self,
        done: int,
        total: int,
        message: str | None = None,
    ) -> None:
        try:
            d = int(done)
        except Exception:
            d = 0
        try:
            t = int(total)
        except Exception:
            t = 0
        try:
            self.progress_items.emit(d, t, str(message or ""), self._generation)
        except Exception:
            pass

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            if self._cancelled:
                self.finished.emit(_CANCELLED, self._generation)
                return
            # Backward-compatible: support both fn() and fn(progress_cb, progress_items_cb)
            # so callers can optionally report progress.
            result: object
            try:
                sig = inspect.signature(self._fn)
                argc = len(
                    [
                        p
                        for p in sig.parameters.values()
                        if p.kind
                        in (
                            inspect.Parameter.POSITIONAL_ONLY,
                            inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        )
                    ]
                )
            except Exception:
                argc = 0

            if argc >= 2:
                result = self._fn(self._emit_progress, self._emit_progress_items)
            elif argc == 1:
                result = self._fn(self._emit_progress_items)
            else:
                result = self._fn()
            if self._cancelled:
                self.finished.emit(_CANCELLED, self._generation)
                return
            self.finished.emit(result, self._generation)
        except Exception as e:
            try:
                self.failed.emit(str(e), self._generation)
            except Exception:
                # Ensure thread can quit even if emitting fails.
                logger.exception("Worker failed and could not emit")


class BackgroundTaskRunner(QObject):
    """Run background tasks with coalescing (latest-wins).

    Usage:
            self._runner = BackgroundTaskRunner(parent=self._parent_window)
            self._runner.run(fn=..., on_success=..., on_error=...)
    """

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        name: str | None = None,
        guard: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = str(name or "task")
        self._guard = guard
        self._generation = 0
        self._thread: QThread | None = None
        self._worker: _FnWorker | None = None
        self._bridge: QObject | None = None

    def invalidate(self) -> None:
        """Invalidate any pending callbacks for this runner.

        Useful when the UI owning the callbacks is being destroyed.
        """

        self._generation += 1
        self.cancel_current()

    def _guard_alive(self) -> bool:
        try:
            return self._guard is None or bool(_is_valid(self._guard))
        except Exception:
            return True

    def cancel_current(self) -> None:
        """Best-effort cancel the current task."""

        try:
            if self._worker is not None:
                self._worker.cancel()
        except Exception:
            pass
        try:
            if self._thread is not None:
                self._thread.quit()
        except Exception:
            pass

    def run(
        self,
        *,
        fn: Callable[..., object],
        on_success: Callable[[object], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_progress: Callable[[int, str], None] | None = None,
        on_progress_items: Callable[[int, int, str], None] | None = None,
        coalesce: bool = True,
    ) -> None:
        """Start a new background task.

        - If coalesce=True: cancel previous and only apply latest result.
        """

        if coalesce:
            self.cancel_current()

        self._generation += 1
        gen = int(self._generation)

        thread = QThread(self.parent())
        worker = _FnWorker(fn=fn, generation=gen)
        worker.moveToThread(thread)

        runner_self = self

        class _Bridge(QObject):
            @Slot(int, str, int)
            def on_progress(self, pct: int, msg: str, generation: int) -> None:
                if not runner_self._guard_alive():
                    return
                if int(generation) != int(runner_self._generation):
                    return
                if on_progress is None:
                    return
                try:
                    on_progress(int(pct), str(msg))
                except Exception:
                    logger.exception("on_progress failed (%s)", runner_self._name)

            @Slot(int, int, str, int)
            def on_progress_items(
                self, done: int, total: int, msg: str, generation: int
            ) -> None:
                if not runner_self._guard_alive():
                    return
                if int(generation) != int(runner_self._generation):
                    return
                if on_progress_items is None:
                    return
                try:
                    on_progress_items(int(done), int(total), str(msg))
                except Exception:
                    logger.exception("on_progress_items failed (%s)", runner_self._name)

            @Slot(object, int)
            def on_finished(self, result: object, generation: int) -> None:
                if not runner_self._guard_alive():
                    return
                if int(generation) != int(runner_self._generation):
                    return
                if result is _CANCELLED:
                    return
                if on_success is None:
                    return
                try:
                    on_success(result)
                except Exception:
                    logger.exception("on_success failed (%s)", runner_self._name)

            @Slot(str, int)
            def on_failed(self, msg: str, generation: int) -> None:
                if not runner_self._guard_alive():
                    return
                if int(generation) != int(runner_self._generation):
                    return
                if on_error is None:
                    return
                try:
                    on_error(str(msg))
                except Exception:
                    logger.exception("on_error failed (%s)", runner_self._name)

        bridge = _Bridge()

        # Keep references
        self._thread = thread
        self._worker = worker
        self._bridge = bridge

        worker.finished.connect(bridge.on_finished)
        worker.failed.connect(bridge.on_failed)
        worker.progress.connect(bridge.on_progress)
        worker.progress_items.connect(bridge.on_progress_items)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)

        def _cleanup() -> None:
            try:
                worker.deleteLater()
            except Exception:
                pass
            try:
                bridge.deleteLater()
            except Exception:
                pass
            try:
                thread.deleteLater()
            except Exception:
                pass

            # Drop refs if still current
            try:
                if runner_self._thread is thread:
                    runner_self._thread = None
                if runner_self._worker is worker:
                    runner_self._worker = None
                if runner_self._bridge is bridge:
                    runner_self._bridge = None
            except Exception:
                pass

        thread.finished.connect(_cleanup)
        thread.started.connect(worker.run)
        thread.start()
