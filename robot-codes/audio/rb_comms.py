import socket
import pyaudio
import numpy as np
import threading

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 1024
DEVICE_INDEX = 0      # Your USB sound card
PC_IP = '10.41.141.105' # Your Windows 11 IP

# Noise Reduction & Gate Settings
GAIN_FACTOR = 8       # Adjusted for clarity
NOISE_THRESHOLD = 450 # Lowered slightly to be more sensitive
HOLD_TIME = 15        # Number of chunks to keep the gate open (~300ms)

p = pyaudio.PyAudio()

def rx_thread():
    """Receives audio from PC and plays on Robot speakers"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 5000))
    server_socket.listen(1)
    
    stream_out = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, 
                        output_device_index=DEVICE_INDEX, frames_per_buffer=CHUNK)
    
    print("Robot RX: Ready.")
    conn, addr = server_socket.accept()
    
    try:
        while True:
            data = conn.recv(CHUNK)
            if not data: break
            stream_out.write(data)
    except Exception as e:
        print(f"Robot RX Error: {e}")
    finally:
        stream_out.close()
        conn.close()

def tx_thread():
    """Reads Robot mic with Noise Gate and Hold Time"""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    stream_in = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, 
                       input_device_index=DEVICE_INDEX, frames_per_buffer=CHUNK)
    
    hold_counter = 0  # Counter for "Hysteresis"
    
    print(f"Robot TX: Connecting to {PC_IP}...")
    try:
        client_socket.connect((PC_IP, 5001))
        while True:
            raw_data = stream_in.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(raw_data, dtype=np.int16)
            
            # Calculate volume level (RMS)
            rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
            
            if rms > NOISE_THRESHOLD:
                # If talking, reset the hold counter
                hold_counter = HOLD_TIME
            
            if hold_counter > 0:
                # Apply gain and send the data
                boosted_data = (audio_data.astype(np.float32) * GAIN_FACTOR)
                boosted_data = np.clip(boosted_data, -32768, 32767).astype(np.int16)
                client_socket.sendall(boosted_data.tobytes())
                hold_counter -= 1
            else:
                # Send near-silence or skip sending to save bandwidth
                # We send a small chunk of zeroes to keep the socket alive
                client_socket.sendall(np.zeros(CHUNK, dtype=np.int16).tobytes())
                
    except Exception as e:
        print(f"Robot TX Error: {e}")
    finally:
        stream_in.close()
        client_socket.close()

if __name__ == "__main__":
    # Start threads
    t1 = threading.Thread(target=rx_thread, daemon=True)
    t2 = threading.Thread(target=tx_thread, daemon=True)
    t1.start()
    t2.start()
    try:
        while True: threading.Event().wait(1)
    except KeyboardInterrupt:
        p.terminate()