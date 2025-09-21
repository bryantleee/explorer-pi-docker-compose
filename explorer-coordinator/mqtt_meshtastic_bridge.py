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
from zoneinfo import ZoneInfo
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
            if meshtastic_message is None:
                return
            
            # Send via Meshtastic
            self.meshtastic_interface.sendText(meshtastic_message, channelIndex=self.channel_index, wantAck=True)
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def calculate_stationary_time(self, path_data, threshold=0.01):
        """
        Calculate the total time an object was stationary based on path data.
        
        Args:
            path_data: List of tuples containing ((x, y), timestamp) coordinates
            threshold: Distance threshold in normalized units for considering movement stationary
            
        Returns:
            float: Total stationary time in seconds, rounded to 1 decimal place
        """
        if not path_data or len(path_data) < 2:
            return 0.0
            
        stationary_time = 0.0
        for i in range(1, len(path_data)):
            (x1, y1), t1 = path_data[i - 1]
            (x2, y2), t2 = path_data[i]
            dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            if dist < threshold:
                stationary_time += t2 - t1
                
        return round(stationary_time, 1)

    def construct_meshtastic_message(self, event_data, topic):
        if not isinstance(event_data, dict):
            logger.warning(f"Skipping non-dict event data: {event_data}")
            return None

        allowed_message_types = {"end"}

        event_type = event_data.get("type")
        if event_type not in allowed_message_types:
            logger.warning(f"Skipping message type: {event_type}")
            return None

        timestamp = datetime.now(ZoneInfo("America/New_York")).strftime("%I:%M:%S %p")
        
        after = event_data.get("after", {})
        before = event_data.get("before", {})
        start_time = before.get("start_time")
        end_time = after.get("end_time")

        duration = None
        if start_time and end_time:
            duration = round(end_time - start_time, 1)

        # Calculate stationary time using the extracted function
        path_data = after.get("path_data", [])
        stationary_time = self.calculate_stationary_time(path_data)

        label = (after.get("label") or before.get("label") or "object").capitalize()
        camera = after.get("camera") or before.get("camera") or "unknown"

        # Build message
        if duration is not None:
            if stationary_time:
                message = f"{timestamp} | {label} detected for {duration}s, stationary for {stationary_time}s"
            else:
                message = f"{timestamp} | {label} detected for {duration}s"
        else:
            message = f"{timestamp} | {label} detected"
        
        logger.info(f"Sending Meshtastic message: {message}")
        # Truncate if too long (leave buffer for Meshtastic overhead)
        if len(message) > 180:
            message = message[:177] + "..."

        return message

    
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
