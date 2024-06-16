import datetime
import socket
import time
import pynmea2
import os
import subprocess
import argparse
import threading

class GPSModule:
    def __init__(self, host='localhost', port=9000):
        self.host = host
        self.port = port
        self.tcp_connection = None
        self.buffer = ""
        self.coordinates = {'latitude': None, 'longitude': None, 'quality': None, 'timestamp': None}
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
    
    def connect(self):
        try:
            print("connect to TCP server")
            self.tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_connection.connect((self.host, self.port))
        except Exception as e:
            print(f"Error connecting to TCP server: {e}")
            self.tcp_connecti
            on = None
    
    def get_current_coordinates(self):
            try:
                while not self.stop_event.is_set():
                    if self.tcp_connection is None:
                        self.connect()
                    if self.tcp_connection:
                        try:
                            data = self.tcp_connection.recv(1024).decode('ascii', errors='replace').strip()
                            self.buffer += data
                            while '$' in self.buffer:
                                line, self.buffer = self.buffer.split('$', 1)
                                line = line.strip().strip('\n')
                                line = f"${line}"
                                try:
                                    #print(line)
                                    msg = pynmea2.parse(line)
                                    if msg.sentence_type == 'GGA':
                                        with self.lock:
                                            self.coordinates['latitude'] = msg.latitude
                                            self.coordinates['longitude'] = msg.longitude
                                            self.coordinates['quality'] = msg.gps_qual
                                            self.coordinates['timestamp'] = datetime.datetime.now()
                                    else:
                                        #print(f"Other sentence: {msg.sentence_type}")
                                        pass
                                except pynmea2.ParseError as e:
                                    print(f"Parse error, no NMEA line: {e}")
                        except Exception as e:
                            print(f"TCP error: {e}")
                            self.tcp_connection.close()
                            self.tcp_connection = None
                    else:
                        time.sleep(1)  # Wait before trying to reconnect 
            except Exception as e:
                print(f"General exception: {e}")

    def start_str2str_server(self):
        # Environment variables
        input_stream = os.getenv('STR2STR_INPUT')
        output_stream = os.getenv('STR2STR_OUTPUT')
        if not input_stream:
            raise ValueError("Environment variables STR2STR_INPUT must be set")
        
        if not output_stream:
            print("Environment variable STR2STR_OUTPUT not set, using default")
            output_stream = "serial://ttyACM0"

        # Construct the command
        command = f"str2str -in {input_stream} -b 1 -out {output_stream}"
        
        # Start the str2str server
        process = subprocess.Popen(command, shell=True)
        return process
    
    def start_reading(self):
        self.stop_event.clear()
        self.gps_thread = threading.Thread(target=self.get_current_coordinates)
        self.gps_thread.daemon = True
        self.gps_thread.start() 
    
    def stop_reading(self):
        self.stop_event.set()
        self.gps_thread.join()
        if self.tcp_connection:
            self.tcp_connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="GPS Module with optional Str2Str server")
    parser.add_argument("-str2str", action="store_true", help="Start Str2Str server")
    
    args = parser.parse_args()
    
    gps = GPSModule()

    if args.str2str:
        gps.start_str2str_server()
        print("Str2Str server started")

    gps.start_reading()
    
    # This is just to keep the main thread alive, you can replace it with your logic
    try:
        while True:
            with gps.lock:
                print(gps.coordinates)
                pass
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping GPS reading...")
        gps.stop_reading()
        print("GPS reading stopped.")
