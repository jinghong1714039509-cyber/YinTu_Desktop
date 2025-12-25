from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, 
                               QPushButton, QFileDialog, QHBoxLayout, QLineEdit, QDialogButtonBox)
from PySide6.QtCore import Qt

class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出标注数据")
        self.setFixedSize(450, 250)
        
        self.output_dir = ""
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 1. 选择格式
        layout.addWidget(QLabel("选择导出格式:"))
        self.combo = QComboBox()
        # 选项数据格式: (显示文本, 内部标识)
        self.combo.addItem("YOLO (.txt) - 实时检测 (Ultralytics/Darknet)", "YOLO")
        self.combo.addItem("Pascal VOC (.xml) - 通用检测基准 (ImageNet)", "VOC")
        self.combo.addItem("COCO (.json) - 大规模检测/分割 (MMDetection)", "COCO")
        self.combo.addItem("LabelMe (.json) - 交互式/实例分割编辑", "LabelMe")
        layout.addWidget(self.combo)
        
        # 2. 选择路径
        layout.addWidget(QLabel("导出路径:"))
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("请选择空文件夹...")
        self.path_edit.setReadOnly(True)
        
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self.select_folder)
        
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        
        # 3. 按钮
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def select_folder(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存位置")
        if d:
            self.output_dir = d
            self.path_edit.setText(d)
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def get_data(self):
        return {
            'format': self.combo.currentData(),
            'path': self.output_dir
        }