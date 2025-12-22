@echo off
REM 꿀템장바구니 자동 수집 스케줄러
REM Windows 작업 스케줄러에서 이 파일을 등록하세요

cd /d "%~dp0"
cd crawler

REM Python 가상환경 활성화 (필요시 경로 수정)
REM call ..\venv\Scripts\activate

REM 스케줄러 실행
python scheduler.py --force --max-videos 20

REM 완료 로그
echo [%date% %time%] Scheduler completed >> ..\data\logs\scheduler_batch.log
