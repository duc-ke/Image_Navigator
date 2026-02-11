# Image Navigator

비전 프로젝트 개발 보조 도구 — 이미지 좌표 확인 및 포인트 마킹 데스크탑 앱

## About

이미지의 특정 좌표를 확인하고 포인트를 마킹하는 작업이 빈번하게 필요하다. 기존에는 matplotlib 기반의 정적 시각화 유틸리티만 존재하여, 실시간으로 좌표를 탐색하거나 포인트를 인터랙티브하게 마킹하기 어려웠다.

Image Navigator는 이 문제를 해결하기 위해 만든 경량 데스크탑 앱으로, 이미지 위에서 마우스만으로 좌표를 실시간 확인하고, 클릭 한 번으로 포인트를 마킹할 수 있다.

## Features

- **이미지 로드/표시** — PNG, JPG, BMP, TIFF, WebP 등 주요 포맷 지원
- **실시간 좌표 표시** — 마우스 커서 옆에 (x, y) 좌표가 실시간으로 표시됨
- **포인트 마킹** — 클릭 시 해당 위치에 빨간 점 + 좌표 라벨 표시
- **Point Reset** — 마킹한 포인트를 모두 제거 (이미지는 유지)
- **Image Reset** — 이미지를 제거하고 새 이미지를 로드할 수 있는 상태로 복귀
- **줌 인/아웃** — 마우스 휠로 확대/축소
- **원본 크기 복원** — 더블클릭으로 원본 보기로 복귀
- **패닝** — 마우스 휠 클릭 또는 Ctrl+좌클릭 드래그로 이미지 이동
- **다크 테마** — 눈의 피로를 줄이는 어두운 UI

## Requirements

- Python 3.10+
- PySide6
- Pillow

## Installation

```bash
git clone <repo-url>
cd image_navigator
pip install -r requirements.txt
```

## Usage

### 커맨드라인 실행

```bash
# 기본 실행
python main.py

# 이미지 경로를 인자로 바로 로드
python main.py /path/to/image.jpg
```

### Mac 앱 빌드 (.app)

```bash
# PyInstaller로 Mac 앱 번들 생성
bash build.sh

# 실행
open dist/ImageNavigator.app

# (선택) Applications 폴더에 복사
cp -r dist/ImageNavigator.app /Applications/
```

### 단축키

| 단축키 | 기능 |
|---|---|
| `Ctrl+O` | 이미지 로드 |
| `Ctrl+R` | 포인트 리셋 |
| `Ctrl+Shift+R` | 이미지 리셋 |
| 마우스 휠 | 줌 인/아웃 |
| 더블클릭 | 원본 크기 복원 |
| 휠 클릭 드래그 / Ctrl+좌클릭 드래그 | 패닝 |

## Project Structure

```
Image_Navigator/
├── main.py            # 앱 엔트리포인트 + 메인 윈도우 (툴바, 상태바, 다크 테마)
├── canvas.py          # 이미지 캔버스 위젯 (좌표 표시, 포인트 마킹, 줌)
├── requirements.txt   # Python 의존성
├── build.sh           # Mac .app 빌드 스크립트
└── README.md
```

## License

MIT
