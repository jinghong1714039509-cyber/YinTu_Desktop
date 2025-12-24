from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class CardWidget(QFrame):
    """
    仿 AdminLTE 风格的卡片组件
    特点：白色背景、阴影、顶部有一条彩色装饰线
    """
    def __init__(self, title="", parent=None, top_color="#007bff"):
        super().__init__(parent)
        self.top_color = top_color
        self.title_text = title
        
        self.initUI()
        self.setupStyle()

    def initUI(self):
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. 标题栏 (Header)
        if self.title_text:
            self.header = QFrame(self)
            self.header.setFixedHeight(45)
            self.header.setStyleSheet("border-bottom: 1px solid #f4f4f4; background: transparent; border-top: none;")
            
            header_layout = QVBoxLayout(self.header)
            header_layout.setContentsMargins(15, 0, 15, 0)
            header_layout.setAlignment(Qt.AlignVCenter)
            
            self.title_label = QLabel(self.title_text)
            self.title_label.setStyleSheet("font-size: 16px; font-weight: 500; color: #444; border: none;")
            header_layout.addWidget(self.title_label)
            
            self.main_layout.addWidget(self.header)

        # 2. 内容区域 (Content)
        self.content_area = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(20, 20, 20, 20) # 内边距
        
        self.main_layout.addWidget(self.content_area)

    def setupStyle(self):
        # 设置卡片本身的样式
        # 注意：这里使用 ID 选择器 #CardWidget 确保样式只应用到外壳，不影响内部控件
        self.setObjectName("CardWidget")
        self.setStyleSheet(f"""
            #CardWidget {{
                background-color: white;
                border-radius: 4px;
                border: 1px solid #d2d6de;
                border-top: 3px solid {self.top_color};
            }}
        """)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 20)) # 淡黑色阴影
        self.setGraphicsEffect(shadow)

    def add_widget(self, widget):
        """向卡片内容区添加控件的快捷方法"""
        self.content_layout.addWidget(widget)