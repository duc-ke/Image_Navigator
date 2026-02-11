"""
ImageCanvas - QGraphicsView 기반 이미지 캔버스 위젯.

기능:
- 이미지 로드 및 표시 (파일 선택 / 드래그 앤 드롭)
- 실시간 마우스 좌표 표시 (커서 옆 오버레이)
- 십자선 가이드
- 클릭으로 포인트 마킹 (빨간 점 + 좌표 텍스트)
- 우클릭으로 최근 포인트 하나씩 취소
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
    QGraphicsLineItem,
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
    QDragEnterEvent,
    QDropEvent,
)


POINT_RADIUS = 4
ZOOM_FACTOR = 1.15
MIN_ZOOM = 0.05
MAX_ZOOM = 50.0


class CoordOverlay:
    """마우스 커서 옆에 좌표를 표시하는 오버레이 (줌 무관 고정 크기)."""

    def __init__(self, scene: QGraphicsScene):
        self._bg = QGraphicsRectItem()
        self._bg.setBrush(QBrush(QColor(0, 0, 0, 180)))
        self._bg.setPen(QPen(Qt.NoPen))
        self._bg.setZValue(1000)
        self._bg.setVisible(False)
        self._bg.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIgnoresTransformations)
        scene.addItem(self._bg)

        self._text = QGraphicsTextItem()
        self._text.setDefaultTextColor(QColor(255, 255, 255))
        self._text.setFont(QFont("Monospace", 13))
        self._text.setZValue(1001)
        self._text.setVisible(False)
        self._text.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIgnoresTransformations)
        scene.addItem(self._text)

    def update(self, scene_pos: QPointF, img_x: int, img_y: int):
        label = f"({img_x}, {img_y})"
        self._text.setPlainText(label)

        self._text.setPos(scene_pos)
        self._bg.setPos(scene_pos)

        rect = self._text.boundingRect()
        offset_x, offset_y = 18, -12
        self._text.setTransformOriginPoint(0, 0)
        self._bg.setTransformOriginPoint(0, 0)

        # ItemIgnoresTransformations이므로 offset은 뷰포트 픽셀 단위
        self._text.setPos(scene_pos)
        self._bg.setPos(scene_pos)

        padding = 3
        self._bg.setRect(
            offset_x - padding,
            offset_y - padding,
            rect.width() + padding * 2,
            rect.height() + padding * 2,
        )
        # text도 같은 offset
        self._text.setPos(scene_pos)
        self._bg.setPos(scene_pos)
        # offset을 prepend transform으로 적용
        from PySide6.QtGui import QTransform

        t = QTransform()
        t.translate(offset_x, offset_y)
        self._text.setTransform(t)

        t_bg = QTransform()
        t_bg.translate(0, 0)
        self._bg.setTransform(t_bg)

        self._bg.setVisible(True)
        self._text.setVisible(True)

    def hide(self):
        self._bg.setVisible(False)
        self._text.setVisible(False)

    def remove(self, scene: QGraphicsScene):
        scene.removeItem(self._bg)
        scene.removeItem(self._text)


class Crosshair:
    """마우스 위치에 표시되는 십자선 가이드."""

    def __init__(self, scene: QGraphicsScene):
        pen = QPen(QColor(255, 255, 255, 100), 0.5, Qt.PenStyle.DashLine)

        self._h_line = QGraphicsLineItem()
        self._h_line.setPen(pen)
        self._h_line.setZValue(999)
        self._h_line.setVisible(False)
        scene.addItem(self._h_line)

        self._v_line = QGraphicsLineItem()
        self._v_line.setPen(pen)
        self._v_line.setZValue(999)
        self._v_line.setVisible(False)
        scene.addItem(self._v_line)

    def update(self, scene_pos: QPointF, img_w: int, img_h: int):
        x, y = scene_pos.x(), scene_pos.y()
        self._h_line.setLine(0, y, img_w, y)
        self._v_line.setLine(x, 0, x, img_h)
        self._h_line.setVisible(True)
        self._v_line.setVisible(True)

    def hide(self):
        self._h_line.setVisible(False)
        self._v_line.setVisible(False)

    def remove(self, scene: QGraphicsScene):
        scene.removeItem(self._h_line)
        scene.removeItem(self._v_line)


class PointMarker:
    """이미지 위에 표시되는 포인트 마커 (원 + 좌표 텍스트, 줌 무관 고정 크기)."""

    def __init__(self, scene: QGraphicsScene, img_x: int, img_y: int):
        self.img_x = img_x
        self.img_y = img_y

        # 빨간 원 — 줌 무관
        r = POINT_RADIUS
        self._circle = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
        self._circle.setPos(img_x, img_y)
        self._circle.setPen(QPen(QColor(255, 50, 50), 1.5))
        self._circle.setBrush(QBrush(QColor(255, 50, 50, 200)))
        self._circle.setZValue(100)
        self._circle.setFlag(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        scene.addItem(self._circle)

        # 좌표 라벨 — 줌 무관
        label = f"({img_x}, {img_y})"
        self._label_text = QGraphicsTextItem()
        self._label_text.setPlainText(label)
        self._label_text.setDefaultTextColor(QColor(255, 255, 255))
        self._label_text.setFont(QFont("Monospace", 13))
        self._label_text.setZValue(102)
        self._label_text.setPos(img_x, img_y)
        self._label_text.setFlag(
            QGraphicsTextItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        scene.addItem(self._label_text)

        # 라벨 배경 — 줌 무관
        self._label_bg = QGraphicsRectItem()
        self._label_bg.setBrush(QBrush(QColor(200, 50, 50, 200)))
        self._label_bg.setPen(QPen(Qt.NoPen))
        self._label_bg.setZValue(101)
        self._label_bg.setPos(img_x, img_y)
        self._label_bg.setFlag(
            QGraphicsRectItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        scene.addItem(self._label_bg)

        # offset (뷰포트 픽셀 단위)
        from PySide6.QtGui import QTransform

        text_offset_x = POINT_RADIUS + 6
        text_offset_y = -8

        t = QTransform()
        t.translate(text_offset_x, text_offset_y)
        self._label_text.setTransform(t)

        rect = self._label_text.boundingRect()
        pad = 2
        self._label_bg.setRect(
            -pad,
            -pad,
            rect.width() + pad * 2,
            rect.height() + pad * 2,
        )
        t_bg = QTransform()
        t_bg.translate(text_offset_x - pad, text_offset_y - pad)
        self._label_bg.setTransform(t_bg)

    def remove(self, scene: QGraphicsScene):
        scene.removeItem(self._circle)
        scene.removeItem(self._label_text)
        scene.removeItem(self._label_bg)


class ImageCanvas(QGraphicsView):
    """이미지 표시 + 인터랙티브 좌표/포인트 캔버스."""

    coord_changed = Signal(int, int)  # (x, y) 이미지 좌표 변경 시그널
    point_added = Signal(int, int)    # 포인트 추가 시그널
    point_undone = Signal()           # 포인트 하나 취소 시그널
    points_cleared = Signal()         # 포인트 전체 삭제 시그널
    image_dropped = Signal(str)       # 드래그앤드롭 이미지 경로 시그널

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

        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)

        # 상태
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._markers: list[PointMarker] = []
        self._coord_overlay = CoordOverlay(self._scene)
        self._crosshair = Crosshair(self._scene)
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

    def undo_last_point(self):
        """가장 최근 포인트 하나를 제거."""
        if self._markers:
            marker = self._markers.pop()
            marker.remove(self._scene)
            self.point_undone.emit()

    def clear_all(self):
        """이미지 + 포인트 모두 제거."""
        self._coord_overlay.hide()
        self._crosshair.hide()
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

    # ──────────────────── Drag & Drop ────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            path = url.toLocalFile()
            if path:
                self.image_dropped.emit(path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

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
            self._crosshair.hide()
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        img_x = int(scene_pos.x())
        img_y = int(scene_pos.y())

        pixmap = self._pixmap_item.pixmap()
        if 0 <= img_x < pixmap.width() and 0 <= img_y < pixmap.height():
            self._coord_overlay.update(scene_pos, img_x, img_y)
            self._crosshair.update(scene_pos, pixmap.width(), pixmap.height())
            self.coord_changed.emit(img_x, img_y)
        else:
            self._coord_overlay.hide()
            self._crosshair.hide()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        # 우클릭 → 최근 포인트 취소
        if event.button() == Qt.MouseButton.RightButton and self._has_image:
            self.undo_last_point()
            return

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
        self._crosshair.hide()
        super().leaveEvent(event)
