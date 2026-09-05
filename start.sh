#!/bin/bash
source ./.venv/bin/activate

# Start the Open WebUI Pipelines server in the background
if [ -d "$HOME/pipelines" ]; then
    echo "[start.sh] Starting Pipelines server on port 9099..."
    cd "$HOME/pipelines"
    python main.py --port 9099 &
    PIPELINES_PID=$!
    cd - > /dev/null
    echo "[start.sh] Pipelines PID: $PIPELINES_PID"
else
    echo "[start.sh] WARNING: ~/pipelines not found — skipping Pipelines server."
    echo "[start.sh] Run: git clone https://github.com/open-webui/pipelines.git ~/pipelines"
fi

# Start NoorRobot
echo "[start.sh] Starting NoorRobot..."
python run.py
