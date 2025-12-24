from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QCursor, QColor, QPalette

class SidebarItem(QPushButton):
    """
    自定义侧边栏按钮 - 仿 AdminLTE 样式
    """
    def __init__(self, text, icon_text="●", parent=None):
        super().__init__(parent)
        self.setText(f" {icon_text}   {text}")
        self.setFixedHeight(50) # 按钮高度
        self.setCursor(Qt.PointingHandCursor)
        
        # 字体设置：使用微软雅黑或 Segoe UI
        font = QFont("Microsoft YaHei UI", 10)
        font.setWeight(QFont.Medium)
        self.setFont(font)
        
        self.setCheckable(True)
        
        # 样式表：包含正常状态、悬停状态、选中状态
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
                background-color: #007bff; /* 选中时的蓝色背景 */
                color: white;
                border-left: 3px solid #0056b3; /* 左侧深蓝装饰条 */
                font-weight: bold;
            }
        """)

class Sidebar(QFrame):
    """
    左侧主导航栏容器
    """
    # 信号：通知主窗口切换页面 (参数: 页面ID)
    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(250) # 固定宽度
        self.setStyleSheet("background-color: #343a40;") # AdminLTE 深色背景
        
        self.current_btn = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === 1. Logo 区域 ===
        logo_box = QFrame()
        logo_box.setFixedHeight(57)
        logo_box.setStyleSheet("border-bottom: 1px solid #4b545c; background-color: #363d42;")
        logo_layout = QHBoxLayout(logo_box)
        logo_layout.setContentsMargins(15, 0, 0, 0)
        
        # 简单的 Logo 图标
        logo_icon = QLabel("Y")
        logo_icon.setFixedSize(32, 32)
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_icon.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; font-size: 18px; border-radius: 4px;")
        
        logo_text = QLabel("YinTu Admin")
        logo_text.setStyleSheet("color: white; font-size: 18px; font-weight: 300; margin-left: 10px;")
        
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch(1)
        
        layout.addWidget(logo_box)

        # === 2. 用户信息区 ===
        user_box = QFrame()
        user_box.setFixedHeight(70)
        user_box.setStyleSheet("border-bottom: 1px solid #4b545c;")
        user_layout = QHBoxLayout(user_box)
        user_layout.setContentsMargins(15, 0, 0, 0)
        
        # 用户头像
        user_avatar = QLabel("A")
        user_avatar.setFixedSize(35, 35)
        user_avatar.setAlignment(Qt.AlignCenter)
        user_avatar.setStyleSheet("background-color: #6c757d; color: white; border-radius: 17px; font-weight: bold;")
        
        # 用户名和状态
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        info_layout.setSpacing(2)
        
        user_name = QLabel("Administrator")
        user_name.setStyleSheet("color: #c2c7d0; font-size: 14px; font-weight: bold;")
        
        user_status = QLabel("● Online")
        user_status.setStyleSheet("color: #28a745; font-size: 11px;") # 绿色在线点
        
        info_layout.addWidget(user_name)
        info_layout.addWidget(user_status)
        
        user_layout.addWidget(user_avatar)
        user_layout.addLayout(info_layout)
        user_layout.addStretch(1)
        
        layout.addWidget(user_box)

        # === 3. 导航菜单标题 ===
        menu_title = QLabel("主导航 / MAIN NAVIGATION")
        menu_title.setFixedHeight(35)
        menu_title.setStyleSheet("color: #6c757d; font-size: 11px; font-weight: bold; background-color: #343a40; padding-top: 10px; padding-left: 15px;")
        layout.addWidget(menu_title)

        # === 4. 导航按钮组 (根据您的需求修改) ===
        
        # 按钮 1: 任务统计 (对应 HomeInterface)
        self.btn_stats = SidebarItem("任务统计 Statistics", "📊")
        self.btn_stats.clicked.connect(lambda: self.on_nav_click("stats"))
        
        # 按钮 2: 任务列表 (对应 TaskListInterface)
        self.btn_tasks = SidebarItem("任务列表 Task List", "📋")
        self.btn_tasks.clicked.connect(lambda: self.on_nav_click("tasks"))
        
        # 按钮 3: 系统设置 (预留)
        self.btn_settings = SidebarItem("系统设置 Settings", "⚙️")
        self.btn_settings.clicked.connect(lambda: self.on_nav_click("settings"))

        layout.addWidget(self.btn_stats)
        layout.addWidget(self.btn_tasks)
        layout.addWidget(self.btn_settings)
        
        layout.addStretch(1) # 底部弹簧，把按钮顶上去

        # === 5. 底部版本号 ===
        version_lbl = QLabel("Version 1.0.0")
        version_lbl.setAlignment(Qt.AlignCenter)
        version_lbl.setStyleSheet("color: #505050; font-size: 10px; margin-bottom: 10px;")
        layout.addWidget(version_lbl)

        # 默认选中第一个
        self.btn_stats.setChecked(True)
        self.current_btn = self.btn_stats

    def on_nav_click(self, page_name):
        """处理按钮点击，实现互斥选中效果"""
        sender = self.sender()
        
        # 如果点击的不是当前选中的，才切换
        if self.current_btn != sender:
            # 取消旧按钮的选中状态
            if self.current_btn:
                self.current_btn.setChecked(False)
            
            # 选中新按钮
            sender.setChecked(True)
            self.current_btn = sender
            
            # 发射信号给主窗口
            self.page_changed.emit(page_name)
        else:
            # 如果点击的是当前按钮，强制保持选中状态（防止被取消选中）
            sender.setChecked(True)