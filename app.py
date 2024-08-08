from flask import Flask, render_template, request, jsonify, send_file
import boto3
import json
import uuid
import logging
import os
from moviepy.editor import VideoFileClip
import time
from PIL import Image

# 프로젝트 루트 디렉토리 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# tmp 폴더 경로
TMP_DIR = os.path.join(BASE_DIR, 'tmp')

# tmp 폴더가 없으면 생성
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB 제한

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


AWS_REGION = os.environ.get('AWS_REGION', 'us-west-2')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'default-bucket-name')


logger.info(f"BUCKET_NAME is {BUCKET_NAME}")

session = boto3.Session(region_name=AWS_REGION)
s3 = session.client('s3')
transcribe = session.client("transcribe")
bedrock = session.client("bedrock-runtime")

VIDEO_FOLDER = 'videos/'
SUBTITLE_FOLDER = 'subtitles/'

# 비디오 파일 이름과 job_name을 연결하여 저장할 딕셔너리
video_job_mapping = {}

def is_valid_video(file_path):
    try:
        clip = VideoFileClip(file_path)
        duration = clip.duration  # 동영상 길이 확인
        clip.close()
        return duration > 0
    except Exception as e:
        logger.error(f"Error validating video: {str(e)}")
        return False
    
@app.route('/')
def index():
    logger.info("Index page accessed")
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    logger.info("File upload processing initiated")
    if 'file' not in request.files:
        logger.error("No file part in the request")
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        logger.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400
    
    # Generate unique filename
    original_filename = file.filename
    file_extension = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    local_path = os.path.join(TMP_DIR, unique_filename)
    
    # 파일 저장
    file.save(local_path)
    
    # 파일 업로드 완료 확인
    max_attempts = 50
    attempts = 0
    while attempts < max_attempts:
        logger.info(f"attempts < max_attempts : {attempts} < {max_attempts}")
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            logger.info(f"os.path.exists(local_path) : {os.path.exists(local_path) }")
            logger.info(f"os.path.getsize(local_path) : {os.path.getsize(local_path) }")
            time.sleep(1)  # 파일 시스템 동기화를 위한 짧은 대기
            break
        time.sleep(2)  # 2초 대기 후 재시도
        attempts += 1
    
    if attempts == max_attempts:
        return jsonify({'error': 'File upload failed or incomplete'}), 500
    
    # 파일 유효성 검사
    if not is_valid_video(local_path):
        os.remove(local_path)  # 유효하지 않은 파일 삭제
        return jsonify({'error': 'Invalid video file'}), 400
    
    logger.info(f"{local_path=}")
    
    
    # S3에 업로드
    s3_video_path = VIDEO_FOLDER + unique_filename
    logger.info(f"Uploading file {unique_filename} to S3 in {s3_video_path}")
    with open(local_path, 'rb') as file_to_upload:
        s3.upload_fileobj(file_to_upload, BUCKET_NAME, s3_video_path)
    logger.info(f"File {unique_filename} uploaded successfully to S3")

    # Start Transcribe job
    job_name = f"transcribe-{uuid.uuid4()}"
    logger.info(f"Starting Transcribe job: {job_name} / s3://{BUCKET_NAME}/{s3_video_path}")
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': f"s3://{BUCKET_NAME}/{s3_video_path}"},
        MediaFormat=file_extension,
        LanguageCode='ko-KR',
        OutputBucketName=BUCKET_NAME,
        OutputKey=f"{SUBTITLE_FOLDER}{job_name}.json"
    )
    logger.info(f"Transcribe job {job_name} started successfully")
    
        
    # 비디오 파일 이름과 job_name 연결 저장
    video_job_mapping[job_name] = unique_filename

    return jsonify({
        'job_name': job_name,
        'file_name': unique_filename
    }), 200

@app.route('/status/<job_name>')
def get_status(job_name):
    logger.info(f"Checking status for job: {job_name}")

    response = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    status = response['TranscriptionJob']['TranscriptionJobStatus']
    
    if status == 'COMPLETED':
        transcript_key = f"{SUBTITLE_FOLDER}{job_name}.json"
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=transcript_key)
        transcript = json.loads(obj['Body'].read().decode('utf-8'))
        
    logger.info(f"Job {job_name} status: {status}")
    
    if status == 'COMPLETED':
        logger.info(f"Job {job_name} completed, processing results")

        # 전체 텍스트 추출
        full_text = transcript['results']['transcripts'][0]['transcript']
        
        # 오디오 세그먼트를 시간 정보와 함께 추출
        audio_segments = transcript['results']['audio_segments']
        full_text_with_time = [
            {
                'text': segment['transcript'],
                'start_time': float(segment['start_time']),
                'end_time': float(segment['end_time'])
            }
            for segment in audio_segments
        ]
                
        logger.info(f"full_text : {full_text}")
        logger.info(f"full_text : {full_text_with_time}")
        logger.info("Calling Claude 3.5 for analysis")

        prompt = f"""긴 영상의 비디오를 유튜브 숏츠와 같은 15~60초 길이의 영상으로 만들 것입니다. 아래는 영상에서 추출한 대화 텍스트입니다. 이 텍스트를 분석하여 주요 대화 주제들을 파악하고 요약해 주세요. 
        각 주제에 대해 해당 내용이 언급된 대략적인 시작 시간과 종료 시간도 함께 제공해 주세요. 대화에 참여한 사람의 이름을 표현할 수 있다면 함께 포함해주세요. 응답은 다음 JSON 구조를 따라 제공해 주세요:

                    {full_text_with_time}

                    {{
                    "topics": [
                        {{
                        "title": "주제 제목",
                        "summary": "주제에 대한 간단한 요약",
                        "importance": "높음/중간/낮음",
                        "start_time": "시작 시간(초)",
                        "end_time": "종료 시간(초)"
                        }}
                    ]
                    }}

                    주의: 모든 응답은 위의 JSON 구조 안에 포함되어야 하며, 추가적인 텍스트나 설명은 포함하지 마세요."""

       
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens":1000,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text" : prompt}]}]})

        
        claude_response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            contentType="application/json",
            accept="application/json",
            body=body
        )
        
        response_body = claude_response['body'].read().decode('utf-8')
        logger.info(f"claude_response : {response_body}")
                         
        
        # Parse the JSON content from Claude's response
        response_json = json.loads(response_body)
        claude_content = response_json['content'][0]['text']
        
        # Parse the actual JSON data from Claude's content
        classification = json.loads(claude_content)

        
        # 시간 정보 매칭 및 조정
        for topic in classification['topics']:
            start_time = float(topic['start_time'])
            end_time = float(topic['end_time'])
            matching_segments = [
                segment for segment in full_text_with_time 
                if segment['start_time'] <= start_time and segment['end_time'] >= end_time
            ]
            if matching_segments:
                topic['start_time'] = matching_segments[0]['start_time']
                topic['end_time'] = matching_segments[-1]['end_time']


        logger.info("Claude 3.5 analysis completed")
        logger.info(f"{status=}")
        logger.info(f"{classification=}")

        return jsonify({
            'status': status,
            'classification': classification,
            'transcript': full_text
        })
    
    return jsonify({'status': status})


def get_thumbnail(video_path, time, output_path):
    try:
        # 비디오 파일 열기
        clip = VideoFileClip(video_path)
        
        # 특정 시간의 프레임 추출
        frame = clip.get_frame(time)
        
        # NumPy 배열을 PIL Image로 변환
        image = Image.fromarray(frame)
        
        # 이미지 저장
        image.save(output_path, format='JPEG')
        
        # 리소스 해제
        clip.close()
        
        return output_path
    except Exception as e:
        logger.error(f"Error generating thumbnail: {str(e)}")
        return None


@app.route('/get_thumbnail/<job_name>/<float:start_time>')
def get_thumbnail_route(job_name, start_time):
    try:
        video_filename = video_job_mapping.get(job_name)
        logger.info(f"Video filename for job {job_name}: {video_filename}")
        if not video_filename:
            raise ValueError(f"No video file found for job {job_name}")

        video_path = os.path.join(TMP_DIR, video_filename)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        output_path = os.path.join(TMP_DIR, f"thumbnail_{job_name}_{start_time}.jpg")
        
        thumbnail_path = get_thumbnail(video_path, start_time, output_path)
        
        if thumbnail_path:
            return send_file(thumbnail_path, mimetype='image/jpeg')
        else:
            return jsonify({'error': 'Failed to generate thumbnail'}), 500
    except Exception as e:
        logger.error(f"Error in get_thumbnail route: {str(e)}")
        return jsonify({'error': 'Failed to generate thumbnail'}), 500
    
@app.route('/create_short_video/<job_name>/<topic_index>', methods=['POST'])
def create_short_video(job_name, topic_index):
    try:
        logger.info(f"Creating short video for job: {job_name}, topic index: {topic_index}")
        
        # 클라이언트에서 전송한 시간 정보 받기
        data = request.json
        start_time = float(data.get('start_time', 0))
        end_time = float(data.get('end_time', 0))
        
        logger.info(f"Received start_time: {start_time}, end_time: {end_time}")

        transcript_key = f"{SUBTITLE_FOLDER}{job_name}.json"
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=transcript_key)
        transcript = json.loads(obj['Body'].read().decode('utf-8'))
        
        video_filename = video_job_mapping.get(job_name)
        if not video_filename:
            raise ValueError(f"No video file found for job {job_name}")
        
        video_path = os.path.join(TMP_DIR, video_filename)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # MoviePy를 사용하여 숏 비디오 생성
        video = VideoFileClip(video_path)
        
        # 비디오 길이 확인 및 시간 조정
        video_duration = video.duration
        start_time = max(0, min(start_time, video_duration))
        end_time = min(end_time, video_duration)
        
        if end_time <= start_time:
            raise ValueError(f"Invalid time range: start_time={start_time}, end_time={end_time}")
        
        duration = end_time - start_time
        if duration > 60:
            end_time = start_time + 60  # 최대 60초 제한

        logger.info(f"Extracting video segment - start time: {start_time}, end time: {end_time}")
        short_video = video.subclip(start_time, end_time)

        output_filename = f"short_{job_name}_{topic_index}.mp4"
        output_path = os.path.join(TMP_DIR, output_filename)

        logger.info(f"Writing short video to: {output_path}")
        short_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

        # if not TEST_MODE:
        short_video_key = f"short_videos/{output_filename}"
        s3.upload_file(output_path, BUCKET_NAME, short_video_key)
        short_video_url = s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': BUCKET_NAME,
                                                            'Key': short_video_key},
                                                    ExpiresIn=3600)
        
        logger.info(f"Short video created successfully. URL: {short_video_url}")
        return jsonify({'url': short_video_url})
    
    except Exception as e:
        logger.error(f"Error creating short video: {str(e)}")
        return jsonify({'error': 'Failed to create short video', 'details': str(e)}), 500
    finally:
        if 'video' in locals():
            video.close()
        if 'short_video' in locals():
            short_video.close()
    
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
