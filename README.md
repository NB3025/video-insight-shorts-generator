# Video Insight Shorts Generator

Video Insight Shorts Generator는 긴 영상을 분석하여 주요 주제를 추출하고, 이를 바탕으로 짧은 동영상 클립(쇼츠)을 생성하는 웹 애플리케이션입니다. 이 도구는 긴 비디오 콘텐츠에서 핵심 내용을 빠르게 파악하고, 소셜 미디어나 마케팅에 활용할 수 있는 짧은 클립을 쉽게 만들 수 있게 해줍니다.

## 주요 기능

- 비디오 파일 업로드 및 분석
- AWS Transcribe를 사용한 음성-텍스트 변환
- AWS Bedrock (Claude 3.5)를 활용한 주제 추출 및 요약
- 주요 주제별 짧은 동영상 클립(쇼츠) 자동 생성
- 인터랙티브 트랜스크립트 제공
- 생성된 쇼츠 미리보기 및 다운로드

## 기술 스택

- Backend: Flask (Python)
- Frontend: HTML, CSS, JavaScript (jQuery)
- AWS 서비스: S3, Transcribe, Bedrock
- 추가 라이브러리: MoviePy (비디오 처리)

## 설치 및 실행

1. 레포지토리 클론
   ```
   git clone https://github.com/NB3025/video-insights-generator.git
   cd video-insights-generator
   ```

2. 가상 환경 생성 및 활성화
   ```
   python -m venv venv
   source venv/bin/activate 
   ```

3. 필요한 패키지 설치
   ```
   pip install -r requirements.txt
   ```

4. AWS 자격 증명 설정
   - AWS CLI를 설치하고 `aws configure` 명령어를 사용하여 자격 증명을 설정하세요.

5. 애플리케이션 실행
   ```
   python app.py
   ```

6. 웹 브라우저에서 `http://localhost:3000` 접속

## 사용 방법

1. 메인 페이지에서 비디오 파일을 업로드합니다.
2. 업로드된 비디오의 분석이 완료될 때까지 기다립니다.
3. 분석 결과로 나온 주요 주제들을 확인합니다.
4. 원하는 주제에 대해 "Create Short Video" 버튼을 클릭하여 짧은 동영상 클립을 생성합니다.
5. 생성된 짧은 동영상을 미리보기하거나 다운로드할 수 있습니다.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 기여

버그 리포트, 기능 제안 또는 풀 리퀘스트는 언제나 환영합니다. 기여하기 전에 프로젝트의 기여 가이드라인을 확인해 주세요.

## 연락처

프로젝트 관리자 - [Your Name](mailto:your.email@example.com)

프로젝트 링크: https://github.com/yourusername/video-insights-generator
