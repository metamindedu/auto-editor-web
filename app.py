import streamlit as st
import os
import subprocess
import time
import tempfile
import shutil
from pathlib import Path
import re

# 세션 종료 시 임시 디렉토리 정리 함수
def cleanup_temp_dirs():
    if "temp_directories" in st.session_state:
        for temp_dir in st.session_state.temp_directories:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass

# 임시 디렉토리 목록 초기화
if "temp_directories" not in st.session_state:
    st.session_state.temp_directories = []

# 페이지 기본 설정
st.set_page_config(
    page_title="Auto-Editor Web",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 설정
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #cce5ff;
        color: #004085;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 헤더 표시
st.markdown('<p class="main-header">Auto-Editor Web</p>', unsafe_allow_html=True)
st.markdown("동영상에서 무음 부분을 자동으로 제거하거나 속도를 조절하세요.")

# 세션 상태 초기화
if 'processed' not in st.session_state:
    st.session_state.processed = False

if 'output_path' not in st.session_state:
    st.session_state.output_path = None

if 'original_path' not in st.session_state:
    st.session_state.original_path = None

if 'output_file_type' not in st.session_state:
    st.session_state.output_file_type = None

# output 디렉토리 생성
output_dir = os.path.join(os.getcwd(), "output")
os.makedirs(output_dir, exist_ok=True)

# 사이드바 - 설정 옵션
with st.sidebar:
    st.header("편집 설정")

    # 편집 방식 선택
    edit_method = st.selectbox(
        "편집 방식",
        ["오디오 기반 (무음 감지)", "움직임 기반 (정지 장면 감지)"],
        index=0
    )

    # 임계값 유형 선택
    threshold_type = st.radio(
        "임계값 유형",
        ["퍼센트 (%)", "데시벨 (dB)"],
        index=1
    )

    # 임계값 설정
    if threshold_type == "퍼센트 (%)":
        if edit_method == "오디오 기반 (무음 감지)":
            threshold = st.slider("무음 임계값 (%)", 0.0, 100.0, 4.0, 0.1, 
                                format="%.1f%%", help="볼륨이 이 값보다 낮으면 '무음'으로 간주합니다.")
            threshold_str = f"{threshold}%"
        else:
            threshold = st.slider("움직임 임계값 (%)", 0.0, 100.0, 2.0, 0.1, 
                                format="%.1f%%", help="움직임이 이 값보다 적으면 '정지 장면'으로 간주합니다.")
            threshold_str = f"{threshold}%"
    else:  # 데시벨
        if edit_method == "오디오 기반 (무음 감지)":
            threshold = st.slider("무음 임계값 (dB)", -60.0, 0.0, -30.0, 0.5, 
                                format="%.1f dB", help="볼륨이 이 값보다 낮으면 '무음'으로 간주합니다.")
            threshold_str = f"{threshold}dB"
        else:
            threshold = st.slider("움직임 임계값 (dB)", -60.0, 0.0, -30.0, 0.5, 
                                format="%.1f dB", help="움직임이 이 값보다 적으면 '정지 장면'으로 간주합니다.")
            threshold_str = f"{threshold}dB"

    # 마진 설정
    margin = st.number_input("마진 (초)", 
                           min_value=0.0, 
                           max_value=5.0, 
                           value=0.2, 
                           step=0.1,
                           help="무음/정지 장면의 앞뒤로 추가할 시간(초)입니다.")

    # 무음 부분 속도
    silent_speed = st.slider("무음/정지 부분 속도", 
                           min_value=1, 
                           max_value=99999, 
                           value=99999, 
                           step=1,
                           help="무음/정지 부분의 재생 속도입니다. 99999는 완전히 제거함을 의미합니다.")

    # 소리/움직임 부분 속도
    video_speed = st.slider("소리/움직임 부분 속도", 
                          min_value=0.1, 
                          max_value=10.0, 
                          value=1.0, 
                          step=0.1,
                          format="%.1f",
                          help="소리/움직임이 있는 부분의 재생 속도입니다.")

    # 내보내기 형식
    export_format = st.selectbox(
        "내보내기 형식",
        ["MP4 파일", "Adobe Premiere Pro", "DaVinci Resolve", "Final Cut Pro", "ShotCut", "개별 클립"],
        index=0
    )
    
    # 내보내기 형식에 따라 원본 파일 경로 입력 필드 표시
    if export_format != "MP4 파일":
        st.markdown("### 🔴 원본 파일 경로 (필수)")
        original_file_path = st.text_input(
            "영상 파일의 실제 경로 (편집 프로그램에서 사용)",
            help="예: C:\\Videos\\my_video.mp4 또는 /Users/name/Videos/my_video.mp4"
        )
    else:
        # MP4 출력 시에는 선택적 입력
        show_original_path = st.checkbox("원본 파일 경로 지정 (선택사항)", value=False)
        original_file_path = ""
        if show_original_path:
            original_file_path = st.text_input(
                "영상 파일의 실제 경로",
                help="예: C:\\Videos\\my_video.mp4 또는 /Users/name/Videos/my_video.mp4"
            )

    # 내보내기 형식에 따른 추가 옵션
    if export_format != "MP4 파일":
        timeline_name = st.text_input("타임라인 이름", "Auto-Editor Media Group", 
                                    help="편집 소프트웨어에서 사용할 타임라인 이름입니다.")

# 메인 영역 - 파일 업로드 및 처리
upload_col, result_col = st.columns(2)
final_output_dir = ''
with upload_col:
    st.markdown('<p class="sub-header">원본 비디오</p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("비디오 파일을 업로드하세요", type=["mp4", "mov", "avi", "mkv", "webm"])
    
    if uploaded_file is not None:
        # 업로드된 파일 저장
        original_file_name = uploaded_file.name
        file_extension = os.path.splitext(original_file_name)[1]
        
        # 임시 파일 및 output 폴더의 영구 파일 경로 설정
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, original_file_name)
        
        # 임시 디렉토리 추적을 위해 세션 상태에 저장
        st.session_state.temp_directories.append(temp_dir)
        
        # 프로젝트 파일용 미디어 파일 경로 - 출력 폴더에 저장
        media_output_path = os.path.join(output_dir, original_file_name)
        
        # 파일 임시 저장
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.session_state.original_path = temp_path
        
        # 비디오 플레이어 표시
        st.video(temp_path)
        
        # 파일 정보 표시
        file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
        st.info(f"파일 이름: {original_file_name}\n\n파일 크기: {file_size_mb:.2f} MB")
        
        # 처리 버튼
        process_button = st.button("작업 시작")
        
        if process_button:
            # 프로젝트 내보내기 시 원본 경로가 필요
            if export_format != "MP4 파일" and not original_file_path:
                st.error("🔴 프로젝트 파일 내보내기를 위해서는 원본 파일 경로를 입력해야 합니다.")
            else:
                # 편집 방식에 따른 명령 옵션 설정
                if edit_method == "오디오 기반 (무음 감지)":
                    edit_option = f"audio:threshold={threshold_str}"
                else:
                    edit_option = f"motion:threshold={threshold_str}"
                
                # 내보내기 형식에 따른 옵션 설정
                if export_format == "MP4 파일":
                    export_option = ""
                    # 파일명에서 공백과 특수문자 제거하여 안전한 파일명 생성
                    safe_filename = re.sub(r'[^\w\.-]', '_', os.path.splitext(original_file_name)[0])
                    # 출력 파일 경로 (확장자 없이)
                    output_path_without_ext = os.path.join(output_dir, safe_filename + "_edited")
                    st.session_state.output_file_type = "video"
                else:
                    # 프로젝트 파일 내보내기 설정
                    if export_format == "Adobe Premiere Pro":
                        export_type = "premiere"
                        project_ext = ".xml"
                    elif export_format == "DaVinci Resolve":
                        export_type = "resolve"
                        project_ext = ".xml"
                    elif export_format == "Final Cut Pro":
                        export_type = "final-cut-pro"
                        project_ext = ".fcpxml"
                    elif export_format == "ShotCut":
                        export_type = "shotcut"
                        project_ext = ".mlt"
                    else:  # 개별 클립
                        export_type = "clip-sequence"
                        project_ext = ""  # 폴더로 내보내짐
                    
                    # 원본 파일명 사용 (업로드된 파일 이름)
                    original_name = os.path.splitext(original_file_name)[0]
                    
                    # 사용자가 입력한 경로가 폴더 경로인지 확인
                    if os.path.isdir(original_file_path):
                        # 폴더 경로면 그대로 사용
                        project_folder = original_file_path
                    else:
                        # 파일 경로라면 디렉토리 부분만 추출
                        project_folder = os.path.dirname(original_file_path)
                    
                    # 프로젝트 파일을 지정된 폴더에 저장 (확장자 없이)
                    # 원본 파일 이름 기반으로 프로젝트 파일명 생성
                    output_path_without_ext = os.path.join(project_folder, original_name + "_project")
                    
                    # 타임라인 이름 설정
                    if timeline_name and timeline_name != "Auto-Editor Media Group":
                        export_option = f"--export {export_type}:name=\"{timeline_name}\""
                    else:
                        export_option = f"--export {export_type}"
                    
                    st.session_state.output_file_type = "project"
                    
                    # 원본 미디어 파일 경로
                    # 폴더 안의 업로드된 파일 이름과 동일한 파일을 찾아야 함
                    media_file_path = os.path.join(project_folder, original_file_name)
                    
                    if os.path.exists(media_file_path):
                        # 폴더 안에 동일한 이름의 파일이 있으면 사용
                        temp_path = media_file_path
                        st.info(f"원본 파일을 찾았습니다: {media_file_path}")
                    else:
                        # 없으면 먼저 임시 파일을 해당 폴더로 복사
                        try:
                            # 폴더가 존재하는지 확인
                            if not os.path.exists(project_folder):
                                os.makedirs(project_folder)
                            
                            # 임시 파일을 해당 폴더로 복사
                            shutil.copy2(temp_path, media_file_path)
                            temp_path = media_file_path
                            st.info(f"파일을 다음 위치로 복사했습니다: {media_file_path}")
                        except Exception as e:
                            st.warning(f"파일 복사 중 오류: {str(e)}")
                            st.warning("임시 업로드된 파일을 사용합니다.")
                
                # 명령어 구성
                cmd = [
                    "auto-editor",
                    temp_path,
                    "--edit", edit_option,
                    "--margin", f"{margin}sec",
                    "--silent-speed", str(silent_speed),
                    "--video-speed", str(video_speed),
                    "--output",  output_path_without_ext
                ]
                
                # 내보내기 옵션 추가 (MP4가 아닌 경우)
                if export_option:
                    cmd.extend(export_option.split())
                
                # 명령 실행 시작
                with st.spinner("작업 중..."):
                    # 명령어 표시 (디버깅용)
                    st.code(" ".join(cmd))
                    
                    # 프로그레스 바
                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                    
                    # 명령 실행 및 진행상황 업데이트
                    log_line = st.empty()
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    # 진행 상황 추적 및 업데이트
                    progress_percentage = 0
                    for line in process.stdout:
                        # 최신 로그 1줄만 표시 
                        log_line.code(line.strip())
                        
                        # 진행 상황 표시
                        if "%" in line and "Progress:" in line:
                            try:
                                percentage_match = re.search(r'(\d+)%', line)
                                if percentage_match:
                                    progress_percentage = int(percentage_match.group(1))
                                    progress_bar.progress(progress_percentage / 100)
                                    progress_text.text(f"처리 중... {progress_percentage}%")
                            except Exception:
                                pass
                    
                    # 프로세스 완료 대기
                    process.wait()
                    
                    # 완료 표시
                    progress_bar.progress(100)
                    progress_text.text("처리 완료!")
                    
                    # XML 파일 경로 수정 (프로젝트 파일인 경우)
                    if export_format != "MP4 파일" and 'original_file_path' in st.session_state:
                        # 실제 프로젝트 파일 경로 결정 (확장자 포함)
                        if export_format == "Adobe Premiere Pro" or export_format == "DaVinci Resolve":
                            actual_output_path = output_path_without_ext + ".xml"
                        elif export_format == "Final Cut Pro":
                            actual_output_path = output_path_without_ext + ".fcpxml"
                        elif export_format == "ShotCut":
                            actual_output_path = output_path_without_ext + ".mlt"
                        else:
                            actual_output_path = output_path_without_ext  # 폴더일 수 있음
                        
                        # 파일이 실제로 생성되었는지 확인
                        if os.path.exists(actual_output_path):
                            try:
                                # XML 파일 읽기
                                with open(actual_output_path, 'r', encoding='utf-8') as file:
                                    xml_content = file.read()
                                
                                # 임시 경로가 있다면 사용자 지정 경로로 교체
                                # 사용자가 입력한 경로 가져오기
                                user_path = st.session_state.original_file_path
                                
                                # Windows 경로를 URL 형식으로 변환 (file:/// 형식용)
                                url_path = user_path.replace("\\", "/").replace(":", "%3A")
                                
                                # XML에서 참조하는 file:/// 형식 경로 패턴
                                file_url_pattern = r'src="file:///[^"]*"'
                                file_url_replacement = f'src="file:///{url_path}"'
                                
                                # 일반 경로 패턴
                                path_pattern = r'src=[\'"][^\'"\n]*[\'"]'
                                path_replacement = f'src="{user_path}"'
                                
                                # 다른 형식의 경로 패턴
                                file_path_pattern = r'<file-path>[^<]*</file-path>'
                                file_path_replacement = f'<file-path>{user_path}</file-path>'
                                
                                # 또 다른 경로 패턴
                                attr_path_pattern = r'path="[^"]*"'
                                attr_path_replacement = f'path="{user_path}"'
                                
                                # 각 패턴에 대해 순차적으로 치환
                                modified_content = xml_content
                                modified_content = re.sub(file_url_pattern, file_url_replacement, modified_content)
                                modified_content = re.sub(path_pattern, path_replacement, modified_content)
                                modified_content = re.sub(file_path_pattern, file_path_replacement, modified_content)
                                modified_content = re.sub(attr_path_pattern, attr_path_replacement, modified_content)
                                
                                # 수정된 내용 저장
                                with open(actual_output_path, 'w', encoding='utf-8') as file:
                                    file.write(modified_content)
                                    
                                log_line.text(f"프로젝트 파일의 미디어 경로를 '{user_path}'로 업데이트했습니다.")
                            except Exception as e:
                                log_line.text(f"프로젝트 파일 경로 수정 중 오류 발생: {str(e)}")
                    
                    # 임시 파일 정리
                    for temp_dir in st.session_state.temp_directories:
                        try:
                            shutil.rmtree(temp_dir, ignore_errors=True)
                        except Exception as e:
                            log_line.text(f"임시 파일 정리 중 오류 발생: {str(e)}")
                    
                    # 임시 파일 목록 초기화
                    st.session_state.temp_directories = []
                    
                    # 처리 완료 메시지만 표시
                    st.success("""
                    처리가 완료되었습니다!
                    
                    output 폴더 또는 원본 파일 경로(입력한 경우)에서 결과 파일을 확인하세요.
                    """)
                    
                    # 경로 표시
                    if project_folder:
                        final_output_dir = project_folder
                    else:
                        final_output_dir = output_dir

                    st.code(f"결과물 폴더 위치: {final_output_dir}")
                    
                    # 세션 상태는 처리 완료만 표시
                    st.session_state.processed = True

# 결과 표시 부분을 수정합니다
with result_col:
    st.markdown('<p class="sub-header">처리 결과</p>', unsafe_allow_html=True)
    
    if st.session_state.processed:                
        st.markdown(f"""
        <div class="success-box">
            <h3>처리 완료!</h3>
            <p>결과 파일은 다음 위치에 저장되었습니다:</p>
            <p><code>{final_output_dir}</code></p>
        </div>
        """, unsafe_allow_html=True)
        
        # 프로젝트 파일 경로 정보 표시 (있는 경우)
        if 'original_file_path' in st.session_state:
            st.markdown(f"""
            <div class="info-box">
                <h4>프로젝트 파일 정보</h4>
                <p>프로젝트 파일은 다음 경로의 미디어를 참조합니다:</p>
                <p><code>{st.session_state.original_file_path}</code></p>
                <p>편집 프로그램에서 프로젝트 파일을 열 때 이 경로에 미디어 파일이 있어야 합니다.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # 출력 폴더 열기 버튼 (Windows에서만 작동)
        if os.name == 'nt':  # Windows
            if st.button("결과물 폴더 열기"):
                os.startfile(final_output_dir)
    else:
        st.info("비디오를 업로드하고 처리를 시작하면 여기에 결과가 표시됩니다.")

# 임시 파일 정리 기능 추가
with st.sidebar:
    st.divider()
    st.markdown("### 디스크 공간 관리")
    
    if st.button("임시 파일 정리"):
        cleanup_count = 0
        for temp_dir in st.session_state.temp_directories:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                cleanup_count += 1
            except:
                pass
        
        # 리스트 초기화
        st.session_state.temp_directories = []
        
        if cleanup_count > 0:
            st.success(f"{cleanup_count}개의 임시 디렉토리를 정리했습니다.")
        else:
            st.info("정리할 임시 파일이 없습니다.")

# 푸터
st.markdown("---")
st.markdown("Auto-Editor Web은 [Auto-Editor](https://github.com/WyattBlue/auto-editor)의 GUI 인터페이스입니다.")

# 영어 버전 전환 버튼 (미구현)
# language_toggle = st.checkbox("Switch to English", value=False)