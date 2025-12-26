from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal

class Header(QFrame):
    """现代风格顶部导航栏 (含窗口控制)"""
    # 定义信号，让主窗口去处理实际的窗口操作
    min_clicked = Signal()
    max_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50) 
        # 背景透明，由主窗口统一控制圆角背景
        self.setStyleSheet("background-color: transparent; border-bottom: 1px solid #eef1f6;")
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 15, 0)
        layout.setSpacing(8)

        # 左侧：Logo / 标题
        logo = QLabel("YinTu")
        logo.setStyleSheet("font-weight: 900; font-size: 16px; color: #007bff; font-family: 'Arial';")
        layout.addWidget(logo)
        
        title = QLabel("Desktop")
        title.setStyleSheet("font-weight: normal; font-size: 16px; color: #555; margin-left: 5px;")
        layout.addWidget(title)

        layout.addStretch(1)

        # 右侧：窗口控制按钮组
        # 1. 最小化
        self.btn_min = self.create_win_btn("─", "最小化")
        self.btn_min.clicked.connect(self.min_clicked.emit)
        
        # 2. 最大化/还原
        self.btn_max = self.create_win_btn("□", "最大化")
        self.btn_max.clicked.connect(self.max_clicked.emit)
        
        # 3. 关闭
        self.btn_close = self.create_win_btn("✕", "关闭", is_close=True)
        self.btn_close.clicked.connect(self.close_clicked.emit)

        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)

    def create_win_btn(self, text, tooltip, is_close=False):
        btn = QPushButton(text)
        btn.setFixedSize(35, 30)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        
        hover_color = "#dc3545" if is_close else "#e2e6ea"
        text_color = "white" if is_close else "#333"
        
        btn.setStyleSheet(f"""
            QPushButton {{
                border: none; border-radius: 4px; 
                font-size: 14px; color: #888;
                background-color: transparent;
            }}
            QPushButton:hover {{
                background-color: {hover_color}; 
                color: {text_color};
            }}
        """)
        return btn