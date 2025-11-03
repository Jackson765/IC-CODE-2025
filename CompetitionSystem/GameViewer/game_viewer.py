#!/usr/bin/env python3
"""
Game Viewer - Tournament Management System
Displays multiple robot video feeds and manages game state
"""

import json
import os
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, List
from datetime import datetime

# Game Viewer Configuration
GV_CONFIG = {
    "gv_ip": "0.0.0.0",  # Listen on all interfaces
    "gv_port": 6000,
    "max_teams": 8,
    "game_duration": 120,  # 2 minutes (configurable)
    "points_per_hit": 100,
    "video_ports_start": 5001  # Team 1 = 5001, Team 2 = 5002, etc.
}

CONFIG_FILE = "game_viewer_config.json"


class GameViewer:
    """Main game viewer application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎯 LASER TAG - Game Viewer")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a1a')
        
        # Load config
        self.config = self.load_config()
        
        # Game state
        self.teams: Dict[int, dict] = {}  # team_id -> team_data
        self.game_active = False
        self.game_start_time = 0
        self.game_time_remaining = 0
        
        # Network
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(0.1)
        
        # Bind to port
        try:
            self.sock.bind((self.config['gv_ip'], self.config['gv_port']))
            print(f"[GV] Listening on {self.config['gv_ip']}:{self.config['gv_port']}")
        except Exception as e:
            messagebox.showerror("Network Error", f"Failed to bind to port: {e}")
            sys.exit(1)
        
        # Hit log
        self.hit_log: List[dict] = []
        
        # Threading
        self.running = True
        
        # Setup GUI
        self.setup_gui()
        
        # Start network listener
        self.start_network_thread()
        
        # Start heartbeat sender
        self.start_heartbeat_thread()
        
        # Start update loop
        self.update_gui()
        
        # Cleanup handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_config(self):
        """Load configuration"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return GV_CONFIG.copy()
    
    def save_config(self):
        """Save configuration"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[GV] Failed to save config: {e}")
    
    def setup_gui(self):
        """Create GUI"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text="🎯 LASER TAG TOURNAMENT - GAME VIEWER",
                              font=('Arial', 24, 'bold'), bg='#1a1a1a', fg='#00ff00')
        title_label.pack(pady=(0, 10))
        
        # Top section - Game status and timer
        top_section = tk.Frame(main_frame, bg='#1a1a1a')
        top_section.pack(fill=tk.X, pady=(0, 10))
        
        # Game status
        status_frame = tk.LabelFrame(top_section, text="🎮 Game Status",
                                     font=('Arial', 12, 'bold'), bg='#2d2d2d', fg='#00ff00')
        status_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.game_status_label = tk.Label(status_frame, text="Status: Waiting",
                                          font=('Arial', 16, 'bold'), bg='#2d2d2d', fg='yellow')
        self.game_status_label.pack(pady=10)
        
        self.timer_label = tk.Label(status_frame, text="Time: 00:00",
                                    font=('Arial', 14), bg='#2d2d2d', fg='white')
        self.timer_label.pack(pady=5)
        
        # Control panel
        control_frame = tk.LabelFrame(top_section, text="🎛️ Control Panel",
                                      font=('Arial', 12, 'bold'), bg='#2d2d2d', fg='#00ff00')
        control_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        btn_frame = tk.Frame(control_frame, bg='#2d2d2d')
        btn_frame.pack(pady=10)
        
        self.ready_check_btn = tk.Button(btn_frame, text="📢 Ready Check",
                                         command=self.send_ready_check,
                                         font=('Arial', 10), bg='#FF9800', fg='white', width=15)
        self.ready_check_btn.pack(pady=2)
        
        self.start_game_btn = tk.Button(btn_frame, text="▶️ Start Game",
                                        command=self.start_game,
                                        font=('Arial', 10, 'bold'), bg='#4CAF50', fg='white', width=15)
        self.start_game_btn.pack(pady=2)
        
        self.end_game_btn = tk.Button(btn_frame, text="⏹️ End Game",
                                      command=self.end_game,
                                      font=('Arial', 10, 'bold'), bg='#f44336', fg='white',
                                      width=15, state=tk.DISABLED)
        self.end_game_btn.pack(pady=2)
        
        tk.Button(btn_frame, text="� View Cameras",
                 command=self.open_camera_viewer,
                 font=('Arial', 10), bg='#9C27B0', fg='white', width=15).pack(pady=2)
        
        tk.Button(btn_frame, text="�💾 Export Log",
                 command=self.export_log,
                 font=('Arial', 10), bg='#2196F3', fg='white', width=15).pack(pady=2)
        
        tk.Button(btn_frame, text="⚙️ Settings",
                 command=self.open_settings,
                 font=('Arial', 10), bg='#607D8B', fg='white', width=15).pack(pady=2)
        
        # Main content - 3 columns
        content_frame = tk.Frame(main_frame, bg='#1a1a1a')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left - Leaderboard
        left_frame = tk.LabelFrame(content_frame, text="🏆 Leaderboard",
                                   font=('Arial', 12, 'bold'), bg='#2d2d2d', fg='#00ff00')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Leaderboard tree
        self.leaderboard_tree = ttk.Treeview(left_frame,
                                            columns=('Rank', 'Team', 'Points', 'K', 'D', 'K/D'),
                                            show='headings', height=15)
        
        for col in ('Rank', 'Team', 'Points', 'K', 'D', 'K/D'):
            self.leaderboard_tree.heading(col, text=col)
        
        self.leaderboard_tree.column('Rank', width=50)
        self.leaderboard_tree.column('Team', width=150)
        self.leaderboard_tree.column('Points', width=80)
        self.leaderboard_tree.column('K', width=50)
        self.leaderboard_tree.column('D', width=50)
        self.leaderboard_tree.column('K/D', width=60)
        
        self.leaderboard_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Middle - Teams info
        middle_frame = tk.LabelFrame(content_frame, text="🤖 Connected Teams",
                                     font=('Arial', 12, 'bold'), bg='#2d2d2d', fg='#00ff00')
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.teams_text = scrolledtext.ScrolledText(middle_frame,
                                                    font=('Courier', 9),
                                                    bg='#1a1a1a', fg='white',
                                                    height=20, width=40)
        self.teams_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right - Hit log
        right_frame = tk.LabelFrame(content_frame, text="💥 Hit Log",
                                    font=('Arial', 12, 'bold'), bg='#2d2d2d', fg='#00ff00')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.hit_log_text = scrolledtext.ScrolledText(right_frame,
                                                      font=('Courier', 8),
                                                      bg='#1a1a1a', fg='#00ff00',
                                                      height=20, width=50)
        self.hit_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bottom - Video info
        bottom_frame = tk.LabelFrame(main_frame, text="📹 Video Streams",
                                     font=('Arial', 12, 'bold'), bg='#2d2d2d', fg='#00ff00')
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        video_info = "Video streams available on ports 5001-5008\n"
        video_info += "Use GStreamer to view: gst-launch-1.0 udpsrc port=<PORT> caps=... ! autovideosink"
        
        tk.Label(bottom_frame, text=video_info,
                font=('Courier', 9), bg='#2d2d2d', fg='cyan', justify=tk.LEFT).pack(padx=10, pady=10)
    
    def start_network_thread(self):
        """Start network listener thread"""
        thread = threading.Thread(target=self.network_loop, daemon=True)
        thread.start()
        print("[GV] Network thread started")
    
    def start_heartbeat_thread(self):
        """Start heartbeat sender thread"""
        thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        thread.start()
        print("[GV] Heartbeat thread started")
    
    def heartbeat_loop(self):
        """Send periodic heartbeats to all connected laptops"""
        while self.running:
            try:
                # Send heartbeat to all teams
                for team_id in list(self.teams.keys()):
                    self.send_to_team(team_id, {'type': 'HEARTBEAT', 'timestamp': time.time()})
                
                time.sleep(1.0)  # Send every 1 second
            except Exception as e:
                if self.running:
                    print(f"[GV] Heartbeat error: {e}")
    
    def network_loop(self):
        """Network listener loop"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                message = json.loads(data.decode('utf-8'))
                self.handle_message(message, addr)
            except socket.timeout:
                continue
            except json.JSONDecodeError:
                continue
            except Exception as e:
                if self.running:
                    print(f"[GV] Network error: {e}")
    
    def handle_message(self, message: dict, addr: tuple):
        """Handle incoming message"""
        msg_type = message.get('type')
        team_id = message.get('team_id')
        
        if msg_type == 'REGISTER':
            # Team registration
            listen_port = message.get('listen_port')
            self.register_team(team_id, message, addr, listen_port)
            # Send acknowledgment back to laptop
            self.send_to_team(team_id, {'type': 'REGISTER_ACK', 'status': 'connected'})
        
        elif msg_type == 'HEARTBEAT':
            # Update team heartbeat
            if team_id in self.teams:
                self.teams[team_id]['last_heartbeat'] = time.time()
                self.teams[team_id]['addr'] = addr
        
        elif msg_type == 'HIT_REPORT':
            # Process hit
            self.process_hit(message.get('data', {}))
        
        elif msg_type == 'READY_STATUS':
            # Update ready status
            if team_id in self.teams:
                self.teams[team_id]['ready'] = message.get('ready', False)
    
    def register_team(self, team_id: int, message: dict, addr: tuple, listen_port: int):
        """Register a new team"""
        if team_id not in self.teams:
            # New team - create entry
            self.teams[team_id] = {
                'team_id': team_id,
                'team_name': message.get('team_name', f'Team {team_id}'),
                'robot_name': message.get('robot_name', f'Robot {team_id}'),
                'points': 0,
                'kills': 0,
                'deaths': 0,
                'ready': False,
                'addr': addr,
                'laptop_ip': addr[0],  # Store laptop IP separately
                'listen_port': listen_port,  # Store laptop's listen port
                'last_heartbeat': time.time(),
                'video_port': self.config['video_ports_start'] + team_id - 1
            }
            print(f"[GV] Team registered: {self.teams[team_id]['team_name']} (ID: {team_id}) on port {listen_port}")
        else:
            # Team already exists - update laptop connection info
            if listen_port is not None:
                self.teams[team_id]['laptop_ip'] = addr[0]
                self.teams[team_id]['listen_port'] = listen_port
                self.teams[team_id]['last_heartbeat'] = time.time()
                print(f"[GV] Laptop connected for team {team_id}: {addr[0]}:{listen_port}")
    
    def process_hit(self, hit_data: dict):
        """Process a hit report"""
        attacker_id = hit_data.get('attacking_team')
        defender_id = hit_data.get('defending_team')
        
        if attacker_id not in self.teams or defender_id not in self.teams:
            return
        
        # Award points to attacker
        self.teams[attacker_id]['points'] += self.config['points_per_hit']
        self.teams[attacker_id]['kills'] += 1
        
        # Record death for defender
        self.teams[defender_id]['deaths'] += 1
        
        # Add to hit log
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {self.teams[attacker_id]['team_name']} HIT {self.teams[defender_id]['team_name']}"
        self.hit_log.append(hit_data)
        
        self.hit_log_text.insert(tk.END, log_entry + "\n")
        self.hit_log_text.see(tk.END)
        
        # Send points update to both teams
        self.send_points_update(attacker_id)
        self.send_points_update(defender_id)
        
        print(f"[GV] Hit: Team {attacker_id} → Team {defender_id}")
    
    def send_to_team(self, team_id: int, message: dict):
        """Send message to a specific team's laptop"""
        if team_id not in self.teams:
            return
        
        team = self.teams[team_id]
        if 'listen_port' not in team or team['listen_port'] is None:
            return
        if 'laptop_ip' not in team or team['laptop_ip'] is None:
            return
        
        try:
            data = json.dumps(message).encode('utf-8')
            # Send to laptop's IP and listen port
            laptop_addr = (team['laptop_ip'], team['listen_port'])
            self.sock.sendto(data, laptop_addr)
        except Exception as e:
            print(f"[GV] Failed to send to team {team_id}: {e}")
    
    def send_points_update(self, team_id: int):
        """Send points update to a team"""
        if team_id not in self.teams:
            return
        
        team = self.teams[team_id]
        message = {
            'type': 'POINTS_UPDATE',
            'points': team['points'],
            'kills': team['kills'],
            'deaths': team['deaths']
        }
        
        try:
            self.sock.sendto(json.dumps(message).encode('utf-8'), team['addr'])
        except Exception as e:
            print(f"[GV] Failed to send points update: {e}")
    
    def send_ready_check(self):
        """Send ready check to all teams"""
        message = {'type': 'READY_CHECK'}
        self.broadcast_message(message)
        print("[GV] Sent ready check")
    
    def start_game(self):
        """Start the game"""
        # Check if any teams are connected
        if not self.teams:
            messagebox.showwarning("No Teams", "No teams are connected!")
            return
        
        # Check if teams are ready (optional)
        ready_teams = sum(1 for t in self.teams.values() if t['ready'])
        if ready_teams < len(self.teams):
            result = messagebox.askyesno("Not All Ready",
                                        f"Only {ready_teams}/{len(self.teams)} teams are ready. Start anyway?")
            if not result:
                return
        
        # Start game
        self.game_active = True
        self.game_start_time = time.time()
        self.game_time_remaining = self.config['game_duration']
        
        # Reset scores
        for team in self.teams.values():
            team['points'] = 0
            team['kills'] = 0
            team['deaths'] = 0
        
        # Clear hit log
        self.hit_log = []
        self.hit_log_text.delete(1.0, tk.END)
        
        # Send game start message WITH DURATION
        message = {
            'type': 'GAME_START',
            'duration': self.config['game_duration']
        }
        self.broadcast_message(message)
        
        # Update UI
        self.game_status_label.config(text="Status: GAME ACTIVE", fg='lime')
        self.start_game_btn.config(state=tk.DISABLED)
        self.end_game_btn.config(state=tk.NORMAL)
        self.ready_check_btn.config(state=tk.DISABLED)
        
        print(f"[GV] Game started! Duration: {self.config['game_duration']}s")
    
    def end_game(self):
        """End the game"""
        self.game_active = False
        
        # Send game end message
        message = {'type': 'GAME_END'}
        self.broadcast_message(message)
        
        # Update UI
        self.game_status_label.config(text="Status: Game Ended", fg='yellow')
        self.start_game_btn.config(state=tk.NORMAL)
        self.end_game_btn.config(state=tk.DISABLED)
        self.ready_check_btn.config(state=tk.NORMAL)
        
        # Show final results
        self.show_final_results()
        
        print("[GV] Game ended!")
    
    def show_final_results(self):
        """Show final results dialog"""
        results_window = tk.Toplevel(self.root)
        results_window.title("🏆 Final Results")
        results_window.geometry("500x400")
        results_window.configure(bg='#2d2d2d')
        
        tk.Label(results_window, text="🏆 FINAL RESULTS 🏆",
                font=('Arial', 18, 'bold'), bg='#2d2d2d', fg='gold').pack(pady=20)
        
        # Sort teams by points
        sorted_teams = sorted(self.teams.values(), key=lambda t: t['points'], reverse=True)
        
        results_text = scrolledtext.ScrolledText(results_window,
                                                font=('Courier', 11),
                                                bg='#1a1a1a', fg='white',
                                                height=15)
        results_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        for rank, team in enumerate(sorted_teams, 1):
            kd_ratio = team['kills'] / team['deaths'] if team['deaths'] > 0 else team['kills']
            line = f"{rank}. {team['team_name']:20s} {team['points']:4d} pts  K/D: {team['kills']}/{team['deaths']} ({kd_ratio:.2f})\n"
            results_text.insert(tk.END, line)
        
        results_text.config(state=tk.DISABLED)
    
    def broadcast_message(self, message: dict):
        """Broadcast message to all teams' laptops"""
        for team_id in self.teams.keys():
            self.send_to_team(team_id, message)
    
    def export_log(self):
        """Export game log to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_log_{timestamp}.json"
        
        log_data = {
            'timestamp': timestamp,
            'teams': self.teams,
            'hit_log': self.hit_log,
            'game_duration': self.config['game_duration']
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(log_data, f, indent=2)
            messagebox.showinfo("Export Success", f"Log exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export: {e}")
    
    def update_gui(self):
        """Update GUI periodically"""
        if not self.running:
            return
        
        current_time = time.time()
        
        # Update game timer
        if self.game_active:
            elapsed = current_time - self.game_start_time
            self.game_time_remaining = max(0, self.config['game_duration'] - elapsed)
            
            minutes = int(self.game_time_remaining // 60)
            seconds = int(self.game_time_remaining % 60)
            self.timer_label.config(text=f"Time: {minutes:02d}:{seconds:02d}")
            
            # Auto-end game when time runs out
            if self.game_time_remaining <= 0:
                self.end_game()
        
        # Update leaderboard
        self.leaderboard_tree.delete(*self.leaderboard_tree.get_children())
        
        sorted_teams = sorted(self.teams.values(), key=lambda t: t['points'], reverse=True)
        
        for rank, team in enumerate(sorted_teams, 1):
            kd_ratio = team['kills'] / team['deaths'] if team['deaths'] > 0 else team['kills']
            
            self.leaderboard_tree.insert('', tk.END, values=(
                rank,
                team['team_name'],
                team['points'],
                team['kills'],
                team['deaths'],
                f"{kd_ratio:.2f}"
            ))
        
        # Update teams info
        self.teams_text.delete(1.0, tk.END)
        
        for team in sorted_teams:
            last_seen = current_time - team['last_heartbeat']
            status = "🟢 ONLINE" if last_seen < 5 else "🔴 OFFLINE"
            ready_status = "✅" if team['ready'] else "⏳"
            
            info = f"{ready_status} Team {team['team_id']}: {team['team_name']}\n"
            info += f"   Robot: {team['robot_name']}\n"
            info += f"   Status: {status} ({last_seen:.1f}s)\n"
            info += f"   Video: Port {team['video_port']}\n"
            info += f"   Score: {team['points']} pts\n"
            info += f"   K/D: {team['kills']}/{team['deaths']}\n"
            info += "-" * 40 + "\n"
            
            self.teams_text.insert(tk.END, info)
        
        # Schedule next update
        self.root.after(100, self.update_gui)
    
    def open_camera_viewer(self):
        """Open team selection dialog first"""
        # Create team selection dialog
        selection_dialog = tk.Toplevel(self.root)
        selection_dialog.title("🎮 Select Teams for Camera View")
        selection_dialog.geometry("450x400")
        selection_dialog.configure(bg='#2a2a2a')
        selection_dialog.transient(self.root)
        selection_dialog.grab_set()
        
        # Title
        tk.Label(selection_dialog, text="Select Teams for Camera View",
                font=('Arial', 16, 'bold'), bg='#2a2a2a', fg='#00ff00').pack(pady=15)
        
        tk.Label(selection_dialog, text="Enter Team IDs (1-8) - Leave empty for unused slots:",
                font=('Arial', 11), bg='#2a2a2a', fg='white').pack(pady=5)
        
        # Available teams display
        if self.teams:
            available_text = "Available Teams: " + ", ".join([f"{tid} ({self.teams[tid]['team_name']})" 
                                                              for tid in sorted(self.teams.keys())])
        else:
            available_text = "No teams connected yet - You can still open the viewer"
        
        tk.Label(selection_dialog, text=available_text,
                font=('Arial', 9), bg='#2a2a2a', fg='cyan', wraplength=400).pack(pady=5)
        
        # Input frame
        input_frame = tk.Frame(selection_dialog, bg='#2a2a2a')
        input_frame.pack(pady=20)
        
        # Create 4 entry fields
        entries = []
        for i in range(4):
            row_frame = tk.Frame(input_frame, bg='#2a2a2a')
            row_frame.pack(pady=5)
            
            tk.Label(row_frame, text=f"Camera {i+1} - Team ID:",
                    font=('Arial', 11), bg='#2a2a2a', fg='white', width=18).pack(side=tk.LEFT, padx=5)
            
            entry = tk.Entry(row_frame, font=('Arial', 12), width=8,
                           bg='#3a3a3a', fg='white', insertbackground='white',
                           justify='center')
            entry.pack(side=tk.LEFT, padx=5)
            entries.append(entry)
            
            # Pre-fill with first 4 available teams
            available_teams = sorted(self.teams.keys())
            if i < len(available_teams):
                entry.insert(0, str(available_teams[i]))
        
        # Info label
        tk.Label(selection_dialog, text="💡 Tip: You can open with 1-4 teams",
                font=('Arial', 9, 'italic'), bg='#2a2a2a', fg='#888888').pack(pady=5)
        
        # Error label
        error_label = tk.Label(selection_dialog, text="",
                              font=('Arial', 10), bg='#2a2a2a', fg='red')
        error_label.pack(pady=5)
        
        # Buttons
        btn_frame = tk.Frame(selection_dialog, bg='#2a2a2a')
        btn_frame.pack(pady=20)
        
        def open_feeds():
            # Get team IDs from entries
            selected_teams = []
            try:
                for entry in entries:
                    value = entry.get().strip()
                    if value:  # Allow empty entries
                        team_id = int(value)
                        if team_id < 1 or team_id > 8:
                            error_label.config(text=f"❌ Team ID must be between 1-8!")
                            return
                        if team_id in selected_teams:
                            error_label.config(text=f"❌ Team {team_id} selected multiple times!")
                            return
                        selected_teams.append(team_id)
                
                if len(selected_teams) == 0:
                    error_label.config(text="❌ Please enter at least one team ID!")
                    return
                
                # Close dialog and open camera viewer
                selection_dialog.destroy()
                self.open_embedded_camera_viewer(selected_teams)
                
            except ValueError:
                error_label.config(text="❌ Please enter valid numbers!")
        
        tk.Button(btn_frame, text="📹 Open Camera Feeds", command=open_feeds,
                 font=('Arial', 12, 'bold'), bg='#4CAF50', fg='white',
                 width=18, height=2).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="✗ Cancel", command=selection_dialog.destroy,
                 font=('Arial', 12, 'bold'), bg='#f44336', fg='white',
                 width=12, height=2).pack(side=tk.LEFT, padx=5)
    
    def open_embedded_camera_viewer(self, team_ids):
        """Open embedded camera viewer with GStreamer via PyGObject"""
        try:
            import gi
            gi.require_version('Gst', '1.0')
            gi.require_version('GstVideo', '1.0')
            from gi.repository import Gst, GLib, GstVideo
            from PIL import Image, ImageTk
            import numpy as np
        except ImportError as e:
            messagebox.showerror("Missing Dependencies", 
                               "PyGObject or GStreamer not installed!\n\n" +
                               f"Error: {e}\n\n" +
                               "Run: sudo apt install python3-gi gir1.2-gstreamer-1.0")
            return
        except ValueError as e:
            messagebox.showerror("GStreamer Error", 
                               f"GStreamer initialization failed!\n\n{e}")
            return
        
        # Initialize GStreamer
        Gst.init(None)
        
        # Create camera viewer window
        cam_window = tk.Toplevel(self.root)
        cam_window.title("📹 Live Camera Monitor - Embedded Feeds")
        cam_window.geometry("1400x900")
        cam_window.configure(bg='#000000')
        
        # Title bar
        title_frame = tk.Frame(cam_window, bg='#1a1a1a')
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(title_frame, text="📹 LIVE CAMERA FEEDS - EMBEDDED VIEW", 
                font=('Arial', 18, 'bold'), bg='#1a1a1a', fg='#00ff00').pack(pady=8)
        
        # Create 2x2 grid for cameras
        grid_frame = tk.Frame(cam_window, bg='#000000')
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid
        grid_frame.grid_rowconfigure(0, weight=1)
        grid_frame.grid_rowconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        
        # Video capture objects and display labels
        video_pipelines = {}
        video_labels = {}
        status_labels = {}
        retry_buttons = {}
        video_frames = {}  # Store latest frames
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        def on_new_sample(sink, team_id):
            """Callback when new video frame arrives"""
            sample = sink.emit('pull-sample')
            if sample:
                buffer = sample.get_buffer()
                caps = sample.get_caps()
                
                # Get video info
                structure = caps.get_structure(0)
                width = structure.get_value('width')
                height = structure.get_value('height')
                
                # Get buffer data
                success, map_info = buffer.map(Gst.MapFlags.READ)
                if success:
                    # Convert to numpy array
                    frame_data = np.ndarray(
                        shape=(height, width, 3),
                        dtype=np.uint8,
                        buffer=map_info.data
                    )
                    
                    # Store frame for display
                    video_frames[team_id] = frame_data.copy()
                    
                    buffer.unmap(map_info)
            
            return Gst.FlowReturn.OK
        
        def connect_to_stream(team_id, video_port):
            """Helper function to create GStreamer pipeline for a video stream"""
            try:
                # Create GStreamer pipeline
                pipeline_str = (
                    f"udpsrc port={video_port} "
                    f"caps=\"application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96\" ! "
                    "rtpjitterbuffer latency=50 ! "
                    "rtph264depay ! "
                    "h264parse ! "
                    "avdec_h264 ! "
                    "videoconvert ! "
                    "video/x-raw,format=RGB ! "
                    "appsink name=sink emit-signals=true max-buffers=1 drop=true"
                )
                
                print(f"[Camera] Creating pipeline for Team {team_id} on port {video_port}...")
                print(f"[Camera] Pipeline: {pipeline_str}")
                
                pipeline = Gst.parse_launch(pipeline_str)
                
                # Get appsink element
                sink = pipeline.get_by_name('sink')
                sink.connect('new-sample', on_new_sample, team_id)
                
                # Start pipeline
                ret = pipeline.set_state(Gst.State.PLAYING)
                if ret == Gst.StateChangeReturn.FAILURE:
                    print(f"[Camera] Failed to start pipeline for Team {team_id}")
                    status_labels[team_id].config(text="❌ Pipeline Failed", fg='red')
                    video_labels[team_id].config(text="❌ Pipeline Start Failed\n\nClick Retry", fg='red')
                    return False
                
                video_pipelines[team_id] = pipeline
                status_labels[team_id].config(text="✅ Pipeline Started", fg='lime')
                print(f"[Camera] Team {team_id} pipeline started!")
                return True
                    
            except Exception as e:
                print(f"[Camera] Error creating pipeline for Team {team_id}: {e}")
                status_labels[team_id].config(text=f"❌ Error", fg='red')
                video_labels[team_id].config(
                    text=f"❌ Pipeline Error\n\n{str(e)[:50]}\n\nClick Retry",
                    fg='red'
                )
                return False
        
        for idx, (row, col) in enumerate(positions):
            # Container frame for each camera
            container = tk.Frame(grid_frame, bg='#1a1a1a', 
                               highlightbackground='#00ff00', highlightthickness=2)
            container.grid(row=row, column=col, sticky='nsew', padx=3, pady=3)
            
            if idx < len(team_ids):
                team_id = team_ids[idx]
                
                # Check if team exists
                if team_id in self.teams:
                    team = self.teams[team_id]
                    team_name = team['team_name']
                    video_port = team['video_port']
                else:
                    # Team not connected yet, but we can still set up the slot
                    team_name = f"Team {team_id}"
                    video_port = self.config['video_ports_start'] + team_id - 1
                
                # Info header
                info_frame = tk.Frame(container, bg='#1a1a1a')
                info_frame.pack(fill=tk.X, pady=2)
                
                tk.Label(info_frame, text=f"🤖 {team_name} (Team {team_id})",
                        font=('Arial', 11, 'bold'), bg='#1a1a1a', fg='#00ff00').pack()
                
                tk.Label(info_frame, text=f"Port: {video_port}",
                        font=('Courier', 8), bg='#1a1a1a', fg='cyan').pack()
                
                # Video display area
                video_label = tk.Label(container, bg='#000000', text="📺 Connecting...",
                                     font=('Arial', 14), fg='yellow')
                video_label.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
                video_labels[team_id] = video_label
                
                # Bottom control bar for this feed
                bottom_bar = tk.Frame(container, bg='#1a1a1a')
                bottom_bar.pack(fill=tk.X, pady=2)
                
                # Status label
                status_label = tk.Label(bottom_bar, text="⏳ Initializing...",
                                      font=('Arial', 9), bg='#1a1a1a', fg='yellow')
                status_label.pack(side=tk.LEFT, padx=5)
                status_labels[team_id] = status_label
                
                # Retry button for this specific feed
                def make_retry_func(tid, vport):
                    def retry():
                        status_labels[tid].config(text="🔄 Retrying...", fg='yellow')
                        video_labels[tid].config(text="🔄 Reconnecting...", fg='yellow')
                        
                        # Stop old pipeline if exists
                        if tid in video_pipelines:
                            try:
                                video_pipelines[tid].set_state(Gst.State.NULL)
                                del video_pipelines[tid]
                            except:
                                pass
                        
                        # Clear frame
                        if tid in video_frames:
                            del video_frames[tid]
                        
                        # Try to reconnect
                        connect_to_stream(tid, vport)
                    return retry
                
                retry_btn = tk.Button(bottom_bar, text="🔄 Retry", 
                                     command=make_retry_func(team_id, video_port),
                                     bg='#FF9800', fg='white', font=('Arial', 8, 'bold'),
                                     width=8, height=1)
                retry_btn.pack(side=tk.RIGHT, padx=5)
                retry_buttons[team_id] = retry_btn
                
                # Try initial connection
                connect_to_stream(team_id, video_port)
            else:
                # Empty slot
                tk.Label(container, text="-- Empty Slot --", 
                        font=('Arial', 14), bg='#1a1a1a', fg='#444444').pack(expand=True)
        
        # Control panel at bottom
        control_frame = tk.Frame(cam_window, bg='#1a1a1a')
        control_frame.pack(fill=tk.X, pady=(5, 0))
        
        def reconnect_all():
            """Reconnect all video streams"""
            for team_id in list(video_labels.keys()):
                status_labels[team_id].config(text="🔄 Reconnecting...", fg='yellow')
                video_labels[team_id].config(text="🔄 Reconnecting...", fg='yellow')
                
                # Stop old pipeline if exists
                if team_id in video_pipelines:
                    try:
                        video_pipelines[team_id].set_state(Gst.State.NULL)
                        del video_pipelines[team_id]
                    except:
                        pass
                
                # Clear frame
                if team_id in video_frames:
                    del video_frames[team_id]
                
                # Get video port
                if team_id in self.teams:
                    video_port = self.teams[team_id]['video_port']
                else:
                    video_port = self.config['video_ports_start'] + team_id - 1
                
                # Try to reconnect
                connect_to_stream(team_id, video_port)
        
        tk.Button(control_frame, text="🔄 Reconnect All", command=reconnect_all,
                 bg='#FF9800', fg='white', font=('Arial', 10, 'bold'),
                 width=15).pack(side=tk.LEFT, padx=10)
        
        info_label = tk.Label(control_frame, 
                             text="💡 Embedded video feeds using GStreamer + PyGObject",
                             font=('Arial', 9), bg='#1a1a1a', fg='#888888')
        info_label.pack(side=tk.RIGHT, padx=10)
        
        # FPS tracking
        fps_label = tk.Label(control_frame, text="FPS: --",
                            font=('Arial', 10), bg='#1a1a1a', fg='cyan')
        fps_label.pack(side=tk.LEFT, padx=10)
        
        # Video display update loop
        last_frame_time = time.time()
        frame_count = 0
        
        def update_video_display():
            """Update video displays with latest frames"""
            nonlocal last_frame_time, frame_count
            
            if not cam_window.winfo_exists():
                return
            
            frame_count += 1
            current_time = time.time()
            
            # Update FPS counter every second
            if current_time - last_frame_time >= 1.0:
                fps = frame_count / (current_time - last_frame_time)
                fps_label.config(text=f"FPS: {fps:.1f}")
                frame_count = 0
                last_frame_time = current_time
            
            # Update each video label with latest frame
            for team_id in video_labels.keys():
                if team_id in video_frames:
                    try:
                        frame = video_frames[team_id]
                        
                        # Resize frame to fit display
                        height, width = frame.shape[:2]
                        display_width = 640
                        display_height = int(display_width * height / width)
                        
                        # Limit height
                        if display_height > 400:
                            display_height = 400
                            display_width = int(display_height * width / height)
                        
                        # Resize using PIL
                        img = Image.fromarray(frame)
                        img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
                        
                        # Add timestamp
                        from PIL import ImageDraw, ImageFont
                        draw = ImageDraw.Draw(img)
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        try:
                            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                        except:
                            font = ImageFont.load_default()
                        draw.text((10, 10), timestamp, fill=(0, 255, 0), font=font)
                        
                        # Convert to PhotoImage
                        photo = ImageTk.PhotoImage(image=img)
                        
                        # Update label
                        video_labels[team_id].config(image=photo, text="")
                        video_labels[team_id].image = photo  # Keep reference
                        
                        status_labels[team_id].config(text="🟢 Live", fg='lime')
                    except Exception as e:
                        print(f"[Camera] Display error for team {team_id}: {e}")
                        status_labels[team_id].config(text="⚠️ Display Error", fg='orange')
            
            # Schedule next update (~30 FPS)
            if cam_window.winfo_exists():
                cam_window.after(33, update_video_display)
        
        # Start display updates
        cam_window.after(500, update_video_display)
        
        # GStreamer main loop (process events)
        def gst_mainloop():
            """Process GStreamer events"""
            if cam_window.winfo_exists():
                # Process pending events
                context = GLib.MainContext.default()
                while context.pending():
                    context.iteration(False)
                cam_window.after(10, gst_mainloop)
        
        gst_mainloop()
        
        # Cleanup function
        def on_close():
            print("[Camera] Closing camera viewer...")
            for pipeline in video_pipelines.values():
                try:
                    pipeline.set_state(Gst.State.NULL)
                except:
                    pass
            cam_window.destroy()
        
        cam_window.protocol("WM_DELETE_WINDOW", on_close)
    
    def open_settings(self):
        """Open settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("⚙️ Game Viewer Settings")
        dialog.geometry("400x300")
        dialog.configure(bg='#2a2a2a')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, bg='#2a2a2a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        tk.Label(main_frame, text="Game Configuration",
                font=('Arial', 14, 'bold'), bg='#2a2a2a', fg='white').pack(pady=10)
        
        # Game Duration
        duration_frame = tk.Frame(main_frame, bg='#2a2a2a')
        duration_frame.pack(fill='x', pady=10)
        
        tk.Label(duration_frame, text="Game Duration (seconds):",
                font=('Arial', 11), bg='#2a2a2a', fg='white').pack(side='left')
        
        duration_var = tk.StringVar(value=str(self.config['game_duration']))
        duration_entry = tk.Entry(duration_frame, textvariable=duration_var,
                                 font=('Arial', 11), width=10,
                                 bg='#3a3a3a', fg='white', insertbackground='white')
        duration_entry.pack(side='left', padx=10)
        
        tk.Label(duration_frame, text=f"({self.config['game_duration']//60} min {self.config['game_duration']%60} sec)",
                font=('Arial', 9), bg='#2a2a2a', fg='#888888').pack(side='left')
        
        # Points per hit
        points_frame = tk.Frame(main_frame, bg='#2a2a2a')
        points_frame.pack(fill='x', pady=10)
        
        tk.Label(points_frame, text="Points per Hit:",
                font=('Arial', 11), bg='#2a2a2a', fg='white').pack(side='left')
        
        points_var = tk.StringVar(value=str(self.config['points_per_hit']))
        points_entry = tk.Entry(points_frame, textvariable=points_var,
                               font=('Arial', 11), width=10,
                               bg='#3a3a3a', fg='white', insertbackground='white')
        points_entry.pack(side='left', padx=10)
        
        # Max teams
        teams_frame = tk.Frame(main_frame, bg='#2a2a2a')
        teams_frame.pack(fill='x', pady=10)
        
        tk.Label(teams_frame, text="Max Teams:",
                font=('Arial', 11), bg='#2a2a2a', fg='white').pack(side='left')
        
        teams_var = tk.StringVar(value=str(self.config['max_teams']))
        teams_entry = tk.Entry(teams_frame, textvariable=teams_var,
                              font=('Arial', 11), width=10,
                              bg='#3a3a3a', fg='white', insertbackground='white')
        teams_entry.pack(side='left', padx=10)
        
        # Save button
        def save_settings():
            try:
                self.config['game_duration'] = int(duration_var.get())
                self.config['points_per_hit'] = int(points_var.get())
                self.config['max_teams'] = int(teams_var.get())
                self.save_config()
                messagebox.showinfo("Success", "Settings saved successfully!")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")
        
        btn_frame = tk.Frame(main_frame, bg='#2a2a2a')
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="💾 Save", command=save_settings,
                 font=('Arial', 11, 'bold'), bg='#4CAF50', fg='white',
                 width=12, height=2).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="✗ Cancel", command=dialog.destroy,
                 font=('Arial', 11, 'bold'), bg='#f44336', fg='white',
                 width=12, height=2).pack(side='left', padx=5)
    
    def on_closing(self):
        """Clean up on close"""
        self.running = False
        
        # End game if active
        if self.game_active:
            self.end_game()
        
        # Close socket
        self.sock.close()
        
        # Save config
        self.save_config()
        
        # Destroy window
        self.root.destroy()
    
    def run(self):
        """Start application"""
        self.root.mainloop()


def main():
    """Entry point"""
    print("=" * 60)
    print("🎯 LASER TAG TOURNAMENT - GAME VIEWER")
    print("=" * 60)
    
    try:
        import os
        gv = GameViewer()
        gv.run()
    
    except KeyboardInterrupt:
        print("\n[GV] Shutdown")
    
    except Exception as e:
        print(f"\n[GV] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
