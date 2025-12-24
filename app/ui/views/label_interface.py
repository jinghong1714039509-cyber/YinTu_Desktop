from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QGraphicsView, 
                               QGraphicsScene, QGraphicsRectItem, 
                               QGraphicsPixmapItem, QGraphicsItem,
                               QFrame, QMessageBox)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QPen, QColor, QBrush

# --- 1. 矩形框对象 ---
class BoxItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h, label_text="Object"):
        super().__init__(x, y, w, h)
        self.label_text = label_text
        self.setPen(QPen(QColor(0, 255, 0), 2)) # AI 的框用绿色
        self.setBrush(QBrush(QColor(0, 255, 0, 30))) # 淡淡的填充
        self.setFlags(QGraphicsItem.ItemIsSelectable | 
                      QGraphicsItem.ItemIsMovable | 
                      QGraphicsItem.ItemSendsGeometryChanges)
        # 鼠标悬停显示标签信息
        self.setToolTip(f"{label_text}")

    def paint(self, painter, option, widget=None):
        # 选中变红，未选中绿色
        color = QColor(255, 0, 0) if self.isSelected() else QColor(0, 255, 0)
        
        pen = QPen(color, 2)
        if self.isSelected():
            pen.setStyle(Qt.DashLine)
            
        painter.setPen(pen)
        painter.setBrush(QBrush(color.lighter(160)) if self.isSelected() else QBrush(Qt.NoBrush))
        painter.drawRect(self.rect())

# --- 2. 画板 View (保持不变，略过重复代码以节省篇幅，功能与之前一致) ---
class ImageGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.mode = 'VIEW' 
        self.first_show = True
        self.temp_item = None
        self.start_point = None

    def set_mode(self, mode):
        self.mode = mode
        if mode == 'VIEW':
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)

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

    def mousePressEvent(self, event):
        if self.mode == 'DRAW' and event.button() == Qt.LeftButton:
            self.start_point = self.mapToScene(event.pos())
            self.temp_item = BoxItem(self.start_point.x(), self.start_point.y(), 0, 0, "New")
            self.scene().addItem(self.temp_item)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mode == 'DRAW' and self.temp_item is not None:
            current_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, current_point).normalized()
            self.temp_item.setRect(0, 0, rect.width(), rect.height())
            self.temp_item.setPos(rect.topLeft())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == 'DRAW' and self.temp_item is not None:
            if self.temp_item.rect().width() < 5 or self.temp_item.rect().height() < 5:
                self.scene().removeItem(self.temp_item)
            self.temp_item = None
        else:
            super().mouseReleaseEvent(event)

# --- 3. 界面主体 ---
class LabelInterface(QWidget):
    # 发送这个信号，让 MainWindow 去调 Worker
    request_ai_signal = Signal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = None
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- 侧边栏 ---
        self.toolBar = QWidget()
        self.toolBar.setFixedWidth(220)
        self.toolBar.setStyleSheet("background-color: #f8f9fa; border-right: 1px solid #dee2e6; color: #333;")
        
        toolLayout = QVBoxLayout(self.toolBar)
        toolLayout.setContentsMargins(15, 20, 15, 20)
        toolLayout.setSpacing(10)
        
        toolTitle = QLabel("工具箱 / Tools")
        toolTitle.setStyleSheet("font-weight: bold; font-size: 14px; color: #495057; margin-bottom: 10px; border: none;")
        toolLayout.addWidget(toolTitle)
        
        btn_style = "QPushButton { background-color: #ffffff; color: #444; border: 1px solid #ced4da; padding: 8px; border-radius: 4px; text-align: left; } QPushButton:hover { background-color: #e9ecef; } QPushButton:checked { background-color: #007bff; color: white; }"
        
        self.btnHand = QPushButton("✋ 浏览模式 (View)")
        self.btnHand.setCheckable(True)
        self.btnHand.setStyleSheet(btn_style)
        self.btnHand.clicked.connect(lambda: self.switch_mode('VIEW'))
        
        self.btnRect = QPushButton("✏️ 矩形标注 (Draw)")
        self.btnRect.setCheckable(True)
        self.btnRect.setStyleSheet(btn_style)
        self.btnRect.clicked.connect(lambda: self.switch_mode('DRAW'))

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ccc; margin: 10px 0;")

        self.btnPrev = QPushButton("⬅️ 上一张")
        self.btnNext = QPushButton("➡️ 下一张")
        self.btnPrev.setStyleSheet(btn_style)
        self.btnNext.setStyleSheet(btn_style)

        # AI 按钮：点击后触发 request_ai
        self.btnAI = QPushButton("🤖 AI 自动识别")
        self.btnAI.setStyleSheet("QPushButton { background-color: #28a745; color: white; border: none; padding: 10px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #218838; }")
        self.btnAI.clicked.connect(self.request_ai)
        
        toolLayout.addWidget(self.btnHand)
        toolLayout.addWidget(self.btnRect)
        toolLayout.addWidget(line)
        toolLayout.addWidget(self.btnPrev)
        toolLayout.addWidget(self.btnNext)
        toolLayout.addStretch(1)
        toolLayout.addWidget(self.btnAI)

        # --- 画布 ---
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(50, 50, 50)) 
        self.view = ImageGraphicsView(self.scene)

        layout.addWidget(self.toolBar)
        layout.addWidget(self.view)
        self.switch_mode('VIEW')

    def switch_mode(self, mode):
        self.view.set_mode(mode)
        self.btnHand.setChecked(mode == 'VIEW')
        self.btnRect.setChecked(mode == 'DRAW')

    def load_image(self, image_path):
        self.current_image_path = image_path
        self.scene.clear()
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            item = QGraphicsPixmapItem(pixmap)
            item.setTransformationMode(Qt.SmoothTransformation)
            self.scene.addItem(item)
            self.view.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.first_show = True
            self.view.fit_image_to_view()

    def request_ai(self):
        """点击按钮 -> 发送信号给主窗口"""
        if self.current_image_path:
            self.btnAI.setText("⏳ 正在识别...")
            self.btnAI.setEnabled(False)
            self.request_ai_signal.emit(self.current_image_path)
        else:
            QMessageBox.warning(self, "提示", "请先加载一张图片")

    def apply_ai_results(self, results):
        """接收 AI 结果并在图上画框"""
        self.btnAI.setText("🤖 AI 自动识别")
        self.btnAI.setEnabled(True)
        
        img_w = self.view.sceneRect().width()
        img_h = self.view.sceneRect().height()

        for box in results:
            # YOLO 返回的是 xywhn (归一化中心坐标)
            # 需要转换为 左上角坐标 (x, y, w, h)
            xc, yc, w_n, h_n = box['rect']
            
            # 计算像素值
            w = w_n * img_w
            h = h_n * img_h
            x = (xc * img_w) - (w / 2)
            y = (yc * img_h) - (h / 2)
            
            # 创建绿框
            item = BoxItem(x, y, w, h, box['label'])
            self.scene.addItem(item)
        
        QMessageBox.information(self, "完成", f"AI 识别到 {len(results)} 个物体")