from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, 
                               QPushButton, QFileDialog, QHBoxLayout, QLineEdit, 
                               QDialogButtonBox, QFormLayout)
from PySide6.QtCore import Qt

class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出标注数据")
        
        # === 修复 1: 移除 FixedSize，改用最小宽度，防止DPI缩放导致内容被截断出现滚动条 ===
        self.setMinimumWidth(500) 
        # self.setFixedSize(450, 250) # <--- 删除这行
        
        # === 修复 2: 强制设置样式，特别是下拉框弹层的背景色，防止透底 ===
        self.setStyleSheet("""
            QDialog { 
                background-color: #ffffff; 
                color: #333333; 
            }
            QLabel { 
                color: #333333; 
                font-size: 14px; 
                font-weight: bold;
            }
            /* 下拉框主体 */
            QComboBox { 
                padding: 6px; 
                border: 1px solid #ccc; 
                border-radius: 4px;
                background-color: #f9f9f9;
                color: #333;
            }
            /* === 关键: 修复下拉弹层透底/黑色问题 === */
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #ccc;
                selection-background-color: #007bff;
                selection-color: white;
                color: #333;
                outline: none;
            }
            /* 输入框 */
            QLineEdit { 
                padding: 6px; 
                color: #333333; 
                background-color: #f0f0f0; 
                border: 1px solid #ccc; 
                border-radius: 4px;
            }
            /* 浏览按钮 */
            QPushButton { 
                padding: 6px 15px; 
                border-radius: 4px;
                background-color: #e0e0e0;
                border: 1px solid #ccc;
                color: #333;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)
        
        self.output_dir = ""
        self.initUI()

    def initUI(self):
        # 主布局使用 VBox，增加边距
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 20)
        main_layout.setSpacing(20)
        
        # === 修复 3: 使用 QFormLayout 自动对齐标签和控件，消除奇怪留白 ===
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight) # 标签右对齐，看起来更专业
        
        # 1. 选择格式
        self.combo = QComboBox()
        self.combo.addItem("YOLO (.txt) - 实时检测 (Ultralytics/Darknet)", "YOLO")
        self.combo.addItem("Pascal VOC (.xml) - 通用检测基准 (ImageNet)", "VOC")
        self.combo.addItem("COCO (.json) - 大规模检测/分割 (MMDetection)", "COCO")
        self.combo.addItem("LabelMe (.json) - 交互式/实例分割编辑", "LabelMe")
        form_layout.addRow("导出格式:", self.combo)
        
        # 2. 选择路径 (组合控件)
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0) # 内部无边距
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("请选择保存文件夹...")
        self.path_edit.setReadOnly(True)
        
        btn_browse = QPushButton("浏览...")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self.select_folder)
        
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(btn_browse)
        
        form_layout.addRow("保存路径:", path_layout)

        main_layout.addLayout(form_layout)
        
        # 弹簧：把按钮顶到底部
        main_layout.addStretch(1)
        
        # 3. 底部按钮
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        
        # 美化确定按钮 (蓝色主色调)
        self.buttons.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0069d9; }
            QPushButton:disabled { background-color: #a0a0a0; }
        """)
        
        main_layout.addWidget(self.buttons)
        
        # 初始禁用 OK 按钮
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