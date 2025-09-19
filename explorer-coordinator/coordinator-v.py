import meshtastic
import meshtastic.serial_interface
import time

# --- CONFIGURE THIS ---
BASE_MESSAGE = "This is a test mesasage. The time is"
SERIAL_PORT = "/dev/ttyACM0"       # change if needed (Windows example: "COM3")
# ----------------------

CHANNEL_MAP = {
    "bryant-misc": 1,
    "apt-6-alert": 2,
    "ai": 3,
}

def main():
    print(f"Connecting directly to radio on {SERIAL_PORT}...")
    
    # Connect directly to the radio over USB/serial
    interface = meshtastic.serial_interface.SerialInterface(SERIAL_PORT)
    print("Connected successfully!")
    
    channel_name = "bryant-misc"
    channel_index = CHANNEL_MAP[channel_name]
    message = BASE_MESSAGE + " " + time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Sending message: '{message}' to channel '{channel_name}' (index {channel_index})")
    
    # Send message directly into the mesh
    interface.sendText(message, channelIndex=channel_index, wantAck=True)
    print("Message sent successfully!")

    # Give some time for ack/messages before closing
    time.sleep(1)

    # Close connection when done
    interface.close()
    print("Connection closed.")

if __name__ == "__main__":
    main()
