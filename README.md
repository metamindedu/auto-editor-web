<p align="center"><img src="https://auto-editor.com/img/auto-editor-banner.webp" title="Auto-Editor Web" width="700"></p>

# Auto-Editor Web

**Auto-Editor Web**은 [Auto-Editor](https://github.com/WyattBlue/auto-editor)를 직관적인 웹 인터페이스로 사용할 수 있게 해주는 애플리케이션입니다. 단순한 클릭 몇 번으로 동영상의 무음 부분을 자동으로 제거하거나 속도를 조절할 수 있습니다.

## 주요 기능

- **직관적인 웹 인터페이스**: 명령 프롬프트 지식이 없이도 쉽게 사용 가능
- **무음 부분 자동 제거**: 오디오 볼륨 기반 편집(퍼센트 or dB)
- **움직임 기반 편집**: 동영상의 움직임이 적은 부분 감지 및 편집
- **실시간 진행률 표시**: 작업 진행 상황을 시각적으로 확인
- **줄어든 시간 표시**: 편집 전후 영상 길이 비교
- **다양한 내보내기 옵션**: MP4, 프리미어 프로, DaVinci Resolve, Final Cut Pro 등
- **손쉬운 설치 및 실행**: 더블클릭으로 실행 가능한 배치 파일

<p align="center"><img src="https://auto-editor.com/img/cross-platform.webp" width="500" title="Windows, MacOS, and Linux"></p>

## 시작하기

### 방법 1: 간편 실행 (Windows)

1. 저장소를 다운로드하거나 클론합니다.
2. 폴더 내의 `run_auto_editor_app.bat` 파일을 더블클릭하여 실행합니다.
3. 앱이 처음 실행될 때는 필요한 패키지를 자동으로 설치합니다.
4. 웹 브라우저가 자동으로 열리고 애플리케이션 인터페이스가 표시됩니다.

### 방법 2: 소스 코드에서 직접 실행

```bash
# 저장소 클론
git clone https://github.com/yourusername/auto-editor-web.git
cd auto-editor-web

# Auto-Editor 소스 가져오기
git clone https://github.com/WyattBlue/auto-editor.git

# 의존성 설치
pip install streamlit numpy av ffmpeg-python
pip install -e ./auto-editor

# Streamlit 앱 실행
streamlit run app.py
```

## 사용 방법

1. 비디오 및 음성 파일 업로드
2. 왼쪽 사이드바에서 편집 설정 조정
   - 편집 방식 선택 (오디오/움직임 기반)
   - 임계값 설정(퍼센트 또는 데시벨)
   - 속도 및 마진 조정
3. "작업 시작" 버튼 클릭
4. 작업 진행 상황 모니터링
5. 작업 완료 후 결과 확인 및 다운로드

## 주의사항

- 작업 시간은 영상 길이와 해상도에 따라 달라집니다
- 고해상도 영상의 경우 작업에 더 많은 시간이 소요될 수 있습니다
- 움직임 기반 편집은 오디오 기반 편집보다 더 많은 컴퓨팅 리소스를 사용합니다

## 제작 정보

이 프로그램은 [메타마인드](https://metamind.kr)가 제작하였으며, 자유로운 수정 및 공유가 가능합니다.

---

© 2025 메타마인드 | [https://metamind.kr](https://metamind.kr)