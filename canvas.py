"""
ImageCanvas - QGraphicsView 기반 이미지 캔버스 위젯.

기능:
- 이미지 로드 및 표시 (파일 선택 / 드래그 앤 드롭)
- 빈 화면에 안내 문구 표시
- Hand 모드 / Point 모드 전환
- 실시간 마우스 좌표 표시 (커서 옆 오버레이)
- 십자선 가이드
- 클릭으로 포인트 마킹 (빨간 점 + 좌표 텍스트)
- 우클릭으로 최근 포인트 하나씩 취소
- 마우스 휠 줌 인/아웃
- 더블클릭 원본 크기 복원 (Hand 모드에서만)
"""

from enum import Enum

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
    QPainter,
    QCursor,
    QTransform,
)


POINT_RADIUS = 4
ZOOM_FACTOR = 1.15
MIN_ZOOM = 0.05
MAX_ZOOM = 50.0


class Mode(Enum):
    HAND = "hand"
    POINT = "point"
    BOX = "box"


def _make_point_cursor() -> QCursor:
    """빨간 십자선 커서 생성."""
    size = 24
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(255, 50, 50, 200), 1.2)
    painter.setPen(pen)
    center = size // 2
    arm = 8
    # 십자선
    painter.drawLine(center - arm, center, center - 2, center)
    painter.drawLine(center + 2, center, center + arm, center)
    painter.drawLine(center, center - arm, center, center - 2)
    painter.drawLine(center, center + 2, center, center + arm)
    # 중심 점
    painter.setPen(QPen(QColor(255, 50, 50, 220), 1.5))
    painter.drawPoint(center, center)
    painter.end()
    return QCursor(pm, center, center)


def _make_box_cursor() -> QCursor:
    """초록색 십자선 커서 생성 (Box 모드용)."""
    size = 24
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(50, 255, 50, 200), 1.2)
    painter.setPen(pen)
    center = size // 2
    arm = 8
    # 십자선
    painter.drawLine(center - arm, center, center - 2, center)
    painter.drawLine(center + 2, center, center + arm, center)
    painter.drawLine(center, center - arm, center, center - 2)
    painter.drawLine(center, center + 2, center, center + arm)
    # 중심 점
    painter.setPen(QPen(QColor(50, 255, 50, 220), 1.5))
    painter.drawPoint(center, center)
    painter.end()
    return QCursor(pm, center, center)


class CoordOverlay:
    """마우스 커서 옆에 좌표를 표시하는 오버레이 (줌 무관 고정 크기)."""

    def __init__(self, scene: QGraphicsScene):
        self._bg = QGraphicsRectItem()
        self._bg.setBrush(QBrush(QColor(0, 0, 0, 80)))
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
        offset_x, offset_y = 20, -40

        padding = 3
        self._bg.setRect(
            offset_x - padding,
            offset_y - padding,
            rect.width() + padding * 2,
            rect.height() + padding * 2,
        )

        t = QTransform()
        t.translate(offset_x, offset_y)
        self._text.setTransform(t)

        t_bg = QTransform()
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
        pen = QPen(QColor(255, 255, 255, 100), 3.5, Qt.PenStyle.DashLine)

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
        self._label_bg.setBrush(QBrush(QColor(200, 50, 50, 80)))
        self._label_bg.setPen(QPen(Qt.NoPen))
        self._label_bg.setZValue(101)
        self._label_bg.setPos(img_x, img_y)
        self._label_bg.setFlag(
            QGraphicsRectItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        scene.addItem(self._label_bg)

        # offset (뷰포트 픽셀 단위)
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


class BoxMarker:
    """Bounding box marker (green border + coordinate labels)."""

    def __init__(self, scene: QGraphicsScene, x1: int, y1: int, x2: int, y2: int):
        # Normalize coordinates (top-left to bottom-right)
        self.x1 = min(x1, x2)
        self.y1 = min(y1, y2)
        self.x2 = max(x1, x2)
        self.y2 = max(y1, y2)
        self.width = abs(x2 - x1)
        self.height = abs(y2 - y1)

        # Green rectangle (3.5px border, transparent fill)
        # Box follows image zoom - NO ItemIgnoresTransformations
        self._rect = QGraphicsRectItem(self.x1, self.y1, self.width, self.height)
        self._rect.setPen(QPen(QColor(50, 255, 50), 3.5))
        self._rect.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self._rect.setZValue(100)
        scene.addItem(self._rect)

        # Coordinate label - show all 4 corners + W, H with labels
        label = (
            f"Xmin,Ymin: ({self.x1},{self.y1})\n"
            f"Xmax,Ymin: ({self.x2},{self.y1})\n"
            f"Xmin,Ymax: ({self.x1},{self.y2})\n"
            f"Xmax,Ymax: ({self.x2},{self.y2})\n"
            f"W:{self.width} H:{self.height}"
        )
        self._label_text = QGraphicsTextItem()
        self._label_text.setPlainText(label)
        self._label_text.setDefaultTextColor(QColor(255, 255, 255))
        self._label_text.setFont(QFont("Monospace", 11))
        self._label_text.setZValue(102)
        self._label_text.setPos(self.x1, self.y1)
        self._label_text.setFlag(
            QGraphicsTextItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        scene.addItem(self._label_text)

        # Label background (green) - more transparent
        self._label_bg = QGraphicsRectItem()
        self._label_bg.setBrush(QBrush(QColor(50, 200, 50, 80)))
        self._label_bg.setPen(QPen(Qt.NoPen))
        self._label_bg.setZValue(101)
        self._label_bg.setPos(self.x1, self.y1)
        self._label_bg.setFlag(
            QGraphicsRectItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        scene.addItem(self._label_bg)

        # Position label with offset (viewport pixels) - above box top-left corner
        text_offset_x = 6
        text_offset_y = -80

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
        scene.removeItem(self._rect)
        scene.removeItem(self._label_text)
        scene.removeItem(self._label_bg)


class ImageCanvas(QGraphicsView):
    """이미지 표시 + 인터랙티브 좌표/포인트 캔버스."""

    coord_changed = Signal(int, int)  # (x, y) 이미지 좌표 변경 시그널
    point_added = Signal(int, int)    # 포인트 추가 시그널
    point_undone = Signal()           # 포인트 하나 취소 시그널
    points_cleared = Signal()         # 포인트 전체 삭제 시그널
    image_dropped = Signal(str)       # 드래그앤드롭 이미지 경로 시그널
    mode_changed = Signal(str)        # 모드 변경 시그널 ("hand" / "point")

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

        # 모드
        self._mode = Mode.HAND
        self._point_cursor = _make_point_cursor()
        self._box_cursor = _make_box_cursor()

        # Box 모드 상태
        self._box_start: QPointF | None = None
        self._box_temp_point: QGraphicsEllipseItem | None = None
        self._box_preview: QGraphicsRectItem | None = None
        self._box_markers: list[BoxMarker] = []

        # 통합 Undo를 위한 히스토리
        self._marker_history: list[PointMarker | BoxMarker] = []

        # 빈 화면 안내 텍스트
        self._placeholder = QGraphicsTextItem()
        self._placeholder.setPlainText("Drop image here\nor click Load Image")
        self._placeholder.setDefaultTextColor(QColor(255, 255, 255, 60))
        self._placeholder.setFont(QFont("Sans", 28))
        self._placeholder.setZValue(0)
        self._placeholder.setFlag(
            QGraphicsTextItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        self._scene.addItem(self._placeholder)
        self._center_placeholder()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._has_image:
            self._center_placeholder()

    def _center_placeholder(self):
        rect = self._placeholder.boundingRect()
        vp = self.viewport().rect()
        scene_center = self.mapToScene(vp.center())
        self._placeholder.setPos(
            scene_center.x() - rect.width() / 2,
            scene_center.y() - rect.height() / 2,
        )

    # ──────────────────── Mode ────────────────────

    @property
    def mode(self) -> Mode:
        return self._mode

    def set_mode(self, mode: Mode):
        # Cleanup box state when leaving BOX mode
        if self._mode == Mode.BOX:
            self._cleanup_box_state()

        self._mode = mode
        if mode == Mode.HAND:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif mode == Mode.POINT:
            self.setCursor(self._point_cursor)
        else:  # Mode.BOX
            self.setCursor(self._box_cursor)
        self.mode_changed.emit(mode.value)

    def toggle_mode(self):
        if self._mode == Mode.HAND:
            self.set_mode(Mode.POINT)
        elif self._mode == Mode.POINT:
            self.set_mode(Mode.BOX)
        else:  # Mode.BOX
            self.set_mode(Mode.HAND)

    # ──────────────────── Box Mode Helpers ────────────────────

    def _create_temp_point(self, x: int, y: int):
        """Create green temporary point for box start."""
        r = POINT_RADIUS
        self._box_temp_point = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
        self._box_temp_point.setPos(x, y)
        self._box_temp_point.setPen(QPen(QColor(50, 255, 50), 1.5))
        self._box_temp_point.setBrush(QBrush(QColor(50, 255, 50, 200)))
        self._box_temp_point.setZValue(99)
        self._box_temp_point.setFlag(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        self._scene.addItem(self._box_temp_point)

    def _create_box_preview(self):
        """Create preview rectangle for box mode."""
        self._box_preview = QGraphicsRectItem()
        self._box_preview.setPen(QPen(QColor(50, 255, 50, 150), 3.5))
        self._box_preview.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self._box_preview.setZValue(99)
        # No ItemIgnoresTransformations - box follows image zoom
        self._scene.addItem(self._box_preview)

    def _update_box_preview(self, start: QPointF, current: QPointF):
        """Update preview box from start to current position."""
        x1, y1 = int(start.x()), int(start.y())
        x2, y2 = int(current.x()), int(current.y())
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        # Use scene coordinates directly
        self._box_preview.setRect(left, top, width, height)
        self._box_preview.setVisible(True)

    def _cleanup_box_state(self):
        """Clear box mode temporary state."""
        self._box_start = None
        if self._box_temp_point:
            self._scene.removeItem(self._box_temp_point)
            self._box_temp_point = None
        if self._box_preview:
            self._box_preview.setVisible(False)

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

        self._placeholder.setVisible(False)

        self._has_image = True
        self._current_zoom = 1.0
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        return True

    def fit_view(self):
        """이미지를 뷰에 맞게 리셋 (원본 비율 Fit)."""
        if self._has_image and self._pixmap_item:
            self._current_zoom = 1.0
            self.resetTransform()
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def clear_points(self):
        """Clear all markers (points and boxes)."""
        for marker in self._markers:
            marker.remove(self._scene)
        self._markers.clear()

        for marker in self._box_markers:
            marker.remove(self._scene)
        self._box_markers.clear()

        self._marker_history.clear()
        self.points_cleared.emit()

    def undo_last_marker(self):
        """Remove most recent marker (Point or Box)."""
        if not self._marker_history:
            return

        marker = self._marker_history.pop()

        if isinstance(marker, PointMarker):
            self._markers.remove(marker)
        elif isinstance(marker, BoxMarker):
            self._box_markers.remove(marker)

        marker.remove(self._scene)
        self.point_undone.emit()

    def clear_all(self):
        """이미지 + 포인트 모두 제거."""
        self._coord_overlay.hide()
        self._crosshair.hide()
        for marker in self._markers:
            marker.remove(self._scene)
        self._markers.clear()

        for marker in self._box_markers:
            marker.remove(self._scene)
        self._box_markers.clear()

        self._marker_history.clear()
        self._cleanup_box_state()

        if self._pixmap_item is not None:
            self._scene.removeItem(self._pixmap_item)
            self._pixmap_item = None

        self._has_image = False
        self._current_zoom = 1.0
        self.resetTransform()

        self._placeholder.setVisible(True)
        self._center_placeholder()

    def get_points(self) -> list[tuple[int, int]]:
        """저장된 포인트 좌표 리스트 반환."""
        return [(m.img_x, m.img_y) for m in self._markers]

    def get_boxes(self) -> list[tuple[int, int, int, int]]:
        """Return box coordinates as (x1, y1, x2, y2) list."""
        return [(b.x1, b.y1, b.x2, b.y2) for b in self._box_markers]

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

            # Box mode: update preview if first click done
            if self._mode == Mode.BOX and self._box_start is not None:
                self._update_box_preview(self._box_start, scene_pos)
        else:
            self._coord_overlay.hide()
            self._crosshair.hide()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if not self._has_image:
            super().mousePressEvent(event)
            return

        # 우클릭 → Box 취소 또는 마커 삭제
        if event.button() == Qt.MouseButton.RightButton:
            # Box mode: cancel in-progress box
            if self._mode == Mode.BOX and self._box_start is not None:
                self._cleanup_box_state()
            else:
                # Undo last marker (Point or Box)
                self.undo_last_marker()
            return

        # Ctrl+좌클릭 또는 중간 버튼 → 패닝 (양쪽 모드 공통)
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        # ── Point 모드 ──
        if self._mode == Mode.POINT:
            if event.button() == Qt.MouseButton.LeftButton:
                scene_pos = self.mapToScene(event.position().toPoint())
                img_x = int(scene_pos.x())
                img_y = int(scene_pos.y())
                pixmap = self._pixmap_item.pixmap()
                if 0 <= img_x < pixmap.width() and 0 <= img_y < pixmap.height():
                    marker = PointMarker(self._scene, img_x, img_y)
                    self._markers.append(marker)
                    self._marker_history.append(marker)
                    self.point_added.emit(img_x, img_y)
                return
            super().mousePressEvent(event)
            return

        # ── Box 모드 ──
        if self._mode == Mode.BOX:
            if event.button() == Qt.MouseButton.LeftButton:
                scene_pos = self.mapToScene(event.position().toPoint())
                img_x = int(scene_pos.x())
                img_y = int(scene_pos.y())
                pixmap = self._pixmap_item.pixmap()

                if not (0 <= img_x < pixmap.width() and 0 <= img_y < pixmap.height()):
                    return

                if self._box_start is None:
                    # First click: start box
                    self._box_start = QPointF(img_x, img_y)
                    self._create_temp_point(img_x, img_y)
                    self._create_box_preview()
                else:
                    # Second click: complete box
                    x1 = int(self._box_start.x())
                    y1 = int(self._box_start.y())

                    if img_x != x1 or img_y != y1:
                        marker = BoxMarker(self._scene, x1, y1, img_x, img_y)
                        self._box_markers.append(marker)
                        self._marker_history.append(marker)
                        self.point_added.emit(x1, y1)

                    self._cleanup_box_state()
                return
            super().mousePressEvent(event)
            return

        # ── Hand 모드 ──
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_panning:
            self._is_panning = False
            if self._mode == Mode.HAND:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self._mode == Mode.POINT:
                self.setCursor(self._point_cursor)
            else:  # Mode.BOX
                self.setCursor(self._box_cursor)
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """더블클릭 시 Fit View — Hand 모드에서만."""
        if (
            self._has_image
            and self._mode == Mode.HAND
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.fit_view()
        # Point 모드에서는 이벤트를 소비하여 추가 포인트 방지

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
