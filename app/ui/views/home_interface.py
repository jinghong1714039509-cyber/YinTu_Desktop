from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import SubtitleLabel, PrimaryPushButton, CardWidget, BodyLabel, IconWidget
from qfluentwidgets import FluentIcon as FIF

class HomeInterface(QWidget):
    project_selected = Signal(str) # 信号：项目路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.initUI()

    def initUI(self):
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        self.titleLabel = SubtitleLabel("欢迎使用 YinTu 智能标注系统", self)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 导入文件夹按钮
        self.importBtn = PrimaryPushButton(FIF.FOLDER, "打开/创建项目文件夹", self)
        self.importBtn.setFixedWidth(240)
        self.importBtn.clicked.connect(self.open_folder)

        # 说明文字
        self.descLabel = BodyLabel("支持导入视频（自动抽帧）或直接导入图片文件夹", self)
        self.descLabel.setTextColor("#808080", "#808080")

        self.vBoxLayout.addStretch(1)
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.descLabel)
        self.vBoxLayout.addSpacing(20)
        self.vBoxLayout.addWidget(self.importBtn)
        self.vBoxLayout.addStretch(1)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if folder:
            self.project_selected.emit(folder)