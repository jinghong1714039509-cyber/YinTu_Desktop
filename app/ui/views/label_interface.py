from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from qfluentwidgets import CardWidget, TitleLabel, PushButton, FluentIcon as FIF

class LabelInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = None
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        
        # 左侧：工具栏
        self.toolBar = CardWidget(self)
        self.toolBar.setFixedWidth(200)
        toolLayout = QVBoxLayout(self.toolBar)
        
        self.btnPrev = PushButton(FIF.LEFT_ARROW, "上一张", self)
        self.btnNext = PushButton(FIF.RIGHT_ARROW, "下一张", self)
        self.btnAI = PushButton(FIF.ROBOT, "AI 自动标注", self)
        
        toolLayout.addWidget(TitleLabel("工具箱", self))
        toolLayout.addWidget(self.btnPrev)
        toolLayout.addWidget(self.btnNext)
        toolLayout.addSpacing(20)
        toolLayout.addWidget(self.btnAI)
        toolLayout.addStretch(1)

        # 右侧：绘图区
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # 允许拖拽
        self.view.setRenderHint(self.view.renderHints() | Qt.RenderHint.Antialiasing)

        layout.addWidget(self.toolBar)
        layout.addWidget(self.view)

    def load_image(self, image_path):
        """加载图片到画布"""
        self.current_image_path = image_path
        self.scene.clear()
        
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(item)
            self.view.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.fitInView(item, Qt.AspectRatioMode.KeepAspectRatio)