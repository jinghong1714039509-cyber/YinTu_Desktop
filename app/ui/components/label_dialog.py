from PySide6.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QLineEdit, 
                               QDialogButtonBox, QLabel)
from PySide6.QtCore import Qt

class LabelDialog(QDialog):
    def __init__(self, predefined_labels=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择标签")
        self.resize(300, 400)
        
        # 预设标签列表
        self.items = predefined_labels if predefined_labels else []
        
        layout = QVBoxLayout(self)
        
        # 输入框
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("输入新标签或从下方选择")
        layout.addWidget(self.edit)
        
        # 列表框
        self.listWidget = QListWidget()
        self.listWidget.addItems(self.items)
        self.listWidget.itemClicked.connect(self.on_item_clicked)
        self.listWidget.itemDoubleClicked.connect(self.accept) # 双击直接确认
        layout.addWidget(self.listWidget)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # 自动聚焦输入框
        self.edit.setFocus()

    def on_item_clicked(self, item):
        self.edit.setText(item.text())

    def get_label(self):
        """获取用户输入的标签"""
        return self.edit.text().strip()