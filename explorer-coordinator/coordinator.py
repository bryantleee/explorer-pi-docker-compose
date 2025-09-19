import meshtastic
import meshtastic.tcp_interface
import time

# --- CONFIGURE THIS ---
MESSAGE     = "Hello, world!"          # your hello world message
# ----------------------

CHANNEL_MAP = {
    "bryant-misc": 1,
    "apt-6-alert": 2,
    "ai" : 3,
}

def main():
    print("Connecting to meshtasticd...")
    
    # Connect to a running meshtasticd instance (default gRPC port 4403)
    interface = meshtastic.tcp_interface.TCPInterface("localhost")
    
    print("Connected successfully!")
    
    channel_name = "bryant-misc"
    channel_index = CHANNEL_MAP[channel_name]
    
    print(f"Sending message: '{MESSAGE}' to channel '{channel_name}' (index {channel_index})")
    
    interface.sendText(MESSAGE, channelIndex=channel_index, wantAck=True)
    print("Message sent successfully!")

    
    # Close connection when done
    interface.close()
    print("Connection closed.")

if __name__ == "__main__":
    main()
