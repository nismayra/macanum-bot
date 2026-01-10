import network, urequests, machine, time, socket, random, bluetooth
from machine import Pin
from ble_uart import BLEUART
led2 = Pin(28, Pin.OUT)

# =========================
# USER SETTINGS
# =========================
SSID = "linksys-2G"
PASSWORD = "ramesh82"

VERSION_URL  = "https://raw.githubusercontent.com/nismayra/macanum-bot/main/version.txt"
FIRMWARE_URL = "https://raw.githubusercontent.com/nismayra/macanum-bot/main/main.py"

WEBHOOK = "https://webhook.site/a4740314-f67a-4a56-927f-39695345b572"

# =========================
# OTA FUNCTIONS
# =========================
import os

# Files to sync in Stage 2 (After main app update)
REQUIRED_FILES = [
    ("ble_advertising.py", "https://raw.githubusercontent.com/nismayra/macanum-bot/main/ble_advertising.py"),
    ("ble_uart.py", "https://raw.githubusercontent.com/nismayra/macanum-bot/main/ble_uart.py"),
]

# Note: FIRMWARE_URL now points to app.py as that is the logic file
FIRMWARE_URL = "https://raw.githubusercontent.com/nismayra/macanum-bot/main/app.py"

def read_local_version():
    try:
        with open("version.txt","r") as f:
            return f.read().strip()
    except:
        return "0"

def write_local_version(v):
    with open("version.txt","w") as f:
        f.write(v)

def file_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
        led2.value(1)
    return wlan.ifconfig()[0]

def post_update(version, ip):
    try:
        data = {
            "device": "MECANUM_BOT",
            "event": "OTA_UPDATE",
            "version": version,
            "ip": ip
        }
        r = urequests.post(WEBHOOK, json=data)
        r.close()
    except:
        pass

def download_file(url, local_path):
    print(f"Downloading {local_path} from {url}...")
    try:
        r = urequests.get(url)
        if r.status_code == 200:
            with open(local_path, "w") as f:
                f.write(r.text)
            r.close()
            return True
        else:
            print(f"Error downloading {local_path}: Status {r.status_code}")
            r.close()
            return False
    except Exception as e:
        print(f"Exception downloading {local_path}: {e}")
        return False

def ota_check():
    ip = connect_wifi()
    print("WiFi:", ip)

    # --- STAGE 2: Dependency Sync ---
    if file_exists("stage2_pending"):
        print("OTA Stage 2: Syncing dependencies...")
        
        # Download all required helper files
        for fname, url in REQUIRED_FILES:
            download_file(url, fname)
            
        # Get remote version to finalize update
        try:
            r = urequests.get(VERSION_URL)
            remote_v = r.text.strip()
            r.close()
            
            write_local_version(remote_v)
            post_update(remote_v, ip)
            
            os.remove("stage2_pending")
            print("Stage 2 Complete. Rebooting...")
            time.sleep(2)
            machine.reset()
        except Exception as e:
            print("Stage 2 Finalization Error:", e)
            return # If we can't verify version, maybe retry next boot?

    # --- STAGE 1: Main App Update ---
    local_v = read_local_version()

    try:
        r = urequests.get(VERSION_URL)
        remote_v = r.text.strip()
        r.close()
    except:
        print("Version check failed")
        return

    print("Local:", local_v, "Remote:", remote_v)

    if remote_v != local_v:
        print("New firmware found. Starting Stage 1...")

        try:
            # 1. Download new App Logic
            print("Downloading app.py...")
            success = download_file(FIRMWARE_URL, "app.new")
            
            if success:
                # 2. Backup & Swap
                print("Creating backup and applying update...")
                try:
                    if file_exists("backup.py"):
                        os.remove("backup.py")
                    
                    os.rename("app.py", "backup.py")
                    os.rename("app.new", "app.py")
                    
                    # 3. Set Stage 2 Flag
                    with open("stage2_pending", "w") as f:
                        f.write("1")
                    
                    # NOTE: We do NOT update version.txt yet.
                    # We want Stage 2 to run on next boot.
                    
                    print("Stage 1 Complete. Rebooting for Stage 2...")
                    time.sleep(2)
                    machine.reset()
                    
                except Exception as e:
                    print(f"Error applying Stage 1: {e}")
                    # Try to revert if possible, or Supervisor will handle it
            else:
                print("Download failed.")

        except Exception as e:
            print("OTA error:", e)
    else:
        post_update(local_v, ip)

# =========================
# RUN OTA ON BOOT
# =========================
ota_check()

# =========================
# ORIGINAL MECANUM BOT LOGIC
# =========================

# MicroPython Base Code for Pico WH Magic Robots
# Released under the GNU GPL v3.0 October 2025

# Aditya Rao, IIT Madras
# 23f3000019@es.study.iitm.ac.in

# MagicThemes for the Pico WH based Magic Robot's themed mobile control panel
# Launched on Diwali, Laxmi Pooja, 2025
# This is the base code using web sockets released on 20th October 2025.

#import network
#import socket
#import time
#import random
#import urequests
#from machine import Pin

# -------- Webhook URL ---------------
#WEBHOOK = "https://webhook.site/a4740314-f67a-4a56-927f-39695345b572"

# LED Indicator
led = Pin('LED', Pin.OUT)
magic_sleep_timer = 0.2

# Mappings
# Motor Driver Objects: Front Left (FL), Rear Left (RL), Front Right (FR), Rear Right (RR)

# Left Motor Driver (Controls Rear Left and Front Left)
# Rear Left Motor (RL)
# IN1 -> GPIO 21 (Pin 27) of the Pico WH
rear_left_forward = Pin(21, Pin.OUT)
# IN2 -> GPIO 20 (Pin 26) of the Pico WH
rear_left_backward = Pin(20, Pin.OUT)

# Front Left Motor (FL)
# IN3 -> GPIO 19 (Pin 25) of the Pico WH
front_left_forward = Pin(19, Pin.OUT)
# IN4 -> GPIO 18 (Pin 24) of the Pico WH
front_left_backward = Pin(18, Pin.OUT)

# Right Motor Driver (Controls Front Right and Rear Right)
# Front Right Motor (FR)
# IN1 -> GPIO 10 (Pin 14) of the Pico WH
front_right_forward = Pin(10, Pin.OUT)
# IN2 -> GPIO 11 (Pin 15)
front_right_backward = Pin(11, Pin.OUT)

# Rear Right Motor (RR)
# IN3 -> GPIO 12 (Pin 16) of the Pico WH
rear_right_forward = Pin(12, Pin.OUT)
# IN4 -> GPIO 13 (Pin 17) of the Pico WH
rear_right_backward = Pin(13, Pin.OUT)

# Wi-Fi credentials
ssid = SSID
password = PASSWORD

def move_stop():
    """Sets all motor control pins LOW to stop all movement."""
    # Front Motors
    front_left_forward.value(0)
    front_left_backward.value(0)
    front_right_forward.value(0)
    front_right_backward.value(0)
    
    # Rear Motors
    rear_left_forward.value(0)
    rear_left_backward.value(0)
    rear_right_forward.value(0)
    rear_right_backward.value(0)

def move_forward():
    """Moves the robot straight forward using only Rear-Wheel Drive (RWD)."""
    # Front Motors: STOPPED
    front_left_forward.value(1); front_left_backward.value(0)
    front_right_forward.value(1); front_right_backward.value(0)
    
    # Rear Motors: FORWARD
    rear_left_forward.value(1); rear_left_backward.value(0)
    rear_right_forward.value(1); rear_right_backward.value(0)

def move_backward():
    """Moves the robot straight backward using only Front-Wheel Drive (FWD)."""
    # Front Motors: BACKWARD
    front_left_forward.value(0); front_left_backward.value(1)
    front_right_forward.value(0); front_right_backward.value(1)
    
    # Rear Motors: STOPPED
    rear_left_forward.value(0); rear_left_backward.value(1)
    rear_right_forward.value(0); rear_right_backward.value(1)

def move_left():
    """Moves the robot left"""
    # Front Motors: STOPPED
    front_left_forward.value(1); front_left_backward.value(0)
    front_right_forward.value(1); front_right_backward.value(0)
    
    # Rear Motors: FORWARD
    rear_left_forward.value(0); rear_left_backward.value(0)
    rear_right_forward.value(0); rear_right_backward.value(0)

def move_right():
    """Moves the robot right """
    # Front Motors: BACKWARD
    front_left_forward.value(0); front_left_backward.value(0)
    front_right_forward.value(0); front_right_backward.value(0)
    
    # Rear Motors: STOPPED
    rear_left_forward.value(1); rear_left_backward.value(0)
    rear_right_forward.value(1); rear_right_backward.value(0)



def move_forward_old():
    """Moves the robot straight forward. All wheels spin in the forward direction."""
    # Front Left (FL) Forward, Rear Left (RL) Forward
    front_left_forward.value(0); front_left_backward.value(0)
    rear_left_forward.value(1); rear_left_backward.value(0)
    
    # Front Right (FR) Forward, Rear Right (RR) Forward
    front_right_forward.value(0); front_right_backward.value(0)
    rear_right_forward.value(1); rear_right_backward.value(0)

def move_backward_old():
    """Moves the robot straight backward. All wheels spin in the backward direction."""
    # Front Left (FL) Backward, Rear Left (RL) Backward
    front_left_forward.value(0); front_left_backward.value(1)
    rear_left_forward.value(0); rear_left_backward.value(0)
    
    # Front Right (FR) Backward, Rear Right (RR) Backward
    front_right_forward.value(0); front_right_backward.value(1)
    rear_right_forward.value(0); rear_right_backward.value(0)

def move_right_old():
    """Spins the robot clockwise (turn right in place)."""
    # Left wheels forward, Right wheels backward
    
    # Left Motors Forward
    front_left_forward.value(1); front_left_backward.value(0)
    rear_left_forward.value(1); rear_left_backward.value(0)
    
    # Right Motors Backward
    front_right_forward.value(0); front_right_backward.value(1)
    rear_right_forward.value(0); rear_right_backward.value(1)

def move_left_old():
    """Spins the robot counter-clockwise (turn left in place)."""
    # Left wheels backward, Right wheels forward
    
    # Left Motors Backward
    front_left_forward.value(0); front_left_backward.value(1)
    rear_left_forward.value(0); rear_left_backward.value(1)
    
    # Right Motors Forward
    front_right_forward.value(1); front_right_backward.value(0)
    rear_right_forward.value(1); rear_right_backward.value(0)
    
def strafe_left():
    """Moves the robot directly to the left (strafe)."""
    # FL & RR Backward, FR & RL Forward
    
    # Front Left Backward, Rear Left Forward
    front_left_forward.value(0); front_left_backward.value(1)
    rear_left_forward.value(1); rear_left_backward.value(0)
    
    # Front Right Forward, Rear Right Backward
    front_right_forward.value(1); front_right_backward.value(0)
    rear_right_forward.value(0); rear_right_backward.value(1)
    time.sleep(magic_sleep_timer)
    move_stop()
    
def strafe_right():
    """Moves the robot directly to the right (strafe)."""
    # FL & RR Forward, FR & RL Backward
    
    # Front Left Forward, Rear Left Backward
    front_left_forward.value(1); front_left_backward.value(0)
    rear_left_forward.value(0); rear_left_backward.value(1)
    
    # Front Right Backward, Rear Right Forward
    front_right_forward.value(0); front_right_backward.value(1)
    rear_right_forward.value(1); rear_right_backward.value(0)
    time.sleep(magic_sleep_timer)
    move_stop()
    
# --- DIAGONAL MOVEMENT FUNCTIONS ---

def forward_left_diagonal():
    """Moves the robot diagonally forward-left."""
    # FL/RR Stop, FR/RL Forward
    move_stop() # Start with stop to clear previous state
    
    # Front Right Forward, Rear Left Forward
    front_right_forward.value(1)
    rear_left_forward.value(1)
    time.sleep(magic_sleep_timer)
    move_stop()

def forward_right_diagonal():
    """Moves the robot diagonally forward-right."""
    # FR/RL Stop, FL/RR Forward
    move_stop() # Start with stop to clear previous state
    
    # Front Left Forward, Rear Right Forward
    front_left_forward.value(1)
    rear_right_forward.value(1)
    time.sleep(magic_sleep_timer)
    move_stop()
    
def backward_left_diagonal():
    """Moves the robot diagonally backward-left."""
    # FL/RR Stop, FR/RL Backward
    move_stop() # Start with stop to clear previous state
    
    # Front Left Backward, Rear Right Backward
    front_left_backward.value(1)
    rear_right_backward.value(1)
    time.sleep(magic_sleep_timer)
    move_stop()

def backward_right_diagonal():
    """Moves the robot diagonally backward-right."""
    # FR/RL Stop, FL/RR Backward
    move_stop() # Start with stop to clear previous state
    
    # Front Right Backward, Rear Left Backward
    front_right_backward.value(1)
    rear_left_backward.value(1)
    time.sleep(magic_sleep_timer)
    move_stop()

# MAGIC function (square pattern twice)
def move_magic():
    """Executes a simple square pattern twice."""
    move_forward()
    time.sleep(magic_sleep_timer)
    move_stop()
    strafe_right()
    time.sleep(magic_sleep_timer)
    move_stop()
    move_backward()
    time.sleep(magic_sleep_timer)
    move_stop()
    strafe_left()
    time.sleep(magic_sleep_timer)
    move_stop()
    
    move_forward()
    time.sleep(magic_sleep_timer)
    move_stop()
    strafe_right()
    time.sleep(magic_sleep_timer)
    move_stop()
    move_backward()
    time.sleep(magic_sleep_timer)
    move_stop()
    strafe_left()
    time.sleep(magic_sleep_timer)
    move_stop()

# MAGIC 1 function
def move_magic_1():
    """Custom Magic Function 1"""
    move_left()
    time.sleep(0.1)
    move_stop()
    
# MAGIC 2 function
def move_magic_2():
    """Custom Magic Function 2"""
    global magic_sleep_timer
    global state
    state = f'Magic 2: Sleep {magic_sleep_timer:.1f}s'
    print(f"Current Magic 2 Sleep: {magic_sleep_timer:.1f}s")
    
    # Increment logic: Increase by 0.1, reset to 0.1 if it exceeds 1.0
    magic_sleep_timer += 0.1
    if magic_sleep_timer > 1.05: # Using 1.05 to avoid floating point precision issues
        magic_sleep_timer = 0.1
        led2.value(0)
        


# MAGIC 3 function
def move_magic_3():
    """Custom Magic Function 3"""
    move_right()
    time.sleep(0.1)
    move_stop()

def LED_On():
    led.value(1)
    led2.value(1)

def LED_Off():
    led.value(0)
    led2.value(0)

# Ensure motors are stopped at boot
move_stop()

def load_webpage_content():
    try:
        
        with open('magic.ar', 'rb') as f:
            print("Serving magic: magic.ar")            
            return f.read(), True 
    except OSError:
        try:            
            with open('alt.ar', 'r') as f:
                print("Serving other: alt.ar")                
                return f.read().encode('utf-8'), False
        except OSError:           
            print("CRITICAL ERROR: magic.ar or alt.ar not found!")
            return b"<h1>CRITICAL ERROR: magic.ar or alt.ar not found!</h1>", False



# Setup web server
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
s.bind(addr)
s.listen(1)
print('Listening on', addr)

# Setup BLE
ble = bluetooth.BLE()
uart = BLEUART(ble, name="MecanumBot")

state = "OFF"
random_value = 0

# --- COMMAND PROCESSING ---
def process_command(cmd):
    """Processes a single character command"""
    global state, magic_sleep_timer
    
    # Simple standardized commands (Bluetooth App Protocol)
    if cmd == 'F':
        move_forward()
        state = 'Moving Forward'
    elif cmd == 'B':
        move_backward()
        state = 'Moving Backward'
    elif cmd == 'R':
        move_right() # Spin Right
        state = 'Spinning Right'
    elif cmd == 'L':
        move_left() # Spin Left
        state = 'Spinning Left'
    elif cmd == 'G':
        forward_left_diagonal()
        state = 'FWD Left Diagonal'
    elif cmd == 'H':
        forward_right_diagonal()
        state = 'FWD Right Diagonal'
    elif cmd == 'I':
        backward_left_diagonal()
        state = 'BKWD Left Diagonal'
    elif cmd == 'J':
        backward_right_diagonal()
        state = 'BKWD Right Diagonal'
    elif cmd == 'S':
        move_stop()
        state = 'Stopped'
    elif cmd == 'Y':
        move_magic()
        state = 'MAGIC Activated'
    elif cmd == 'U':
        LED_On()
        state = 'Headlight ON'
    elif cmd == 'u':
        LED_Off()
        state = 'Headlight OFF'

# Make socket non-blocking for Cooperative Multitasking
s.settimeout(0.01)

def on_rx():
    """Interrupt handler for BLE Data"""
    # We can process data here or in main loop. 
    # For simplicity/safety with motor code, we'll just let main loop poll, 
    # or just read buffer here. 
    # Careful: Interrupt context.
    pass

uart.irq(on_rx)

while True:
    try:
        # 1. Check BLE
        if uart.any():
            data = uart.read().decode().strip()
            print("BLE Command:", data)
            # Some apps send "F", some "F\r\n".
            # Some might send stream "FFFFF". 
            # We take the last valid char or process all?
            # Processing all might cause lag. Let's process the last meaningful char if burst?
            # Or iterate.
            for char in data:
                process_command(char)
        
        # 2. Check Web Server
        try:
            conn, addr = s.accept() # Will raise OS error if timeout
            print('Got a connection from mobile/laptop: ', addr)
            
            # Receive and process the HTTP request
            request = conn.recv(1024)
            request_str = str(request)
            
            try:
                # Extract the path (e.g., '/forward', '/stop')
                path = request_str.split(' ')[1]
            except IndexError:
                path = '/'

            client_accepts_gzip = b'Accept-Encoding: gzip' in request
            
            # --- WEB ROUTES HANDLER --- (Legacy + Web Interface)
            if path == '/lighton':
                process_command('U')
            elif path == '/lightoff':
                process_command('u')
            elif path == '/forward':
                process_command('F')
                time.sleep(magic_sleep_timer)
                process_command('S')
            elif path == '/backward':
                process_command('B')
                time.sleep(magic_sleep_timer)
                process_command('S')
            elif path == '/left':
                process_command('L')
                time.sleep(magic_sleep_timer)
                process_command('S')
            elif path == '/right':
                process_command('R')
                time.sleep(magic_sleep_timer)
                process_command('S')
            elif path == '/stop':
                process_command('S')
            
            # Direct mapping for original diagonals/specifics not in single-char standard
            elif path == '/strafe_left':
                strafe_left()
                state = 'Strafing Left'
                time.sleep(magic_sleep_timer)
                move_stop()
            elif path == '/strafe_right':
                strafe_right()
                state = 'Strafing Right'
                time.sleep(magic_sleep_timer)
                move_stop()
            elif path == '/front_left':
                process_command('G')
                time.sleep(magic_sleep_timer)
                process_command('S')
            elif path == '/front_right':
                process_command('H')
                time.sleep(magic_sleep_timer)
                process_command('S')
            elif path == '/back_left':
                process_command('I')
                time.sleep(magic_sleep_timer)
                process_command('S')
            elif path == '/back_right':
                process_command('J')
                time.sleep(magic_sleep_timer)
                process_command('S')
            
            # Magic modes (Not in BLE standard)
            elif path == '/magic':
                move_magic()
                state = 'MAGIC Activated'
            elif path == '/magic1':
                move_magic_1()
                state = 'MAGIC 1 Activated'
            elif path == '/magic2':
                move_magic_2()
                state = 'MAGIC 2 Activated'
            elif path == '/magic3':
                move_magic_3()
                state = 'MAGIC 3 Activated'

            # Individual Wheel Control (Legacy)
            elif path == '/fl_fw':
                move_stop(); front_left_forward.value(1); time.sleep(magic_sleep_timer); move_stop()
            elif path == '/fl_rev':
                move_stop(); front_left_backward.value(1); time.sleep(magic_sleep_timer); move_stop()
            elif path == '/fr_fw':
                move_stop(); front_right_forward.value(1); time.sleep(magic_sleep_timer); move_stop()
            elif path == '/fr_rev':
                move_stop(); front_right_backward.value(1); time.sleep(magic_sleep_timer); move_stop()
            elif path == '/rl_fw':
                move_stop(); rear_left_forward.value(1); time.sleep(magic_sleep_timer); move_stop()
            elif path == '/rl_rev':
                move_stop(); rear_left_backward.value(1); time.sleep(magic_sleep_timer); move_stop()
            elif path == '/rr_fw':
                move_stop(); rear_right_forward.value(1); time.sleep(magic_sleep_timer); move_stop()
            elif path == '/rr_rev':
                move_stop(); rear_right_backward.value(1); time.sleep(magic_sleep_timer); move_stop()
            
            
            if IS_GZIPPED and client_accepts_gzip:            
                header = 'HTTP/1.0 200 OK\r\nContent-Encoding: gzip\r\nContent-type: text/html\r\n\r\n'
                response_content = HTML_CONTENT
            else:            
                header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
                response_content = HTML_CONTENT
            
            conn.send(header.encode('utf-8'))
            conn.send(response_content) 
            conn.close()

        except OSError as e:
            if e.errno == 110: # ETIMEDOUT
                # Normal, just loop back
                pass 
            else:
                # Actual error
                pass

    except OSError as e:
        
        print(f"Error: {e}. Closing connection.")
        try:
            conn.close()
        except NameError:
            pass
        time.sleep(0.05)
