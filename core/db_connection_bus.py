"""core.db_connection_bus

A tiny event bus to notify open views when DB connection settings have been
updated and verified successfully.

We intentionally keep this minimal:
- No DB calls here.
- Emits only after CSDL connection is tested OK + saved.

Controllers can subscribe and trigger background refresh to repopulate UI after
switching from offline -> online.
"""

from __future__ import annotations

import weakref
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal


class DbConnectionBus(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.generation: int = 0
        # Keep Python-callable wrappers alive; PySide can drop callbacks that
        # have no other strong references even after signal.connect().
        self._weak_wrappers: list[Callable[..., Any]] = []

    def emit_changed(self) -> None:
        """Increment generation and emit `changed`.

        Controllers/widgets can use `generation` to decide whether a cached UI
        snapshot is stale (e.g. created while offline) and should not overwrite
        freshly reloaded data after DB becomes available.
        """

        try:
            self.generation = int(self.generation) + 1
        except Exception:
            self.generation = 1

        try:
            self.changed.emit()
        except Exception:
            pass

    def connect_changed_weak(self, slot: Callable[..., Any]) -> None:
        """Connect a bound-method slot without keeping its instance alive.

        This prevents leaks when controllers/widgets get recreated while the bus
        persists for the whole process.
        """

        try:
            obj = getattr(slot, "__self__", None)
            fn = getattr(slot, "__func__", None)
            if obj is None or fn is None:
                self.changed.connect(slot)
                return

            obj_ref = weakref.ref(obj)
            fn_name = str(getattr(fn, "__name__", ""))

            def _wrapper(*args: Any, **kwargs: Any) -> Any:
                inst = obj_ref()
                if inst is None:
                    try:
                        self.changed.disconnect(_wrapper)
                    except Exception:
                        pass
                    try:
                        if _wrapper in self._weak_wrappers:
                            self._weak_wrappers.remove(_wrapper)
                    except Exception:
                        pass
                    return None
                try:
                    meth = getattr(inst, fn_name)
                except Exception:
                    return None
                return meth(*args, **kwargs)

            self.changed.connect(_wrapper)
            try:
                self._weak_wrappers.append(_wrapper)
            except Exception:
                pass
        except Exception:
            # Best-effort fallback.
            try:
                self.changed.connect(slot)
            except Exception:
                pass


db_connection_bus = DbConnectionBus()
