# Explorer Coordinator

A Docker containerized MQTT to Meshtastic bridge that listens for Frigate NVR events and forwards them to your Meshtastic mesh network.

## What it does

- Connects to the Mosquitto MQTT broker on the shared Docker network
- Listens for Frigate events on the `frigate/events` topic
- Forwards formatted event messages to the Meshtastic network via the `apt-6-alert` channel
- Runs as a Docker container with proper device access for the Meshtastic radio

## Prerequisites

- Docker and Docker Compose installed
- Meshtastic radio connected to `/dev/ttyACM0`
- Mosquitto MQTT broker running on the shared `explorer-network`
- Frigate NVR publishing events to MQTT

## How to run

### Using Docker Compose (Recommended)

1. Make sure all other containers (mosquitto, frigate, meshtasticd) are running on the shared network
2. From the explorer-coordinator directory:

```bash
docker compose up -d
```

### View logs

```bash
docker logs explorer-coordinator -f
```

### Stop the container

```bash
docker compose down
```

## Configuration

The main configuration is in `mqtt_meshtastic_bridge.py`:

- **MQTT_BROKER**: Set to `mosquitto` (container name)
- **MQTT_TOPIC**: Listens to `frigate/events`
- **SERIAL_PORT**: Uses `/dev/ttyACM0` for Meshtastic radio
- **CHANNEL**: Sends to `apt-6-alert` channel

## Network Requirements

This container must run on the `explorer-network` to communicate with:
- **mosquitto**: MQTT broker
- **frigate**: NVR system (via MQTT)

## Device Access

The container requires access to:
- `/dev/ttyACM0`: Meshtastic radio serial connection

## Troubleshooting

- Check container logs: `docker logs explorer-coordinator`
- Verify Meshtastic radio is connected to `/dev/ttyACM0`
- Ensure mosquitto container is running and accessible
- Check that Frigate is publishing events to the MQTT broker
