"""ui.dialog.export_grid_list_dialog

Dialog cấu hình xuất lưới chấm công.

Gồm:
- Input: Tên công ty, Địa chỉ, Số điện thoại, Người tạo danh sách, Ghi chú
- Formatting ghi chú: cỡ chữ, đậm/nghiêng/gạch dưới, căn trái/giữa/phải (dùng ICON_ALGIN_*)
- Button: Lưu, Xuất lưới

Không dùng QMessageBox: hiển thị status nội tuyến.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.resource import (
    COLOR_BG_HEADER,
    COLOR_BORDER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
    CONTENT_FONT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    INPUT_WIDTH_DEFAULT,
    UI_FONT,
    resource_path,
)


@dataclass(frozen=True)
class NoteStyle:
    font_size: int = 13
    bold: bool = False
    italic: bool = False
    underline: bool = False
    align: str = "left"  # left|center|right


class ExportGridListDialog(QDialog):
    def __init__(self, parent=None, *, export_button_text: str = "Xuất lưới") -> None:
        super().__init__(parent)
        self._did_export: bool = False
        self._is_formatting_text = False
        self._export_button_text = str(export_button_text or "Xuất lưới")
        self._active_field: str = "note"  # field key
        self._field_styles: dict[str, NoteStyle] = {
            "company_name": NoteStyle(),
            "company_address": NoteStyle(),
            "company_phone": NoteStyle(),
            "creator": NoteStyle(),
            "note": NoteStyle(),
        }
        self._style_pressed_state: dict[str, bool] = {}
        self._init_ui()

    def eventFilter(self, obj, event):
        try:
            if event.type() == event.Type.FocusIn:
                if obj is getattr(self, "input_company_name", None):
                    self._set_active_field("company_name")
                elif obj is getattr(self, "input_company_address", None):
                    self._set_active_field("company_address")
                elif obj is getattr(self, "input_company_phone", None):
                    self._set_active_field("company_phone")
                if obj is getattr(self, "input_creator", None):
                    self._set_active_field("creator")
                elif (
                    obj is getattr(self, "input_note", None)
                    or obj
                    is getattr(
                        getattr(self, "input_note", None), "viewport", lambda: None
                    )()
                ):
                    self._set_active_field("note")
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _set_active_field(self, key: str) -> None:
        if key not in self._field_styles:
            return
        self._active_field = key
        self._load_toolbar_from_style(self._field_styles.get(key) or NoteStyle())

    def _load_toolbar_from_style(self, st: NoteStyle) -> None:
        try:
            self.spin_font_size.blockSignals(True)
            self.btn_bold.blockSignals(True)
            self.btn_italic.blockSignals(True)
            self.btn_underline.blockSignals(True)
            self.btn_align_left.blockSignals(True)
            self.btn_align_center.blockSignals(True)
            self.btn_align_right.blockSignals(True)

            self.spin_font_size.setValue(int(st.font_size))

            # allow none active among bold/italic/underline
            old_ex = self._text_style_group.exclusive()
            self._text_style_group.setExclusive(False)
            self.btn_bold.setChecked(bool(st.bold))
            self.btn_italic.setChecked(bool(st.italic))
            self.btn_underline.setChecked(bool(st.underline))
            self._text_style_group.setExclusive(old_ex)

            a = str(st.align or "left").strip().lower()
            if a == "center":
                self.btn_align_center.setChecked(True)
            elif a == "right":
                self.btn_align_right.setChecked(True)
            else:
                self.btn_align_left.setChecked(True)
        except Exception:
            pass
        finally:
            try:
                self.spin_font_size.blockSignals(False)
                self.btn_bold.blockSignals(False)
                self.btn_italic.blockSignals(False)
                self.btn_underline.blockSignals(False)
                self.btn_align_left.blockSignals(False)
                self.btn_align_center.blockSignals(False)
                self.btn_align_right.blockSignals(False)
            except Exception:
                pass
        self._refresh_format_icons()

    def _update_style_from_toolbar(self) -> None:
        key = self._active_field
        if key not in self._field_styles:
            return

        align = "left"
        if self.btn_align_center.isChecked():
            align = "center"
        elif self.btn_align_right.isChecked():
            align = "right"

        bold = bool(self.btn_bold.isChecked())
        italic = bool(self.btn_italic.isChecked())
        underline = bool(self.btn_underline.isChecked())

        self._field_styles[key] = NoteStyle(
            font_size=int(self.spin_font_size.value()),
            bold=bold,
            italic=italic,
            underline=underline,
            align=align,
        )

    def _make_tinted_icon(
        self, icon_path: str, *, color_hex: str, size: int = 18
    ) -> QIcon:
        """Render svg/png then tint to a single color and center the glyph.

        Một số SVG có viewBox dư khoảng trống làm icon nhìn lệch; đoạn này sẽ trim vùng
        có alpha > 0 rồi đặt lại vào giữa khung size x size.
        """
        abs_path = resource_path(icon_path)

        # Render big first (SVG is 256x256) then tint + downscale.
        render_size = max(256, int(size) * 18)
        img = QImage(render_size, render_size, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        rendered = False
        if str(abs_path).lower().endswith(".svg"):
            try:
                from PySide6.QtSvg import QSvgRenderer  # type: ignore

                renderer = QSvgRenderer(abs_path)
                if renderer.isValid():
                    p = QPainter(img)
                    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                    renderer.render(p)
                    p.end()
                    rendered = True
            except Exception:
                rendered = False

        if not rendered:
            # Fallback: let QIcon rasterize (may be lower quality for some SVGs)
            pix = QIcon(abs_path).pixmap(
                render_size,
                render_size,
                QIcon.Mode.Normal,
                QIcon.State.On,
            )
            if pix.isNull():
                return QIcon()
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            p.drawPixmap(0, 0, pix)
            p.end()

        # Tint to requested color
        p = QPainter(img)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(img.rect(), QColor(color_hex))
        p.end()

        # Trim transparent padding and re-center
        try:
            w = int(img.width())
            h = int(img.height())
            min_x, min_y = w, h
            max_x, max_y = -1, -1
            alpha_threshold = 10
            for yy in range(h):
                for xx in range(w):
                    if QColor(img.pixel(xx, yy)).alpha() > alpha_threshold:
                        if xx < min_x:
                            min_x = xx
                        if yy < min_y:
                            min_y = yy
                        if xx > max_x:
                            max_x = xx
                        if yy > max_y:
                            max_y = yy

            if max_x >= min_x and max_y >= min_y:
                pad = max(6, int(render_size * 0.02))
                x1 = max(0, min_x - pad)
                y1 = max(0, min_y - pad)
                x2 = min(w - 1, max_x + pad)
                y2 = min(h - 1, max_y + pad)
                crop = img.copy(x1, y1, (x2 - x1 + 1), (y2 - y1 + 1))

                # Scale crop to fit into size x size (avoid clipping / distortion)
                inner = max(10, int(size) - 2)
                scaled = crop.scaled(
                    inner,
                    inner,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                out = QImage(int(size), int(size), QImage.Format.Format_ARGB32)
                out.fill(Qt.GlobalColor.transparent)
                ox = int((int(size) - scaled.width()) / 2)
                oy = int((int(size) - scaled.height()) / 2)
                pp = QPainter(out)
                pp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                pp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                pp.drawImage(max(0, ox), max(0, oy), scaled)
                pp.end()
                return QIcon(QPixmap.fromImage(out))
        except Exception:
            pass

        return QIcon(QPixmap.fromImage(img))

    def _apply_button_icon(self, btn: QPushButton, icon_path: str) -> None:
        color = "#FFFFFF" if btn.isChecked() else str(COLOR_TEXT_PRIMARY)
        btn.setIcon(self._make_tinted_icon(icon_path, color_hex=color, size=18))
        btn.setIconSize(QSize(18, 18))

    def _refresh_format_icons(self) -> None:
        # B/I/U are text, align uses text (L≡/C≡/R≡) => no icon refresh needed.
        return

    def _init_ui(self) -> None:
        if "chi tiết" in str(self._export_button_text or "").lower():
            self.setWindowTitle("Xuất chi tiết chấm công")
        else:
            self.setWindowTitle("Xuất lưới chấm công")
        self.setModal(True)
        self.setMinimumWidth(620)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        form_widget = QWidget(self)
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        def _mk_line(placeholder: str) -> QLineEdit:
            w = QLineEdit(self)
            w.setFont(font_normal)
            w.setFixedHeight(INPUT_HEIGHT_DEFAULT)
            w.setMinimumWidth(INPUT_WIDTH_DEFAULT)
            w.setPlaceholderText(placeholder)
            w.setCursor(Qt.CursorShape.IBeamCursor)
            w.setStyleSheet(
                "\n".join(
                    [
                        f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 0px; }}",
                        f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                    ]
                )
            )
            return w

        self.input_company_name = _mk_line("Nhập tên công ty")
        self.input_company_address = _mk_line("Nhập địa chỉ")
        self.input_company_phone = _mk_line("Nhập số điện thoại")
        self.input_creator = _mk_line("Nhập người tạo danh sách")
        self.input_company_name.installEventFilter(self)
        self.input_company_address.installEventFilter(self)
        self.input_company_phone.installEventFilter(self)
        self.input_creator.installEventFilter(self)

        self.input_note = QTextEdit(self)
        self.input_note.setFont(font_normal)
        self.input_note.setMinimumHeight(120)
        self.input_note.setStyleSheet(
            "\n".join(
                [
                    f"QTextEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 6px 8px; border-radius: 0px; }}",
                    f"QTextEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                ]
            )
        )
        try:
            self.input_note.installEventFilter(self)
            self.input_note.viewport().installEventFilter(self)
        except Exception:
            pass

        form.addRow("Tên công ty", self.input_company_name)
        form.addRow("Địa chỉ", self.input_company_address)
        form.addRow("Số điện thoại", self.input_company_phone)
        form.addRow("Người tạo danh sách", self.input_creator)
        form.addRow("Ghi chú", self.input_note)

        # Note formatting row
        fmt_row = QWidget(self)
        fmt = QHBoxLayout(fmt_row)
        fmt.setContentsMargins(0, 0, 0, 0)
        fmt.setSpacing(8)

        self.spin_font_size = QSpinBox(self)
        self.spin_font_size.setRange(8, 40)
        self.spin_font_size.setValue(13)
        self.spin_font_size.setFixedHeight(32)
        self.spin_font_size.setFixedWidth(90)

        self.btn_bold = QPushButton("𝐁", self)
        self.btn_bold.setCheckable(True)
        self.btn_bold.setFixedSize(40, 32)
        self.btn_bold.setToolTip("Đậm")

        self.btn_italic = QPushButton("𝐼", self)
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedSize(40, 32)
        self.btn_italic.setToolTip("Nghiêng")

        self.btn_underline = QPushButton("U̲", self)
        self.btn_underline.setCheckable(True)
        self.btn_underline.setFixedSize(40, 32)
        self.btn_underline.setToolTip("Gạch dưới")

        def _mk_align_btn(tooltip: str) -> QPushButton:
            b = QPushButton(self)
            b.setCheckable(True)
            b.setFixedSize(40, 32)
            b.setToolTip(tooltip)
            return b

        self.btn_align_left = _mk_align_btn("Căn trái")
        self.btn_align_left.setText("L≡")
        self.btn_align_center = _mk_align_btn("Căn giữa")
        self.btn_align_center.setText("C≡")
        self.btn_align_right = _mk_align_btn("Căn phải")
        self.btn_align_right.setText("R≡")

        # Bold/Italic/Underline are independent toggles
        self._text_style_group = QButtonGroup(self)
        self._text_style_group.setExclusive(False)
        self._text_style_group.addButton(self.btn_bold)
        self._text_style_group.addButton(self.btn_italic)
        self._text_style_group.addButton(self.btn_underline)

        self._align_group = QButtonGroup(self)
        self._align_group.setExclusive(True)
        self._align_group.addButton(self.btn_align_left)
        self._align_group.addButton(self.btn_align_center)
        self._align_group.addButton(self.btn_align_right)
        self.btn_align_left.setChecked(True)

        # Simple common style
        for b in (
            self.btn_bold,
            self.btn_italic,
            self.btn_underline,
            self.btn_align_left,
            self.btn_align_center,
            self.btn_align_right,
        ):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                "\n".join(
                    [
                        f"QPushButton {{ background: {COLOR_BG_HEADER}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; border-radius: 0px; }}",
                        f"QPushButton:checked {{ background: {COLOR_BUTTON_PRIMARY}; color: #FFFFFF; }}",
                        f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_BG_HEADER}; }}",
                    ]
                )
            )

        # Apply formatting per active field (creator/note)
        try:
            self.spin_font_size.valueChanged.connect(
                lambda _=0: (
                    self._update_style_from_toolbar(),
                    self._refresh_format_icons(),
                )
            )

            def _bind_style_btn(key: str, btn: QPushButton) -> None:
                btn.pressed.connect(
                    lambda k=key, b=btn: self._style_pressed_state.__setitem__(
                        k, bool(b.isChecked())
                    )
                )

                def _clicked(k=key, b=btn) -> None:
                    was_checked = bool(self._style_pressed_state.get(k, False))
                    if was_checked:
                        old_ex = self._text_style_group.exclusive()
                        self._text_style_group.setExclusive(False)
                        b.setChecked(False)
                        self._text_style_group.setExclusive(old_ex)

                btn.clicked.connect(_clicked)
                btn.toggled.connect(
                    lambda _=False: (
                        self._update_style_from_toolbar(),
                        self._refresh_format_icons(),
                    )
                )

            _bind_style_btn("bold", self.btn_bold)
            _bind_style_btn("italic", self.btn_italic)
            _bind_style_btn("underline", self.btn_underline)

            self.btn_align_left.toggled.connect(
                lambda _=False: (
                    self._update_style_from_toolbar(),
                    self._refresh_format_icons(),
                )
            )
            self.btn_align_center.toggled.connect(
                lambda _=False: (
                    self._update_style_from_toolbar(),
                    self._refresh_format_icons(),
                )
            )
            self.btn_align_right.toggled.connect(
                lambda _=False: (
                    self._update_style_from_toolbar(),
                    self._refresh_format_icons(),
                )
            )
        except Exception:
            pass

        self._refresh_format_icons()
        self._set_active_field("note")

        fmt.addWidget(QLabel("Cỡ chữ", self))
        fmt.addWidget(self.spin_font_size)
        fmt.addSpacing(10)
        fmt.addWidget(self.btn_bold)
        fmt.addWidget(self.btn_italic)
        fmt.addWidget(self.btn_underline)
        fmt.addSpacing(10)
        fmt.addWidget(self.btn_align_left)
        fmt.addWidget(self.btn_align_center)
        fmt.addWidget(self.btn_align_right)
        fmt.addStretch(1)

        self.label_status = QLabel("", self)
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)

        btn_row = QWidget(self)
        btns = QHBoxLayout(btn_row)
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(10)
        btns.addStretch(1)

        # Export dropdown (type + time pairs)
        self.cbo_export = QComboBox(self)
        self.cbo_export.setFixedHeight(36)
        self.cbo_export.setMinimumWidth(180)
        self.cbo_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cbo_export.setStyleSheet(
            "\n".join(
                [
                    f"QComboBox {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 0px; }}",
                    f"QComboBox:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                    f"QComboBox QAbstractItemView {{ background: {INPUT_COLOR_BG}; selection-background-color: {INPUT_COLOR_BG}; selection-color: {COLOR_TEXT_PRIMARY}; outline: 0px; }}",
                ]
            )
        )

        # Show only the export kind that matches the button the user clicked.
        preferred_kind = (
            "detail" if "chi tiết" in self._export_button_text.lower() else "grid"
        )
        options: list[tuple[str, tuple[str, int]]] = []
        if preferred_kind == "detail":
            # Detail export supports choosing time-pair cap (2/4/6)
            for tp in (2, 4, 6):
                options.append((f"Xuất chi tiết - {tp}", (preferred_kind, tp)))
        else:
            # Grid export: remove the 2/4/6 variants (always a single choice)
            options.append(("Xuất lưới", (preferred_kind, 4)))

        for text, data in options:
            self.cbo_export.addItem(text, data)

        self.btn_save = QPushButton("Lưu", self)
        self.btn_save.setFont(font_button)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(36)
        self.btn_save.setMinimumWidth(120)
        self.btn_save.setAutoDefault(False)
        self.btn_save.setDefault(False)
        self.btn_save.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BG_HEADER}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_BG_HEADER}; }}",
                ]
            )
        )

        self.btn_export = QPushButton(self._export_button_text, self)
        self.btn_export.setFont(font_button)
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setFixedHeight(36)
        self.btn_export.setMinimumWidth(140)
        self.btn_export.setAutoDefault(True)
        self.btn_export.setDefault(True)
        self.btn_export.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_PRIMARY}; color: {COLOR_BG_HEADER}; border: none; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; }}",
                ]
            )
        )

        btns.addWidget(self.btn_save)
        btns.addWidget(self.cbo_export)
        btns.addWidget(self.btn_export)

        root.addWidget(form_widget)
        root.addWidget(fmt_row)
        root.addWidget(self.label_status)
        root.addStretch(1)
        root.addWidget(btn_row)

    def set_status(self, message: str, ok: bool = True) -> None:
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )
        self.label_status.setText(message or "")

    def did_export(self) -> bool:
        return bool(self._did_export)

    def mark_export(self) -> None:
        self._did_export = True

    def get_values(self) -> dict:
        return {
            "company_name": (self.input_company_name.text() or "").strip(),
            "company_address": (self.input_company_address.text() or "").strip(),
            "company_phone": (self.input_company_phone.text() or "").strip(),
            "creator": (self.input_creator.text() or "").strip(),
            "note_text": (self.input_note.toPlainText() or ""),
        }

    def get_export_kind(self) -> str:
        def _norm_choice(v) -> tuple[str, int]:
            try:
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    k = str(v[0] or "grid").strip().lower()
                    tp = int(v[1])
                    return (k, tp)
            except Exception:
                pass
            return ("grid", 4)

        kind = "grid"
        try:
            data = self.cbo_export.currentData()
            kind, _tp = _norm_choice(data)
        except Exception:
            kind = "grid"

        # Fallback: parse from displayed text (more reliable across PySide variants)
        if kind not in {"grid", "detail"}:
            try:
                txt = str(self.cbo_export.currentText() or "").strip().lower()
                kind = "detail" if "chi tiết" in txt else "grid"
            except Exception:
                kind = "grid"

        return kind if kind in {"grid", "detail"} else "grid"

    def get_time_pairs(self) -> int:
        def _norm_choice(v) -> tuple[str, int]:
            try:
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    k = str(v[0] or "grid").strip().lower()
                    tp = int(v[1])
                    return (k, tp)
            except Exception:
                pass
            return ("grid", 4)

        v = 4
        try:
            data = self.cbo_export.currentData()
            _kind, tp = _norm_choice(data)
            v = int(tp)
        except Exception:
            v = 4

        # Fallback: parse from displayed text like "Xuất chi tiết - 4"
        if v not in {2, 4, 6}:
            try:
                txt = str(self.cbo_export.currentText() or "")
                part = txt.split("-")[-1].strip()
                v = int(part)
            except Exception:
                v = 4

        return v if v in {2, 4, 6} else 4

    def set_export_choice(self, *, export_kind: str, time_pairs: int) -> None:
        kind = str(export_kind or "grid").strip().lower()
        if kind not in {"grid", "detail"}:
            kind = "grid"
        try:
            tp = int(time_pairs)
        except Exception:
            tp = 4
        if tp not in {2, 4, 6}:
            tp = 4

        target = (kind, tp)
        try:
            for i in range(int(self.cbo_export.count())):
                item = self.cbo_export.itemData(i)
                if item == target:
                    self.cbo_export.setCurrentIndex(i)
                    break
                try:
                    if isinstance(item, (list, tuple)) and tuple(item) == target:
                        self.cbo_export.setCurrentIndex(i)
                        break
                except Exception:
                    pass
                # If grid has only one choice, always select it.
                if kind == "grid":
                    try:
                        t = str(self.cbo_export.itemText(i) or "").strip().lower()
                        if t == "xuất lưới":
                            self.cbo_export.setCurrentIndex(i)
                            break
                    except Exception:
                        pass
                # Last resort: match by displayed text
                try:
                    t = str(self.cbo_export.itemText(i) or "").strip().lower()
                    if t.endswith(f"- {tp}"):
                        if kind == "detail" and "chi tiết" in t:
                            self.cbo_export.setCurrentIndex(i)
                            break
                        if kind == "grid" and "chi tiết" not in t:
                            self.cbo_export.setCurrentIndex(i)
                            break
                except Exception:
                    pass
        except Exception:
            pass

    def get_note_style(self) -> NoteStyle:
        return self._field_styles.get("note") or NoteStyle()

    def get_creator_style(self) -> NoteStyle:
        return self._field_styles.get("creator") or NoteStyle()

    def get_company_name_style(self) -> NoteStyle:
        return self._field_styles.get("company_name") or NoteStyle()

    def get_company_address_style(self) -> NoteStyle:
        return self._field_styles.get("company_address") or NoteStyle()

    def get_company_phone_style(self) -> NoteStyle:
        return self._field_styles.get("company_phone") or NoteStyle()

    def set_values(
        self,
        *,
        company_name: str = "",
        company_address: str = "",
        company_phone: str = "",
        creator: str = "",
        note_text: str = "",
        company_name_style: NoteStyle | None = None,
        company_address_style: NoteStyle | None = None,
        company_phone_style: NoteStyle | None = None,
        creator_style: NoteStyle | None = None,
        note_style: NoteStyle | None = None,
        export_kind: str | None = None,
        time_pairs: int | None = None,
    ) -> None:
        self.input_company_name.setText(company_name or "")
        self.input_company_address.setText(company_address or "")
        self.input_company_phone.setText(company_phone or "")
        self.input_creator.setText(creator or "")
        self.input_note.setPlainText(note_text or "")

        if company_name_style is not None:
            self._field_styles["company_name"] = company_name_style
        if company_address_style is not None:
            self._field_styles["company_address"] = company_address_style
        if company_phone_style is not None:
            self._field_styles["company_phone"] = company_phone_style

        if creator_style is not None:
            self._field_styles["creator"] = creator_style
        if note_style is not None:
            self._field_styles["note"] = note_style

        # Keep toolbar in sync with current active field
        self._load_toolbar_from_style(
            self._field_styles.get(self._active_field) or NoteStyle()
        )

        # Export dropdown defaults
        if export_kind is not None or time_pairs is not None:
            self.set_export_choice(
                export_kind=str(export_kind or self.get_export_kind()),
                time_pairs=int(time_pairs or self.get_time_pairs()),
            )
