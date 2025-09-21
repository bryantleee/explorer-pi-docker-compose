#!/usr/bin/env python3
"""
MQTT to Meshtastic Bridge
Listens for MQTT events and forwards them to Meshtastic network via apt-6-alert channel.
"""

import json
import time
import paho.mqtt.client as mqtt
import meshtastic
import meshtastic.serial_interface
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURE THIS ---
SERIAL_PORT = "/dev/ttyACM0"       # change if needed (Windows example: "COM3")
MQTT_BROKER = "mosquitto"          # MQTT broker address (container name)
MQTT_PORT = 1883                   # MQTT broker port
MQTT_TOPIC = "frigate/events"      # MQTT topic to listen to
MQTT_USERNAME = None               # MQTT username (None if no auth)
MQTT_PASSWORD = None               # MQTT password (None if no auth)
# ----------------------

CHANNEL_MAP = {
    "bryant-misc": 1,
    "apt-6-alert": 2,
    "ai": 3,
}

class MQTTMeshtasticBridge:
    def __init__(self):
        self.meshtastic_interface = None
        self.mqtt_client = None
        self.channel_name = "apt-6-alert"
        self.channel_index = CHANNEL_MAP[self.channel_name]
        
    def connect_meshtastic(self):
        """Connect to Meshtastic radio"""
        try:
            logger.info(f"Connecting to Meshtastic radio on {SERIAL_PORT}...")
            self.meshtastic_interface = meshtastic.serial_interface.SerialInterface(SERIAL_PORT)
            logger.info("Connected to Meshtastic successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Meshtastic: {e}")
            return False
    
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            # Use the latest callback API version (VERSION2)
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            
            # Set up MQTT callbacks
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            
            # Set authentication if provided
            if MQTT_USERNAME and MQTT_PASSWORD:
                self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            
            logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def on_mqtt_connect(self, client, userdata, connect_flags, reason_code, properties):
        """MQTT connection callback"""
        if reason_code == 0:
            logger.info("Connected to MQTT broker successfully!")
            client.subscribe(MQTT_TOPIC)
            logger.info(f"Subscribed to topic: {MQTT_TOPIC}")
        else:
            logger.error(f"Failed to connect to MQTT broker. Reason code: {reason_code}")
    
    def on_mqtt_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """MQTT disconnection callback"""
        if reason_code != 0:
            logger.warning(f"Unexpected MQTT disconnection. Will auto-reconnect.")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            # Parse the MQTT message
            payload = msg.payload.decode('utf-8')
            logger.info(f"Received MQTT message on {msg.topic}: {payload}")
            
            # Parse JSON payload
            try:
                event_data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"Non-JSON payload received: {payload}")
                event_data = {"raw_message": payload}
            
            # Format message for Meshtastic
            meshtastic_message = self.construct_meshtastic_message(event_data, msg.topic)
            
            # Send via Meshtastic
            self.send_meshtastic_message(meshtastic_message)
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def construct_meshtastic_message(self, event_data, topic):
        # allowed_message_types = set({"end"})

        """Format MQTT event data into a concise Meshtastic message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Extract key information based on common MQTT event structures
        message_parts = [f"[{timestamp}]"]
        
        # Handle different types of events
        if isinstance(event_data, dict):
            # Frigate events (common structure)
            if "type" in event_data:
                message_parts.append(f"Type: {event_data['type']}")
            
            if "camera" in event_data:
                message_parts.append(f"Cam: {event_data['camera']}")
            
            if "label" in event_data:
                message_parts.append(f"Label: {event_data['label']}")
            
            if "score" in event_data:
                score = float(event_data['score']) * 100
                message_parts.append(f"Conf: {score:.0f}%")
            
            if "id" in event_data:
                message_parts.append(f"ID: {event_data['id']}")
            
            # Handle motion/object detection
            if "after" in event_data and "id" in event_data["after"]:
                message_parts.append(f"Motion: {event_data['after']['id']}")
            
            # Handle zone events
            if "current_zones" in event_data:
                zones = event_data["current_zones"]
                if zones:
                    message_parts.append(f"Zone: {','.join(zones)}")
            
            # Handle raw messages
            if "raw_message" in event_data:
                raw_msg = event_data["raw_message"][:50]  # Truncate long messages
                message_parts.append(f"Msg: {raw_msg}")
        
        # Join parts and ensure under 200 bytes
        message = " | ".join(message_parts)
        
        # Truncate if too long (leave some buffer for Meshtastic overhead)
        if len(message) > 180:
            message = message[:177] + "..."
        
        return message
    
    def send_meshtastic_message(self, message):
        """Send message via Meshtastic"""
        if not self.meshtastic_interface:
            logger.error("Meshtastic interface not connected")
            return
        
        try:
            logger.info(f"Sending to {self.channel_name}: {message}")
            self.meshtastic_interface.sendText(
                message, 
                channelIndex=self.channel_index, 
                wantAck=True
            )
            logger.info("Message sent successfully!")
        except Exception as e:
            logger.error(f"Failed to send Meshtastic message: {e}")
    
    def run(self):
        """Main run loop"""
        logger.info("Starting MQTT to Meshtastic Bridge...")
        
        # Connect to Meshtastic
        if not self.connect_meshtastic():
            logger.error("Failed to connect to Meshtastic. Exiting.")
            return
        
        # Connect to MQTT
        if not self.connect_mqtt():
            logger.error("Failed to connect to MQTT. Exiting.")
            return
        
        try:
            # Start MQTT loop
            logger.info("Starting MQTT message loop...")
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal. Shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up connections"""
        if self.mqtt_client:
            self.mqtt_client.disconnect()
            logger.info("Disconnected from MQTT broker")
        
        if self.meshtastic_interface:
            self.meshtastic_interface.close()
            logger.info("Disconnected from Meshtastic radio")

def main():
    bridge = MQTTMeshtasticBridge()
    bridge.run()

if __name__ == "__main__":
    main()
