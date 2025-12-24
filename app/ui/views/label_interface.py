from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QScrollArea, QListWidget, QListWidgetItem, QSizePolicy
)

from qfluentwidgets import (
    CardWidget, TitleLabel, BodyLabel, PrimaryPushButton, PushButton
)

from app.services.data_manager import DataManager


@dataclass
class TaskViewModel:
    id: int
    file_path: str
    status: int


def _status_text(status: int) -> str:
    if status == DataManager.STATUS_UNLABELED:
        return "未标注"
    if status == DataManager.STATUS_IN_PROGRESS:
        return "标注中"
    if status == DataManager.STATUS_DONE:
        return "已标注"
    return "未知"


class TaskCard(CardWidget):
    annotate_clicked = Signal(int)  # media_id

    def __init__(self, task: TaskViewModel, parent=None):
        super().__init__(parent)
        self.task = task
        self._build()

    def _build(self):
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(84)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # 左：文本
        left = QWidget(self)
        leftLayout = QVBoxLayout(left)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setSpacing(6)

        name = Path(self.task.file_path).name
        self.title = TitleLabel(name, left)
        self.title.setMaximumHeight(26)

        self.meta = BodyLabel(f"状态：{_status_text(self.task.status)}", left)
        self.meta.setWordWrap(False)

        leftLayout.addWidget(self.title)
        leftLayout.addWidget(self.meta)

        # 右：动作
        self.btn = PrimaryPushButton("标注", self)
        self.btn.clicked.connect(lambda: self.annotate_clicked.emit(self.task.id))

        layout.addWidget(left, stretch=1)
        layout.addWidget(self.btn, stretch=0, alignment=Qt.AlignmentFlag.AlignVCenter)

    def set_selected(self, selected: bool):
        # 轻量选中态：按钮文本变化（避免依赖复杂样式）
        if selected:
            self.btn.setText("继续标注")
        else:
            self.btn.setText("标注")


class LabelInterface(QWidget):
    """标注工作台

    左侧：任务统计 + 任务列表（卡片）
    右侧：标注画布（当前仅加载图片；标注能力后续逐步接入）
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project_id: Optional[int] = None
        self.current_task_id: Optional[int] = None
        self.current_image_path: Optional[str] = None
        self._task_cards: List[TaskCard] = []

        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # 左侧侧边栏
        self.sidebar = CardWidget(self)
        self.sidebar.setFixedWidth(360)
        sideLayout = QVBoxLayout(self.sidebar)
        sideLayout.setContentsMargins(16, 16, 16, 16)
        sideLayout.setSpacing(12)

        self.statTitle = TitleLabel("任务统计", self.sidebar)
        sideLayout.addWidget(self.statTitle)

        self.statList = QListWidget(self.sidebar)
        self.statList.setFixedHeight(120)
        self.statList.itemClicked.connect(self._on_stat_clicked)
        sideLayout.addWidget(self.statList)

        self.listTitle = TitleLabel("任务列表", self.sidebar)
        sideLayout.addWidget(self.listTitle)

        # 任务列表滚动区
        self.scrollArea = QScrollArea(self.sidebar)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.scrollBody = QWidget(self.scrollArea)
        self.scrollLayout = QVBoxLayout(self.scrollBody)
        self.scrollLayout.setContentsMargins(0, 0, 0, 0)
        self.scrollLayout.setSpacing(10)
        self.scrollLayout.addStretch(1)

        self.scrollArea.setWidget(self.scrollBody)
        sideLayout.addWidget(self.scrollArea, stretch=1)

        # 右侧标注区
        self.canvasPanel = CardWidget(self)
        canvasLayout = QVBoxLayout(self.canvasPanel)
        canvasLayout.setContentsMargins(16, 16, 16, 16)
        canvasLayout.setSpacing(10)

        # 顶部工具条（后续你接入真正的标注逻辑时可以继续扩展）
        topBar = QWidget(self.canvasPanel)
        topBarLayout = QHBoxLayout(topBar)
        topBarLayout.setContentsMargins(0, 0, 0, 0)
        topBarLayout.setSpacing(10)

        self.canvasTitle = TitleLabel("画布", topBar)
        self.saveBtn = PushButton("保存", topBar)
        self.doneBtn = PrimaryPushButton("完成", topBar)

        self.saveBtn.clicked.connect(self._on_save)
        self.doneBtn.clicked.connect(self._on_done)

        topBarLayout.addWidget(self.canvasTitle, stretch=1)
        topBarLayout.addWidget(self.saveBtn)
        topBarLayout.addWidget(self.doneBtn)

        canvasLayout.addWidget(topBar)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self.canvasPanel)
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        canvasLayout.addWidget(self.view, stretch=1)

        root.addWidget(self.sidebar, stretch=0)
        root.addWidget(self.canvasPanel, stretch=1)

    # ---------------- Public API ----------------
    def set_project(self, project_id: int):
        self.project_id = project_id
        self.current_task_id = None
        self.current_image_path = None
        self.scene.clear()
        self.refresh()

    def refresh(self, status_filter: Optional[int] = None):
        if self.project_id is None:
            return

        # 1) 任务统计
        stats = DataManager.get_task_stats(self.project_id)
        self._render_stats(stats)

        # 2) 任务列表
        tasks = DataManager.get_project_media(self.project_id, status=status_filter)
        self._render_task_cards(tasks)

    # ---------------- Rendering ----------------
    def _render_stats(self, stats: dict):
        self.statList.clear()

        items = [
            ("未标注", DataManager.STATUS_UNLABELED, stats.get("unlabeled", 0)),
            ("标注中", DataManager.STATUS_IN_PROGRESS, stats.get("in_progress", 0)),
            ("已标注", DataManager.STATUS_DONE, stats.get("done", 0)),
        ]
        for text, status, count in items:
            it = QListWidgetItem(f"{text}    {count}")
            it.setData(Qt.ItemDataRole.UserRole, status)
            self.statList.addItem(it)

    def _render_task_cards(self, media_items):
        # 清空旧卡片
        for c in self._task_cards:
            c.setParent(None)
        self._task_cards.clear()

        # 清空 layout（保留最后一个 stretch）
        while self.scrollLayout.count() > 0:
            item = self.scrollLayout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # 重建
        for m in media_items:
            vm = TaskViewModel(id=m.id, file_path=m.file_path, status=m.label_status)
            card = TaskCard(vm, self.scrollBody)
            card.annotate_clicked.connect(self.open_task)
            self._task_cards.append(card)
            self.scrollLayout.addWidget(card)

        self.scrollLayout.addStretch(1)

        # 如果当前任务仍在过滤结果里，更新选中态
        self._sync_selected_state()

    def _sync_selected_state(self):
        for c in self._task_cards:
            c.set_selected(self.current_task_id == c.task.id)

    # ---------------- Actions ----------------
    def _on_stat_clicked(self, item: QListWidgetItem):
        status = item.data(Qt.ItemDataRole.UserRole)
        self.refresh(status_filter=status)

    def open_task(self, media_id: int):
        """从卡片点击进入标注（加载图片 + 标记为标注中）。"""
        if self.project_id is None:
            return

        # 找到 media
        tasks = DataManager.get_project_media(self.project_id)
        m = next((x for x in tasks if x.id == media_id), None)
        if not m:
            return

        self.current_task_id = m.id
        self.load_image(m.file_path)

        # 切到“标注中”
        if m.label_status == DataManager.STATUS_UNLABELED:
            DataManager.set_task_status(m.id, DataManager.STATUS_IN_PROGRESS)

        self.refresh()  # 统计与列表同步
        self._sync_selected_state()

    def load_image(self, image_path: str):
        self.current_image_path = image_path
        self.scene.clear()

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.canvasTitle.setText("画布（图片加载失败）")
            return

        self.canvasTitle.setText(f"画布  ·  {Path(image_path).name}")
        item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(item)
        self.view.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self.view.fitInView(item, Qt.AspectRatioMode.KeepAspectRatio)

    def _on_save(self):
        # 目前仅预留：未来你接入标注工具后，这里保存 annotation 到 DB / yolo txt
        # 现在先确保状态至少是“标注中”
        if self.current_task_id is None:
            return
        DataManager.set_task_status(self.current_task_id, DataManager.STATUS_IN_PROGRESS)
        self.refresh()

    def _on_done(self):
        # “完成”= 置为已标注
        if self.current_task_id is None:
            return
        DataManager.set_task_status(self.current_task_id, DataManager.STATUS_DONE)
        self.refresh()
        self._sync_selected_state()
