"""ui.common.header

Header của ứng dụng.

Yêu cầu:
- BG COLOR_BG_HEADER
- Min width theo MIN_MAINWINDOW_WIDTH
- Chiều cao cố định 150px
- Phần 1: cao 40px, có 4 phím chức năng: Khai báo, Kết nối, Chấm công, Công cụ
  - Có border-bottom cho phần 1 (không áp dụng border-bottom cho các phím)
  - 4 phím có chiều rộng cố định
- Phần 2: cao 120px, để trống, có border-bottom
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.resource import (
    BUTTON_FONT,
    COLOR_BG_HEADER,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_BUTTON_ACTIVE,
    COLOR_BORDER,
    FONT_WEIGHT_NORMAL,
    CONTENT_FONT,
    MIN_MAINWINDOW_WIDTH,
    UI_FONT,
    resource_path,
)

from ui.controllers.header_controllers import HeaderController


class Header(QWidget):
    """Header chính gồm 2 phần (40px + 120px)."""

    action_triggered = Signal(str)

    _BUTTON_FIXED_WIDTH = 160
    _ACTION_BUTTON_FIXED_WIDTH = 120
    _ACTION_BUTTON_FIXED_HEIGHT = 100
    _ACTION_ICON_SIZE = 32

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller: HeaderController | None = None

        self._ribbon_scroll: QScrollArea | None = None
        self._ribbon_content: QWidget | None = None
        self._ribbon_layout: QHBoxLayout | None = None
        self._ribbon_font: QFont | None = None
        self._init_ui()

        # Controller: điều khiển tab + danh sách ribbon
        self._controller = HeaderController(self)
        self._controller.bind()

    def _init_ui(self) -> None:
        self.setObjectName("Header")
        self.setMinimumWidth(MIN_MAINWINDOW_WIDTH)
        # Phần 1: 40px, Phần 2: 110px
        self.setFixedHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Style cho tab: hover/active đổi màu background
        self.setStyleSheet(
            "\n".join(
                [
                    f"#Header {{ background-color: {COLOR_BG_HEADER}; }}",
                    f"#HeaderTopBar {{ background-color: {COLOR_BG_HEADER}; border-bottom: 1px solid {COLOR_BORDER}; }}",
                    f"#HeaderBottomArea {{ background-color: {COLOR_BG_HEADER}; border-bottom: 1px solid {COLOR_BORDER}; }}",
                    # QScrollArea có viewport riêng, cần set cả viewport/content
                    f"QScrollArea#HeaderRibbon {{ background-color: {COLOR_BG_HEADER}; }}",
                    # Tránh apply cho mọi QWidget (sẽ đè QToolButton:hover)
                    f"QScrollArea#HeaderRibbon QWidget#qt_scrollarea_viewport {{ background-color: {COLOR_BG_HEADER}; }}",
                    f"#HeaderRibbonContent {{ background-color: {COLOR_BG_HEADER}; }}",
                    'QPushButton[tabButton="true"] { border: none; background: transparent; border-radius: 0px; }',
                    # Hover/Active nhẹ, tạo cảm giác liền mạch
                    f'QPushButton[tabButton="true"]:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_BG_HEADER}; border-radius: 0px; }}',
                    f'QPushButton[tabButton="true"][active="true"] {{ background-color: {COLOR_BUTTON_ACTIVE}; color: {COLOR_BG_HEADER}; border-radius: 0px; }}',
                    "#Header QToolButton { border: none; background: transparent; padding: 6px 6px; margin: 0px; border-radius: 0px; }",
                    f"#Header QToolButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; border-radius: 0px; color: {COLOR_BG_HEADER}; }}",
                ]
            )
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -----------------------------
        # Phần 1: 40px - thanh chức năng
        # -----------------------------
        top_bar = QWidget(self)
        top_bar.setObjectName("HeaderTopBar")
        top_bar.setMinimumWidth(MIN_MAINWINDOW_WIDTH)
        top_bar.setFixedHeight(40)
        top_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # border-bottom đã đặt trong stylesheet của Header

        top_layout = QHBoxLayout(top_bar)
        # Tạo khoảng thở nhẹ giữa các tab
        top_layout.setContentsMargins(8, 0, 8, 0)
        top_layout.setSpacing(0)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        button_font = QFont(UI_FONT, BUTTON_FONT)
        # Theo yêu cầu: giảm font + FONT_WEIGHT_NORMAL
        button_font.setPointSize(max(9, CONTENT_FONT))
        if FONT_WEIGHT_NORMAL >= 400:
            button_font.setWeight(QFont.Weight.Normal)

        self.btn_khai_bao = self._create_tab_button(
            "Khai báo", button_font, HeaderController.TAB_KHAI_BAO
        )
        self.btn_ket_noi = self._create_tab_button(
            "Kết nối", button_font, HeaderController.TAB_KET_NOI
        )
        self.btn_cham_cong = self._create_tab_button(
            "Chấm công", button_font, HeaderController.TAB_CHAM_CONG
        )
        self.btn_cong_cu = self._create_tab_button(
            "Công cụ", button_font, HeaderController.TAB_CONG_CU
        )

        # Không dùng gạch dọc; dùng spacing để tạo cảm giác liền mạch
        top_layout.addWidget(self.btn_khai_bao)
        top_layout.addWidget(self.btn_ket_noi)
        top_layout.addWidget(self.btn_cham_cong)
        top_layout.addWidget(self.btn_cong_cu)
        top_layout.addStretch(1)

        # -----------------------------
        # Phần 2: 110px - để trống
        # -----------------------------
        bottom_area = QWidget(self)
        bottom_area.setObjectName("HeaderBottomArea")
        bottom_area.setMinimumWidth(MIN_MAINWINDOW_WIDTH)
        bottom_area.setFixedHeight(110)
        bottom_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        # border-bottom đã đặt trong stylesheet của Header

        bottom_layout = QVBoxLayout(bottom_area)
        # Phần 2 cao cố định 110px, không thể cộng thêm padding dọc nếu không sẽ thiếu chỗ
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        # Phần 2: các phím chức năng (ribbon) trong vùng 120px
        ribbon = self._create_actions_ribbon(bottom_area)
        bottom_layout.addWidget(ribbon)

        root_layout.addWidget(top_bar)
        root_layout.addWidget(bottom_area)

    def _create_tab_button(self, text: str, font: QFont, tab_key: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFont(font)
        btn.setFixedWidth(self._BUTTON_FIXED_WIDTH)
        btn.setFixedHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        btn.setProperty("tabButton", "true")
        btn.setProperty("tabKey", tab_key)
        btn.setProperty("active", "false")
        return btn

    def set_active_tab(self, tab_key: str) -> None:
        """Đổi trạng thái active cho 4 tab."""
        tab_buttons = [
            self.btn_khai_bao,
            self.btn_ket_noi,
            self.btn_cham_cong,
            self.btn_cong_cu,
        ]

        for btn in tab_buttons:
            is_active = btn.property("tabKey") == tab_key
            btn.setProperty("active", "true" if is_active else "false")
            # Refresh QSS
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _create_actions_ribbon(self, parent: QWidget) -> QScrollArea:
        """Tạo dải phím chức năng cho phần 2 (120px)."""
        scroll = QScrollArea(parent)
        scroll.setObjectName("HeaderRibbon")
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(self._ACTION_BUTTON_FIXED_HEIGHT)

        content = QWidget()
        content.setObjectName("HeaderRibbonContent")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        content.setFixedHeight(self._ACTION_BUTTON_FIXED_HEIGHT)

        layout = QHBoxLayout(content)
        # Padding top/bottom + khoảng cách giữa các phím
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Theo yêu cầu: giảm font + FONT_WEIGHT_NORMAL
        font_normal = QFont(UI_FONT, max(9, CONTENT_FONT - 1))
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        # Lưu lại để controller cập nhật động
        self._ribbon_scroll = scroll
        self._ribbon_content = content
        self._ribbon_layout = layout
        self._ribbon_font = font_normal
        self.action_buttons: dict[str, QToolButton] = {}

        # Mặc định để controller set_actions()
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def set_actions(self, actions: list[tuple[str, str]]) -> None:
        """Render lại danh sách nút chức năng ở phần 2 theo tab hiện tại."""
        if self._ribbon_layout is None or self._ribbon_font is None:
            return

        # Xoá toàn bộ widget cũ (trừ stretch cuối)
        while self._ribbon_layout.count() > 0:
            item = self._ribbon_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        self.action_buttons.clear()

        for text, svg_file in actions:
            btn = self._create_action_button(text, svg_file, self._ribbon_font)
            btn.clicked.connect(
                lambda _checked=False, t=text: self.action_triggered.emit(t)
            )
            self._ribbon_layout.addWidget(btn)
            self.action_buttons[text] = btn

        self._ribbon_layout.addStretch(1)

    def _create_action_button(
        self, text: str, svg_file: str, font: QFont
    ) -> QToolButton:
        """Tạo 1 phím chức năng: icon trên, text dưới (có xuống dòng)."""
        btn = QToolButton()
        btn.setText(text)
        btn.setFont(font)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn.setFixedSize(
            self._ACTION_BUTTON_FIXED_WIDTH, self._ACTION_BUTTON_FIXED_HEIGHT
        )
        btn.setIconSize(QSize(self._ACTION_ICON_SIZE, self._ACTION_ICON_SIZE))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoRaise(True)
        # Style hover đã được áp dụng bằng stylesheet của Header

        s = str(svg_file or "").strip()
        if "/" in s or "\\" in s:
            icon_path = resource_path(s)
        else:
            icon_path = resource_path(f"assets/images/{s}")
        btn.setIcon(QIcon(icon_path))
        return btn
