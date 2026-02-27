import os
import requests
import json
import time
import threading
import sys
import traceback
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, HTTPServer

# --- CONFIGURATION ---
BASE_URL = "https://ncod153.n-able.com"
JWT = os.environ.get("NABLE_TOKEN")
THRESHOLD_MINS = 6
DATA_FILE = "data.json"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def harvest_data():
    if not JWT:
        log("!! ERROR: NABLE_TOKEN environment variable is missing!")
        return

    while True:
        try:
            log(">>> Starting N-able Hybrid Harvest...")
            headers = {"Authorization": f"Bearer {JWT}", "Accept": "application/json"}
            auth_res = requests.post(f"{BASE_URL}/api/auth/authenticate", headers=headers, timeout=30)
            
            if auth_res.status_code != 200:
                log(f"!! AUTH FAILED: {auth_res.status_code} - {auth_res.text}")
                time.sleep(60)
                continue

            access_token = auth_res.json()['tokens']['access']['token']
            api_headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

            devices = []
            next_uri = f"{BASE_URL}/api/devices?pageSize=1000"
            while next_uri:
                res_raw = requests.get(next_uri, headers=api_headers, timeout=60)
                res_raw.raise_for_status()
                res = res_raw.json()
                devices.extend(res.get('data', []))
                next_page = res.get('_links', {}).get('nextPage')
                next_uri = f"{BASE_URL}{next_page}" if next_page else None

            wallboard_data = {}
            current_time = datetime.now(timezone.utc)

            for dev in devices:
                if "Server" in (dev.get("deviceClass") or "") and dev.get("lastApplianceCheckinTime"):
                    raw_ts = dev["lastApplianceCheckinTime"]
                    clean_ts = raw_ts[:19]
                    
                    try:
                        last_seen = datetime.strptime(clean_ts, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                        diff_mins = (current_time - last_seen).total_seconds() / 60
                        
                        # Restore the proper time formatting!
                        if diff_mins > 10080: 
                            time_display = f"{int(diff_mins / 1440)}d ago"
                        elif diff_mins > 1440:
                            time_display = f"{int(diff_mins / 60)}h ago"
                        else:
                            time_display = f"{int(diff_mins)}m ago"
                        
                        # --- CORRECTED TAKE CONTROL LOGIC ---
                        tc_status = str(dev.get("remoteControlStatus", "")).lower()
                        
                        # N-central uses "Disconnected" to mean "Healthy but no active session"
                        # We only treat it as dead if it's explicitly broken or missing
                        tc_dead_states = ["offline", "failed", "error", "not installed", "uninstalled", "none", "null", ""]
                        tc_active = tc_status not in tc_dead_states
                        
                        agent_active = (diff_mins <= THRESHOLD_MINS)
                        
                        cust = dev.get("customerName", "Unknown")
                        if cust not in wallboard_data:
                            wallboard_data[cust] = {
                                "Customer": cust, 
                                "Status": "Green", 
                                "TotalServers": 0, 
                                "IssuesCount": 0, 
                                "IssuesList": []
                            }
                        
                        wallboard_data[cust]["TotalServers"] += 1
                        
                        issue_label = None
                        severity = None
                        weight = 0

                        if not agent_active:
                            # Agent is late. Does TC prove it's alive?
                            if tc_active:
                                issue_label = "🛠️ FIX AGENT (TC Alive)"
                                severity = "warning"
                                weight = 1
                            else:
                                issue_label = "🚨 CONFIRMED DOWN"
                                severity = "critical"
                                weight = 2
                        else:
                            # Agent is fine. Did TC explicitly crash?
                            if tc_status in ["offline", "failed", "error"]:
                                issue_label = "🔌 FIX TAKE CONTROL"
                                severity = "warning"
                                weight = 0.5
                                
                        if issue_label:
                            wallboard_data[cust]["Status"] = "Red"
                            wallboard_data[cust]["IssuesCount"] += weight
                            wallboard_data[cust]["IssuesList"].append({
                                "name": dev['longName'],
                                "time": time_display,  # Uses the corrected formatted time
                                "label": issue_label,
                                "severity": severity
                            })

                    except Exception as e:
                        continue

            final_output = sorted(wallboard_data.values(), key=lambda x: (-x['IssuesCount'], x['Customer']))
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(final_output, f, indent=4)
            log("*** HARVEST SUCCESS ***")
            
        except Exception as e:
            log(f"!! ERROR: {str(e)}")
            log(traceback.format_exc())
        
        time.sleep(300)

class MyHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args): log(f"WEB: {format % args}")
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

if __name__ == "__main__":
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f: json.dump([], f)
    threading.Thread(target=harvest_data, daemon=True).start()
    HTTPServer(('0.0.0.0', 8080), MyHandler).serve_forever()
