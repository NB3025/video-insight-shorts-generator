

let jobName;

function updateProcessStep(step) {
    $('.process-step').removeClass('active');
    $(`#step-${step}`).addClass('active');
    $(`#step-${step}`).prevAll('.process-step').addClass('completed');

    // 현재 단계 아이콘 크기 변경
    $(`#step-${step} i`).css({
        'transform': 'scale(1.2)',
        'transition': 'all 0.5s ease'
    });

    // 이전 단계 아이콘 크기 변경
    $(`#step-${step}`).prevAll('.process-step').find('i').css({
        'transform': 'scale(1.1)',
        'transition': 'all 0.5s ease'
    });

    // 다음 단계 아이콘 초기화
    $(`#step-${step}`).nextAll('.process-step').find('i').css({
        'transform': 'scale(1)',
        'transition': 'all 0.5s ease'
    });
}

function uploadVideo() {

    updateProcessStep('upload');

    var file = $('#videoFile')[0].files[0];
    if (!file) {
        alert("Please select a file to upload.");
        return;
    }

    var formData = new FormData();
    formData.append('file', file);

    $('#progressBarContainer').show();
    updateProgressBar(0);
    $('#status').text('Uploading...');
    $('#uploadBtn').prop('disabled', true);   
    $.ajax({
        url: '/upload',
        type: 'POST',
        data: formData,
        contentType: false,
        processData: false,
        xhr: function() {
            var xhr = new window.XMLHttpRequest();
            xhr.upload.addEventListener("progress", function(evt) {
                if (evt.lengthComputable) {
                    var percentComplete = evt.loaded / evt.total * 100;
                    updateProgressBar(percentComplete);
                }
            }, false);
            return xhr;
        },
        success: function(response) {
            $('#status').text('Upload complete. Processing...');
            $('#uploadedFileName').text('Analyzing: ' + response.file_name);
            jobName = response.job_name;
            checkStatus(jobName);
        },
        error: function(xhr, status, error) {
            $('#status').text('Upload failed');
            $('#uploadBtn').prop('disabled', false);
        }
    });
}

function checkStatus(jobName) {
    $.get('/status/' + jobName, function(response) {
        if (response.status === 'COMPLETED') {
            $('#status').text('Analysis completed');
            $('#progressBarContainer').hide();
            $('#uploadBtn').prop('disabled', false);
            
            updateProcessStep('bedrock');  // Bedrock 단계 활성화
            
            if (response.classification) {
                displayResults(response.classification, response.transcript);
            } else {
                $('#result').html('<p>Failed to analyze the video.</p>');
            }
            
        } else if (response.status === 'IN_PROGRESS') {
            $('#status').text('Processing: Transcribing');
            updateProcessStep('transcribe');  // Transcribe 단계 활성화
            setTimeout(function() { checkStatus(jobName); }, 5000);
        } else if (response.status === 'QUEUED') {
            $('#status').text('Processing: Queued');
            updateProcessStep('s3');  // S3 단계 활성화
            setTimeout(function() { checkStatus(jobName); }, 5000);
        } else {
            $('#status').text('Processing: ' + response.status);
            updateProcessStep('s3');  // 기본적으로 S3 단계 활성화
            setTimeout(function() { checkStatus(jobName); }, 5000);
        }
    }).fail(function(xhr, status, error) {
        $('#status').text('Error checking status');
        $('#uploadBtn').prop('disabled', false);
        console.error('Error checking status:', error);
    });
}

function displayResults(classification, transcript) {
    let topicsHtml = classification.topics.map((topic, index) => 
        `<li class="fade-in">
    <img src="/get_thumbnail/${jobName}/${topic.start_time}" alt="Topic thumbnail" class="topic-thumbnail">
            <strong class="accent-text">${topic.title}</strong> (${topic.importance})
            <p>${topic.summary}</p>
            <p>Time: ${secondsToMMSS(topic.start_time)} - ${secondsToMMSS(topic.end_time)}</p>
            <button class="create-short-video-btn accent-bg" data-topic-index="${index}" data-start-time="${topic.start_time}" data-end-time="${topic.end_time}">Create Short Video</button>
        </li>`
    ).join('');
    $('#topicsList').html(topicsHtml);

    displayInteractiveTranscript(transcript);

    showWithAnimation('#resultSection');
    showWithAnimation('#transcriptSection');

    $('.create-short-video-btn').click(function() {
        const topicIndex = $(this).data('topic-index');
        const startTime = $(this).data('start-time');
        const endTime = $(this).data('end-time');
        createShortVideo(jobName, topicIndex, startTime, endTime);
    });
}

// 인터랙티브 트랜스크립트 표시
function displayInteractiveTranscript(transcript) {
    const words = transcript.split(' ');
    const transcriptHtml = words.map((word, index) => 
        `<span data-index="${index}">${word}</span>`
    ).join(' ');
    $('#transcriptContent').html(transcriptHtml);

    $('#transcriptContent span').click(function() {
        const wordIndex = $(this).data('index');
        // 여기에 비디오 재생 위치 이동 로직 추가
        console.log(`Clicked word at index: ${wordIndex}`);
    });
}

function createShortVideo(jobName, topicIndex, startTime, endTime) {
    $('#status').text('Creating short video...');
    
    $.ajax({
        url: `/create_short_video/${jobName}/${topicIndex}`,
        type: 'POST',
        data: JSON.stringify({ start_time: startTime, end_time: endTime }),
        contentType: 'application/json',
        success: function(response) {
            if (response.url) {
                $('#status').text('Short video created successfully');
                const videoPreview = `
                    <div class="short-video-item fade-in">
                        <video width="100%" controls>
                            <source src="${response.url}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                        <p>Time: ${secondsToMMSS(startTime)} - ${secondsToMMSS(endTime)}</p>
                        <a href="${response.url}" download class="action-button">Download</a>
                    </div>`;
                $('#shortVideosPreview').append(videoPreview);
                showWithAnimation('#shortVideosSection');
            } else {
                $('#status').text('Failed to create short video');
            }
        },
        error: function() {
            $('#status').text('Error creating short video');
        }
    });
}



// 원형 프로그레스 바 업데이트
function updateProgressBar(percent) {
    $('.progress-bar').css('--progress', percent + '%');
    $('.progress-bar').text(Math.round(percent) + '%');
}

// 애니메이션 효과
function showWithAnimation(elementId) {
    $(elementId).addClass('fade-in').show();
}





function secondsToMMSS(seconds) {
    return new Date(seconds * 1000).toISOString().substr(14, 5);
}
const dropZone = document.getElementById('dropZone');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, unhighlight, false);
});

function highlight() {
    dropZone.classList.add('drag-over');
}

function unhighlight() {
    dropZone.classList.remove('drag-over');
}

dropZone.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const file = dt.files[0];
    document.getElementById('videoFile').files = dt.files;
    handleFileSelect(file);
}

function handleFileSelect(file) {
    if (file) {
        $('#fileLabel').text(file.name);
        $('.upload-button').addClass('file-selected');
    } else {
        $('#fileLabel').text('Choose File or Drag & Drop');
        $('.upload-button').removeClass('file-selected');
    }
}

$('#videoFile').on('change', function() {
    handleFileSelect(this.files[0]);
});


function showTranscript(transcript) {
    $('#transcriptContent').text(transcript);
    $('#transcriptModal').css('display', 'block');
}

// Close modal when clicking on close button or outside the modal
$('.close-button, .modal').click(function() {
    $('#transcriptModal').css('display', 'none');
});

// Prevent modal from closing when clicking inside it
$('.modal-content').click(function(event) {
    event.stopPropagation();
});

$('#videoFile').on('change', function() {
    var fileName = $(this).val().split('\\').pop();
    if (fileName) {
        $('#fileLabel').text(fileName);
        $('.upload-button').addClass('file-selected');
    } else {
        $('#fileLabel').text('Choose File');
        $('.upload-button').removeClass('file-selected');
    }
});