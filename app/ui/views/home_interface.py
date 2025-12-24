from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, PrimaryPushButton, CardWidget, IconWidget,
    FluentIcon as FIF
)


class HomeInterface(QWidget):
    """项目管理页：选择项目目录。"""

    project_selected = Signal(str)  # 信号：项目路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.initUI()

    def initUI(self):
        self.vBoxLayout.setSpacing(18)
        self.vBoxLayout.setContentsMargins(40, 40, 40, 40)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题与描述（卡片式）
        self.heroCard = CardWidget(self)
        heroLayout = QVBoxLayout(self.heroCard)
        heroLayout.setSpacing(10)
        heroLayout.setContentsMargins(26, 22, 26, 22)

        titleRow = QWidget(self.heroCard)
        titleRowLayout = QVBoxLayout(titleRow)
        titleRowLayout.setContentsMargins(0, 0, 0, 0)
        titleRowLayout.setSpacing(8)

        self.icon = IconWidget(FIF.FOLDER, self.heroCard)
        self.icon.setFixedSize(48, 48)

        self.titleLabel = SubtitleLabel("YinTu Desktop", self.heroCard)
        self.descLabel = BodyLabel("导入图片文件夹（后续可扩展：导入视频自动抽帧）", self.heroCard)
        self.descLabel.setWordWrap(True)

        titleRowLayout.addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        titleRowLayout.addWidget(self.titleLabel, alignment=Qt.AlignmentFlag.AlignHCenter)
        titleRowLayout.addWidget(self.descLabel, alignment=Qt.AlignmentFlag.AlignHCenter)

        heroLayout.addWidget(titleRow)

        self.importBtn = PrimaryPushButton("选择项目目录", self)
        self.importBtn.setIcon(FIF.FOLDER_ADD)
        self.importBtn.clicked.connect(self.open_folder)

        self.vBoxLayout.addStretch(1)
        self.vBoxLayout.addWidget(self.heroCard, stretch=0)
        self.vBoxLayout.addSpacing(8)
        self.vBoxLayout.addWidget(self.importBtn, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.vBoxLayout.addStretch(1)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if folder:
            self.project_selected.emit(str(Path(folder).resolve()))
