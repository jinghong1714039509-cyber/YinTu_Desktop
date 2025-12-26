import json
import math
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QGraphicsView, 
                               QGraphicsScene, QGraphicsRectItem, QGraphicsPolygonItem, 
                               QGraphicsPathItem, QGraphicsItem, QFrame, QMessageBox, 
                               QListWidget, QListWidgetItem, QGraphicsLineItem, QGraphicsEllipseItem,
                               QSplitter, QButtonGroup, QGraphicsTextItem, QDialog, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSize
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QPen, QColor, QBrush, QPolygonF, QPainterPath, QFont, QAction, QKeySequence

# === 引入专业 UI 库 ===
from qfluentwidgets import FluentIcon as FIF, ToolButton, ToggleButton
from qfluentwidgets import themeColor

from app.ui.components.label_dialog import LabelDialog
from app.ui.components.export_dialog import ExportDialog
from app.services.data_manager import DataManager
from app.models.schema import MediaItem

# === 0. 快捷键帮助弹窗 (保持不变) ===
class ShortcutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("快捷键列表 / Shortcuts")
        self.setFixedSize(400, 300)
        self.setStyleSheet("background: white;")
        layout = QVBoxLayout(self)
        
        table = QTableWidget(6, 2)
        table.setHorizontalHeaderLabels(["功能", "按键"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet("border: 1px solid #e0e0e0;")
        
        data = [
            ("上一张 / 下一张", "A / D"),
            ("矩形工具", "W"),
            ("多边形工具", "P"),
            ("浏览/拖拽模式", "Esc"),
            ("删除选中框", "Delete / Backspace"),
            ("保存", "Ctrl + S"),
        ]
        
        for i, (desc, key) in enumerate(data):
            table.setItem(i, 0, QTableWidgetItem(desc))
            table.setItem(i, 1, QTableWidgetItem(key))
            table.item(i, 0).setFlags(Qt.ItemIsEnabled)
            table.item(i, 1).setFlags(Qt.ItemIsEnabled)
            
        layout.addWidget(table)
        btn = QPushButton("知道了")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

# === 1. 图形项：矩形 (保持不变) ===
class BoxItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h, label="Object"):
        super().__init__(x, y, w, h)
        self.label_text = label
        self.setPen(QPen(QColor(0, 255, 0), 2))
        self.setBrush(QBrush(QColor(0, 255, 0, 40)))
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setToolTip(f"{label}")

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            painter.setPen(QPen(QColor(255, 255, 0), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 255, 0, 60)))
        else:
            painter.setPen(QPen(QColor(0, 255, 0), 2))
            painter.setBrush(QBrush(QColor(0, 255, 0, 40)))
        painter.drawRect(self.rect())

# === 2. 图形项：多边形 (保持不变) ===
class PolyItem(QGraphicsPolygonItem):
    def __init__(self, points, label="Object"):
        super().__init__(QPolygonF(points))
        self.label_text = label
        self.setPen(QPen(QColor(255, 0, 0), 2)) 
        self.setBrush(QBrush(QColor(255, 0, 0, 40))) 
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setToolTip(f"{label}")

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            painter.setPen(QPen(QColor(255, 255, 0), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 255, 0, 60)))
        else:
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(QBrush(QColor(255, 0, 0, 40)))
        painter.drawPolygon(self.polygon())

# === 3. 画布视图 (保持不变) ===
class LabelGraphicsView(QGraphicsView):
    draw_finished = Signal(str, object) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse) 
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.viewport().setCursor(Qt.CrossCursor)
        self.mode = 'VIEW'
        
        self.temp_rect = None
        self.start_point = None
        self.poly_points = []       
        self.temp_path_item = None  
        self.rubber_band = None     
        self.vertex_items = []      
        self.start_dot = None       
        self.snap_threshold = 15.0

    def set_mode(self, mode):
        self.mode = mode
        self.cleanup_temp_items() 
        if mode == 'VIEW':
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)

    def cleanup_temp_items(self):
        scene = self.scene()
        if not scene: return
        if self.temp_rect: scene.removeItem(self.temp_rect); self.temp_rect = None
        if self.temp_path_item: scene.removeItem(self.temp_path_item); self.temp_path_item = None
        if self.rubber_band: scene.removeItem(self.rubber_band); self.rubber_band = None
        if self.start_dot: scene.removeItem(self.start_dot); self.start_dot = None
        for v in self.vertex_items: scene.removeItem(v)
        self.vertex_items = []
        self.poly_points = []

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            zoomIn = 1.15
            zoomOut = 1.0 / zoomIn
            factor = zoomIn if event.angleDelta().y() > 0 else zoomOut
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self.mode == 'DRAW_RECT' and event.button() == Qt.LeftButton:
            self.start_point = pos
            self.temp_rect = QGraphicsRectItem(QRectF(pos, pos))
            self.temp_rect.setPen(QPen(Qt.green, 2, Qt.DashLine))
            self.scene().addItem(self.temp_rect)
            return
        if self.mode == 'DRAW_POLY':
            if event.button() == Qt.LeftButton:
                if len(self.poly_points) > 2 and self.is_close_to_start(pos):
                    self.finish_polygon()
                    return
                self.poly_points.append(pos)
                dot = self.scene().addEllipse(pos.x()-3, pos.y()-3, 6, 6, QPen(Qt.red), QBrush(Qt.red))
                dot.setZValue(100)
                self.vertex_items.append(dot)
                if len(self.poly_points) == 1:
                    self.start_dot = self.scene().addEllipse(pos.x()-6, pos.y()-6, 12, 12, QPen(Qt.yellow, 2), QBrush(Qt.transparent))
                    self.start_dot.setZValue(101)
                self.update_poly_visuals()
                return
            elif event.button() == Qt.RightButton:
                if self.poly_points:
                    self.poly_points.pop()
                    if self.vertex_items:
                        v = self.vertex_items.pop()
                        self.scene().removeItem(v)
                    if len(self.poly_points) == 0 and self.start_dot:
                        self.scene().removeItem(self.start_dot)
                        self.start_dot = None
                    self.update_poly_visuals()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self.mode == 'DRAW_RECT' and self.temp_rect:
            rect = QRectF(self.start_point, pos).normalized()
            self.temp_rect.setRect(rect)
        if self.mode == 'DRAW_POLY' and len(self.poly_points) > 0:
            last_pt = self.poly_points[-1]
            if not self.rubber_band:
                self.rubber_band = QGraphicsLineItem()
                self.rubber_band.setPen(QPen(Qt.red, 2, Qt.DashLine))
                self.scene().addItem(self.rubber_band)
            target_pos = pos
            if len(self.poly_points) > 2 and self.is_close_to_start(pos):
                target_pos = self.poly_points[0] 
                self.start_dot.setBrush(QBrush(Qt.yellow))
                self.viewport().setCursor(Qt.PointingHandCursor)
            else:
                if self.start_dot: self.start_dot.setBrush(QBrush(Qt.transparent))
                self.viewport().setCursor(Qt.CrossCursor)
            self.rubber_band.setLine(last_pt.x(), last_pt.y(), target_pos.x(), target_pos.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == 'DRAW_RECT' and event.button() == Qt.LeftButton and self.temp_rect:
            rect = self.temp_rect.rect()
            self.cleanup_temp_items()
            if rect.width() > 5 and rect.height() > 5:
                self.draw_finished.emit('rect', rect)
        super().mouseReleaseEvent(event)

    def update_poly_visuals(self):
        if not self.temp_path_item:
            self.temp_path_item = QGraphicsPathItem()
            self.temp_path_item.setPen(QPen(Qt.red, 2))
            self.scene().addItem(self.temp_path_item)
        path = QPainterPath()
        if self.poly_points:
            path.moveTo(self.poly_points[0])
            for p in self.poly_points[1:]:
                path.lineTo(p)
        self.temp_path_item.setPath(path)

    def is_close_to_start(self, pos):
        if not self.poly_points: return False
        start = self.poly_points[0]
        dist = math.sqrt((pos.x() - start.x())**2 + (pos.y() - start.y())**2)
        return dist < self.snap_threshold / self.transform().m11() # 考虑缩放

    def finish_polygon(self):
        final_points = list(self.poly_points)
        self.cleanup_temp_items() 
        self.draw_finished.emit('polygon', final_points)


# === 4. 主界面 (UI 全面升级) ===
class LabelInterface(QWidget):
    request_ai_signal = Signal(str)
    back_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = None
        self.all_files = [] 
        self.project_classes = [] 
        self.current_project = None 
        self.initUI()
        self.setFocusPolicy(Qt.StrongFocus)

    def set_project(self, project_obj):
        self.current_project = project_obj
        if project_obj and project_obj.classes:
            self.project_classes = [c.strip() for c in project_obj.classes.split(',') if c.strip()]
        else:
            self.project_classes = []

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === 1. 左侧专业工具条 (Medical/Enterprise Style) ===
        self.toolBar = QFrame()
        self.toolBar.setFixedWidth(56) # 稍微加宽一点点以容纳 padding
        self.toolBar.setStyleSheet("""
            QFrame { 
                background-color: #ffffff; 
                border-right: 1px solid #e5e7eb; 
            }
        """)
        
        tb_layout = QVBoxLayout(self.toolBar)
        tb_layout.setContentsMargins(8, 12, 8, 12)
        tb_layout.setSpacing(8)

        # 返回按钮 (最顶部，强调)
        self.btnBack = self.create_icon_btn(FIF.LEFT_ARROW, "返回任务列表 (Back)")
        self.btnBack.clicked.connect(self.back_clicked.emit)
        tb_layout.addWidget(self.btnBack)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e5e7eb; max-height: 1px;")
        tb_layout.addWidget(line)
        tb_layout.addSpacing(4)

        # 工具组 (互斥)
        self.modeGroup = QButtonGroup(self)
        self.modeGroup.setExclusive(True)

        # 映射图标：浏览=MOVE, 矩形=CHECKBOX(方框), 多边形=PENCIL(绘制)
        self.btnHand = self.create_tool_btn(FIF.MOVE, "浏览模式 / View (Esc)", 'VIEW')
        self.btnRect = self.create_tool_btn(FIF.CHECKBOX, "矩形标注 / Rectangle (W)", 'DRAW_RECT')
        self.btnPoly = self.create_tool_btn(FIF.PENCIL, "多边形标注 / Polygon (P)", 'DRAW_POLY')
        
        self.modeGroup.addButton(self.btnHand)
        self.modeGroup.addButton(self.btnRect)
        self.modeGroup.addButton(self.btnPoly)

        tb_layout.addWidget(self.btnHand)
        tb_layout.addWidget(self.btnRect)
        tb_layout.addWidget(self.btnPoly)
        
        tb_layout.addSpacing(15)

        # 功能组
        # AI=ROBOT, 导出=SHARE, 帮助=HELP, 保存=SAVE
        self.btnAI = self.create_icon_btn(FIF.ROBOT, "AI 自动识别")
        self.btnAI.clicked.connect(self.request_ai)
        
        self.btnExport = self.create_icon_btn(FIF.SHARE, "导出数据集")
        self.btnExport.clicked.connect(self.show_export_dialog)

        self.btnHelp = self.create_icon_btn(FIF.HELP, "快捷键帮助")
        self.btnHelp.clicked.connect(self.show_shortcuts)

        self.btnSaveSmall = self.create_icon_btn(FIF.SAVE, "保存 (Ctrl+S)")
        self.btnSaveSmall.clicked.connect(lambda: self.save_current_work(silent=False))

        tb_layout.addWidget(self.btnAI)
        tb_layout.addWidget(self.btnExport) 
        tb_layout.addWidget(self.btnHelp)
        tb_layout.addWidget(self.btnSaveSmall)
        tb_layout.addStretch()

        # === 2. 中间画布 (深色沉浸) ===
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(40, 40, 40)) 
        self.view = LabelGraphicsView(self.scene)
        self.view.draw_finished.connect(self.on_draw_finished)

        # === 3. 右侧面板 (白色清爽) ===
        rightPanel = QSplitter(Qt.Vertical)
        rightPanel.setFixedWidth(240)
        rightPanel.setStyleSheet("""
            QSplitter::handle { background-color: #e5e7eb; height: 1px; }
            QWidget { background-color: #ffffff; }
            QListWidget { border: none; background-color: white; }
            QLabel { 
                font-weight: 600; color: #374151; padding: 8px; 
                background: #f9fafb; border-bottom: 1px solid #e5e7eb;
            }
        """)

        # 标签列表
        labelContainer = QWidget()
        labelLayout = QVBoxLayout(labelContainer)
        labelLayout.setContentsMargins(0, 0, 0, 0)
        labelLayout.addWidget(QLabel("标签列表 / Labels"))
        self.labelList = QListWidget()
        self.labelList.setAlternatingRowColors(True)
        self.labelList.itemClicked.connect(self.highlight_shape)
        labelLayout.addWidget(self.labelList)
        
        # 文件列表
        fileContainer = QWidget()
        fileLayout = QVBoxLayout(fileContainer)
        fileLayout.setContentsMargins(0, 0, 0, 0)
        fileLayout.addWidget(QLabel("文件列表 / Files"))
        self.fileList = QListWidget()
        self.fileList.setAlternatingRowColors(True)
        self.fileList.itemClicked.connect(self.on_file_clicked)
        fileLayout.addWidget(self.fileList)

        # 底部保存按钮区域
        saveContainer = QFrame()
        saveContainer.setFixedHeight(50)
        saveContainer.setStyleSheet("background-color: #f9fafb; border-top: 1px solid #e5e7eb;")
        saveLayout = QHBoxLayout(saveContainer)
        saveLayout.setContentsMargins(12, 8, 12, 8)

        self.btnSaveBig = QPushButton("💾 保存当前结果")
        self.btnSaveBig.setCursor(Qt.PointingHandCursor)
        self.btnSaveBig.setStyleSheet("""
            QPushButton { 
                background-color: #2563EB; color: white; border-radius: 6px; 
                font-weight: 600; font-size: 13px; border: none;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
        """)
        self.btnSaveBig.clicked.connect(lambda: self.save_current_work(silent=False))
        saveLayout.addWidget(self.btnSaveBig)
        fileLayout.addWidget(saveContainer)

        rightPanel.addWidget(labelContainer)
        rightPanel.addWidget(fileContainer)
        rightPanel.setSizes([300, 400]) 

        layout.addWidget(self.toolBar)
        layout.addWidget(self.view, 1) 
        layout.addWidget(rightPanel)
        
        self.switch_mode('VIEW')

    # === 工具方法：创建样式统一的图标按钮 ===
    def create_icon_btn(self, fluent_icon, tooltip):
        """创建普通功能按钮 (Normal / Hover / Pressed)"""
        btn = QPushButton()
        btn.setIcon(fluent_icon.icon())
        btn.setIconSize(QSize(20, 20))
        btn.setToolTip(tooltip)
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.PointingHandCursor)
        # 医疗/企业级风格 CSS
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #f3f4f6; /* 浅灰 Hover */
            }
            QPushButton:pressed {
                background-color: #e5e7eb; /* 深灰 Press */
            }
        """)
        return btn

    def create_tool_btn(self, fluent_icon, tooltip, mode):
        """创建工具模式按钮 (Checkable: Default / Hover / Checked)"""
        btn = QPushButton()
        btn.setIcon(fluent_icon.icon())
        btn.setIconSize(QSize(20, 20))
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.PointingHandCursor)
        
        # 核心：使用 QSS 实现选中态的蓝色高亮 (#DBEAFE) 和 图标色变化逻辑
        # 注意：QIcon 本身颜色很难通过 CSS 改变，但背景色变化已经足够清晰
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
            }
            QPushButton:checked {
                background-color: #dbeafe; /* 浅蓝选中底色 */
                border: 1px solid #bfdbfe; /* 选中描边 */
            }
        """)
        
        if mode:
            btn.clicked.connect(lambda: self.switch_mode(mode))
        return btn

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()
        self.activateWindow()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_A: self.prev_image()
        elif key == Qt.Key_D: self.next_image()
        elif key == Qt.Key_W: self.switch_mode('DRAW_RECT')
        elif key == Qt.Key_P: self.switch_mode('DRAW_POLY')
        elif key == Qt.Key_Escape: self.switch_mode('VIEW')
        elif key == Qt.Key_S and (event.modifiers() & Qt.ControlModifier): self.save_current_work(silent=False)
        elif key == Qt.Key_Delete or key == Qt.Key_Backspace: self.delete_selected_shape()
        else: super().keyPressEvent(event)

    def switch_mode(self, mode):
        self.view.set_mode(mode)
        self.btnHand.setChecked(mode == 'VIEW')
        self.btnRect.setChecked(mode == 'DRAW_RECT')
        self.btnPoly.setChecked(mode == 'DRAW_POLY')
        self.view.setFocus()

    def show_export_dialog(self):
        self.save_current_work(silent=True)
        if not self.current_project: return
        dialog = ExportDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                count = DataManager.export_dataset(self.current_project, data['path'], data['format'])
                # 提示框样式修复
                msg = QMessageBox(self)
                msg.setWindowTitle("导出成功")
                msg.setText(f"成功导出 {count} 张！")
                msg.setStyleSheet("background-color: white; color: #333;")
                msg.exec()
            except Exception as e: 
                QMessageBox.critical(self, "失败", str(e))

    def show_shortcuts(self):
        d = ShortcutDialog(self)
        d.exec()

    def load_file_list(self, files, current_path=None):
        self.all_files = files
        self.fileList.clear()
        current_row = 0
        for i, f in enumerate(files):
            item = QListWidgetItem(os.path.basename(f))
            item.setData(Qt.UserRole, f); self.fileList.addItem(item)
            if f == current_path: current_row = i
        self.fileList.setCurrentRow(current_row)

    def on_file_clicked(self, item):
        path = item.data(Qt.UserRole)
        self.save_current_work(silent=True) 
        self.load_image(path)

    def prev_image(self):
        row = self.fileList.currentRow()
        if row > 0: self.fileList.setCurrentRow(row - 1); self.on_file_clicked(self.fileList.currentItem())

    def next_image(self):
        row = self.fileList.currentRow()
        if row < self.fileList.count() - 1: self.fileList.setCurrentRow(row + 1); self.on_file_clicked(self.fileList.currentItem())

    def load_image(self, image_path):
        self.current_image_path = image_path
        self.scene.clear(); self.labelList.clear()
        if not os.path.exists(image_path):
            error_text = self.scene.addText(f"无法找到文件:\n{image_path}")
            error_text.setDefaultTextColor(Qt.red); error_text.setFont(QFont("Arial", 16))
            return
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            bg = self.scene.addPixmap(pixmap); bg.setZValue(-1)
            self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.fitInView(bg, Qt.KeepAspectRatio)
            self.view.viewport().update()
            try:
                if hasattr(self.parent(), 'current_project') and self.parent().current_project:
                    classes_str = self.parent().current_project.classes
                    self.project_classes = classes_str.split(',') if classes_str else []
            except: pass
            self.load_annotations_from_db()
        else: self.scene.addText("图片格式不支持或已损坏").setDefaultTextColor(Qt.red)

    def on_draw_finished(self, shape_type, data):
        dialog = LabelDialog(self.project_classes, self)
        if dialog.exec():
            label = dialog.get_label()
            if not label: label = "Object"
            if label not in self.project_classes: self.project_classes.append(label)
            if shape_type == 'rect': item = BoxItem(data.x(), data.y(), data.width(), data.height(), label); self.scene.addItem(item)
            elif shape_type == 'polygon': item = PolyItem(data, label); self.scene.addItem(item)
            self.refresh_label_list(); self.switch_mode('VIEW')

    def refresh_label_list(self):
        self.labelList.clear()
        for item in self.scene.items():
            if isinstance(item, (BoxItem, PolyItem)):
                list_item = QListWidgetItem(item.label_text)
                list_item.setData(Qt.UserRole, item); self.labelList.addItem(list_item)

    def highlight_shape(self, list_item):
        shape = list_item.data(Qt.UserRole); self.scene.clearSelection(); shape.setSelected(True)

    def delete_selected_shape(self):
        for item in self.scene.selectedItems(): self.scene.removeItem(item)
        self.refresh_label_list()

    def save_current_work(self, silent=False):
        if not self.current_image_path: return
        box_data = []
        img_w = self.view.sceneRect().width(); img_h = self.view.sceneRect().height()
        if img_w <= 0 or img_h <= 0: return
        for item in self.scene.items():
            ann = {}
            if isinstance(item, BoxItem):
                ann['shape_type'] = 'rect'; ann['label'] = item.label_text
                r = item.rect(); pos = item.scenePos()
                ann['rect'] = [(pos.x()+r.x()+r.width()/2)/img_w, (pos.y()+r.y()+r.height()/2)/img_h, r.width()/img_w, r.height()/img_h]
            elif isinstance(item, PolyItem):
                ann['shape_type'] = 'polygon'; ann['label'] = item.label_text
                poly = item.polygon(); pos = item.scenePos()
                points_list = []; xs = []; ys = []
                for p in poly:
                    px = p.x() + pos.x(); py = p.y() + pos.y()
                    points_list.append([px / img_w, py / img_h]); xs.append(px); ys.append(py)
                ann['points'] = json.dumps(points_list)
                if xs: ann['rect'] = [(min(xs)+(max(xs)-min(xs))/2)/img_w, (min(ys)+(max(ys)-min(ys))/2)/img_h, (max(xs)-min(xs))/img_w, (max(ys)-min(ys))/img_h]
                else: continue
            if ann: box_data.append(ann)
        if DataManager.save_annotations(self.current_image_path, box_data):
            if not silent:
                self.btnSaveBig.setText("✅ 已保存")
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, lambda: self.btnSaveBig.setText("💾 保存当前结果"))
        else:
            if not silent: QMessageBox.warning(self, "错误", "保存失败")

    def load_annotations_from_db(self):
        media_item = MediaItem.get_or_none(MediaItem.file_path == self.current_image_path)
        if not media_item: return
        img_w = self.view.sceneRect().width(); img_h = self.view.sceneRect().height()
        for ann in media_item.annotations:
            if ann.shape_type == 'polygon' and ann.points:
                try:
                    pts = json.loads(ann.points); qpoints = [QPointF(p[0]*img_w, p[1]*img_h) for p in pts]
                    item = PolyItem(qpoints, ann.label); self.scene.addItem(item)
                except: pass 
            else:
                w = ann.w * img_w; h = ann.h * img_h
                x = (ann.x * img_w) - (w/2); y = (ann.y * img_h) - (h/2)
                item = BoxItem(x, y, w, h, ann.label); self.scene.addItem(item)
        self.refresh_label_list()

    def request_ai(self):
        if self.current_image_path: self.btnAI.setEnabled(False); self.request_ai_signal.emit(self.current_image_path)

    def apply_ai_results(self, results):
        self.btnAI.setEnabled(True)
        img_w = self.view.sceneRect().width(); img_h = self.view.sceneRect().height()
        for box in results:
            w = box['rect'][2] * img_w; h = box['rect'][3] * img_h
            x = (box['rect'][0] * img_w) - (w / 2); y = (box['rect'][1] * img_h) - (h / 2)
            item = BoxItem(x, y, w, h, box['label']); self.scene.addItem(item)
        self.refresh_label_list()
        QMessageBox.information(self, "AI 完成", f"识别到 {len(results)} 个物体")