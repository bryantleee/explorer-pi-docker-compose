#!/usr/bin/env python3

import subprocess
import sys
import time

def main():
    print("Starting Meshtastic Message Monitor...")
    print("This will show messages using the meshtastic CLI")
    print("Press Ctrl+C to stop")
    
    try:
        # Use the meshtastic CLI to listen for messages
        cmd = ["meshtastic", "--host", "localhost", "--listen"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        if 'process' in locals():
            process.terminate()
        print("Monitor stopped.")

if __name__ == "__main__":
    main()
