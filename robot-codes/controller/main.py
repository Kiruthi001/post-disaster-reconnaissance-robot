import serial
import time
import pygame
import socket

# --- Network Setup ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- Hardware Setup ---
# Note: Ensure /dev/ttyUSB0 is correct for your Windows environment (e.g., 'COM3')
try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.05)
except serial.SerialException:
    print("Could not open serial port. Check your connection.")
    exit()

time.sleep(2) 
ser.reset_input_buffer()
ser.reset_output_buffer()

pygame.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

pygame.event.pump()
pygame.event.clear()

# --- Logic Variables ---
mode = 0 # 0: Manual, 1: Smart Auto
sensor_state = "K"
current_cmd = 'S'

# New State Machine Variables
auto_state = "DRIVING" # States: DRIVING, TURNING_RIGHT, TURNING_LEFT, TURNING_BACK
state_start_time = 0
TURN_DURATION = 0.8  # Time in seconds for a 90-degree tank turn. Adjust this.

print("Mode: MANUAL. Press Button 7 (Start) to toggle SMART AUTO.")
print("Press Button 3 (Y) to toggle Lights.")
print("Hold Button 0 (A) to OVERRIDE sensor blocks.")

while True:
    pygame.event.pump()
    current_time = time.time()

    # 1. Get detailed sensor data
    if ser.in_waiting > 0:
        sensor_state = ser.readline().decode('utf-8', errors='ignore').strip()
        try:
            sock.sendto(sensor_state.encode(), (UDP_IP, UDP_PORT))
        except:
            pass

    # 2. Check for Override (Button 0 - A Button)
    override_active = joystick.get_button(0)

    # 3. Event Handling (Toggles)
    for event in pygame.event.get():
        if event.type == pygame.JOYBUTTONDOWN and event.button == 7:
            mode = 1 if mode == 0 else 0
            auto_state = "DRIVING" # Reset state when toggling
            joystick.rumble(1.0, 1.0, 400)
            print(f"SWITCHED TO: {'AUTO' if mode == 1 else 'MANUAL'}")

        if event.type == pygame.JOYBUTTONDOWN and event.button == 3:
            ser.write(b'A')
            print("Command Sent: A (Light Toggle)")

    new_cmd = 'S'

    # --- CONTROL LOGIC ---
    """
    if mode == 0: # MANUAL CONTROL
        y = joystick.get_axis(1)
        x = joystick.get_axis(0)

        if y < -0.3: # Moving Forward
            if sensor_state == "K" or override_active:
                new_cmd = 'F'
            else:
                new_cmd = 'S'
                joystick.rumble(0.5, 0.5, 50)
        elif y > 0.3: new_cmd = 'B'
        elif x < -0.3: new_cmd = 'L'
        elif x > 0.3: new_cmd = 'R'
    """
    # --- CONTROL LOGIC ---
    if mode == 0: # MANUAL CONTROL
        # get_hat(0) returns (x, y). 
        # x: -1 is Left, 1 is Right. 
        # y: -1 is Down, 1 is Up.
        dpad_x, dpad_y = joystick.get_hat(0)

        if dpad_y == 1: # Moving Forward (D-pad Up)
            if sensor_state == "K" or override_active:
                new_cmd = 'F'
            else:
                new_cmd = 'S'
                joystick.rumble(0.5, 0.5, 50)
        elif dpad_y == -1: 
            new_cmd = 'B' # Moving Backward (D-pad Down)
        elif dpad_x == -1: 
            new_cmd = 'L' # Turning Left (D-pad Left)
        elif dpad_x == 1: 
            new_cmd = 'R'  # Turning Right (D-pad Right)
            
    else: # SMART AUTO-DRIVE STATE MACHINE
        if override_active:
            new_cmd = 'F'
            auto_state = "DRIVING"
        
        elif auto_state == "DRIVING":
            if sensor_state == "K":
                new_cmd = 'F'
            else:
                # Obstacle found: Stop and initiate right turn
                new_cmd = 'S'
                auto_state = "TURNING_RIGHT"
                state_start_time = current_time
                print("Obstacle! Stopping and Turning Right...")

        elif auto_state == "TURNING_RIGHT":
            if current_time - state_start_time < TURN_DURATION:
                new_cmd = 'R' # Tank turn right
            else:
                # Finished turn, check sensors
                if sensor_state == "K":
                    auto_state = "DRIVING"
                    print("Path clear. Proceeding Right.")
                else:
                    # Still blocked, turn to the original Left 
                    # (90 deg back to center + 90 deg to face Left = 180 deg total change)
                    auto_state = "TURNING_LEFT"
                    state_start_time = current_time
                    print("Right blocked. Turning Left...")

        elif auto_state == "TURNING_LEFT":
            # Turning to the original left requires twice the turn duration
            if current_time - state_start_time < (TURN_DURATION * 2):
                new_cmd = 'L' # Tank turn left
            else:
                if sensor_state == "K":
                    auto_state = "DRIVING"
                    print("Path clear. Proceeding Left.")
                else:
                    # Still blocked, turn to face the Back
                    auto_state = "TURNING_BACK"
                    state_start_time = current_time
                    print("Left blocked. Turning to the Back...")

        elif auto_state == "TURNING_BACK":
            # Finish the rotation to face 180 degrees from start
            if current_time - state_start_time < TURN_DURATION:
                new_cmd = 'L' # Continue left turn to reach 'Back' position
            else:
                auto_state = "DRIVING"
                print("Facing Back. Proceeding.")

    # 4. Serial Communication
    if new_cmd != current_cmd:
        ser.write(new_cmd.encode())
        current_cmd = new_cmd
        print(f"Executing: {new_cmd} (Sensors: {sensor_state} | State: {auto_state})")

    time.sleep(0.05)
