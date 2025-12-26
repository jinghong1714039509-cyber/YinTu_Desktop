from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QCursor, QColor, QPalette

class SidebarItem(QPushButton):
    """
    自定义侧边栏按钮
    """
    def __init__(self, text, icon_text="●", parent=None):
        super().__init__(parent)
        self.setText(f" {icon_text}   {text}")
        self.setFixedHeight(50) 
        self.setCursor(Qt.PointingHandCursor)
        
        font = QFont("Microsoft YaHei UI", 10)
        font.setWeight(QFont.Medium)
        self.setFont(font)
        
        self.setCheckable(True)
        
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #c2c7d0;
                text-align: left;
                padding-left: 20px;
                border: none;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: #494e53;
                color: white;
            }
            QPushButton:checked {
                background-color: #007bff; 
                color: white;
                border-left: 3px solid #0056b3; 
                font-weight: bold;
            }
        """)

class Sidebar(QFrame):
    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(250) 
        
        # === 关键修改：添加左侧圆角，匹配主窗口 ===
        self.setStyleSheet("""
            Sidebar {
                background-color: #343a40;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
            }
        """)
        
        self.current_btn = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === 1. Logo 区域 ===
        logo_box = QFrame()
        logo_box.setFixedHeight(60)
        # 注意：这里去掉了背景色，让它透出 Sidebar 的圆角背景，或者单独设置圆角
        logo_box.setStyleSheet("background-color: transparent; border-bottom: 1px solid #4b545c;")
        logo_layout = QHBoxLayout(logo_box)
        logo_layout.setContentsMargins(15, 0, 0, 0)
        
        logo_icon = QLabel("Y")
        logo_icon.setFixedSize(32, 32)
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_icon.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; font-size: 18px; border-radius: 4px;")
        
        logo_text = QLabel("YinTu Admin")
        logo_text.setStyleSheet("color: white; font-size: 18px; font-weight: 300; margin-left: 10px; background-color: transparent;")
        
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch(1)
        layout.addWidget(logo_box)

        # === 2. 用户信息区 ===
        user_box = QFrame()
        user_box.setFixedHeight(70)
        user_box.setStyleSheet("border-bottom: 1px solid #4b545c; background-color: transparent;")
        user_layout = QHBoxLayout(user_box)
        user_layout.setContentsMargins(15, 0, 0, 0)
        
        user_avatar = QLabel("A")
        user_avatar.setFixedSize(35, 35)
        user_avatar.setAlignment(Qt.AlignCenter)
        user_avatar.setStyleSheet("background-color: #6c757d; color: white; border-radius: 17px; font-weight: bold;")
        
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        info_layout.setSpacing(2)
        
        user_name = QLabel("Administrator")
        user_name.setStyleSheet("color: #c2c7d0; font-size: 14px; font-weight: bold; background-color: transparent;")
        
        user_status = QLabel("● Online")
        user_status.setStyleSheet("color: #28a745; font-size: 11px; background-color: transparent;") 
        
        info_layout.addWidget(user_name)
        info_layout.addWidget(user_status)
        
        user_layout.addWidget(user_avatar)
        user_layout.addLayout(info_layout)
        user_layout.addStretch(1)
        layout.addWidget(user_box)

        # === 3. 导航菜单标题 ===
        menu_title = QLabel("主导航 / MAIN NAVIGATION")
        menu_title.setFixedHeight(35)
        menu_title.setStyleSheet("color: #6c757d; font-size: 11px; font-weight: bold; background-color: transparent; padding-top: 10px; padding-left: 15px;")
        layout.addWidget(menu_title)

        # === 4. 导航按钮组 ===
        self.btn_tasks = SidebarItem("任务列表 Task List", "📋")
        self.btn_tasks.clicked.connect(lambda: self.on_nav_click("tasks", self.btn_tasks))
        layout.addWidget(self.btn_tasks)
        
        layout.addStretch(1)

        # === 5. 底部版本号 ===
        version_lbl = QLabel("Version 1.0.0")
        version_lbl.setAlignment(Qt.AlignCenter)
        version_lbl.setStyleSheet("color: #505050; font-size: 10px; margin-bottom: 10px; background-color: transparent;")
        layout.addWidget(version_lbl)

        # 默认选中
        self.btn_tasks.setChecked(True)
        self.current_btn = self.btn_tasks

    def on_nav_click(self, page_name, sender_btn):
        if self.current_btn != sender_btn:
            if self.current_btn:
                self.current_btn.setChecked(False)
            sender_btn.setChecked(True)
            self.current_btn = sender_btn
            self.page_changed.emit(page_name)
        else:
            sender_btn.setChecked(True)