# Image Navigator

비전 프로젝트 개발 보조 도구 — 이미지 좌표 확인, 포인트 마킹 및 바운딩 박스 표시 데스크탑 앱

<img src="sample/Image_Navigator.png" width="700">

## About

이미지의 특정 좌표를 확인하고 포인트를 마킹하거나 바운딩 박스를 그리는 작업이 빈번하게 필요하다. 기존에는 matplotlib 기반의 정적 시각화 유틸리티만 존재하여, 실시간으로 좌표를 탐색하거나 포인트를 인터랙티브하게 마킹하기 어려웠다.

Image Navigator는 이 문제를 해결하기 위해 만든 경량 데스크탑 앱으로, 이미지 위에서 마우스만으로 좌표를 실시간 확인하고, 클릭 한 번으로 포인트를 마킹하거나 바운딩 박스를 그릴 수 있다.

스크립트 실행도 되고 빌드하면 어플처럼 쓸 수 있다.

## Features

- **Hand / Point / Box 모드** — `P` 키로 순환 전환. Hand 모드에서는 드래그로 이동, Point 모드에서는 클릭으로 포인트 마킹, Box 모드에서는 바운딩 박스 그리기
- **포인트 마킹** — Point 모드에서 좌클릭 시 해당 위치에 빨간 점 + 좌표 라벨 표시
- **바운딩 박스** — Box 모드에서 두 번의 클릭으로 초록색 바운딩 박스 생성. 네 꼭지점 좌표와 크기(W, H) 라벨 표시
- **마커 Undo** — 우클릭으로 가장 최근 마커(포인트 또는 박스)부터 하나씩 취소
-  마킹한 포인트와 박스를 하나씩 또는 모두 제거 기능
- **줌 인/아웃** — 마우스 휠로 확대/축소, 리셋기능
- **단축키 가이드** — 툴바의 Shortcuts 버튼 또는 `Ctrl+/`로 단축키 목록 팝업
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

### Windows 빌드 (.exe)

```cmd
REM 배치파일 실행
build.bat

REM 실행 파일실행
dist\ImageNavigator\ImageNavigator.exe
```

### 단축키

**General**

| 단축키 | 기능 |
|---|---|
| `Ctrl+O` | 이미지 로드 |
| `P` | Hand / Point / Box 모드 순환 |
| `Ctrl+R` | 모든 마커 리셋 |
| `Ctrl+/` | 단축키 가이드 |
| `F` | Fit View (원본 비율) |
| 마우스 휠 | 줌 인/아웃 |
| 우클릭 | 박스 취소 또는 최근 마커 삭제 |
| 드래그 앤 드롭 | 이미지 파일 로드 |

**Hand Mode**

| 단축키 | 기능 |
|---|---|
| 좌클릭 드래그 | 패닝 (이미지 이동) |
| 더블클릭 | Fit View (원본 비율) |

**Point Mode**

| 단축키 | 기능 |
|---|---|
| 좌클릭 | 포인트 마킹 |
| `Ctrl`+좌클릭 드래그 | 패닝 (이동) |

**Box Mode**

| 단축키 | 기능 |
|---|---|
| 좌클릭 (1번) | 박스 시작점 설정 |
| 좌클릭 (2번) | 박스 완성 |
| 우클릭 | 박스 취소 또는 최근 마커 삭제 |
| `Ctrl`+좌클릭 드래그 | 패닝 (이동) |

## Project Structure

```
Image_Navigator/
├── main.py            # 앱 엔트리포인트 + 메인 윈도우 (툴바, 상태바, 다크 테마)
├── canvas.py          # 이미지 캔버스 위젯 (좌표 표시, 포인트/박스 마킹, 줌)
├── requirements.txt   # Python 의존성
├── build.sh           # Mac .app 빌드 스크립트
├── build.bat          # Windows .exe 빌드 스크립트
└── README.md
```

## License

MIT
