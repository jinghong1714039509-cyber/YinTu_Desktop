import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QCursor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QToolTip


def get_icon_path(icon_name: str) -> Optional[str]:
    """Return an absolute icon path for both dev-run and packaged (PyInstaller) runs."""
    candidates: list[Path] = []

    # PyInstaller one-file bundle
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "app" / "ui" / "assets" / "icons" / icon_name)

    # Normal source layout: app/ui/components -> app/ui/assets/icons
    ui_dir = Path(__file__).resolve().parents[1]  # .../app/ui
    candidates.append(ui_dir / "assets" / "icons" / icon_name)

    # Fallback: run from project root (cwd)
    candidates.append(Path.cwd() / "app" / "ui" / "assets" / "icons" / icon_name)

    for p in candidates:
        if p.exists():
            return str(p)

    return None


def render_icon_with_bg(
    icon_path: str,
    size: int,
    fg: QColor,
    bg: QColor,
    radius: int = 10,
    padding: int = 4,
) -> QPixmap:
    """
    Render svg icon to pixmap with a solid background tile to avoid transparency issues.
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    if not icon_path:
        return pm

    # render svg to pixmap
    renderer = QSvgRenderer(icon_path)
    icon_pm = QPixmap(size - padding * 2, size - padding * 2)
    icon_pm.fill(Qt.transparent)

    p = QPainter(icon_pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(p)
    p.end()

    # tint svg-rendered pixmap
    tinted = QPixmap(icon_pm.size())
    tinted.fill(Qt.transparent)

    p = QPainter(tinted)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.drawPixmap(0, 0, icon_pm)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(tinted.rect(), fg)
    p.end()

    # compose bg + tinted icon
    out = QPixmap(size, size)
    out.fill(Qt.transparent)

    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    p.setBrush(bg)  # 不透明底板
    p.drawRoundedRect(0, 0, size, size, radius, radius)
    p.drawPixmap(padding, padding, tinted)
    p.end()

    return out


class SidebarItem(QPushButton):
    def __init__(self, icon_name: str, tooltip: str, parent=None):
        super().__init__(parent=parent)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setCheckable(True)

        self.icon_name = icon_name
        self.icon_path = get_icon_path(icon_name)

        # 按钮本体保持干净：图标自己带“不透明底板”，避免透出桌面壁纸
        self.setStyleSheet(
            """
            QPushButton { background-color: transparent; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: rgba(59,130,246,0.12); }
            QPushButton:checked { background-color: rgba(59,130,246,0.18); }
            """
        )

        self.update_icon()

    def update_icon(self):
        if not self.icon_path:
            self.setText(self.icon_name[0].upper() if self.icon_name else "?")
            return

        fg = QColor("#3B82F6") if self.isChecked() else QColor("#555555")
        bg = QColor("#FFFFFF")
        pm = render_icon_with_bg(self.icon_path, 28, fg, bg, radius=10, padding=5)

        if pm.isNull():
            self.setText(self.icon_name[0].upper() if self.icon_name else "?")
            return

        self.setIcon(QIcon(pm))
        self.setIconSize(QSize(28, 28))
        self.setText("")

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.isChecked():
            p = QPainter(self)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#3B82F6"))
            p.drawRoundedRect(0, 12, 3, 20, 1.5, 1.5)
            p.end()


class Sidebar(QFrame):
    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(68)
        self.setStyleSheet(
            """
            Sidebar {
                background-color: #F3F3F3;
                border-right: 1px solid #E0E0E0;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
            }
            """
        )
        self.current_btn = None
        self.initUI()

    def show_todo_tip(self, message: str = "功能待补充"):
        """Show a tooltip near cursor for unimplemented navigation items."""
        QToolTip.showText(QCursor.pos(), message, self)

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignHCenter)

        logo = QLabel("Y")
        logo.setFixedSize(40, 40)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B82F6, stop:1 #2563EB); "
            "color: white; font-weight: 700; border-radius: 10px;"
        )
        layout.addWidget(logo)

        layout.addSpacing(8)

        # 第一个按钮：真实可用
        self.btn_tasks = SidebarItem("folder.svg", "任务列表")
        self.btn_tasks.clicked.connect(lambda: self.on_nav_click("tasks", self.btn_tasks))
        layout.addWidget(self.btn_tasks)

        # 其它按钮：暂未实现 -> 悬停/点击提示“功能待补充”
        self.btn_label = SidebarItem("edit.svg", "功能待补充")
        self.btn_label.setCheckable(False)
        self.btn_label.clicked.connect(lambda: self.show_todo_tip())
        layout.addWidget(self.btn_label)

        self.btn_ai = SidebarItem("brain.svg", "功能待补充")
        self.btn_ai.setCheckable(False)
        self.btn_ai.clicked.connect(lambda: self.show_todo_tip())
        layout.addWidget(self.btn_ai)

        self.btn_stats = SidebarItem("chart.svg", "功能待补充")
        self.btn_stats.setCheckable(False)
        self.btn_stats.clicked.connect(lambda: self.show_todo_tip())
        layout.addWidget(self.btn_stats)

        layout.addStretch(1)

        self.btn_settings = SidebarItem("setting.svg", "功能待补充")
        self.btn_settings.setCheckable(False)
        self.btn_settings.clicked.connect(lambda: self.show_todo_tip())
        layout.addWidget(self.btn_settings)

        self.btn_user = SidebarItem("user.svg", "功能待补充")
        self.btn_user.setCheckable(False)
        self.btn_user.clicked.connect(lambda: self.show_todo_tip())
        layout.addWidget(self.btn_user)

        self.btn_tasks.setChecked(True)
        self.current_btn = self.btn_tasks

    def on_nav_click(self, page_name: str, sender_btn: SidebarItem):
        if self.current_btn != sender_btn:
            if self.current_btn:
                self.current_btn.setChecked(False)
            sender_btn.setChecked(True)
            self.current_btn = sender_btn
            self.page_changed.emit(page_name)
        else:
            sender_btn.setChecked(True)
