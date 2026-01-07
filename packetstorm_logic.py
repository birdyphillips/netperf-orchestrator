import urllib.request
import urllib.parse
import json
from datetime import datetime
from logger import Logger
from log_rotator import LogRotator

class PacketStormLogic:
    def __init__(self, rtt_config):
        self.logger = Logger("PacketStormLogic")
        self.test_id = int(datetime.now().timestamp())
        self.timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"/home/aphillips/Projects/Access_Architecture/LLD_TEST_CLT/logs/packetstorm_{self.timestamp_str}.log"
        self.log_rotator = LogRotator(self.log_file)
        
        # PacketStorm configuration
        self.url = "http://10.241.0.118/xgui/rest"
        self.username = "automation"  # Default username
        self.password = "automation"  # Default password
        self.config = rtt_config.replace('.json', '')
    
    def login_request(self):
        return json.dumps({
            "op": "login",
            "user": self.username,
            "args": {"password": self.password}
        })
    
    def start_request(self):
        return json.dumps({
            "op": "start",
            "user": self.username,
            "args": {"config": f"{self.config}.json"}
        })
    
    def stop_request(self):
        return json.dumps({
            "op": "stop",
            "user": self.username
        })
    
    def send_request(self, data):
        try:
            req = urllib.request.Request(self.url, data=data.encode('utf-8'))
            req.add_header('Content-Type', 'application/json')
            response = urllib.request.urlopen(req, timeout=30)
            response_text = response.read().decode('utf-8')
            self.logger.info(f"PacketStorm response: {response_text}")
            return response.status == 200
        except Exception as e:
            self.logger.error(f"PacketStorm request failed: {e}")
            return False
    
    def start_config(self):
        """PacketStorm: login, start config, logout"""
        try:
            self.logger.info("PacketStorm: login → start config → logout")
            
            # Login and start config
            success = (self.send_request(self.login_request()) and 
                      self.send_request(self.start_request()))
            
            log_content = f"\n=== PacketStorm Start Config ===\n"
            log_content += f"Config: {self.config}\n"
            log_content += f"Status: {'SUCCESS' if success else 'FAILED'}\n"
            self.log_rotator.write_log(log_content)
            
            return success
            
        except Exception as e:
            error_msg = f"PacketStorm start config failed: {str(e)}"
            self.logger.error(error_msg)
            self.log_rotator.write_log(f"\nERROR: {error_msg}\n")
            return False
    
    def stop_config(self):
        """PacketStorm: login, stop, logout"""
        try:
            self.logger.info("PacketStorm: login → stop → logout")
            
            # Login and stop
            success = (self.send_request(self.login_request()) and 
                      self.send_request(self.stop_request()))
            
            log_content = f"\n=== PacketStorm Stop Config ===\n"
            log_content += f"Status: {'SUCCESS' if success else 'FAILED'}\n"
            self.log_rotator.write_log(log_content)
            
            return success
            
        except Exception as e:
            error_msg = f"PacketStorm stop config failed: {str(e)}"
            self.logger.error(error_msg)
            self.log_rotator.write_log(f"\nERROR: {error_msg}\n")
            return False