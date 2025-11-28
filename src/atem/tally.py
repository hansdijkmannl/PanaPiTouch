"""
Blackmagic ATEM Tally Integration

Connects to ATEM switchers to receive tally information for cameras.
"""
import threading
import time
from typing import Dict, Callable, Optional
from dataclasses import dataclass
from enum import Enum


class TallyState(Enum):
    """Tally state for a camera"""
    OFF = 0
    PREVIEW = 1  # Green - camera is in preview
    PROGRAM = 2  # Red - camera is live/on-air


@dataclass
class TallyInfo:
    """Tally information for an input"""
    input_id: int
    state: TallyState
    input_name: str = ""


class ATEMTallyController:
    """
    ATEM Tally Controller
    
    Connects to Blackmagic ATEM switchers and monitors tally state.
    Uses PyATEMMax library for communication.
    """
    
    def __init__(self, ip_address: str = ""):
        self.ip_address = ip_address
        self._atem = None
        self._connected = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list = []
        self._tally_state: Dict[int, TallyState] = {}
        self._input_names: Dict[int, str] = {}
        self._lock = threading.Lock()
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def add_tally_callback(self, callback: Callable[[int, TallyState], None]):
        """Add callback for tally changes"""
        self._callbacks.append(callback)
    
    def remove_tally_callback(self, callback: Callable[[int, TallyState], None]):
        """Remove tally callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, input_id: int, state: TallyState):
        """Notify all callbacks of tally change"""
        for callback in self._callbacks:
            try:
                callback(input_id, state)
            except Exception as e:
                print(f"Tally callback error: {e}")
    
    def get_tally_state(self, input_id: int) -> TallyState:
        """Get current tally state for input"""
        with self._lock:
            return self._tally_state.get(input_id, TallyState.OFF)
    
    def get_input_name(self, input_id: int) -> str:
        """Get input name from ATEM"""
        with self._lock:
            return self._input_names.get(input_id, f"Input {input_id}")
    
    def _connection_loop(self):
        """Main connection and monitoring loop"""
        try:
            import PyATEMMax
            
            while self._running:
                try:
                    # Create ATEM connection
                    self._atem = PyATEMMax.ATEMMax()
                    self._atem.connect(self.ip_address)
                    
                    # Wait for connection
                    timeout = 10
                    while not self._atem.connected and timeout > 0 and self._running:
                        time.sleep(0.5)
                        timeout -= 0.5
                    
                    if not self._atem.connected:
                        print(f"Failed to connect to ATEM at {self.ip_address}")
                        self._connected = False
                        time.sleep(5)
                        continue
                    
                    self._connected = True
                    print(f"Connected to ATEM at {self.ip_address}")
                    
                    # Get input names
                    self._update_input_names()
                    
                    # Monitor tally state
                    while self._running and self._atem.connected:
                        self._update_tally_state()
                        time.sleep(0.05)  # 50ms polling
                    
                    self._connected = False
                    
                except Exception as e:
                    print(f"ATEM connection error: {e}")
                    self._connected = False
                    time.sleep(5)
                    
        except ImportError:
            print("PyATEMMax not installed. ATEM tally disabled.")
            self._connected = False
    
    def _update_input_names(self):
        """Update input names from ATEM"""
        if not self._atem:
            return
        
        try:
            with self._lock:
                # Get input names for inputs 1-20 (typical ATEM range)
                for i in range(1, 21):
                    try:
                        name = self._atem.inputProperties.get(i, {}).get('longName', f'Input {i}')
                        self._input_names[i] = name
                    except:
                        self._input_names[i] = f"Input {i}"
        except Exception as e:
            print(f"Error getting input names: {e}")
    
    def _update_tally_state(self):
        """Update tally state from ATEM"""
        if not self._atem:
            return
        
        try:
            # Get program and preview inputs
            program_input = self._atem.programInput.get(0, 0)  # ME 0
            preview_input = self._atem.previewInput.get(0, 0)  # ME 0
            
            with self._lock:
                # Check each input for tally state
                for input_id in range(1, 21):
                    old_state = self._tally_state.get(input_id, TallyState.OFF)
                    
                    if input_id == program_input:
                        new_state = TallyState.PROGRAM
                    elif input_id == preview_input:
                        new_state = TallyState.PREVIEW
                    else:
                        new_state = TallyState.OFF
                    
                    if new_state != old_state:
                        self._tally_state[input_id] = new_state
                        # Notify outside lock
                        threading.Thread(
                            target=self._notify_callbacks,
                            args=(input_id, new_state),
                            daemon=True
                        ).start()
                        
        except Exception as e:
            print(f"Error updating tally state: {e}")
    
    def connect(self, ip_address: str = None):
        """Connect to ATEM switcher"""
        if ip_address:
            self.ip_address = ip_address
        
        if not self.ip_address:
            print("No ATEM IP address configured")
            return
        
        if self._running:
            self.disconnect()
        
        self._running = True
        self._thread = threading.Thread(target=self._connection_loop, daemon=True)
        self._thread.start()
    
    def disconnect(self):
        """Disconnect from ATEM"""
        self._running = False
        
        if self._atem:
            try:
                self._atem.disconnect()
            except:
                pass
            self._atem = None
        
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        
        self._connected = False
        
        # Reset all tally states
        with self._lock:
            for input_id in list(self._tally_state.keys()):
                if self._tally_state[input_id] != TallyState.OFF:
                    self._tally_state[input_id] = TallyState.OFF
                    self._notify_callbacks(input_id, TallyState.OFF)
    
    def test_connection(self, ip_address: str = None) -> tuple:
        """Test ATEM connection"""
        test_ip = ip_address or self.ip_address
        
        if not test_ip:
            return False, "No IP address specified"
        
        try:
            import PyATEMMax
            
            atem = PyATEMMax.ATEMMax()
            atem.connect(test_ip)
            
            # Wait for connection
            timeout = 5
            while not atem.connected and timeout > 0:
                time.sleep(0.5)
                timeout -= 0.5
            
            if atem.connected:
                product_name = atem.atemModel or "Unknown ATEM"
                atem.disconnect()
                return True, f"Connected to {product_name}"
            else:
                return False, "Connection timeout"
                
        except ImportError:
            return False, "PyATEMMax not installed"
        except Exception as e:
            return False, str(e)

