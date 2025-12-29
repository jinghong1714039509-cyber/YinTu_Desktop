import os
import sys
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QPainter, QColor, QPixmap

# === 帮助函数：获取图标绝对路径 ===
def get_icon_path(icon_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    path = os.path.join(project_root, "app", "assets", "icons", icon_name)
    if os.path.exists(path):
        return path
    path_local = os.path.abspath(os.path.join("app", "assets", "icons", icon_name))
    if os.path.exists(path_local):
        return path_local
    return None

class SidebarItem(QPushButton):
    def __init__(self, icon_name, tooltip, parent=None):
        super().__init__(parent=parent)
        self.setFixedSize(44, 44) 
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setCheckable(True)
        
        self.icon_name = icon_name
        self.icon_path = get_icon_path(icon_name)
        
        self.update_icon_color()

        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border-radius: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            QPushButton:checked {
                background-color: #E6F0FF;
            }
        """)
        
        self.toggled.connect(self.update_icon_color)

    def update_icon_color(self):
        if not self.icon_path:
            self.setText(self.icon_name[0].upper() if self.icon_name else "?") 
            return
            
        pixmap = QPixmap(self.icon_path)
        target_color = QColor("#3B82F6") if self.isChecked() else QColor("#555555")
        
        if not pixmap.isNull():
            mask = pixmap.createMaskFromColor(Qt.transparent, Qt.MaskInColor)
            pixmap.fill(target_color)
            pixmap.setMask(mask)
            self.setIcon(QIcon(pixmap))
            self.setIconSize(QSize(24, 24))
            self.setText("")

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.isChecked():
            painter = QPainter(self)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#3B82F6"))
            painter.drawRoundedRect(0, 12, 3, 20, 1.5, 1.5)

class Sidebar(QFrame):
    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(68) 
        self.setStyleSheet("""
            Sidebar {
                background-color: #F3F3F3; 
                border-right: 1px solid #E0E0E0; 
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
            }
        """)
        self.current_btn = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignHCenter)

        logo = QLabel("Y")
        logo.setFixedSize(40, 40)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B82F6, stop:1 #2563EB); color: white; font-weight: 900; font-size: 20px; border-radius: 10px;")
        layout.addWidget(logo)
        layout.addSpacing(20)

        # 确保这些 SVG 文件名与您文件夹里的一致
        self.btn_tasks = SidebarItem("folder.svg", "任务列表")
        self.btn_tasks.clicked.connect(lambda: self.on_nav_click("tasks", self.btn_tasks))
        layout.addWidget(self.btn_tasks)

        self.btn_label = SidebarItem("edit.svg", "标注工作台")
        self.btn_label.setCheckable(True)
        layout.addWidget(self.btn_label)

        self.btn_ai = SidebarItem("brain.svg", "AI 模型")
        layout.addWidget(self.btn_ai)

        self.btn_stats = SidebarItem("chart.svg", "统计报表")
        layout.addWidget(self.btn_stats)

        layout.addStretch(1)

        self.btn_settings = SidebarItem("settings.svg", "设置")
        layout.addWidget(self.btn_settings)
        
        self.btn_user = SidebarItem("user.svg", "用户")
        layout.addWidget(self.btn_user)

        self.btn_tasks.setChecked(True)
        self.current_btn = self.btn_tasks

    def on_nav_click(self, page_name, sender_btn):
        if self.current_btn != sender_btn:
            if self.current_btn: self.current_btn.setChecked(False)
            sender_btn.setChecked(True)
            self.current_btn = sender_btn
            self.page_changed.emit(page_name)
        else:
            sender_btn.setChecked(True)