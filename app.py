import streamlit as st
import os
import subprocess
import time
import tempfile
import shutil
from pathlib import Path
import re
import json
import datetime
import atexit

# Constants for temp directory tracking
TEMP_DIR_TRACKER_FILE = "temp_dir_tracker.json"
MAX_TEMP_DIR_AGE_HOURS = 24  # Clean up directories older than this

# Function to load the list of tracked temporary directories
def load_temp_dirs():
    try:
        if os.path.exists(TEMP_DIR_TRACKER_FILE):
            with open(TEMP_DIR_TRACKER_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

# Function to save the list of tracked temporary directories
def save_temp_dirs(temp_dirs_dict):
    try:
        with open(TEMP_DIR_TRACKER_FILE, 'w') as f:
            json.dump(temp_dirs_dict, f)
    except Exception:
        pass

# Function to track a temporary directory
def track_temp_dir(temp_dir):
    temp_dirs = load_temp_dirs()
    temp_dirs[temp_dir] = datetime.datetime.now().isoformat()
    save_temp_dirs(temp_dirs)
    
    # Also add to session state for current session
    if "temp_directories" not in st.session_state:
        st.session_state.temp_directories = []
    if temp_dir not in st.session_state.temp_directories:
        st.session_state.temp_directories.append(temp_dir)

# Function to remove a temporary directory from tracking
def untrack_temp_dir(temp_dir):
    temp_dirs = load_temp_dirs()
    if temp_dir in temp_dirs:
        del temp_dirs[temp_dir]
    save_temp_dirs(temp_dirs)
    
    # Also remove from session state if it exists
    if "temp_directories" in st.session_state and temp_dir in st.session_state.temp_directories:
        st.session_state.temp_directories.remove(temp_dir)

# Function to determine if file is audio or video
def is_audio_file(file_path):
    # Get file extension
    _, file_ext = os.path.splitext(file_path)
    file_ext = file_ext.lower()
    
    # WAV 파일만 오디오 파일로 인식
    audio_extensions = ['.wav']
    return file_ext in audio_extensions

# Handle file upload and state changes
def handle_upload():
    if uploaded_file is not None:
        # 업로드된 파일 저장
        original_file_name = uploaded_file.name
        file_extension = os.path.splitext(original_file_name)[1]
        
        # 파일 타입 감지
        file_is_audio = is_audio_file(original_file_name)
        
        # 세션 상태 업데이트
        st.session_state.is_audio_file = file_is_audio
        st.session_state.original_file_name = original_file_name
        
        # 임시 파일 경로 설정
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, original_file_name)
        
        # 임시 디렉토리 추적
        track_temp_dir(temp_dir)
        
        # 파일 임시 저장
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.session_state.original_path = temp_path
        st.session_state.temp_path = temp_path
        st.session_state.selected_upload_path = temp_path  # 새로 업로드된 파일을 선택된 파일로 설정
        
        # 디버깅 정보
        st.write(f"파일 '{original_file_name}'이 업로드되었습니다.")
        st.write(f"파일 타입: {'오디오' if file_is_audio else '비디오'}")
        
        return True
    return False

def get_all_tracked_uploads():
    uploads = []
    # temp_dir_tracker.json에 기록된 모든 임시 디렉토리 읽기
    temp_dirs = load_temp_dirs()  # 예: {temp_dir: timestamp, ...}
    
    # 타임스탬프 기준으로 역순 정렬 (최신 순)
    sorted_temp_dirs = sorted(temp_dirs.items(), key=lambda x: x[1], reverse=True)
    
    for temp_dir, ts in sorted_temp_dirs:
        if os.path.exists(temp_dir):
            # 해당 디렉토리 내의 파일들을 순회
            for file in os.listdir(temp_dir):
                if file.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".wav")):
                    file_path = os.path.join(temp_dir, file)
                    uploads.append((file, file_path))
        else:
            # 존재하지 않는 디렉토리는 추적 목록에서 제거
            untrack_temp_dir(temp_dir)
    return uploads


# Function to clean up a temporary directory
def cleanup_temp_dir(temp_dir):
    try:
        if os.path.exists(temp_dir):
            # Try different cleanup methods
            try:
                # First attempt with standard method
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            
            # If directory still exists, try with OS-specific commands
            if os.path.exists(temp_dir):
                if os.name == 'nt':  # Windows
                    try:
                        os.system(f'rd /s /q "{temp_dir}"')
                    except:
                        pass
                else:  # Unix/Linux/Mac
                    try:
                        os.system(f'rm -rf "{temp_dir}"')
                    except:
                        pass
        
        # Remove from tracking
        untrack_temp_dir(temp_dir)
        
        # Success if directory no longer exists
        return not os.path.exists(temp_dir)
    except Exception:
        return False

# Function to clean up old temporary directories
def cleanup_old_temp_dirs():
    # First clean tracked directories
    temp_dirs = load_temp_dirs()
    now = datetime.datetime.now()
    success_count = 0
    
    for temp_dir, created_at_str in list(temp_dirs.items()):
        try:
            created_at = datetime.datetime.fromisoformat(created_at_str)
            age_hours = (now - created_at).total_seconds() / 3600
            
            if age_hours > MAX_TEMP_DIR_AGE_HOURS:
                if cleanup_temp_dir(temp_dir):
                    success_count += 1
        except Exception:
            # If we can't parse the date, try to clean up anyway
            if cleanup_temp_dir(temp_dir):
                success_count += 1
    
    # Now search for and clean up any untracked temporary directories
    try:
        # Get system temp directory
        system_temp = tempfile.gettempdir()
        
        # Look for directories that match our pattern
        for item in os.listdir(system_temp):
            item_path = os.path.join(system_temp, item)
            
            # Check if it's a directory and has our typical temp pattern (starts with 'tmp')
            if os.path.isdir(item_path) and item.startswith('tmp'):
                # Check if it's old enough (older than 3 hours)
                item_age_hours = (now - datetime.datetime.fromtimestamp(os.path.getctime(item_path))).total_seconds() / 3600
                if item_age_hours > MAX_TEMP_DIR_AGE_HOURS:
                    if cleanup_temp_dir(item_path):
                        success_count += 1
    except Exception:
        # If we encounter an error scanning the system temp dir, just continue
        pass
    
    return success_count

# Register cleanup function to run when Python exits
@atexit.register
def cleanup_on_exit():
    # Clean tracked directories in session state
    if "temp_directories" in st.session_state:
        for temp_dir in list(st.session_state.temp_directories):
            cleanup_temp_dir(temp_dir)
    
    # Also clean up any tmp directories in the system temp folder
    try:
        system_temp = tempfile.gettempdir()
        for item in os.listdir(system_temp):
            item_path = os.path.join(system_temp, item)
            if os.path.isdir(item_path) and item.startswith('tmp'):
                try:
                    shutil.rmtree(item_path, ignore_errors=True)
                    # If still exists, try OS-specific command
                    if os.path.exists(item_path):
                        if os.name == 'nt':  # Windows
                            os.system(f'rd /s /q "{item_path}"')
                        else:
                            os.system(f'rm -rf "{item_path}"')
                except:
                    pass
    except:
        pass

# Run cleanup of old temp dirs on startup
startup_cleanup_count = cleanup_old_temp_dirs()

# 세션 종료 시 임시 디렉토리 정리 함수 - 이제 atexit을 통해 관리
def cleanup_temp_dirs():
    if "temp_directories" in st.session_state:
        for temp_dir in list(st.session_state.temp_directories):
            cleanup_temp_dir(temp_dir)

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

# 세션 상태 초기화
if 'processed' not in st.session_state:
    st.session_state.processed = False

if 'output_path' not in st.session_state:
    st.session_state.output_path = None

if 'original_path' not in st.session_state:
    st.session_state.original_path = None

if 'output_file_type' not in st.session_state:
    st.session_state.output_file_type = None

if 'is_audio_file' not in st.session_state:
    st.session_state.is_audio_file = False

if 'original_file_name' not in st.session_state:
    st.session_state.original_file_name = None
    
if 'temp_path' not in st.session_state:
    st.session_state.temp_path = None

# 헤더 표시
st.markdown('<h1 class="main-header">Auto-Editor Web</h1>', unsafe_allow_html=True)
st.markdown(" ")
st.markdown("동영상 또는 오디오에서 무음 부분을 자동으로 제거하거나 속도를 조절하세요.")

# output 디렉토리 생성
output_dir = os.path.join(os.getcwd(), "output")
os.makedirs(output_dir, exist_ok=True)

# 사이드바 - 설정 옵션
with st.sidebar:
    with st.sidebar.expander("최근 파일 업로드 내역", expanded=False):
        uploads = get_all_tracked_uploads()  # temp_dir_tracker.json 기반 실제 파일 존재 여부 확인
        if uploads:
            # 파일명만 옵션으로 표시
            options = [name for name, path in uploads]
            
            # 파일을 방금 업로드했다면 해당 파일을 자동 선택
            if st.session_state.get("selected_upload_path"):
                selected_filename = os.path.basename(st.session_state.get("selected_upload_path"))
                if selected_filename in options:
                    default_index = options.index(selected_filename)
                else:
                    default_index = 0
            else:
                default_index = 0  # 기본적으로 첫 번째 항목(최신 파일) 선택
                
            selected_name = st.selectbox("업로드된 파일 선택", options, index=default_index, key="recent_file")
            # 선택된 항목의 파일 경로 저장 및 미리보기
            for name, file_path in uploads:
                if name == selected_name:
                    st.session_state.selected_upload_path = file_path
                    st.info(f"선택된 파일: {file_path}")
                    
                    # 파일 타입 감지 및 저장
                    file_is_audio = is_audio_file(file_path)
                    st.session_state.is_audio_file = file_is_audio
                    
                    # 파일 타입에 따른 미리보기
                    if file_is_audio:
                        st.audio(file_path)
                    else:
                        st.video(file_path)
                    break
        else:
            st.info("최근 업로드된 파일이 없습니다.")

        if st.button("목록 초기화", help="임시파일을 삭제하여 디스크 공간을 확보할 수 있습니다."):
            # 모든 임시 디렉토리 삭제
            temp_dirs = list(load_temp_dirs().keys())
            for temp_dir in temp_dirs:
                cleanup_temp_dir(temp_dir)
            
            # 더 이상 유효하지 않은 세션 변수 초기화
            st.session_state.original_path = None
            st.session_state.selected_upload_path = None
            st.session_state.is_audio_file = False

            st.success("임시 파일 목록이 초기화되었습니다.")
            
            # 화면을 새로고침하여, 이미 사라진 파일 경로를 다시 표시하지 않도록 함
            st.rerun()

        st.markdown(f"※ 디스크 공간 절약을 위하여, {MAX_TEMP_DIR_AGE_HOURS}시간 동안만 유지됩니다.")

    st.header("편집 설정")

    # 현재 업로드된 파일의 타입에 따라 편집 방식 선택 옵션을 조정
    if st.session_state.is_audio_file:
        edit_method = "오디오 기반 (무음 감지)"
        st.info("오디오 파일은 오디오 기반 편집만 지원합니다.")
    else:
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

    # 내보내기 형식 - 파일 타입에 따라 옵션 제한
    if st.session_state.is_audio_file:
        # 오디오 파일인 경우 WAV 형식만 제공
        export_format = "WAV 파일"
        st.info("오디오 파일은 WAV 형식으로만 내보내기가 가능합니다.")
    else:
        # 비디오 파일인 경우 옵션 제공
        export_format = st.selectbox(
            "내보내기 형식",
            ["MP4 파일", "WAV 파일", "Adobe Premiere Pro", "DaVinci Resolve", "Final Cut Pro", "ShotCut", "개별 클립"],
            index=0
        )
    
    # 내보내기 형식에 따라 원본 파일 경로 입력 필드 표시
    if export_format in ["Adobe Premiere Pro", "DaVinci Resolve", "Final Cut Pro", "ShotCut", "개별 클립"]:
        st.markdown("### 🔴 원본 파일 경로 (필수)")
        original_file_path = st.text_input(
            "파일의 실제 경로 (편집 프로그램에서 사용)",
            help="예: C:\\Videos\\my_video.mp4 또는 /Users/name/Videos/my_video.mp4"
        )
    else:
        # 다른 출력 형식은 선택적 입력
        show_original_path = st.checkbox("원본 파일 경로 지정 (선택사항)", value=False)
        original_file_path = ""
        if show_original_path:
            original_file_path = st.text_input(
                "파일의 실제 경로",
                help="예: C:\\Videos\\my_video.mp4 또는 /Users/name/Videos/my_video.mp4"
            )

    # 내보내기 형식에 따른 추가 옵션
    if export_format in ["Adobe Premiere Pro", "DaVinci Resolve", "Final Cut Pro", "ShotCut"]:
        timeline_name = st.text_input("타임라인 이름", "Auto-Editor Media Group", 
                                    help="편집 소프트웨어에서 사용할 타임라인 이름입니다.")

# 메인 영역 - 파일 업로드 및 처리
upload_col, result_col = st.columns(2)
final_output_dir = ''
temp_path = None
with upload_col:
    st.markdown('<p class="sub-header">원본 파일</p>', unsafe_allow_html=True)
    
    # 비디오 및 오디오 파일 업로더
    uploaded_file = st.file_uploader("파일을 업로드하세요", 
                                    type=["mp4", "mov", "avi", "mkv", "webm", "wav"])
    
    # 파일 업로드 처리
    if uploaded_file is not None and (st.session_state.original_file_name != uploaded_file.name):
        # 파일 이름이 변경되었으면 처리
        if handle_upload():
            st.rerun()
    
    # 기존 업로드된 파일이 있는지 확인
    temp_path = st.session_state.temp_path
    
    # 만약 새 파일이 업로드되지 않았고, 최근 업로드 내역에서 선택한 파일이 있다면
    if uploaded_file is None and st.session_state.get("selected_upload_path"):
        st.session_state.original_path = st.session_state.selected_upload_path
        temp_path = st.session_state.original_path
        
        # 파일 타입 감지
        file_is_audio = is_audio_file(st.session_state.selected_upload_path)
        st.session_state.is_audio_file = file_is_audio
        
        # 파일 타입에 따른 미리보기
        if file_is_audio:
            st.audio(st.session_state.original_path)
        else:
            st.video(st.session_state.original_path)
    else:
        if uploaded_file is not None:
            # 파일이 이미 업로드되었고 처리되었는지 확인
            if st.session_state.temp_path and os.path.exists(st.session_state.temp_path):
                temp_path = st.session_state.temp_path
                
                # 파일 타입에 따른 미리보기
                if st.session_state.is_audio_file:
                    st.audio(temp_path)
                else:
                    st.video(temp_path)
            else:
                # 만약 아직 처리되지 않았으면 처리
                if handle_upload():
                    st.rerun()
    
    if temp_path and os.path.exists(temp_path):
        # 파일 정보 표시
        file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
        file_name = os.path.basename(temp_path)
        file_type = "오디오" if st.session_state.is_audio_file else "비디오"
        st.info(f"파일 이름: {file_name}\n\n파일 크기: {file_size_mb:.2f} MB\n\n파일 타입: {file_type}")

    if st.session_state.get("original_path") and os.path.exists(st.session_state.get("original_path")):
        process_button = st.button("작업 시작")
    
        if process_button:
            # 프로젝트 내보내기 시 원본 경로가 필요
            if export_format in ["Adobe Premiere Pro", "DaVinci Resolve", "Final Cut Pro", "ShotCut", "개별 클립"] and not original_file_path:
                st.error("🔴 프로젝트 파일 내보내기를 위해서는 원본 파일 경로를 입력해야 합니다.")
            else:
                # 편집 방식에 따른 명령 옵션 설정
                if edit_method == "오디오 기반 (무음 감지)":
                    edit_option = f"audio:threshold={threshold_str}"
                else:
                    edit_option = f"motion:threshold={threshold_str}"
                
                # 내보내기 형식에 따른 옵션 설정
                export_option = ""
                
                # 파일명에서 공백과 특수문자 제거하여 안전한 파일명 생성
                safe_filename = re.sub(r'[^\w\.-]', '_', os.path.splitext(os.path.basename(temp_path))[0])
                # 출력 파일 경로 (확장자 없이)
                output_path_without_ext = os.path.join(output_dir, safe_filename + "_edited")
                
                # 내보내기 형식 설정
                if export_format == "MP4 파일":
                    st.session_state.output_file_type = "video"
                elif export_format == "WAV 파일":
                    export_option = "--export audio --output-format wav"
                    st.session_state.output_file_type = "audio"
                else:
                    # 프로젝트 파일 내보내기 설정 (원본 파일 경로 필수)
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
                    original_name = os.path.splitext(os.path.basename(temp_path))[0]
                    
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
                    media_file_path = os.path.join(project_folder, os.path.basename(temp_path))
                    
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
                
                # 내보내기 옵션 추가 (있는 경우)
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
                    if export_format in ["Adobe Premiere Pro", "DaVinci Resolve", "Final Cut Pro", "ShotCut"] and 'original_file_path' in st.session_state:
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
                    
                    # 처리 완료 메시지만 표시
                    st.success("""
                    처리가 완료되었습니다!
                    
                    output 폴더 또는 원본 파일 경로(입력한 경우)에서 결과 파일을 확인하세요.
                    """)
                    
                    # 경로 표시
                    if export_format in ["Adobe Premiere Pro", "DaVinci Resolve", "Final Cut Pro", "ShotCut", "개별 클립"] and 'project_folder' in locals():
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
        st.info("파일을 업로드하고 처리를 시작하면 여기에 결과가 표시됩니다.")

# 임시 파일 정리 등 시스템 알림 영역 추가
with st.sidebar:
    st.divider()
    st.markdown("### 시스템 알림")
    
    # 시작 시 정리된 임시 파일이 있으면 알림
    if startup_cleanup_count > 0:
        st.info(f"시작 시 {startup_cleanup_count}개의 오래된 임시 파일을 자동으로 정리했습니다.")

st.markdown("---")
# 푸터 컨테이너 생성
footer = st.container()

with footer:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px;">
                <p style="font-size: 0.9em; color: #666;">
                    Auto-Editor Web은 <a href="https://github.com/WyattBlue/auto-editor" target="_blank" style="color: #4B9CFF; text-decoration: none;">Auto-Editor</a>의 GUI 인터페이스 Wrapper 앱입니다.<br>
                    이 프로그램은 <a href="https://metamind.kr" target="_blank" style="color: #4B9CFF; text-decoration: none;">메타마인드</a>가 제작하였으며, 자유로운 수정 및 공유가 가능합니다.
                </p>
                <p style="font-size: 0.8em; color: #888;">© 2025 메타마인드</p>
            </div>
            """, 
            unsafe_allow_html=True
        )