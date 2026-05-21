#!/usr/bin/env bash
# Build PeerReviewChecker for macOS / Linux
# Output: dist/PeerReviewChecker  (Linux)
#         dist/PeerReviewChecker.app  (macOS)
set -e

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm peer_review_checker.spec

echo ""
echo "Build complete."
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "App bundle: dist/PeerReviewChecker.app"
    echo "Copy your .env file next to the .app before distributing, or"
    echo "users can create it themselves (see README)."
else
    echo "Executable: dist/PeerReviewChecker"
    echo "Copy your .env file next to the executable before distributing."
fi
