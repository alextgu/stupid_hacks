#!/usr/bin/env python3
"""
Cross-platform cursor WebSocket server

Python server that receives `dx, dy` deltas over WebSocket and moves the cursor
using pynput for cross-platform compatibility (Windows, macOS, Linux).
"""

import asyncio
import json
import logging
import math
import os
import signal
import socket
import sys
import time
import threading
from typing import Optional, Tuple

import websockets
from pynput.mouse import Button, Listener as MouseListener
from pynput import mouse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class CursorServer:
    def __init__(self):
        # Configuration from environment variables
        self.port = int(os.getenv('PORT', '8080'))
        self.gain = float(os.getenv('GAIN', '1.2'))
        self.max_step = float(os.getenv('MAX_STEP', '60'))
        self.friction = float(os.getenv('FRICTION', '0.12'))
        self.debug = os.getenv('DEBUG') == '1'
        self.selftest = os.getenv('SELFTEST') == '1'
        
        # Velocity integrator for smoothing
        self.vx = 0.0
        self.vy = 0.0
        
        # Diagnostics
        self.msgs = 0
        self.last_pos = None
        
        # Mouse controller
        self.mouse_controller = mouse.Controller()
        self.last_pos = self.mouse_controller.position
        
        # WebSocket server
        self.server = None
        self.connected_clients = set()
        
        # Start diagnostics monitoring
        self._start_diagnostics()
        
        # Start selftest if enabled
        if self.selftest:
            self._start_selftest()

    def _start_diagnostics(self):
        """Start the diagnostics monitoring thread"""
        def monitor():
            while True:
                time.sleep(2)
                try:
                    now_pos = self.mouse_controller.position
                    moved = (now_pos[0] != self.last_pos[0] or 
                            now_pos[1] != self.last_pos[1])
                    
                    if not moved and self.msgs > 10:
                        logger.warning(
                            'No cursor movement detected despite incoming data. '
                            'Check system permissions.'
                        )
                    
                    if self.msgs > 0:
                        status = '' if moved else ' (no-move)'
                        logger.info(f'Msgs last 2s: {self.msgs}{status}')
                    
                    self.msgs = 0
                    self.last_pos = now_pos
                except Exception as e:
                    logger.error(f'Diagnostics error: {e}')
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def _start_selftest(self):
        """Start the selftest cursor jiggle"""
        logger.info('SELFTEST enabled: moving cursor slightly every 1s')
        
        def selftest():
            while True:
                time.sleep(1)
                try:
                    pos = self.mouse_controller.position
                    self.mouse_controller.position = (pos[0] + 1, pos[1] + 1)
                    time.sleep(0.01)  # Small delay
                    self.mouse_controller.position = pos
                except Exception as e:
                    logger.error(f'Selftest error: {e}')
        
        thread = threading.Thread(target=selftest, daemon=True)
        thread.start()

    def _get_local_ips(self) -> list:
        """Get local network interface IP addresses"""
        ips = []
        try:
            # Connect to a dummy address to find the local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
                ips.append(local_ip)
        except Exception:
            pass
        
        # Alternative method using hostname
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip not in ips:
                ips.append(local_ip)
        except Exception:
            pass
            
        return ips

    async def handle_client(self, websocket):
        """Handle WebSocket client connection"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f'Client connected: {client_addr}')
        
        self.connected_clients.add(websocket)
        
        try:
            async for message in websocket:
                self.msgs += 1
                try:
                    data = json.loads(message)
                    
                    if not isinstance(data, dict):
                        continue
                    
                    dx = data.get('dx')
                    dy = data.get('dy')
                    
                    if not isinstance(dx, (int, float)) or not isinstance(dy, (int, float)):
                        continue
                    
                    # Apply gain and clamp per-frame step
                    dx = float(dx) * self.gain
                    dy = float(dy) * self.gain
                    
                    step_mag = math.hypot(dx, dy)
                    if step_mag > self.max_step and step_mag > 0:
                        scale = self.max_step / step_mag
                        dx *= scale
                        dy *= scale
                    
                    # Exponential smoothing on velocity
                    self.vx = self.vx * (1 - self.friction) + dx * self.friction
                    self.vy = self.vy * (1 - self.friction) + dy * self.friction
                    
                    # Get current position and calculate next position
                    pos = self.mouse_controller.position
                    next_x = round(pos[0] + self.vx)
                    next_y = round(pos[1] + self.vy)
                    
                    # Move the mouse
                    self.mouse_controller.position = (next_x, next_y)
                    
                    if self.debug:
                        logger.info(
                            f'dx={dx:.2f} dy={dy:.2f} | '
                            f'v=({self.vx:.2f}, {self.vy:.2f}) -> '
                            f'({next_x}, {next_y})'
                        )
                        
                except json.JSONDecodeError:
                    logger.error('Failed to parse JSON message')
                except Exception as e:
                    logger.error(f'Failed to process message: {e}')
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f'Client handler error: {e}')
        finally:
            self.connected_clients.discard(websocket)
            logger.info(f'Client disconnected: {client_addr}')

    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f'WebSocket listening on ws://0.0.0.0:{self.port}')
        
        # Show local IP addresses
        local_ips = self._get_local_ips()
        if local_ips:
            ip_urls = [f'ws://{ip}:{self.port}' for ip in local_ips]
            logger.info(f'Local IPs: {", ".join(ip_urls)}')
        
        logger.info('Env tuning: GAIN, MAX_STEP, FRICTION')
        
        # Start the server
        # websockets v15+ passes only the connection object to the handler
        self.server = await websockets.serve(
            self.handle_client,
            '0.0.0.0',
            self.port
        )
        
        return self.server

    async def shutdown(self):
        """Shutdown the server gracefully"""
        logger.info('Shutting down...')
        if self.server:
            self.server.close()
            await self.server.wait_closed()

async def main():
    """Main server entry point"""
    server_instance = CursorServer()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f'Received signal {signum}')
        # Create a new event loop for shutdown if needed
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(server_instance.shutdown())
        except RuntimeError:
            pass
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the server
        await server_instance.start_server()
        
        # Keep the server running
        await asyncio.Future()  # Run forever
        
    except KeyboardInterrupt:
        await server_instance.shutdown()
    except Exception as e:
        logger.error(f'Server error: {e}')
        await server_instance.shutdown()

if __name__ == '__main__':
    asyncio.run(main())