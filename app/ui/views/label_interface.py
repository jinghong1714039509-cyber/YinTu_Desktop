import json
import os
import sys
import math
import hashlib

# === 修复核心 1: 补全 QGraphicsLineItem，彻底解决多边形画线崩溃问题 ===
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QPushButton, QLabel, QGraphicsView,
                               QGraphicsScene, QGraphicsRectItem, QGraphicsPolygonItem,
                               QGraphicsPathItem, QGraphicsItem, QFrame, QMessageBox,
                               QListWidget, QListWidgetItem, QGraphicsLineItem, QGraphicsEllipseItem,
                               QSplitter, QButtonGroup, QGraphicsTextItem, QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
                               QStyle, QScrollArea, QGraphicsDropShadowEffect, QApplication, QFileDialog)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSize
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QPen, QColor, QBrush, QPolygonF, QPainterPath, QFont, QAction, QKeySequence, QIcon, QShortcut
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
    undoRequested = Signal()

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
        self.poly_hover_pos = None
        # 缓存 VIEW 模式自定义光标（cursor.svg）
        self._cursor_view = render_svg_cursor("cursor.svg", size=24, hotspot_x=1, hotspot_y=1)
        # 初始化为 VIEW 时的悬停光标
        self.viewport().setCursor(self._cursor_view)


    def set_mode(self, mode: str):
        self.mode = mode
        self.rect_start = None

        sc = self.scene()

        def _safe_remove(item):
            if not item or sc is None:
                return
            try:
                sc.removeItem(item)
            except RuntimeError:
                # 可能已被 Qt (C++) 释放/scene.clear 清空
                pass

        # 清理临时矩形
        if self.temp_rect_item:
            _safe_remove(self.temp_rect_item)
            self.temp_rect_item = None

        # 清理临时多边形路径
        if self.temp_path_item:
            _safe_remove(self.temp_path_item)
            self.temp_path_item = None

        self.poly_points.clear()
        self.poly_hover_pos = None

        # === 根据模式设置拖拽与光标 ===
        if mode == "VIEW":
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.viewport().setCursor(self._cursor_view)      # 悬停光标：cursor.svg
        else:
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.CrossCursor)         # 绘制光标：十字准星

        # 仅在 VIEW 允许鼠标与标注交互（拖动/点选）；绘制模式下禁止，避免误拖动重叠标注
        self._apply_annotation_interaction()


    def _apply_annotation_interaction(self):
        """Enable mouse interaction (move/click) for existing annotations only in VIEW mode.

        In drawing modes, annotations stay selectable programmatically (e.g. from the right list),
        but they do not accept mouse events and cannot be moved, preventing accidental dragging when
        annotations overlap.
        """
        sc = self.scene()
        if sc is None:
            return

        movable = (self.mode == "VIEW")
        for item in sc.items():
            if isinstance(item, (RectShape, PolyShape)):
                # Always keep selectable so list-driven selection/highlight still works
                item.setFlag(QGraphicsItem.ItemIsSelectable, True)
                item.setFlag(QGraphicsItem.ItemIsMovable, movable)
                item.setAcceptedMouseButtons(Qt.LeftButton if movable else Qt.NoButton)
                if not movable:
                    item.setSelected(False)

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)


    def enterEvent(self, event):
        super().enterEvent(event)
        # 进入画布时，确保光标与当前模式一致（避免 ScrollHandDrag 默认手型覆盖）
        if self.mode == "VIEW":
            self.viewport().setCursor(self._cursor_view)
        else:
            self.viewport().setCursor(Qt.CrossCursor)

    # === 限制标注在图片范围内（sceneRect 即图片区域） ===
    def _image_rect(self) -> QRectF:
        sc = self.scene()
        return sc.sceneRect() if sc else QRectF()

    def _in_image(self, p: QPointF) -> bool:
        r = self._image_rect()
        return (not r.isNull()) and r.contains(p)

    def _clamp_to_image(self, p: QPointF) -> QPointF:
        r = self._image_rect()
        if r.isNull():
            return p
        x = min(max(p.x(), r.left()), r.right())
        y = min(max(p.y(), r.top()), r.bottom())
        return QPointF(x, y)

    def mousePressEvent(self, event):
        # 右键撤销：仅在绘制模式拦截（避免影响 VIEW 模式右键行为/未来右键菜单）
        if event.button() == Qt.RightButton:
            if self.mode == "DRAW_POLY":
                # 多边形绘制中：优先回退最后一个点（比直接清空更符合直觉）
                if self.poly_points:
                    self.poly_points.pop()
                    if not self.poly_points:
                        # 没有点了，清理临时状态
                        self.clear_poly_temp()
                    else:
                        # 刷新预览线到当前鼠标位置（并限制在图片内）
                        pos = self._clamp_to_image(self.mapToScene(event.pos()))
                        self.poly_hover_pos = pos
                        self.update_temp_path(pos)
                    event.accept()
                    return
                # 没有点：视为撤销上一条已完成标注
                self.undoRequested.emit()
                event.accept()
                return

            if self.mode == "DRAW_RECT":
                # 矩形绘制中：若已点击起点，则取消本次矩形绘制；否则撤销上一条标注
                if self.rect_start is not None:
                    sc = self.scene()
                    if self.temp_rect_item and sc is not None:
                        try:
                            sc.removeItem(self.temp_rect_item)
                        except RuntimeError:
                            pass
                    self.temp_rect_item = None
                    self.rect_start = None
                    event.accept()
                    return
                self.undoRequested.emit()
                event.accept()
                return

            # VIEW 模式不拦截右键
            super().mousePressEvent(event)
            return

        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        pos = self.mapToScene(event.pos())

        # VIEW：允许拖拽/选择；并发出点击信号（保持原行为）
        if self.mode == "VIEW":
            self.pointClicked.emit(pos)
            super().mousePressEvent(event)
            return

        # 未加载图片时，sceneRect 可能为空；绘制直接忽略
        if self._image_rect().isNull():
            return

        if self.mode == "DRAW_RECT":
            if self.rect_start is None:
                # 起点必须在图片内
                if not self._in_image(pos):
                    return
                pos = self._clamp_to_image(pos)
                self.pointClicked.emit(pos)

                self.rect_start = pos
                self.temp_rect_item = QGraphicsRectItem(QRectF(pos, pos))
                self.temp_rect_item.setPen(QPen(QColor("#3B82F6"), 2))
                self.temp_rect_item.setBrush(QBrush(QColor(59, 130, 246, 30)))
                self.scene().addItem(self.temp_rect_item)
            else:
                # 终点 clamp 到图片边界，确保矩形不越界
                pos = self._clamp_to_image(pos)
                self.pointClicked.emit(pos)

                rect = QRectF(self.rect_start, pos).normalized()
                if self.temp_rect_item:
                    self.scene().removeItem(self.temp_rect_item)
                    self.temp_rect_item = None
                self.rect_start = None
                self.draw_finished.emit("rect", rect)
            event.accept()
            return

        if self.mode == "DRAW_POLY":
            # 每个点必须在图片内
            if not self._in_image(pos):
                return
            pos = self._clamp_to_image(pos)
            self.pointClicked.emit(pos)

            if self.is_close_to_start(pos) and len(self.poly_points) >= 3:
                # 闭合
                self.draw_finished.emit("poly", list(self.poly_points))
                self.clear_poly_temp()
            else:
                self.poly_points.append(pos)
                # 立即刷新一次 hover 预览，避免用户不移动鼠标时看不到反馈
                self.poly_hover_pos = pos
                self.update_temp_path(self.poly_hover_pos)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())

        # VIEW 模式：鼠标悬停时强制使用 cursor.svg（避免拖拽模式变成手型）
        if self.mode == "VIEW" and event.buttons() == Qt.NoButton:
            self.viewport().setCursor(self._cursor_view)

        # 未加载图片时，不做绘制预览
        if self._image_rect().isNull():
            super().mouseMoveEvent(event)
            return

        # 矩形拖拽预览（终点 clamp 到图片边界）
        if self.mode == "DRAW_RECT" and self.rect_start is not None and self.temp_rect_item:
            pos = self._clamp_to_image(pos)
            rect = QRectF(self.rect_start, pos).normalized()
            self.temp_rect_item.setRect(rect)

        # 多边形预览：最后一点 -> 鼠标（hover 也 clamp 到图片边界）
        elif self.mode == "DRAW_POLY" and self.poly_points:
            pos = self._clamp_to_image(pos)
            if self.is_close_to_start(pos) and len(self.poly_points) >= 3:
                hover_pos = self.poly_points[0]
            else:
                hover_pos = pos
            self.poly_hover_pos = hover_pos
            self.update_temp_path(hover_pos)
        if self.mode != "VIEW":
            event.accept()
            return

        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.mode == "VIEW":
            # 拖拽结束后，强制恢复为 cursor.svg 悬停光标
            self.viewport().setCursor(self._cursor_view)


    def clear_poly_temp(self):
        """清理多边形临时绘制状态（不影响已提交的标注）。"""
        sc = self.scene()
        if self.temp_path_item:
            try:
                if sc:
                    sc.removeItem(self.temp_path_item)
            except RuntimeError:
                # 可能已被 Qt (C++) 释放
                pass
            self.temp_path_item = None
        self.poly_points.clear()
        self.poly_hover_pos = None

    def update_temp_path(self, hover_pos=None):
        """更新多边形临时路径；hover_pos 用于绘制最后一点到鼠标的预览线。
        修复：避免引用已被 Qt 删除的 QGraphicsPathItem（Internal C++ object already deleted）。
        """
        sc = self.scene()
        if sc is None:
            return

        # 若临时 item 已失效/脱离 scene，丢弃引用并重建
        if self.temp_path_item is not None:
            try:
                if self.temp_path_item.scene() is None or self.temp_path_item.scene() is not sc:
                    self.temp_path_item = None
            except RuntimeError:
                self.temp_path_item = None

        if self.temp_path_item is None:
            self.temp_path_item = QGraphicsPathItem()
            self.temp_path_item.setPen(QPen(Qt.red, 2))
            sc.addItem(self.temp_path_item)

        path = QPainterPath()
        if self.poly_points:
            path.moveTo(self.poly_points[0])
            for p in self.poly_points[1:]:
                path.lineTo(p)
            if hover_pos is not None:
                path.lineTo(hover_pos)

        try:
            self.temp_path_item.setPath(path)
        except RuntimeError:
            # 极端情况下 setPath 前 item 又被释放，重建再试一次
            self.temp_path_item = QGraphicsPathItem()
            self.temp_path_item.setPen(QPen(Qt.red, 2))
            sc.addItem(self.temp_path_item)
            self.temp_path_item.setPath(path)

    def is_close_to_start(self, pos):
        if not self.poly_points:
            return False
        start = self.poly_points[0]
        dist = math.sqrt((pos.x() - start.x()) ** 2 + (pos.y() - start.y()) ** 2)
        return dist < self.snap_threshold / self.transform().m11()


# =====================
# 按类别着色：不同 label 使用不同颜色
# - 同一 label 始终同色（稳定）
# - 若项目已定义 classes，则按 classes 顺序分配颜色
# - 否则使用 label 哈希映射到调色板，保证跨会话一致
# =====================
_LABEL_COLOR_PALETTE = [
    "#3B82F6",  # blue
    "#EF4444",  # red
    "#10B981",  # green
    "#F59E0B",  # amber
    "#8B5CF6",  # purple
    "#06B6D4",  # cyan
    "#EC4899",  # pink
    "#22C55E",  # green2
    "#A855F7",  # violet
    "#0EA5E9",  # sky
    "#F97316",  # orange
    "#14B8A6",  # teal
    "#E11D48",  # rose
    "#84CC16",  # lime
    "#6366F1",  # indigo
    "#D946EF",  # fuchsia
    "#64748B",  # slate
    "#9333EA",  # purple2
    "#FB7185",  # pink2
    "#2DD4BF",  # teal2
]


def color_for_label(label: str, classes=None) -> QColor:
    """Get a stable QColor for a label.

    Args:
        label: annotation class name
        classes: optional list of project classes; if provided and contains label,
                 the color is based on the class index (stable within project).
    """
    if not label:
        return QColor(_LABEL_COLOR_PALETTE[0])

    idx = None
    try:
        if classes and label in classes:
            idx = int(classes.index(label))
    except Exception:
        idx = None

    if idx is None:
        h = hashlib.md5(label.encode("utf-8")).hexdigest()
        idx = int(h[:8], 16)

    return QColor(_LABEL_COLOR_PALETTE[idx % len(_LABEL_COLOR_PALETTE)])


class RectShape(QGraphicsRectItem):
    def __init__(self, rect, label, color: QColor = None):
        super().__init__(rect)
        self.label = label
        if color is None:
            color = color_for_label(label)
        self._color = QColor(color)
        self.setPen(QPen(self._color, 2))
        self.setBrush(QBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), 40)))
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)

    def set_color(self, color: QColor):
        """Update pen/brush color for this shape."""
        self._color = QColor(color)
        self.setPen(QPen(self._color, 2))
        self.setBrush(QBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), 40)))


class PolyShape(QGraphicsPolygonItem):
    def __init__(self, points, label, color: QColor = None):
        super().__init__(QPolygonF(points))
        self.label = label
        if color is None:
            color = color_for_label(label)
        self._color = QColor(color)
        self.setPen(QPen(self._color, 2))
        self.setBrush(QBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), 40)))
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)

    def set_color(self, color: QColor):
        """Update pen/brush color for this shape."""
        self._color = QColor(color)
        self.setPen(QPen(self._color, 2))
        self.setBrush(QBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), 40)))


class LabelInterface(QWidget):
    request_ai_signal = Signal(str)
    # 当用户在标注页中切换/新增 AI 模型时，通知 MainWindow 立即更新 ai_worker 配置
    ai_model_changed_signal = Signal(str)
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

        self.view.undoRequested.connect(self.undo_last_action)

        self.image_item = None
        self.annotations = []
        self.selected_shape_item = None

        self.initUI()

        # 画布选中项 <-> 右侧列表联动
        self._syncing_selection = False
        self.scene.selectionChanged.connect(self.on_scene_selection_changed)

        self.initShortcuts()

    def set_project(self, project_obj):
        self.current_project = project_obj
        if project_obj and getattr(project_obj, "classes", None):
            self.project_classes = [c.strip() for c in project_obj.classes.split(',') if c.strip()]
        else:
            self.project_classes = []
        self.refresh_task_classes_ui()

    def get_label_color(self, label: str) -> QColor:
        """Return stable color for a given label within current project."""
        return color_for_label(label, self.project_classes)

    def load_file_list(self, all_files, target_path):
        self.all_files = all_files or []
        # 更新右下角文件夹内容列表（基于目标文件所在目录）
        try:
            self.update_file_info_list(os.path.dirname(target_path) if target_path else "")
        except Exception:
            pass
        try:
            self.current_index = self.all_files.index(target_path)
        except Exception:
            self.current_index = -1

    def update_file_info_list(self, folder_path: str):
        """更新右下角『文件信息』：显示指定文件夹内的文件列表（仅第一层）。"""
        if not hasattr(self, "fileListInfo"):
            return

        self.fileListInfo.clear()

        if not folder_path or (not os.path.isdir(folder_path)):
            if hasattr(self, "lblFolder"):
                self.lblFolder.setText("文件夹：未选择")
            if hasattr(self, "lblFileCount"):
                self.lblFileCount.setText("")
            return

        if hasattr(self, "lblFolder"):
            self.lblFolder.setText(f"文件夹：{folder_path}")

        try:
            files = [f for f in os.listdir(folder_path)
                     if os.path.isfile(os.path.join(folder_path, f))]
            files.sort(key=lambda s: s.lower())
        except Exception:
            files = []

        max_show = 200
        shown = files[:max_show]

        for name in shown:
            self.fileListInfo.addItem(QListWidgetItem(name))

        extra = "" if len(files) <= max_show else f"（仅显示前 {max_show} 个）"
        if hasattr(self, "lblFileCount"):
            self.lblFileCount.setText(f"文件数：{len(files)}{extra}")

        # 高亮当前文件
        try:
            cur = os.path.basename(self.current_image_path or "")
            if cur:
                for i, name in enumerate(shown):
                    if name == cur:
                        self.fileListInfo.setCurrentRow(i)
                        break
        except Exception:
            pass


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

        # AI 模型配置（新增/切换）
        self.btnAIModel = self.create_tool_btn("ai2.svg", "设置/切换 AI 模型", None)
        self.btnAI = self.create_tool_btn("ai.svg", "AI 标注", None)
        self.btnSave = self.create_tool_btn("save.svg", "保存 (Ctrl+S)", None)
        self.btnExport = self.create_tool_btn("export.svg", "导出", None)
        self.btnHelp = self.create_tool_btn("help.svg", "快捷键说明", None)

        self.btnAIModel.clicked.connect(self.choose_ai_model)
        self.btnAI.clicked.connect(self.request_ai)
        self.btnSave.clicked.connect(lambda: self.save_current_work(silent=False))
        self.btnExport.clicked.connect(self.export_dataset)
        self.btnHelp.clicked.connect(self.show_shortcuts)

        tb_layout.addWidget(self.btnAIModel)
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
        # 显示当前文件夹及其内文件（右下角文件信息）
        self.lblFolder = QLabel("文件夹：未选择")
        self.lblFolder.setWordWrap(True)
        self.lblFolder.setStyleSheet("color:#6B7280; font-size: 12px;")
        fileLayout.addWidget(self.lblFolder)

        self.lblFileCount = QLabel("")
        self.lblFileCount.setStyleSheet("color:#6B7280; font-size: 12px;")
        fileLayout.addWidget(self.lblFileCount)

        self.fileListInfo = QListWidget()
        self.fileListInfo.setStyleSheet("""
            QListWidget{ border:1px solid #E5E7EB; border-radius:10px; }
            QListWidget::item{ padding:6px; }
            QListWidget::item:selected{ background:#E6F0FF; color:#111827; }
        """)
        self.fileListInfo.setMaximumHeight(220)
        self.fileListInfo.setSelectionMode(QListWidget.SingleSelection)
        fileLayout.addWidget(self.fileListInfo)


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

        # 进入标注界面时，主窗口默认最大化（更接近“初始全屏”的体验）
        if not getattr(self, "_did_request_maximize", False):
            self._did_request_maximize = True
            try:
                w = self.window()
                if w is not None:
                    w.showMaximized()
            except Exception:
                pass

        self.setFocus()
        self.activateWindow()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_V:
            self.switch_mode("VIEW")
        elif key == Qt.Key_R:
            self.switch_mode("DRAW_RECT")
        elif key == Qt.Key_P:
            self.switch_mode("DRAW_POLY")
        elif key == Qt.Key_S and (event.modifiers() & Qt.ControlModifier):
            self.save_current_work(silent=False)
        elif key == Qt.Key_Z and (event.modifiers() & Qt.ControlModifier):
            self.undo_last_action()
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected_shapes()
        elif key == Qt.Key_Escape:
            if self.view.mode == "DRAW_POLY":
                self.view.clear_poly_temp()
        super().keyPressEvent(event)


    def initShortcuts(self):
        """A/D 切图使用 QShortcut，确保焦点在画布/列表时也可用。"""
        def _modal_open() -> bool:
            return QApplication.activeModalWidget() is not None

        sc_prev = QShortcut(QKeySequence("A"), self)
        sc_prev.setContext(Qt.WidgetWithChildrenShortcut)
        sc_prev.activated.connect(lambda: None if _modal_open() else self.prev_image())

        sc_next = QShortcut(QKeySequence("D"), self)
        sc_next.setContext(Qt.WidgetWithChildrenShortcut)
        sc_next.activated.connect(lambda: None if _modal_open() else self.next_image())

        sc_delete = QShortcut(QKeySequence("Delete"), self)
        sc_delete.setContext(Qt.WidgetWithChildrenShortcut)
        sc_delete.activated.connect(lambda: None if _modal_open() else self.delete_selected_shapes())

        sc_backspace = QShortcut(QKeySequence("Backspace"), self)
        sc_backspace.setContext(Qt.WidgetWithChildrenShortcut)
        sc_backspace.activated.connect(lambda: None if _modal_open() else self.delete_selected_shapes())

        # 防止被垃圾回收
        self._shortcuts = [sc_prev, sc_next, sc_delete, sc_backspace]


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
                item = RectShape(rect, label, self.get_label_color(label))
                self.scene.addItem(item)
                self.annotations.append(item)
                self.view._apply_annotation_interaction()
                self.refresh_label_list()

            elif shape_type == "poly":
                points = data
                item = PolyShape(points, label, self.get_label_color(label))
                self.scene.addItem(item)
                self.annotations.append(item)
                self.view._apply_annotation_interaction()
                self.refresh_label_list()

            self.view.setFocus()


    def refresh_label_list(self):
        """Rebuild the right-side annotation list and keep selection in sync."""
        current = self.selected_shape_item
        self._syncing_selection = True
        try:
            self.labelList.clear()
            for it in self.annotations:
                self.labelList.addItem(QListWidgetItem(it.label))

            # Restore selection if possible
            if current is not None and current in self.annotations:
                idx = self.annotations.index(current)
                self.labelList.setCurrentRow(idx)
                if self.labelList.item(idx):
                    self.labelList.item(idx).setSelected(True)
        finally:
            self._syncing_selection = False

    def on_scene_selection_changed(self):
        """Sync canvas selection -> right list selection (VIEW mode)."""
        if getattr(self, "_syncing_selection", False):
            return
        if not hasattr(self, "labelList"):
            return

        items = [it for it in self.scene.selectedItems() if isinstance(it, (RectShape, PolyShape))]
        if not items:
            self.selected_shape_item = None
            self._syncing_selection = True
            try:
                self.labelList.clearSelection()
            finally:
                self._syncing_selection = False
            return

        # Prefer the first selected item
        shp = items[0]
        self.selected_shape_item = shp

        try:
            idx = self.annotations.index(shp)
        except ValueError:
            return

        self._syncing_selection = True
        try:
            self.labelList.setCurrentRow(idx)
            if self.labelList.item(idx):
                self.labelList.item(idx).setSelected(True)
        finally:
            self._syncing_selection = False

    def highlight_shape(self, item):
        """Right list click -> select/highlight the corresponding shape on canvas."""
        if getattr(self, "_syncing_selection", False):
            return
        idx = self.labelList.row(item)
        if idx < 0 or idx >= len(self.annotations):
            return

        shp = self.annotations[idx]
        self._syncing_selection = True
        try:
            self.scene.clearSelection()
            shp.setSelected(True)
            self.selected_shape_item = shp
        finally:
            self._syncing_selection = False

        self.view.centerOn(shp)

    def delete_selected_shapes(self):
        """Delete selected annotations.

        Supported selection sources:
          1) Selected rows in the right annotation list
          2) Selected shapes on canvas (VIEW mode)
        Also supports legacy self.selected_shape_item.
        """
        to_delete = []

        # From right list selection
        try:
            for mi in self.labelList.selectedIndexes():
                r = mi.row()
                if 0 <= r < len(self.annotations):
                    to_delete.append(self.annotations[r])
        except Exception:
            pass

        # From canvas selection
        try:
            for it in self.scene.selectedItems():
                if isinstance(it, (RectShape, PolyShape)):
                    to_delete.append(it)
        except Exception:
            pass

        # Fallback
        if not to_delete and self.selected_shape_item is not None:
            to_delete.append(self.selected_shape_item)

        # Deduplicate while preserving order
        seen = set()
        uniq = []
        for it in to_delete:
            if id(it) not in seen:
                seen.add(id(it))
                uniq.append(it)

        if not uniq:
            return

        for it in uniq:
            try:
                self.scene.removeItem(it)
            except Exception:
                pass
            try:
                if it in self.annotations:
                    self.annotations.remove(it)
            except Exception:
                pass

        self.scene.clearSelection()
        self.selected_shape_item = None
        self.refresh_label_list()

    def delete_selected_shape(self):
        """Backward-compatible wrapper."""
        self.delete_selected_shapes()

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

        # 更新右下角文件夹内容列表
        try:
            self.update_file_info_list(os.path.dirname(image_path) if image_path else "")
        except Exception:
            pass

        # 清空 scene（会在 C++ 层销毁所有 items）
        self.scene.clear()

        # 同步清理 view 里可能残留的临时 item 引用，避免后续 update_temp_path/setPath 触发 “已删除对象”
        try:
            self.view.temp_rect_item = None
            self.view.temp_path_item = None
            self.view.rect_start = None
            self.view.poly_points.clear()
            self.view.poly_hover_pos = None
        except Exception:
            pass

        # 保持当前工具不变，但重新应用拖拽/光标设置
        try:
            self.view.set_mode(self.view.mode)
        except Exception:
            pass

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
        self.view._apply_annotation_interaction()
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
                    item = PolyShape(qpoints, ann.label, self.get_label_color(ann.label))
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
                    item = RectShape(rect, ann.label, self.get_label_color(ann.label))
                    self.scene.addItem(item)
                    self.annotations.append(item)
                except Exception:
                    pass

        # 若 DB 中出现了新的 label，而 Project.classes 为空或缺失，则自动补齐到『任务历史标签』
        try:
            changed = False
            for it in self.annotations:
                lbl = getattr(it, "label", None)
                if lbl and lbl not in self.project_classes:
                    self.project_classes.append(lbl)
                    changed = True
            if changed:
                if self.current_project:
                    self.current_project.classes = ",".join(self.project_classes)
                    self.current_project.save()
                self.refresh_task_classes_ui()
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

        # 统一保存结构：写入 x/y/w/h（归一化中心点+宽高）用于数据库字段，同时保留 rect 兼容旧逻辑
        box_data = []
        for it in self.annotations:
            if isinstance(it, RectShape):
                r = it.rect().normalized()
                x = (r.center().x()) / img_w
                y = (r.center().y()) / img_h
                w = r.width() / img_w
                h = r.height() / img_h
                box_data.append({
                    "shape_type": "rect",
                    "label": it.label,
                    "x": x, "y": y, "w": w, "h": h,
                    "rect": [x, y, w, h]
                })

            elif isinstance(it, PolyShape):
                poly = it.polygon()
                pts = [(float(poly[i].x()) / img_w, float(poly[i].y()) / img_h) for i in range(poly.count())]
                br = poly.boundingRect()
                cx = br.center().x() / img_w
                cy = br.center().y() / img_h
                w = br.width() / img_w
                h = br.height() / img_h
                box_data.append({
                    "shape_type": "poly",
                    "label": it.label,
                    "x": cx, "y": cy, "w": w, "h": h,
                    "rect": [cx, cy, w, h],
                    "points": json.dumps(pts)
                })

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

    def choose_ai_model(self):
        """新增/切换 AI 模型：选择模型文件 -> 写入 Project -> 通知 MainWindow 更新 ai_worker。"""
        if not self.current_project:
            QMessageBox.information(self, "提示", "请先进入某个任务的标注界面后再设置 AI 模型。")
            return

        # 默认打开上次模型所在目录；否则打开当前工作目录
        start_dir = os.getcwd()
        try:
            mp = getattr(self.current_project, "model_path", None)
            if mp and isinstance(mp, str) and os.path.exists(os.path.dirname(mp)):
                start_dir = os.path.dirname(mp)
        except Exception:
            pass

        filt = "Model Files (*.pt *.onnx *.engine *.xml *.tflite *.pb *.pth *.pkl);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 AI 模型文件", start_dir, filt)
        if not file_path:
            return

        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "失败", "选择的模型文件不存在，请重新选择。")
            return

        # 写入 Project（peewee Model）并持久化
        try:
            self.current_project.model_path = file_path
            self.current_project.save()
        except Exception:
            # 即便写库失败，也尽量让当前会话可用
            pass

        # 立即通知主窗口更新 ai_worker 配置
        try:
            self.ai_model_changed_signal.emit(file_path)
        except Exception:
            pass

        QMessageBox.information(self, "成功", f"AI 模型已设置为：\n{file_path}")

    def request_ai(self):
        if not self.current_image_path:
            QMessageBox.information(self, "提示", "请先选择图像。")
            return

        # 若任务未设置模型，优先提示用户设置（避免默认模型缺失时反复报错）
        model_path = None
        try:
            model_path = getattr(self.current_project, "model_path", None)
        except Exception:
            model_path = None

        if not model_path:
            QMessageBox.information(self, "提示", "当前任务未设置 AI 模型，请先点击左侧『设置/切换 AI 模型』按钮选择模型文件。")
            return

        if model_path and (not os.path.exists(model_path)):
            QMessageBox.warning(self, "提示", "当前任务的 AI 模型文件不存在或路径无效，请重新选择模型文件。")
            return

        self.request_ai_signal.emit(self.current_image_path)

    def apply_ai_results(self, results):
        if not results:
            return

        # AI 结果可能包含新的类别：同步进 Project.classes，并刷新右侧『任务历史标签』
        try:
            changed = False
            for ann in results:
                lbl = ann.get("label") or "Object"
                if lbl not in self.project_classes:
                    self.project_classes.append(lbl)
                    changed = True
            if changed:
                if self.current_project:
                    self.current_project.classes = ",".join(self.project_classes)
                    self.current_project.save()
                self.refresh_task_classes_ui()
        except Exception:
            pass

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
                    lbl = ann.get("label", "Object")
                    item = PolyShape(qpoints, lbl, self.get_label_color(lbl))
                    self.scene.addItem(item)
                    self.annotations.append(item)
                else:
                    rect = ann.get("rect", [0, 0, 0, 0])
                    cx, cy, w, h = rect
                    wpx = w * img_w
                    hpx = h * img_h
                    x = cx * img_w - wpx / 2
                    y = cy * img_h - hpx / 2
                    lbl = ann.get("label", "Object")
                    item = RectShape(QRectF(x, y, wpx, hpx), lbl, self.get_label_color(lbl))
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
