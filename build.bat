@echo off
REM Build PeerReviewChecker for Windows
REM Output: dist\PeerReviewChecker.exe

python -m venv .venv
call .venv\Scripts\activate

pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm peer_review_checker.spec

echo.
echo Build complete.
echo Executable: dist\PeerReviewChecker.exe
echo Copy your .env file next to the .exe before distributing, or
echo users can create it themselves (see README).
