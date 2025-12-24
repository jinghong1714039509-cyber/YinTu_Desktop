from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt

class Header(QFrame):
    """仿 AdminLTE 顶部白色导航栏"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(57) # 标准高度
        self.setStyleSheet("background-color: white; border-bottom: 1px solid #dee2e6;")
        
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)

        # 左侧：汉堡菜单按钮 (装饰用)
        self.btn_menu = QPushButton("☰")
        self.btn_menu.setFixedSize(40, 40)
        self.btn_menu.setCursor(Qt.PointingHandCursor)
        self.btn_menu.setStyleSheet("""
            QPushButton { border: none; font-size: 20px; color: #606060; }
            QPushButton:hover { color: #333; }
        """)
        layout.addWidget(self.btn_menu)

        # 左侧：文字导航
        lbl_home = QLabel("Home")
        lbl_home.setStyleSheet("color: #707070; margin-left: 10px; font-size: 14px;")
        layout.addWidget(lbl_home)

        # 中间弹簧 (把后面的东西顶到右边)
        layout.addStretch(1)

        # 右侧：功能图标
        self.add_icon_btn("🔔") # 通知
        self.add_icon_btn("⚙️") # 设置

        # --- 关键：关闭程序的按钮 ---
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(45, 57)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton { border: none; font-size: 16px; color: #707070; }
            QPushButton:hover { background-color: #dc3545; color: white; }
        """)
        layout.addWidget(self.btn_close)

    def add_icon_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { border: none; font-size: 16px; color: #707070; }
            QPushButton:hover { color: #333; }
        """)
        self.layout().addWidget(btn)