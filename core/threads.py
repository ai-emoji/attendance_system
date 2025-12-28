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
from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot


logger = logging.getLogger(__name__)


_CANCELLED = object()


class _FnWorker(QObject):
	finished = Signal(object, int)  # result, generation
	failed = Signal(str, int)  # message, generation

	def __init__(self, fn: Callable[[], object], generation: int) -> None:
		super().__init__()
		self._fn = fn
		self._generation = int(generation)
		self._cancelled = False

	def cancel(self) -> None:
		self._cancelled = True

	def run(self) -> None:
		try:
			if self._cancelled:
				self.finished.emit(_CANCELLED, self._generation)
				return
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

	def __init__(self, parent: QObject | None = None, *, name: str | None = None) -> None:
		super().__init__(parent)
		self._name = str(name or "task")
		self._generation = 0
		self._thread: QThread | None = None
		self._worker: _FnWorker | None = None
		self._bridge: QObject | None = None

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
		fn: Callable[[], object],
		on_success: Callable[[object], None] | None = None,
		on_error: Callable[[str], None] | None = None,
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
			@Slot(object, int)
			def on_finished(self, result: object, generation: int) -> None:
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

