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
    QWidget,
    QVBoxLayout,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QKeySequence

from canvas import ImageCanvas


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
        self._canvas.points_cleared.connect(self._on_points_cleared)

        # 초기 이미지 로드
        if initial_image and os.path.isfile(initial_image):
            self._load_image(initial_image)

    def _setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            """
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
            """
        )
        self.addToolBar(toolbar)

        # Load Image
        load_action = QAction("Load Image", self)
        load_action.setShortcut(QKeySequence("Ctrl+O"))
        load_action.triggered.connect(self._on_load_image)
        toolbar.addAction(load_action)

        toolbar.addSeparator()

        # Point Reset
        point_reset_action = QAction("Point Reset", self)
        point_reset_action.setShortcut(QKeySequence("Ctrl+R"))
        point_reset_action.triggered.connect(self._on_point_reset)
        toolbar.addAction(point_reset_action)

        # Image Reset
        img_reset_action = QAction("Image Reset", self)
        img_reset_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        img_reset_action.triggered.connect(self._on_image_reset)
        toolbar.addAction(img_reset_action)

        toolbar.addSeparator()

        # 포인트 카운트 라벨
        self._point_count_label = QLabel("  Points: 0  ")
        self._point_count_label.setStyleSheet(
            "color: #aaa; font-size: 13px; padding: 0 8px;"
        )
        toolbar.addWidget(self._point_count_label)

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

        self._coord_label = QLabel("Ready")
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

    def _load_image(self, path: str):
        if self._canvas.load_image(path):
            filename = os.path.basename(path)
            self.setWindowTitle(f"Image Navigator - {filename}")
            self._file_label.setText(f"  {path}")
            self._update_point_count()
        else:
            QMessageBox.warning(self, "Error", f"이미지를 로드할 수 없습니다:\n{path}")

    def _on_point_reset(self):
        self._canvas.clear_points()
        self._update_point_count()

    def _on_image_reset(self):
        self._canvas.clear_all()
        self.setWindowTitle("Image Navigator")
        self._file_label.setText("")
        self._coord_label.setText("Ready")
        self._update_point_count()

    # ──────────────────── Signals ────────────────────

    def _on_coord_changed(self, x: int, y: int):
        self._coord_label.setText(f"  x: {x}  y: {y}  ")

    def _on_point_added(self, x: int, y: int):
        self._update_point_count()

    def _on_points_cleared(self):
        self._update_point_count()

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
