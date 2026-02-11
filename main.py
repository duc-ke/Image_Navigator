#!/usr/bin/env python3
"""
Image Navigator - SAM3 개발 보조 도구.

이미지를 로드하여 좌표 확인 및 포인트 마킹을 할 수 있는 데스크탑 앱.

사용법:
    python main.py
    python main.py /path/to/image.jpg
"""

import sys
import os

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QToolBar,
    QStatusBar,
    QFileDialog,
    QLabel,
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QKeySequence

from canvas import ImageCanvas, Mode


SHORTCUTS = [
    ("Ctrl+O", "이미지 로드"),
    ("P", "Hand / Point 모드 전환"),
    ("Ctrl+R", "모든 포인트 리셋"),
    ("Ctrl+Shift+R", "Fit View (원본 비율)"),
    ("Ctrl+/", "단축키 가이드"),
    ("좌클릭 (Hand)", "패닝 (이미지 이동)"),
    ("좌클릭 (Point)", "포인트 마킹"),
    ("우클릭", "최근 포인트 취소 (Undo)"),
    ("더블클릭 (Hand)", "Fit View (원본 비율)"),
    ("마우스 휠", "줌 인/아웃"),
    ("드래그 앤 드롭", "이미지 파일 로드"),
]


class ShortcutDialog(QDialog):
    """단축키 가이드 팝업."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shortcut Guide")
        self.setMinimumSize(420, 400)
        self.setStyleSheet(
            """
            QDialog {
                background: #353535;
            }
            QTableWidget {
                background: #2b2b2b;
                color: #ddd;
                border: none;
                gridline-color: #444;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px 12px;
            }
            QHeaderView::section {
                background: #3c3c3c;
                color: #aaa;
                border: 1px solid #444;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        table = QTableWidget(len(SHORTCUTS), 2)
        table.setHorizontalHeaderLabels(["Shortcut", "Action"])
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for row, (key, desc) in enumerate(SHORTCUTS):
            key_item = QTableWidgetItem(key)
            key_item.setFont(QFont("Monospace", 13))
            table.setItem(row, 0, key_item)
            table.setItem(row, 1, QTableWidgetItem(desc))

        layout.addWidget(table)


TOOLBAR_STYLE = """
    QToolBar {
        spacing: 8px;
        padding: 4px;
        background: #2b2b2b;
        border-bottom: 1px solid #444;
    }
    QToolButton {
        color: #ddd;
        background: #3c3c3c;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 6px 14px;
        font-size: 13px;
    }
    QToolButton:hover {
        background: #4a4a4a;
        border-color: #777;
    }
    QToolButton:pressed {
        background: #555;
    }
    QToolButton:checked {
        background: #c83232;
        border-color: #e05050;
        color: #fff;
    }
"""


class MainWindow(QMainWindow):
    def __init__(self, initial_image: str | None = None):
        super().__init__()
        self.setWindowTitle("Image Navigator")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

        # Canvas
        self._canvas = ImageCanvas()
        self.setCentralWidget(self._canvas)

        # Toolbar
        self._setup_toolbar()

        # Status bar
        self._setup_statusbar()

        # 시그널 연결
        self._canvas.coord_changed.connect(self._on_coord_changed)
        self._canvas.point_added.connect(self._on_point_added)
        self._canvas.point_undone.connect(self._update_point_count)
        self._canvas.points_cleared.connect(self._on_points_cleared)
        self._canvas.image_dropped.connect(self._on_image_dropped)
        self._canvas.mode_changed.connect(self._on_mode_changed)

        # 초기 이미지 로드
        if initial_image and os.path.isfile(initial_image):
            self._load_image(initial_image)

    def _setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(TOOLBAR_STYLE)
        self.addToolBar(toolbar)

        # Load Image
        load_action = QAction("Load Image", self)
        load_action.setShortcut(QKeySequence("Ctrl+O"))
        load_action.triggered.connect(self._on_load_image)
        toolbar.addAction(load_action)

        toolbar.addSeparator()

        # Point 모드 토글 (checkable)
        self._point_action = QAction("Point", self)
        self._point_action.setCheckable(True)
        self._point_action.setShortcut(QKeySequence("P"))
        self._point_action.triggered.connect(self._on_toggle_mode)
        toolbar.addAction(self._point_action)

        toolbar.addSeparator()

        # All Points Reset
        point_reset_action = QAction("All Points Reset", self)
        point_reset_action.setShortcut(QKeySequence("Ctrl+R"))
        point_reset_action.triggered.connect(self._on_point_reset)
        toolbar.addAction(point_reset_action)

        # Fit View (기존 Image Reset → 이미지 비율 원본으로 리셋)
        fit_action = QAction("Fit View", self)
        fit_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        fit_action.triggered.connect(self._on_fit_view)
        toolbar.addAction(fit_action)

        toolbar.addSeparator()

        # 포인트 카운트 라벨
        self._point_count_label = QLabel("  Points: 0  ")
        self._point_count_label.setStyleSheet(
            "color: #aaa; font-size: 13px; padding: 0 8px;"
        )
        toolbar.addWidget(self._point_count_label)

        # 모드 표시 라벨
        self._mode_label = QLabel("  Hand  ")
        self._mode_label.setStyleSheet(
            "color: #8cf; font-size: 13px; font-weight: bold; padding: 0 8px;"
        )
        toolbar.addWidget(self._mode_label)

        # 스페이서
        spacer = QLabel()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Shortcut Guide
        shortcut_action = QAction("Shortcuts", self)
        shortcut_action.setShortcut(QKeySequence("Ctrl+/"))
        shortcut_action.triggered.connect(self._on_show_shortcuts)
        toolbar.addAction(shortcut_action)

    def _setup_statusbar(self):
        status_bar = QStatusBar()
        status_bar.setStyleSheet(
            """
            QStatusBar {
                background: #2b2b2b;
                color: #aaa;
                border-top: 1px solid #444;
                font-size: 12px;
            }
            """
        )
        self.setStatusBar(status_bar)

        self._coord_label = QLabel("Ready — Load an image or drag & drop")
        self._coord_label.setFont(QFont("Monospace", 11))
        status_bar.addPermanentWidget(self._coord_label)

        self._file_label = QLabel("")
        status_bar.addWidget(self._file_label)

    # ──────────────────── Actions ────────────────────

    def _on_load_image(self):
        if self._canvas.has_image():
            reply = QMessageBox.question(
                self,
                "Load Image",
                "현재 이미지를 교체하시겠습니까?\n(기존 포인트는 삭제됩니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp);;All Files (*)",
        )
        if file_path:
            self._load_image(file_path)

    def _on_image_dropped(self, path: str):
        """드래그 앤 드롭으로 이미지 로드."""
        ext = os.path.splitext(path)[1].lower()
        supported = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
        if ext not in supported:
            QMessageBox.warning(
                self, "Error", f"지원하지 않는 파일 형식: {ext}\n{path}"
            )
            return
        self._load_image(path)

    def _load_image(self, path: str):
        if self._canvas.load_image(path):
            filename = os.path.basename(path)
            self.setWindowTitle(f"Image Navigator - {filename}")
            self._file_label.setText(f"  {path}")
            self._update_point_count()
        else:
            QMessageBox.warning(self, "Error", f"이미지를 로드할 수 없습니다:\n{path}")

    def _on_toggle_mode(self):
        self._canvas.toggle_mode()

    def _on_point_reset(self):
        self._canvas.clear_points()
        self._update_point_count()

    def _on_fit_view(self):
        self._canvas.fit_view()

    def _on_show_shortcuts(self):
        dialog = ShortcutDialog(self)
        dialog.show()

    # ──────────────────── Signals ────────────────────

    def _on_coord_changed(self, x: int, y: int):
        self._coord_label.setText(f"  x: {x}  y: {y}  ")

    def _on_point_added(self, x: int, y: int):
        self._update_point_count()

    def _on_points_cleared(self):
        self._update_point_count()

    def _on_mode_changed(self, mode_str: str):
        if mode_str == "hand":
            self._mode_label.setText("  Hand  ")
            self._mode_label.setStyleSheet(
                "color: #8cf; font-size: 13px; font-weight: bold; padding: 0 8px;"
            )
            self._point_action.setChecked(False)
        else:
            self._mode_label.setText("  Point  ")
            self._mode_label.setStyleSheet(
                "color: #f66; font-size: 13px; font-weight: bold; padding: 0 8px;"
            )
            self._point_action.setChecked(True)

    def _update_point_count(self):
        count = len(self._canvas.get_points())
        self._point_count_label.setText(f"  Points: {count}  ")


def main():
    app = QApplication(sys.argv)

    # 다크 테마 기본 적용
    app.setStyle("Fusion")
    from PySide6.QtGui import QPalette, QColor

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(200, 200, 200))
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(200, 200, 200))
    palette.setColor(QPalette.ColorRole.Text, QColor(200, 200, 200))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(200, 200, 200))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 50, 50))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    # 커맨드라인 인자로 이미지 경로 받기
    initial_image = sys.argv[1] if len(sys.argv) > 1 else None

    window = MainWindow(initial_image=initial_image)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
