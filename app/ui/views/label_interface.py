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
from PySide6.QtGui import QCursor
from PySide6.QtSvg import QSvgRenderer

from app.ui.components.label_dialog import LabelDialog
from app.ui.components.export_dialog import ExportDialog
from app.services.data_manager import DataManager
from app.models.schema import MediaItem
from app.ui.components.sidebar import render_icon_with_bg


def get_icon_path(icon_name: str):
    """Return an absolute icon path for both dev-run and packaged (PyInstaller) runs.

    Icons may exist in:
      - app/ui/assets/icons (source)
      - app/assets/icons    (some deployments)
    This helper tries both, plus PyInstaller bundle paths and cwd fallbacks.
    """
    candidates = []

    # PyInstaller one-file bundle
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "app", "ui", "assets", "icons", icon_name))
        candidates.append(os.path.join(sys._MEIPASS, "app", "assets", "icons", icon_name))

    # Normal source layout: app/ui/views -> app/ui/assets/icons
    ui_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app/ui
    app_dir = os.path.dirname(ui_dir)  # .../app

    candidates.append(os.path.join(ui_dir, "assets", "icons", icon_name))
    candidates.append(os.path.join(app_dir, "assets", "icons", icon_name))

    # Fallback: run from project root (cwd)
    candidates.append(os.path.abspath(os.path.join("app", "ui", "assets", "icons", icon_name)))
    candidates.append(os.path.abspath(os.path.join("app", "assets", "icons", icon_name)))
    candidates.append(os.path.abspath(os.path.join("assets", "icons", icon_name)))

    for p in candidates:
        if p and os.path.exists(p):
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

def render_svg_cursor(icon_name: str, size: int = 24, hotspot_x: int = 1, hotspot_y: int = 1) -> QCursor:
    """Render an SVG icon into a QCursor (用于自定义鼠标悬停光标)."""
    icon_path = get_icon_path(icon_name)

    # 如果找不到 svg，退回系统默认箭头，避免程序崩
    if not icon_path or (not icon_path.lower().endswith(".svg")):
        return QCursor(Qt.ArrowCursor)

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    renderer = QSvgRenderer(icon_path)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()

    return QCursor(pm, hotspot_x, hotspot_y)


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
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)

        data = [
            ("选择/浏览", "V"),
            ("矩形标注", "R"),
            ("多边形标注", "P"),
            ("上一张", "A"),
            ("下一张", "D"),
            ("撤销/回退", "Ctrl+Z"),
        ]
        for i, (desc, key) in enumerate(data):
            table.setItem(i, 0, QTableWidgetItem(desc))
            table.setItem(i, 1, QTableWidgetItem(key))

        layout.addWidget(table)

        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class ImageViewer(QGraphicsView):
    pointClicked = Signal(QPointF)
    draw_finished = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        # 模式/状态
        self.mode = "VIEW"  # VIEW / DRAW_RECT / DRAW_POLY
        self.rect_start = None
        self.temp_rect_item = None

        self.poly_points = []
        self.temp_path_item = None
        self.snap_threshold = 12

    def set_mode(self, mode: str):
        self.mode = mode
        self.rect_start = None
        if self.temp_rect_item:
            self.scene().removeItem(self.temp_rect_item)
            self.temp_rect_item = None
        if self.temp_path_item:
            self.scene().removeItem(self.temp_path_item)
            self.temp_path_item = None
        self.poly_points.clear()

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        pos = self.mapToScene(event.pos())
        self.pointClicked.emit(pos)

        if self.mode == "DRAW_RECT":
            if self.rect_start is None:
                self.rect_start = pos
                self.temp_rect_item = QGraphicsRectItem(QRectF(pos, pos))
                self.temp_rect_item.setPen(QPen(QColor("#3B82F6"), 2))
                self.temp_rect_item.setBrush(QBrush(QColor(59, 130, 246, 30)))
                self.scene().addItem(self.temp_rect_item)
            else:
                rect = QRectF(self.rect_start, pos).normalized()
                if self.temp_rect_item:
                    self.scene().removeItem(self.temp_rect_item)
                    self.temp_rect_item = None
                self.rect_start = None
                self.draw_finished.emit("rect", rect)

        elif self.mode == "DRAW_POLY":
            if self.is_close_to_start(pos) and len(self.poly_points) >= 3:
                # 闭合
                self.draw_finished.emit("poly", list(self.poly_points))
                self.clear_poly_temp()
            else:
                self.poly_points.append(pos)
                self.update_temp_path()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mode == "DRAW_RECT" and self.rect_start is not None and self.temp_rect_item:
            pos = self.mapToScene(event.pos())
            rect = QRectF(self.rect_start, pos).normalized()
            self.temp_rect_item.setRect(rect)

        super().mouseMoveEvent(event)

    def clear_poly_temp(self):
        if self.temp_path_item:
            self.scene().removeItem(self.temp_path_item)
            self.temp_path_item = None
        self.poly_points.clear()

    def update_temp_path(self):
        if self.temp_path_item is None:
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


class RectShape(QGraphicsRectItem):
    def __init__(self, rect, label):
        super().__init__(rect)
        self.label = label
        self.setPen(QPen(QColor("#3B82F6"), 2))
        self.setBrush(QBrush(QColor(59, 130, 246, 40)))
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)


class PolyShape(QGraphicsPolygonItem):
    def __init__(self, points, label):
        super().__init__(QPolygonF(points))
        self.label = label
        self.setPen(QPen(QColor("#FF4D4D"), 2))
        self.setBrush(QBrush(QColor(255, 77, 77, 40)))
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)


class LabelInterface(QWidget):
    request_ai_signal = Signal(str)
    back_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #FFFFFF;")

        self.current_project = None
        self.project_classes = []
        self.current_image_path = None
        self.all_files = []
        self.current_index = -1

        self.scene = QGraphicsScene(self)
        self.view = ImageViewer(self)
        self.view.setScene(self.scene)

        self.view.pointClicked.connect(self.on_canvas_clicked)
        self.view.draw_finished.connect(self.on_draw_finished)

        self.image_item = None
        self.annotations = []
        self.selected_shape_item = None

        self.initUI()
        self.initShortcuts()

    def set_project(self, project_obj):
        self.current_project = project_obj
        if project_obj and getattr(project_obj, "classes", None):
            self.project_classes = [c.strip() for c in project_obj.classes.split(',') if c.strip()]
        else:
            self.project_classes = []
        self.refresh_task_classes_ui()

    def load_file_list(self, all_files, target_path):
        self.all_files = all_files or []
        try:
            self.current_index = self.all_files.index(target_path)
        except Exception:
            self.current_index = -1

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
        self.btnCursor.setChecked(True)

        tb_layout.addWidget(self.btnCursor)
        tb_layout.addWidget(self.btnRect)
        tb_layout.addWidget(self.btnPoly)

        tb_layout.addSpacing(10)

        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #EEE; max-height: 1px;")
        tb_layout.addWidget(line2)
        tb_layout.addSpacing(4)

        self.btnAI = self.create_tool_btn("ai.svg", "AI 标注", None)
        self.btnSave = self.create_tool_btn("save.svg", "保存 (Ctrl+S)", None)
        self.btnExport = self.create_tool_btn("export.svg", "导出", None)
        self.btnHelp = self.create_tool_btn("help.svg", "快捷键说明", None)

        self.btnAI.clicked.connect(self.request_ai)
        self.btnSave.clicked.connect(lambda: self.save_current_work(silent=False))
        self.btnExport.clicked.connect(self.export_dataset)
        self.btnHelp.clicked.connect(self.show_shortcuts)

        tb_layout.addWidget(self.btnAI)
        tb_layout.addWidget(self.btnSave)
        tb_layout.addWidget(self.btnExport)
        tb_layout.addWidget(self.btnHelp)

        tb_layout.addStretch(1)

        # 2. 右侧面板
        rightPanel = QSplitter(Qt.Vertical)
        rightPanel.setFixedWidth(260)
        rightPanel.setStyleSheet("QSplitter::handle{ background:#F3F4F6; height: 1px;}")

        # 当前标注列表
        labelContainer = QFrame()
        labelContainer.setStyleSheet("QFrame{ background:#FFFFFF; border-left: 1px solid #DDD; }")
        labelLayout = QVBoxLayout(labelContainer)
        labelLayout.setContentsMargins(12, 12, 12, 12)
        labelLayout.setSpacing(8)

        titleLabel = QLabel("当前标注 / Annotations")
        titleLabel.setStyleSheet("font-weight:700; color:#111827;")
        labelLayout.addWidget(titleLabel)

        self.labelList = QListWidget()
        self.labelList.setStyleSheet("""
            QListWidget{ border:1px solid #E5E7EB; border-radius:10px; }
            QListWidget::item{ padding:8px; }
            QListWidget::item:selected{ background:#E6F0FF; color:#111827; }
        """)
        self.labelList.itemClicked.connect(self.highlight_shape)
        labelLayout.addWidget(self.labelList, 1)

        # 类别列表
        taskClassContainer = QFrame()
        taskClassContainer.setStyleSheet("QFrame{ background:#FFFFFF; border-left: 1px solid #DDD; }")
        taskClassLayout = QVBoxLayout(taskClassContainer)
        taskClassLayout.setContentsMargins(12, 12, 12, 12)
        taskClassLayout.setSpacing(8)

        titleCls = QLabel("任务历史标签 / Task Classes")
        titleCls.setStyleSheet("font-weight:700; color:#111827;")
        taskClassLayout.addWidget(titleCls)

        self.classList = QListWidget()
        self.classList.setStyleSheet("""
            QListWidget{ border:1px solid #E5E7EB; border-radius:10px; }
            QListWidget::item{ padding:8px; }
            QListWidget::item:selected{ background:#E6F0FF; color:#111827; }
        """)
        taskClassLayout.addWidget(self.classList, 1)

        # 文件信息 + 大保存按钮
        fileContainer = QFrame()
        fileContainer.setStyleSheet("QFrame{ background:#FFFFFF; border-left: 1px solid #DDD; }")
        fileLayout = QVBoxLayout(fileContainer)
        fileLayout.setContentsMargins(12, 12, 12, 12)
        fileLayout.setSpacing(8)

        titleFile = QLabel("文件信息")
        titleFile.setStyleSheet("font-weight:700; color:#111827;")
        fileLayout.addWidget(titleFile)

        self.lblFile = QLabel("未选择")
        self.lblFile.setWordWrap(True)
        self.lblFile.setStyleSheet("color:#374151;")
        fileLayout.addWidget(self.lblFile)

        self.btnSaveBig = QPushButton("💾 保存当前结果")
        self.btnSaveBig.setCursor(Qt.PointingHandCursor)
        self.btnSaveBig.setFixedHeight(38)
        self.btnSaveBig.setStyleSheet(
            "QPushButton { background-color: #3B82F6; color: white; border-radius: 8px; font-weight: 700; border: none; } "
            "QPushButton:hover { background-color: #2563EB; } "
            "QPushButton:pressed { background-color: #1D4ED8; }"
        )
        self.btnSaveBig.clicked.connect(lambda: self.save_current_work(silent=False))
        fileLayout.addWidget(self.btnSaveBig)

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

        # 关键：在主窗口启用半透明/无边框绘制时，也强制让按钮按样式表绘制底色
        btn.setAttribute(Qt.WA_StyledBackground, True)
        btn.setAutoFillBackground(True)

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

        fg = QColor("#3B82F6") if btn.isChecked() else QColor("#555555")
        bg = QColor("#E6F0FF") if btn.isChecked() else QColor("#FFFFFF")

        # 关键：给图标绘制一个不透明“底板”，避免在半透明窗口/全局透明样式下看起来像“穿透”
        try:
            pixmap = render_icon_with_bg(btn.icon_path, 20, fg, bg, radius=8, padding=3)
        except Exception:
            pixmap = render_tinted_pixmap(btn.icon_path, 20, fg)

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
        if key == Qt.Key_A:
            self.prev_image()
        elif key == Qt.Key_D:
            self.next_image()
        elif key == Qt.Key_V:
            self.switch_mode("VIEW")
        elif key == Qt.Key_R:
            self.switch_mode("DRAW_RECT")
        elif key == Qt.Key_P:
            self.switch_mode("DRAW_POLY")
        elif key == Qt.Key_S and (event.modifiers() & Qt.ControlModifier):
            self.save_current_work(silent=False)
        elif key == Qt.Key_Z and (event.modifiers() & Qt.ControlModifier):
            self.undo_last_action()
        elif key == Qt.Key_Delete:
            self.delete_selected_shape()
        elif key == Qt.Key_Escape:
            if self.view.mode == "DRAW_POLY":
                self.view.clear_poly_temp()
        super().keyPressEvent(event)

    def initShortcuts(self):
        # 原版保留：快捷键主要在 keyPressEvent 中处理
        pass

    def show_shortcuts(self):
        dlg = ShortcutDialog(self)
        dlg.exec()

    def switch_mode(self, mode: str):
        self.view.set_mode(mode)
        if mode == 'VIEW':
            self.btnCursor.setChecked(True)
        elif mode == 'DRAW_RECT':
            self.btnRect.setChecked(True)
        elif mode == 'DRAW_POLY':
            self.btnPoly.setChecked(True)

    def on_canvas_clicked(self, pos: QPointF):
        pass

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

            if shape_type == "rect":
                rect: QRectF = data
                item = RectShape(rect, label)
                self.scene.addItem(item)
                self.annotations.append(item)
                self.refresh_label_list()

            elif shape_type == "poly":
                points = data
                item = PolyShape(points, label)
                self.scene.addItem(item)
                self.annotations.append(item)
                self.refresh_label_list()

            self.switch_mode('VIEW')

    def refresh_label_list(self):
        self.labelList.clear()
        for it in self.annotations:
            self.labelList.addItem(QListWidgetItem(it.label))

    def highlight_shape(self, item):
        idx = self.labelList.row(item)
        if idx < 0 or idx >= len(self.annotations):
            return
        shp = self.annotations[idx]
        shp.setSelected(True)
        self.selected_shape_item = shp
        self.view.centerOn(shp)

    def delete_selected_shape(self):
        if self.selected_shape_item:
            try:
                self.scene.removeItem(self.selected_shape_item)
            except Exception:
                pass
            if self.selected_shape_item in self.annotations:
                self.annotations.remove(self.selected_shape_item)
            self.selected_shape_item = None
            self.refresh_label_list()

    def undo_last_action(self):
        if self.view.mode == "DRAW_POLY" and self.view.poly_points:
            self.view.clear_poly_temp()
            return
        if not self.annotations:
            return
        last = self.annotations.pop()
        try:
            self.scene.removeItem(last)
        except Exception:
            pass
        self.refresh_label_list()

    def load_image(self, image_path: str):
        self.current_image_path = image_path
        self.lblFile.setText(image_path or "未选择")

        self.scene.clear()
        self.image_item = None
        self.annotations = []
        self.selected_shape_item = None

        if not image_path or not os.path.exists(image_path):
            QMessageBox.warning(self, "加载失败", f"找不到图像文件：{image_path}")
            return

        pm = QPixmap(image_path)
        if pm.isNull():
            QMessageBox.warning(self, "加载失败", "图像文件无法读取。")
            return

        self.image_item = self.scene.addPixmap(pm)
        self.scene.setSceneRect(QRectF(pm.rect()))
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

        # 从数据库加载标注（原版逻辑）
        self.load_annotations_from_db()
        self.refresh_label_list()

    def load_annotations_from_db(self):
        if not self.current_image_path:
            return

        media_item = MediaItem.get_or_none(MediaItem.file_path == self.current_image_path)
        if not media_item:
            return

        img_w = self.view.sceneRect().width()
        img_h = self.view.sceneRect().height()
        if img_w <= 0 or img_h <= 0:
            return

        for ann in media_item.annotations:
            if getattr(ann, "shape_type", "") == "poly" and getattr(ann, "points", None):
                try:
                    pts = json.loads(ann.points)
                    qpoints = [QPointF(p[0] * img_w, p[1] * img_h) for p in pts]
                    item = PolyShape(qpoints, ann.label)
                    self.scene.addItem(item)
                    self.annotations.append(item)
                except Exception:
                    pass
            else:
                try:
                    # DB 中存的是归一化中心点 + 归一化宽高（rect）
                    w = ann.w * img_w
                    h = ann.h * img_h
                    x = (ann.x * img_w) - (w / 2)
                    y = (ann.y * img_h) - (h / 2)
                    rect = QRectF(x, y, w, h)
                    item = RectShape(rect, ann.label)
                    self.scene.addItem(item)
                    self.annotations.append(item)
                except Exception:
                    pass

    def save_current_work(self, silent=True):
        if not self.current_image_path:
            if not silent:
                QMessageBox.information(self, "提示", "请先加载图像。")
            return

        img_w = self.view.sceneRect().width()
        img_h = self.view.sceneRect().height()
        if img_w <= 0 or img_h <= 0:
            if not silent:
                QMessageBox.warning(self, "保存失败", "画布尺寸异常，无法保存。")
            return

        box_data = []
        for it in self.annotations:
            if isinstance(it, RectShape):
                r = it.rect().normalized()
                x = (r.center().x()) / img_w
                y = (r.center().y()) / img_h
                w = r.width() / img_w
                h = r.height() / img_h
                box_data.append({"shape_type": "rect", "label": it.label, "rect": [x, y, w, h]})

            elif isinstance(it, PolyShape):
                poly = it.polygon()
                pts = [(float(poly[i].x()) / img_w, float(poly[i].y()) / img_h) for i in range(poly.count())]
                box_data.append({"shape_type": "poly", "label": it.label, "points": json.dumps(pts)})

        ok = DataManager.save_annotations(self.current_image_path, box_data)

        if ok:
            if not silent:
                QMessageBox.information(self, "保存成功", "标注已保存。")
            if hasattr(self, "btnSaveBig"):
                self.btnSaveBig.setText("✅ 已保存")
                # 不用 QTimer，避免某些情况下未导入导致异常（原版里一般是 OK 的）
        else:
            if not silent:
                QMessageBox.warning(self, "保存失败", "保存失败，请检查数据库/路径。")

    def request_ai(self):
        if not self.current_image_path:
            QMessageBox.information(self, "提示", "请先选择图像。")
            return
        self.request_ai_signal.emit(self.current_image_path)

    def apply_ai_results(self, results):
        if not results:
            return

        # 先清空现有标注（保留底图）
        for it in list(self.annotations):
            try:
                self.scene.removeItem(it)
            except Exception:
                pass
        self.annotations = []

        img_w = self.view.sceneRect().width()
        img_h = self.view.sceneRect().height()
        if img_w <= 0 or img_h <= 0:
            return

        try:
            for ann in results:
                if ann.get("shape_type") == "poly" and ann.get("points"):
                    pts = json.loads(ann["points"])
                    qpoints = [QPointF(p[0] * img_w, p[1] * img_h) for p in pts]
                    item = PolyShape(qpoints, ann.get("label", "Object"))
                    self.scene.addItem(item)
                    self.annotations.append(item)
                else:
                    rect = ann.get("rect", [0, 0, 0, 0])
                    cx, cy, w, h = rect
                    wpx = w * img_w
                    hpx = h * img_h
                    x = cx * img_w - wpx / 2
                    y = cy * img_h - hpx / 2
                    item = RectShape(QRectF(x, y, wpx, hpx), ann.get("label", "Object"))
                    self.scene.addItem(item)
                    self.annotations.append(item)
        except Exception:
            pass

        self.refresh_label_list()

    def export_dataset(self):
        if not self.current_project:
            QMessageBox.information(self, "提示", "请先选择项目。")
            return
        dlg = ExportDialog(self, self.current_project)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data or not data.get("path"):
            return
        try:
            DataManager.export_dataset(self.current_project, data['path'], data['format'])
            QMessageBox.information(self, "导出完成", "导出成功。")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"{e}")

    def prev_image(self):
        if not self.all_files:
            return
        if self.current_index <= 0:
            return
        self.save_current_work(silent=True)
        self.current_index -= 1
        self.load_image(self.all_files[self.current_index])

    def next_image(self):
        if not self.all_files:
            return
        if self.current_index < 0:
            return
        if self.current_index >= len(self.all_files) - 1:
            return
        self.save_current_work(silent=True)
        self.current_index += 1
        self.load_image(self.all_files[self.current_index])
