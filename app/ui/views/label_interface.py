import json
import os
import sys
import math

# === 修复核心 1: 补全 QGraphicsLineItem，彻底解决多边形画线崩溃问题 ===
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QPushButton, QLabel, QGraphicsView,
                               QGraphicsScene, QGraphicsRectItem, QGraphicsPolygonItem,
                               QGraphicsPathItem, QGraphicsItem, QFrame, QMessageBox,
                               QListWidget, QListWidgetItem, QGraphicsLineItem, QGraphicsEllipseItem,
                               QSplitter, QButtonGroup, QGraphicsTextItem, QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
                               QStyle, QScrollArea, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSize
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QPen, QColor, QBrush, QPolygonF, QPainterPath, QFont, QAction, QKeySequence, QIcon
from PySide6.QtSvg import QSvgRenderer

from app.ui.components.label_dialog import LabelDialog
from app.ui.components.export_dialog import ExportDialog
from app.services.data_manager import DataManager
from app.models.schema import MediaItem


def get_icon_path(icon_name: str):
    """Return an absolute icon path for both dev-run and packaged (PyInstaller) runs."""
    candidates = []

    # PyInstaller one-file bundle
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "app", "ui", "assets", "icons", icon_name))

    # Normal source layout: app/ui/views -> app/ui/assets/icons
    ui_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(ui_dir, "assets", "icons", icon_name))

    # Fallback: run from project root (cwd)
    candidates.append(os.path.abspath(os.path.join("app", "ui", "assets", "icons", icon_name)))

    for p in candidates:
        if os.path.exists(p):
            return p

    print(f"❌ 警告: 找不到图标文件 {icon_name}，尝试路径: {candidates}")
    return None


def render_tinted_pixmap(icon_path: str, size: int, color: QColor) -> QPixmap:
    """Render SVG/bitmap to a pixmap and tint it with a target color (保持透明背景)."""
    icon_path_l = (icon_path or "").lower()

    if icon_path_l.endswith(".svg"):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        renderer = QSvgRenderer(icon_path)
        painter = QPainter(pm)
        renderer.render(painter)
        painter.end()
    else:
        pm = QPixmap(icon_path)
        if not pm.isNull():
            pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    if pm.isNull():
        return QPixmap()

    tinted = QPixmap(pm.size())
    tinted.fill(color)
    painter = QPainter(tinted)
    painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    painter.drawPixmap(0, 0, pm)
    painter.end()
    return tinted


class ShortcutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("快捷键列表")
        self.setFixedSize(400, 300)
        self.setStyleSheet("""
            QDialog { background-color: #FFFFFF; color: #333; }
            QTableWidget { background-color: #FFFFFF; color: #333; border: 1px solid #E0E0E0; gridline-color: #EEE; }
            QHeaderView::section { background-color: #F5F5F5; color: #333; border: none; height: 30px; }
            QPushButton { background-color: #3B82F6; color: white; border-radius: 4px; padding: 6px; border: none; }
            QPushButton:hover { background-color: #2563EB; }
        """)
        layout = QVBoxLayout(self)
        table = QTableWidget(6, 2)
        table.setHorizontalHeaderLabels(["功能", "按键"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        data = [("上一张 / 下一张", "A / D"), ("矩形工具", "W"), ("多边形工具", "P"),
                ("选择/浏览", "Esc"), ("删除选中框", "Delete"), ("保存", "Ctrl + S")]
        for i, (desc, key) in enumerate(data):
            table.setItem(i, 0, QTableWidgetItem(desc))
            table.setItem(i, 1, QTableWidgetItem(key))
            table.item(i, 0).setFlags(Qt.ItemIsEnabled)
            table.item(i, 1).setFlags(Qt.ItemIsEnabled)
        layout.addWidget(table)
        btn = QPushButton("知道了")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class BoxItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h, label="Object"):
        super().__init__(x, y, w, h)
        self.label_text = label
        self.setPen(QPen(QColor("#00FF00"), 2))
        self.setBrush(QBrush(QColor(0, 255, 0, 40)))
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setToolTip(f"{label}")

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            painter.setPen(QPen(QColor("#FFFF00"), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 255, 0, 60)))
        else:
            painter.setPen(QPen(QColor("#00FF00"), 2))
            painter.setBrush(QBrush(QColor(0, 255, 0, 40)))
        painter.drawRect(self.rect())


class PolyItem(QGraphicsPolygonItem):
    def __init__(self, points, label="Object"):
        super().__init__(QPolygonF(points))
        self.label_text = label
        self.setPen(QPen(QColor("#FF4D4D"), 2))
        self.setBrush(QBrush(QColor(255, 77, 77, 40)))
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setToolTip(f"{label}")

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            painter.setPen(QPen(QColor("#FFFF00"), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 255, 0, 60)))
        else:
            painter.setPen(QPen(QColor("#FF4D4D"), 2))
            painter.setBrush(QBrush(QColor(255, 77, 77, 40)))
        painter.drawPolygon(self.polygon())


class LabelGraphicsView(QGraphicsView):
    draw_finished = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.setBackgroundBrush(QColor("#F5F5F5"))
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
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)

    def cleanup_temp_items(self):
        scene = self.scene()
        if not scene:
            return
        if self.temp_rect:
            scene.removeItem(self.temp_rect)
            self.temp_rect = None
        if self.temp_path_item:
            scene.removeItem(self.temp_path_item)
            self.temp_path_item = None
        if self.rubber_band:
            scene.removeItem(self.rubber_band)
            self.rubber_band = None
        if self.start_dot:
            scene.removeItem(self.start_dot)
            self.start_dot = None
        for v in self.vertex_items:
            scene.removeItem(v)
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
                dot = self.scene().addEllipse(pos.x() - 3, pos.y() - 3, 6, 6, QPen(Qt.red), QBrush(Qt.red))
                dot.setZValue(100)
                self.vertex_items.append(dot)
                if len(self.poly_points) == 1:
                    self.start_dot = self.scene().addEllipse(pos.x() - 6, pos.y() - 6, 12, 12, QPen(Qt.yellow, 2), QBrush(Qt.transparent))
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
                if self.start_dot:
                    self.start_dot.setBrush(QBrush(Qt.yellow))
                self.viewport().setCursor(Qt.PointingHandCursor)
            else:
                if self.start_dot:
                    self.start_dot.setBrush(QBrush(Qt.transparent))
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
        if not self.poly_points:
            return False
        start = self.poly_points[0]
        dist = math.sqrt((pos.x() - start.x()) ** 2 + (pos.y() - start.y()) ** 2)
        return dist < self.snap_threshold / self.transform().m11()

    def finish_polygon(self):
        final_points = list(self.poly_points)
        self.cleanup_temp_items()
        self.draw_finished.emit('polygon', final_points)


class LabelInterface(QWidget):
    request_ai_signal = Signal(str)
    back_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # 统一背景为纯白（避免父窗口/圆角透明导致透出桌面壁纸）
        self.setObjectName("LabelInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#LabelInterface { background-color: #FFFFFF; }")

        self.current_image_path = None
        self.all_files = []
        self.project_classes = []
        self.current_project = None
        self.initUI()
        self.setFocusPolicy(Qt.StrongFocus)

    def set_project(self, project_obj):
        self.current_project = project_obj
        if project_obj and getattr(project_obj, "classes", None):
            self.project_classes = [c.strip() for c in project_obj.classes.split(',') if c.strip()]
        else:
            self.project_classes = []
        self.refresh_task_classes_ui()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. 工具栏（纯白、强制绘制背景）
        self.toolBar = QFrame()
        self.toolBar.setFixedWidth(56)
        self.toolBar.setAttribute(Qt.WA_StyledBackground, True)
        self.toolBar.setStyleSheet("QFrame { background-color: #FFFFFF; border-right: 1px solid #DDD; }")

        tb_layout = QVBoxLayout(self.toolBar)
        tb_layout.setContentsMargins(8, 12, 8, 12)
        tb_layout.setSpacing(10)

        self.btnBack = self.create_tool_btn("back.svg", "返回 (Back)", None)
        self.btnBack.clicked.connect(self.back_clicked.emit)
        tb_layout.addWidget(self.btnBack)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #EEE; max-height: 1px;")
        tb_layout.addWidget(line)
        tb_layout.addSpacing(4)

        self.modeGroup = QButtonGroup(self)
        self.modeGroup.setExclusive(True)

        self.btnCursor = self.create_tool_btn("cursor.svg", "选择/浏览 (V)", 'VIEW')
        self.btnRect = self.create_tool_btn("rect.svg", "矩形 (R)", 'DRAW_RECT')
        self.btnPoly = self.create_tool_btn("poly.svg", "多边形 (P)", 'DRAW_POLY')

        self.modeGroup.addButton(self.btnCursor)
        self.modeGroup.addButton(self.btnRect)
        self.modeGroup.addButton(self.btnPoly)

        tb_layout.addWidget(self.btnCursor)
        tb_layout.addWidget(self.btnRect)
        tb_layout.addWidget(self.btnPoly)

        tb_layout.addSpacing(15)

        self.btnAI = self.create_tool_btn("ai.svg", "AI 自动识别", None)
        self.btnAI.clicked.connect(self.request_ai)

        self.btnExport = self.create_tool_btn("export.svg", "导出数据集", None)
        self.btnExport.clicked.connect(self.show_export_dialog)

        self.btnHelp = self.create_tool_btn("help.svg", "快捷键帮助", None)
        self.btnHelp.clicked.connect(self.show_shortcuts)

        self.btnSaveSmall = self.create_tool_btn("save.svg", "保存 (Ctrl+S)", None)
        self.btnSaveSmall.clicked.connect(lambda: self.save_current_work(silent=False))

        tb_layout.addWidget(self.btnAI)
        tb_layout.addWidget(self.btnExport)
        tb_layout.addWidget(self.btnHelp)
        tb_layout.addWidget(self.btnSaveSmall)
        tb_layout.addStretch()

        # 2. 画布
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor("#F5F5F5"))
        self.view = LabelGraphicsView()
        self.view.setScene(self.scene)
        self.view.draw_finished.connect(self.on_draw_finished)

        # 3. 右侧面板（整体纯白）
        rightPanel = QSplitter(Qt.Vertical)
        rightPanel.setFixedWidth(240)
        rightPanel.setStyleSheet("""
            QSplitter::handle { background-color: #DDD; height: 1px; }
            QWidget { background-color: #FFFFFF; }
            QListWidget { border: none; background-color: #FFFFFF; color: #333; }
            QLabel { font-weight: 600; color: #666; padding: 8px; background: #FAFAFA; border-bottom: 1px solid #EEE; }
        """)

        labelContainer = QWidget()
        labelLayout = QVBoxLayout(labelContainer)
        labelLayout.setContentsMargins(0, 0, 0, 0)
        labelLayout.addWidget(QLabel("当前标注 / Annotations"))
        self.labelList = QListWidget()
        self.labelList.setAlternatingRowColors(True)
        self.labelList.setStyleSheet(
            "QListWidget::item:selected { background-color: #E6F0FF; color: black; } "
            "QListWidget::item:hover { background-color: #F5F5F5; }"
        )
        self.labelList.itemClicked.connect(self.highlight_shape)
        labelLayout.addWidget(self.labelList)

        taskClassContainer = QWidget()
        taskClassLayout = QVBoxLayout(taskClassContainer)
        taskClassLayout.setContentsMargins(0, 0, 0, 0)
        taskClassLayout.addWidget(QLabel("任务历史标签 / Task Classes"))
        self.classList = QListWidget()
        self.classList.setStyleSheet("color: #555; font-style: italic;")
        taskClassLayout.addWidget(self.classList)

        fileContainer = QWidget()
        fileLayout = QVBoxLayout(fileContainer)
        fileLayout.setContentsMargins(0, 0, 0, 0)
        fileLayout.addWidget(QLabel("文件列表 / Files"))
        self.fileList = QListWidget()
        self.fileList.setAlternatingRowColors(True)
        self.fileList.setStyleSheet(
            "QListWidget::item:selected { background-color: #E6F0FF; color: black; } "
            "QListWidget::item:hover { background-color: #F5F5F5; }"
        )
        self.fileList.itemClicked.connect(self.on_file_clicked)
        fileLayout.addWidget(self.fileList)

        saveContainer = QFrame()
        saveContainer.setFixedHeight(50)
        saveContainer.setStyleSheet("background-color: #FAFAFA; border-top: 1px solid #EEE;")
        saveLayout = QHBoxLayout(saveContainer)
        saveLayout.setContentsMargins(12, 8, 12, 8)

        self.btnSaveBig = QPushButton("💾 保存当前结果")
        self.btnSaveBig.setCursor(Qt.PointingHandCursor)
        self.btnSaveBig.setStyleSheet(
            "QPushButton { background-color: #3B82F6; color: white; border-radius: 6px; font-weight: 600; font-size: 13px; border: none; } "
            "QPushButton:hover { background-color: #2563EB; } "
            "QPushButton:pressed { background-color: #1D4ED8; }"
        )
        self.btnSaveBig.clicked.connect(lambda: self.save_current_work(silent=False))
        saveLayout.addWidget(self.btnSaveBig)
        fileLayout.addWidget(saveContainer)

        rightPanel.addWidget(labelContainer)
        rightPanel.addWidget(taskClassContainer)
        rightPanel.addWidget(fileContainer)
        rightPanel.setSizes([200, 150, 400])

        layout.addWidget(self.toolBar)
        layout.addWidget(self.view, 1)
        layout.addWidget(rightPanel)

        self.switch_mode('VIEW')

    def create_tool_btn(self, icon_file, tooltip, mode):
        btn = QPushButton()
        btn.setToolTip(tooltip)
        btn.setCheckable(mode is not None)
        btn.setFixedSize(36, 36)
        btn.setCursor(Qt.PointingHandCursor)

        btn.icon_path = get_icon_path(icon_file)
        self.update_btn_icon(btn)

        # 白色按钮底 + 透明图标叠加（图标本身不做底板）
        btn.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; border-radius: 8px; border: 1px solid #E5E7EB; }"
            "QPushButton:hover { background-color: #F3F4F6; border: 1px solid #D1D5DB; }"
            "QPushButton:checked { background-color: #E6F0FF; border: 1px solid #3B82F6; }"
        )

        if mode:
            btn.clicked.connect(lambda: self.switch_mode(mode))
            btn.toggled.connect(lambda: self.update_btn_icon(btn))

        return btn

    def update_btn_icon(self, btn):
        if not hasattr(btn, "icon_path") or not btn.icon_path:
            btn.setText("?")
            return

        target_color = QColor("#3B82F6") if btn.isChecked() else QColor("#555555")
        pixmap = render_tinted_pixmap(btn.icon_path, 20, target_color)

        if pixmap.isNull():
            btn.setText("?")
            return

        btn.setIcon(QIcon(pixmap))
        btn.setIconSize(QSize(20, 20))
        btn.setText("")

    def refresh_task_classes_ui(self):
        self.classList.clear()
        for cls_name in self.project_classes:
            self.classList.addItem(QListWidgetItem(cls_name))

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
        self.btnCursor.setChecked(mode == 'VIEW')
        self.btnRect.setChecked(mode == 'DRAW_RECT')
        self.btnPoly.setChecked(mode == 'DRAW_POLY')
        self.update_btn_icon(self.btnCursor)
        self.update_btn_icon(self.btnRect)
        self.update_btn_icon(self.btnPoly)
        self.view.setFocus()

    def show_export_dialog(self):
        self.save_current_work(silent=True)
        if not self.current_project:
            return
        dialog = ExportDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                count = DataManager.export_dataset(self.current_project, data['path'], data['format'])
                msg = QMessageBox(self)
                msg.setWindowTitle("导出成功")
                msg.setText(f"成功导出 {count} 张！")
                msg.setStyleSheet("QMessageBox { background-color: #FFF; color: #333; } QLabel { color: #333; }")
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
            item.setData(Qt.UserRole, f)
            self.fileList.addItem(item)
            if f == current_path:
                current_row = i
        self.fileList.setCurrentRow(current_row)

    def on_file_clicked(self, item):
        path = item.data(Qt.UserRole)
        self.save_current_work(silent=True)
        self.load_image(path)

    def prev_image(self):
        row = self.fileList.currentRow()
        if row > 0:
            self.fileList.setCurrentRow(row - 1)
            self.on_file_clicked(self.fileList.currentItem())

    def next_image(self):
        row = self.fileList.currentRow()
        if row < self.fileList.count() - 1:
            self.fileList.setCurrentRow(row + 1)
            self.on_file_clicked(self.fileList.currentItem())

    def load_image(self, image_path):
        self.current_image_path = image_path
        self.scene.clear()
        self.labelList.clear()

        if not os.path.exists(image_path):
            error_text = self.scene.addText(f"无法找到文件:\n{image_path}")
            error_text.setDefaultTextColor(Qt.red)
            error_text.setFont(QFont("Arial", 16))
            return

        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            bg = self.scene.addPixmap(pixmap)
            bg.setZValue(-1)
            self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.fitInView(bg, Qt.KeepAspectRatio)
            self.view.viewport().update()
            self.load_annotations_from_db()
        else:
            self.scene.addText("图片格式不支持或已损坏").setDefaultTextColor(Qt.red)

    def on_draw_finished(self, shape_type, data):
        dialog = LabelDialog(self.project_classes, self)
        dialog.setStyleSheet(
            "QDialog { background-color: #FFF; color: #000; } "
            "QListWidget { background-color: #FFF; color: #000; border: 1px solid #CCC; }"
        )

        if dialog.exec():
            label = dialog.get_label() or "Object"

            if label not in self.project_classes:
                self.project_classes.append(label)
                if self.current_project:
                    self.current_project.classes = ",".join(self.project_classes)
                    self.current_project.save()
                    self.refresh_task_classes_ui()

            if shape_type == 'rect':
                item = BoxItem(data.x(), data.y(), data.width(), data.height(), label)
                self.scene.addItem(item)
            elif shape_type == 'polygon':
                item = PolyItem(data, label)
                self.scene.addItem(item)

            self.refresh_label_list()
            self.switch_mode('VIEW')

    def refresh_label_list(self):
        self.labelList.clear()
        for item in self.scene.items():
            if isinstance(item, (BoxItem, PolyItem)):
                list_item = QListWidgetItem(item.label_text)
                list_item.setData(Qt.UserRole, item)
                self.labelList.addItem(list_item)

    def highlight_shape(self, list_item):
        shape = list_item.data(Qt.UserRole)
        self.scene.clearSelection()
        shape.setSelected(True)

    def delete_selected_shape(self):
        for item in self.scene.selectedItems():
            self.scene.removeItem(item)
        self.refresh_label_list()

    def save_current_work(self, silent=False):
        if not self.current_image_path:
            return
        box_data = []
        img_w = self.view.sceneRect().width()
        img_h = self.view.sceneRect().height()
        if img_w <= 0 or img_h <= 0:
            return

        for item in self.scene.items():
            ann = {}
            if isinstance(item, BoxItem):
                ann['shape_type'] = 'rect'
                ann['label'] = item.label_text
                r = item.rect()
                pos = item.scenePos()
                ann['rect'] = [
                    (pos.x() + r.x() + r.width() / 2) / img_w,
                    (pos.y() + r.y() + r.height() / 2) / img_h,
                    r.width() / img_w,
                    r.height() / img_h
                ]
            elif isinstance(item, PolyItem):
                ann['shape_type'] = 'polygon'
                ann['label'] = item.label_text
                poly = item.polygon()
                pos = item.scenePos()
                points_list = []
                xs = []
                ys = []
                for p in poly:
                    px = p.x() + pos.x()
                    py = p.y() + pos.y()
                    points_list.append([px / img_w, py / img_h])
                    xs.append(px)
                    ys.append(py)
                ann['points'] = json.dumps(points_list)
                if xs:
                    ann['rect'] = [
                        (min(xs) + (max(xs) - min(xs)) / 2) / img_w,
                        (min(ys) + (max(ys) - min(ys)) / 2) / img_h,
                        (max(xs) - min(xs)) / img_w,
                        (max(ys) - min(ys)) / img_h
                    ]
                else:
                    continue

            if ann:
                box_data.append(ann)

        if DataManager.save_annotations(self.current_image_path, box_data):
            if not silent:
                self.btnSaveBig.setText("✅ 已保存")
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, lambda: self.btnSaveBig.setText("💾 保存当前结果"))
        else:
            if not silent:
                QMessageBox.warning(self, "错误", "保存失败")

    def load_annotations_from_db(self):
        media_item = MediaItem.get_or_none(MediaItem.file_path == self.current_image_path)
        if not media_item:
            return

        img_w = self.view.sceneRect().width()
        img_h = self.view.sceneRect().height()

        for ann in media_item.annotations:
            if ann.shape_type == 'polygon' and ann.points:
                try:
                    pts = json.loads(ann.points)
                    qpoints = [QPointF(p[0] * img_w, p[1] * img_h) for p in pts]
                    item = PolyItem(qpoints, ann.label)
                    self.scene.addItem(item)
                except Exception:
                    pass
            else:
                w = ann.w * img_w
                h = ann.h * img_h
                x = (ann.x * img_w) - (w / 2)
                y = (ann.y * img_h) - (h / 2)
                item = BoxItem(x, y, w, h, ann.label)
                self.scene.addItem(item)

        self.refresh_label_list()

    def request_ai(self):
        if self.current_image_path:
            self.btnAI.setEnabled(False)
            self.request_ai_signal.emit(self.current_image_path)

    def apply_ai_results(self, results):
        self.btnAI.setEnabled(True)
        img_w = self.view.sceneRect().width()
        img_h = self.view.sceneRect().height()
        for box in results:
            w = box['rect'][2] * img_w
            h = box['rect'][3] * img_h
            x = (box['rect'][0] * img_w) - (w / 2)
            y = (box['rect'][1] * img_h) - (h / 2)
            item = BoxItem(x, y, w, h, box['label'])
            self.scene.addItem(item)
        self.refresh_label_list()
        msg = QMessageBox(self)
        msg.setWindowTitle("AI 完成")
        msg.setText(f"识别到 {len(results)} 个物体")
        msg.setStyleSheet("QMessageBox { background-color: #FFF; color: #333; } QLabel { color: #333; }")
        msg.exec()
