#!/bin/bash

SESSION="robot_control"

# Start a new tmux session and name it
tmux new-session -d -s $SESSION -n "Main"

# Pane 1: MediaMTX (Top Left)
tmux send-keys -t $SESSION "/usr/local/bin/mediamtx mediamtx.yml" C-m

# Pane 2: Controller (Top Right)
tmux split-window -h -t $SESSION
tmux send-keys -t $SESSION "cd ~/controller && source venv/bin/activate && python3 main.py" C-m

# Pane 3: Robot Vision (Bottom Left)
tmux split-window -v -t $SESSION:0.0
tmux send-keys -t $SESSION "cd ~/robot_vision && source venv/bin/activate && python3 main.py" C-m

# Pane 4: Server (Bottom Middle)
tmux split-window -h -t $SESSION:0.1
tmux send-keys -t $SESSION "cd ~/server && source venv/bin/activate && python3 main.py" C-m

# Pane 5: LoRa (Bottom Right)
tmux split-window -h -t $SESSION:0.2
tmux send-keys -t $SESSION "cd ~/lora && source venv/bin/activate && python3 server.py" C-m

# Arrange panes into a tiled layout
tmux select-layout -t $SESSION tiled

# Attach to the session
tmux attach-session -t $SESSION
