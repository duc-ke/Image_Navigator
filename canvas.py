"""
ImageCanvas - QGraphicsView 기반 이미지 캔버스 위젯.

기능:
- 이미지 로드 및 표시
- 실시간 마우스 좌표 표시 (커서 옆 오버레이)
- 클릭으로 포인트 마킹 (빨간 점 + 좌표 텍스트)
- 마우스 휠 줌 인/아웃
- 더블클릭 원본 크기 복원
"""

from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
    QGraphicsRectItem,
)
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import (
    QPixmap,
    QPen,
    QBrush,
    QColor,
    QFont,
    QWheelEvent,
    QMouseEvent,
)


POINT_RADIUS = 4
ZOOM_FACTOR = 1.15
MIN_ZOOM = 0.05
MAX_ZOOM = 50.0


class CoordOverlay:
    """마우스 커서 옆에 좌표를 표시하는 오버레이."""

    def __init__(self, scene: QGraphicsScene):
        self._bg = QGraphicsRectItem()
        self._bg.setBrush(QBrush(QColor(0, 0, 0, 180)))
        self._bg.setPen(QPen(Qt.NoPen))
        self._bg.setZValue(1000)
        self._bg.setVisible(False)
        scene.addItem(self._bg)

        self._text = QGraphicsTextItem()
        self._text.setDefaultTextColor(QColor(255, 255, 255))
        self._text.setFont(QFont("Monospace", 10))
        self._text.setZValue(1001)
        self._text.setVisible(False)
        scene.addItem(self._text)

    def update(self, scene_pos: QPointF, img_x: int, img_y: int):
        label = f"({img_x}, {img_y})"
        self._text.setPlainText(label)

        offset_x, offset_y = 15, -10
        self._text.setPos(scene_pos.x() + offset_x, scene_pos.y() + offset_y)

        rect = self._text.boundingRect()
        padding = 3
        self._bg.setRect(
            scene_pos.x() + offset_x - padding,
            scene_pos.y() + offset_y - padding,
            rect.width() + padding * 2,
            rect.height() + padding * 2,
        )
        self._bg.setVisible(True)
        self._text.setVisible(True)

    def hide(self):
        self._bg.setVisible(False)
        self._text.setVisible(False)

    def remove(self, scene: QGraphicsScene):
        scene.removeItem(self._bg)
        scene.removeItem(self._text)


class PointMarker:
    """이미지 위에 표시되는 포인트 마커 (원 + 좌표 텍스트)."""

    def __init__(self, scene: QGraphicsScene, img_x: int, img_y: int):
        self.img_x = img_x
        self.img_y = img_y

        # 빨간 원
        self._circle = QGraphicsEllipseItem(
            img_x - POINT_RADIUS,
            img_y - POINT_RADIUS,
            POINT_RADIUS * 2,
            POINT_RADIUS * 2,
        )
        self._circle.setPen(QPen(QColor(255, 50, 50), 1.5))
        self._circle.setBrush(QBrush(QColor(255, 50, 50, 200)))
        self._circle.setZValue(100)
        scene.addItem(self._circle)

        # 좌표 라벨 배경
        label = f"({img_x}, {img_y})"
        self._label_text = QGraphicsTextItem()
        self._label_text.setPlainText(label)
        self._label_text.setDefaultTextColor(QColor(255, 255, 255))
        self._label_text.setFont(QFont("Monospace", 8))
        self._label_text.setZValue(102)
        self._label_text.setPos(img_x + POINT_RADIUS + 4, img_y - 8)
        scene.addItem(self._label_text)

        self._label_bg = QGraphicsRectItem()
        self._label_bg.setBrush(QBrush(QColor(200, 50, 50, 200)))
        self._label_bg.setPen(QPen(Qt.NoPen))
        self._label_bg.setZValue(101)
        rect = self._label_text.boundingRect()
        pad = 2
        self._label_bg.setRect(
            img_x + POINT_RADIUS + 4 - pad,
            img_y - 8 - pad,
            rect.width() + pad * 2,
            rect.height() + pad * 2,
        )
        scene.addItem(self._label_bg)

    def remove(self, scene: QGraphicsScene):
        scene.removeItem(self._circle)
        scene.removeItem(self._label_text)
        scene.removeItem(self._label_bg)


class ImageCanvas(QGraphicsView):
    """이미지 표시 + 인터랙티브 좌표/포인트 캔버스."""

    coord_changed = Signal(int, int)  # (x, y) 이미지 좌표 변경 시그널
    point_added = Signal(int, int)    # 포인트 추가 시그널
    points_cleared = Signal()         # 포인트 전체 삭제 시그널

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # 설정
        self.setMouseTracking(True)
        self.setRenderHint(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))

        # 상태
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._markers: list[PointMarker] = []
        self._coord_overlay = CoordOverlay(self._scene)
        self._current_zoom = 1.0
        self._has_image = False
        self._is_panning = False
        self._pan_start = QPointF()

    # ──────────────────── Public API ────────────────────

    def load_image(self, path: str) -> bool:
        """이미지 파일을 로드하여 캔버스에 표시."""
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return False

        self.clear_all()

        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._pixmap_item.setZValue(0)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())

        self._has_image = True
        self._current_zoom = 1.0
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        return True

    def clear_points(self):
        """모든 포인트 마커를 제거."""
        for marker in self._markers:
            marker.remove(self._scene)
        self._markers.clear()
        self.points_cleared.emit()

    def clear_all(self):
        """이미지 + 포인트 모두 제거."""
        self._coord_overlay.hide()
        for marker in self._markers:
            marker.remove(self._scene)
        self._markers.clear()

        if self._pixmap_item is not None:
            self._scene.removeItem(self._pixmap_item)
            self._pixmap_item = None

        self._has_image = False
        self._current_zoom = 1.0
        self.resetTransform()

    def get_points(self) -> list[tuple[int, int]]:
        """저장된 포인트 좌표 리스트 반환."""
        return [(m.img_x, m.img_y) for m in self._markers]

    def has_image(self) -> bool:
        return self._has_image

    # ──────────────────── Mouse Events ────────────────────

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            return

        if not self._has_image:
            self._coord_overlay.hide()
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        img_x = int(scene_pos.x())
        img_y = int(scene_pos.y())

        pixmap = self._pixmap_item.pixmap()
        if 0 <= img_x < pixmap.width() and 0 <= img_y < pixmap.height():
            self._coord_overlay.update(scene_pos, img_x, img_y)
            self.coord_changed.emit(img_x, img_y)
        else:
            self._coord_overlay.hide()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        # 중간 버튼(휠 클릭) 또는 Ctrl+좌클릭으로 패닝
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() != Qt.MouseButton.LeftButton or not self._has_image:
            super().mousePressEvent(event)
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        img_x = int(scene_pos.x())
        img_y = int(scene_pos.y())

        pixmap = self._pixmap_item.pixmap()
        if 0 <= img_x < pixmap.width() and 0 <= img_y < pixmap.height():
            marker = PointMarker(self._scene, img_x, img_y)
            self._markers.append(marker)
            self.point_added.emit(img_x, img_y)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """더블클릭 시 원본 크기(fit in view)로 복원."""
        if self._has_image and event.button() == Qt.MouseButton.LeftButton:
            self._current_zoom = 1.0
            self.resetTransform()
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        """마우스 휠로 줌 인/아웃."""
        if not self._has_image:
            return

        if event.angleDelta().y() > 0:
            factor = ZOOM_FACTOR
        else:
            factor = 1.0 / ZOOM_FACTOR

        new_zoom = self._current_zoom * factor
        if MIN_ZOOM <= new_zoom <= MAX_ZOOM:
            self._current_zoom = new_zoom
            self.scale(factor, factor)

    def leaveEvent(self, event):
        self._coord_overlay.hide()
        super().leaveEvent(event)
