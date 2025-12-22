from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QGraphicsView, 
                               QGraphicsScene, QGraphicsRectItem, 
                               QGraphicsPixmapItem, QGraphicsItem)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QPen, QColor, QBrush

# --- 1. 自定义标注框对象 (BoxItem) ---
class BoxItem(QGraphicsRectItem):
    """
    这是画在图上的那个红框框
    """
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)
        # 设置画笔（红色，宽度2）
        self.setPen(QPen(QColor(255, 0, 0), 2))
        # 设置笔刷（透明的红色，选中时变色）
        self.setBrush(QBrush(Qt.NoBrush))
        
        # 允许被选中、允许被移动
        self.setFlags(QGraphicsItem.ItemIsSelectable | 
                      QGraphicsItem.ItemIsMovable | 
                      QGraphicsItem.ItemSendsGeometryChanges)

    def paint(self, painter, option, widget=None):
        # 自定义绘制，为了选中时更好看
        if self.isSelected():
            # 选中时：虚线框，内部填充淡红色
            pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 0, 0, 50)))
        else:
            # 普通：实线框，无填充
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(Qt.NoBrush)
            
        painter.drawRect(self.rect())

# --- 2. 自定义画板 (View) ---
class ImageGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 基础设置
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 模式状态：'VIEW' (浏览/拖拽) 或 'DRAW' (画框)
        self.mode = 'VIEW' 
        self.first_show = True
        
        # 绘图临时变量
        self.temp_item = None
        self.start_point = None

    def set_mode(self, mode):
        self.mode = mode
        if mode == 'VIEW':
            self.setDragMode(QGraphicsView.ScrollHandDrag) # 手型拖拽
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.NoDrag) # 禁用自带拖拽，自己处理
            self.setCursor(Qt.CrossCursor) # 十字光标

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.first_show and self.scene() and self.scene().itemsBoundingRect().isValid():
             self.fit_image_to_view()

    def fit_image_to_view(self):
        if self.scene() and self.scene().itemsBoundingRect().isValid():
            rect = self.scene().itemsBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent):
        self.first_show = False
        zoomInFactor = 1.15
        zoomOutFactor = 1 / zoomInFactor
        zoom_factor = zoomInFactor if event.angleDelta().y() > 0 else zoomOutFactor
        self.scale(zoom_factor, zoom_factor)

    # --- 鼠标事件：处理画框核心逻辑 ---
    def mousePressEvent(self, event):
        if self.mode == 'DRAW' and event.button() == Qt.LeftButton:
            # 1. 获取点击在场景中的坐标
            self.start_point = self.mapToScene(event.pos())
            # 2. 创建一个临时矩形
            self.temp_item = BoxItem(self.start_point.x(), self.start_point.y(), 0, 0)
            self.scene().addItem(self.temp_item)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mode == 'DRAW' and self.temp_item is not None:
            # 拖动时，更新矩形的大小
            current_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, current_point).normalized()
            self.temp_item.setRect(0, 0, rect.width(), rect.height())
            self.temp_item.setPos(rect.topLeft())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == 'DRAW' and self.temp_item is not None:
            # 松开鼠标，画框完成
            # 如果框太小（误触），就删掉
            if self.temp_item.rect().width() < 5 or self.temp_item.rect().height() < 5:
                self.scene().removeItem(self.temp_item)
            
            self.temp_item = None # 重置
            # 可选：画完一个框后是否自动切回浏览模式？这里先保持连续画图
        else:
            super().mouseReleaseEvent(event)

# --- 3. 界面主体 ---
class LabelInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = None
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- 左侧工具栏 ---
        self.toolBar = QWidget()
        self.toolBar.setFixedWidth(200)
        self.toolBar.setStyleSheet("background-color: #2b2b2b; border-right: 1px solid #3c3c3c;")
        
        toolLayout = QVBoxLayout(self.toolBar)
        
        # 标题
        toolTitle = QLabel("工具箱")
        toolTitle.setStyleSheet("color: white; font-weight: bold; font-size: 16px; margin-top: 10px;")
        toolTitle.setAlignment(Qt.AlignCenter)
        
        # 样式
        btn_style = """
            QPushButton { background-color: #3c3c3c; color: white; border: none; padding: 10px; border-radius: 4px; text-align: left; }
            QPushButton:hover { background-color: #4c4c4c; }
            QPushButton:checked { background-color: #0078d4; }
        """
        
        # 模式切换按钮
        self.btnHand = QPushButton("✋ 浏览模式 (Hand)")
        self.btnHand.setCheckable(True)
        self.btnHand.setStyleSheet(btn_style)
        self.btnHand.clicked.connect(lambda: self.switch_mode('VIEW'))
        
        self.btnRect = QPushButton("✏️ 标矩形框 (Rect)")
        self.btnRect.setCheckable(True)
        self.btnRect.setStyleSheet(btn_style)
        self.btnRect.clicked.connect(lambda: self.switch_mode('DRAW'))

        self.btnPrev = QPushButton("⬅️ 上一张")
        self.btnNext = QPushButton("➡️ 下一张")
        self.btnPrev.setStyleSheet(btn_style)
        self.btnNext.setStyleSheet(btn_style)

        self.btnAI = QPushButton("🤖 AI 自动标注")
        self.btnAI.setStyleSheet("background-color: #28a745; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
        
        # 布局添加
        toolLayout.addWidget(toolTitle)
        toolLayout.addSpacing(20)
        toolLayout.addWidget(self.btnHand)
        toolLayout.addWidget(self.btnRect)
        toolLayout.addSpacing(20)
        toolLayout.addWidget(self.btnAI)
        toolLayout.addStretch(1)
        toolLayout.addWidget(self.btnPrev)
        toolLayout.addWidget(self.btnNext)
        toolLayout.addSpacing(20)

        # --- 右侧绘图区 ---
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(30, 30, 30))
        self.view = ImageGraphicsView(self.scene)

        layout.addWidget(self.toolBar)
        layout.addWidget(self.view)

        # 默认选中浏览模式
        self.switch_mode('VIEW')

    def switch_mode(self, mode):
        """切换工具模式"""
        self.view.set_mode(mode)
        # 更新按钮状态
        self.btnHand.setChecked(mode == 'VIEW')
        self.btnRect.setChecked(mode == 'DRAW')

    def load_image(self, image_path):
        self.current_image_path = image_path
        self.scene.clear()
        
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            item = QGraphicsPixmapItem(pixmap)
            item.setTransformationMode(Qt.SmoothTransformation)
            # 图片不能被移动，只能被看
            item.setFlags(QGraphicsItem.ItemIsSelectable) 
            self.scene.addItem(item)
            
            self.view.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.first_show = True
            self.view.fit_image_to_view()