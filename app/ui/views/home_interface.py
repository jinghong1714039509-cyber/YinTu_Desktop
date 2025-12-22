# app/ui/views/home_interface.py
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from qfluentwidgets import SubtitleLabel, BodyLabel

class HomeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("homeInterface")
        self.vBoxLayout = QVBoxLayout(self)
        
        self.titleLabel = SubtitleLabel('YinTu 智能标注系统', self)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.descLabel = BodyLabel('PySide6 环境配置成功！可以开始写业务逻辑了。', self)
        self.descLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.vBoxLayout.addStretch(1)
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.descLabel)
        self.vBoxLayout.addStretch(1)