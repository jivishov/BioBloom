import threading
import cv2
from PIL import Image, ImageTk
import os
from openai import OpenAI
import base64
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
from datetime import datetime
import re
from datetime import datetime
from tkinter import simpledialog

class ArduinoSensorDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Arduino Sensor Dashboard")
        self.root.geometry("1000x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        

        # Apply a theme
        style = ttk.Style()
        style.theme_use('clam')  # 'clam', 'alt', 'default', 'classic' or other available themes
        
        # Configure colors
        self.bg_color = "#f5f5f5"
        self.header_color = "#3498db"
        self.text_color = "#2c3e50"
        self.accent_color = "#e74c3c"
        
        style.configure('TFrame', background=self.bg_color)
        style.configure('TLabel', background=self.bg_color, foreground=self.text_color)
        style.configure('TButton', background=self.header_color, foreground='white')
        style.configure('Header.TLabel', background=self.header_color, foreground='white', font=('Arial', 12, 'bold'))
        style.configure('ValueDisplay.TLabel', font=('Arial', 14))
        style.configure('SensorValue.TLabel', font=('Arial', 16, 'bold'))
        
        # Enhanced button styles
        style.configure('TButton', font=('Arial', 10), relief='raised', borderwidth=2)
        style.configure('Accent.TButton', background=self.accent_color, foreground='white', 
                        font=('Arial', 10, 'bold'))
        style.map('TButton',
                  background=[('active', '#d1d1d1')],
                  relief=[('pressed', 'sunken')])
        style.map('Accent.TButton',
                  background=[('active', '#c0392b')],
                  relief=[('pressed', 'sunken')])

        self.root.configure(bg=self.bg_color)
        
        self.serial_connection = None
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Data storage
        self.timestamps = []
        self.ldr_data = []
        self.voltage_data = []
        self.ph_data = []
        self.temp_data = []
        
        self.max_data_points = 100
        
        self.create_widgets()
        self.update_port_list()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ---------------------------------------------------------------------
        # Instead of top_frame, use a horizontal PanedWindow with two panes:
        # Left Pane -> Connection Settings
        # Right Pane -> Current Sensor Readings
        # ---------------------------------------------------------------------
        top_paned = ttk.PanedWindow(main_frame, orient='horizontal')
        top_paned.pack(fill="x", expand=False, padx=5, pady=5)
        
        # 1) Left Pane: Connection settings
        connection_frame = ttk.LabelFrame(top_paned, text="Connection Settings", padding=10)
        
        # 2) Right Pane: Compact dashboard for current readings
        readings_frame = ttk.LabelFrame(top_paned, text="Current Sensor Readings", padding=(10, 5))
        
        # Add both frames to the PanedWindow with desired weight
        top_paned.add(connection_frame, weight=3)  # Heavier weight means it starts wider
        top_paned.add(readings_frame, weight=2)
        
        # ---------------------------------------------------------------------
        # Connection Settings layout
        # ---------------------------------------------------------------------
        for i in range(5):
            connection_frame.columnconfigure(i, weight=0)
        connection_frame.columnconfigure(1, weight=1)
        
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.port_combo = ttk.Combobox(connection_frame, width=20)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        refresh_btn = ttk.Button(connection_frame, text="Refresh", command=self.update_port_list, width=10)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(connection_frame, text="Baud Rate:").grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.baud_combo = ttk.Combobox(connection_frame, width=10, 
                                       values=["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.current(0)
        self.baud_combo.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.connect_btn = tk.Button(
            connection_frame,
            text="Connect",
            command=self.toggle_connection,
            width=15,
            bg="#3498db",
            fg="white",
            font=('Arial', 10),
            activebackground='#2980b9',
            activeforeground='white',
            relief='raised',
            bd=2
        )
        self.connect_btn.grid(row=0, column=5, padx=(20, 5), pady=5, sticky="e")
        
        # ---------------------------------------------------------------------
        # Current Sensor Readings layout
        # ---------------------------------------------------------------------
        readings_inner = ttk.Frame(readings_frame)
        readings_inner.pack(fill="x", expand=True)
        for i in range(4):
            readings_inner.columnconfigure(i, weight=1)

        style = ttk.Style()
        style.configure('SensorValue.TLabel', font=('Arial', 16, 'bold'), anchor='center')
        style.configure('SensorHeader.TLabel', foreground='white', font=('Arial', 11, 'bold'), anchor='center')
        
        def create_sensor_display(parent, column, title, unit=""):
            sensor_frame = tk.Frame(parent, bg=self.bg_color, padx=2, pady=2)
            sensor_frame.grid(row=0, column=column, padx=5, pady=0, sticky="nsew")
            
            header_frame = tk.Frame(sensor_frame, bg=self.header_color)
            header_frame.pack(fill="x", expand=False)
            
            header_canvas = tk.Canvas(header_frame, height=25, bg=self.header_color, 
                                      highlightthickness=0, bd=0)
            header_canvas.pack(fill="x", expand=True)
            header_canvas.create_text(header_canvas.winfo_reqwidth()//2, 12,
                                      text=title, fill="white", font=('Arial', 11, 'bold'))
            
            value_frame = tk.Frame(sensor_frame, bg='white', highlightthickness=1, 
                                   highlightbackground='#cccccc', bd=0, padx=5, pady=5)
            value_frame.pack(fill="x", expand=False)
            
            value_label = ttk.Label(value_frame, text=f"-- {unit}", style='SensorValue.TLabel')
            value_label.pack(anchor="center")
            return value_label
        
        self.ldr_value = create_sensor_display(readings_inner, 0, "LDR Value")
        self.voltage_value = create_sensor_display(readings_inner, 1, "Voltage", "V")
        self.ph_value = create_sensor_display(readings_inner, 2, "pH Value")
        self.temp_value = create_sensor_display(readings_inner, 3, "Temperature", "°C")
        
        # ---------------------------------------------------------------------
        # Notebook with Graphs + Raw Data
        # ---------------------------------------------------------------------
        tab_control = ttk.Notebook(main_frame)
        tab_control.pack(fill="both", expand=True, padx=5, pady=10)
        
        graph_tab = ttk.Frame(tab_control)
        tab_control.add(graph_tab, text="Graphs")
        
        self.fig, self.axes = plt.subplots(2, 2, figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        
        self.ldr_line, = self.axes[0, 0].plot([], [], 'r-')
        self.axes[0, 0].set_title("LDR Value")
        self.axes[0, 0].set_xlabel("Time")
        self.axes[0, 0].set_ylabel("Value")
        self.axes[0, 0].grid(True)
        
        self.voltage_line, = self.axes[0, 1].plot([], [], 'g-')
        self.axes[0, 1].set_title("Voltage")
        self.axes[0, 1].set_xlabel("Time")
        self.axes[0, 1].set_ylabel("Volts (V)")
        self.axes[0, 1].grid(True)
        
        self.ph_line, = self.axes[1, 0].plot([], [], 'b-')
        self.axes[1, 0].set_title("pH Value")
        self.axes[1, 0].set_xlabel("Time")
        self.axes[1, 0].set_ylabel("pH")
        self.axes[1, 0].grid(True)
        
        self.temp_line, = self.axes[1, 1].plot([], [], 'y-')
        self.axes[1, 1].set_title("Temperature")
        self.axes[1, 1].set_xlabel("Time")
        self.axes[1, 1].set_ylabel("Temperature (°C)")
        self.axes[1, 1].grid(True)
        
        self.fig.tight_layout()
        
        data_tab = ttk.Frame(tab_control)
        tab_control.add(data_tab, text="Raw Data")
        
        data_frame = ttk.Frame(data_tab)
        data_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.data_text = tk.Text(data_frame, height=20, width=80, font=('Consolas', 10))
        self.data_text.pack(fill="both", expand=True, side="left")
        
        scrollbar = ttk.Scrollbar(data_frame, orient="vertical", command=self.data_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.data_text.config(yscrollcommand=scrollbar.set)
        self.data_text.config(state="disabled")
        
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        self.save_btn = ttk.Button(control_frame, text="Save Data", command=self.save_data, state="disabled", width=15)
        self.save_btn.pack(side="left", padx=5, pady=5)
        
        self.clear_btn = ttk.Button(control_frame, text="Clear Data", command=self.clear_data, state="disabled", width=15)
        self.clear_btn.pack(side="left", padx=5, pady=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

    def update_port_list(self):
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        
        if not port_list:
            self.port_combo["values"] = ["No ports available"]
            self.port_combo.current(0)
            self.connect_btn.config(state="disabled")
        else:
            self.port_combo["values"] = port_list
            self.port_combo.current(0)
            self.connect_btn.config(state="normal")
    
    def toggle_connection(self):
        if self.serial_connection is None:  # Not connected
            try:
                port = self.port_combo.get()
                baud_rate = int(self.baud_combo.get())
                
                self.serial_connection = serial.Serial(port, baud_rate, timeout=1)
                time.sleep(2)  # let Arduino reset
                
                self.is_monitoring = True
                self.monitor_thread = threading.Thread(target=self.read_data, daemon=True)
                self.monitor_thread.start()
                
                self.connect_btn.config(text="Disconnect")
                self.status_var.set(f"Connected to {port} at {baud_rate} baud")
                self.save_btn.config(state="normal")
                self.clear_btn.config(state="normal")
            
            except serial.SerialException as e:
                messagebox.showerror("Connection Error", f"Could not connect to port {port}: {str(e)}")
                self.serial_connection = None
        
        else:  # Disconnect
            self.is_monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=1.0)
            
            if self.serial_connection:
                self.serial_connection.close()
                self.serial_connection = None
            
            self.connect_btn.config(text="Connect")
            self.status_var.set("Not connected")
            self.save_btn.config(state="disabled")
            self.clear_btn.config(state="disabled")
    
    def read_data(self):
        while self.is_monitoring and self.serial_connection:
            try:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    self.root.after(10, lambda d=line, t=timestamp: self.process_data(d, t))
                time.sleep(0.05)
            except serial.SerialException:
                self.root.after(0, lambda: messagebox.showerror("Connection Lost", "Serial connection was lost"))
                self.root.after(0, self.toggle_connection)
                break
    
    def process_data(self, data, timestamp):
        self.data_text.config(state="normal")
        self.data_text.insert(tk.END, f"[{timestamp}] {data}\n")
        
        line_count = int(self.data_text.index('end-1c').split('.')[0])
        if line_count > 100:
            self.data_text.delete("1.0", "2.0")
        
        self.data_text.see(tk.END)
        self.data_text.config(state="disabled")
        
        ldr_match = re.search(r'LDR Value: (\d+)', data)
        voltage_match = re.search(r'Voltage: ([\d.]+)', data)
        ph_match = re.search(r'pH Value: ([\d.]+)', data)
        temp_match = re.search(r'Temperature: ([\d.]+)', data)
        
        try:
            if ldr_match and voltage_match and ph_match and temp_match:
                ldr_val = int(ldr_match.group(1))
                voltage_val = float(voltage_match.group(1))
                ph_val = float(ph_match.group(1))
                temp_val = float(temp_match.group(1))
                
                self.ldr_value.config(text=f"{ldr_val}")
                self.voltage_value.config(text=f"{voltage_val} V")
                self.ph_value.config(text=f"{ph_val}")
                self.temp_value.config(text=f"{temp_val} °C")
                
                self.timestamps.append(timestamp)
                self.ldr_data.append(ldr_val)
                self.voltage_data.append(voltage_val)
                self.ph_data.append(ph_val)
                self.temp_data.append(temp_val)
                
                if len(self.timestamps) > self.max_data_points:
                    self.timestamps.pop(0)
                    self.ldr_data.pop(0)
                    self.voltage_data.pop(0)
                    self.ph_data.pop(0)
                    self.temp_data.pop(0)
                
                self.update_graphs()
        except Exception as e:
            print(f"Error parsing data: {e}")
    
    def update_graphs(self):
        if not self.timestamps:
            return
        
        x_indices = list(range(len(self.timestamps)))
        
        # LDR
        self.axes[0, 0].clear()
        self.axes[0, 0].plot(x_indices, self.ldr_data, 'r-')
        self.axes[0, 0].set_title("LDR Value")
        self.axes[0, 0].set_xlabel("Time")
        self.axes[0, 0].set_ylabel("Value")
        self.axes[0, 0].grid(True)
        if self.ldr_data:
            min_ldr = max(0, min(self.ldr_data) - 10)
            max_ldr = max(self.ldr_data) + 10
            self.axes[0, 0].set_ylim(min_ldr, max_ldr)
        
        # Voltage
        self.axes[0, 1].clear()
        self.axes[0, 1].plot(x_indices, self.voltage_data, 'g-')
        self.axes[0, 1].set_title("Voltage")
        self.axes[0, 1].set_xlabel("Time")
        self.axes[0, 1].set_ylabel("Volts (V)")
        self.axes[0, 1].grid(True)
        if self.voltage_data:
            min_volt = max(0, min(self.voltage_data) - 0.5)
            max_volt = min(6, max(self.voltage_data) + 0.5)
            self.axes[0, 1].set_ylim(min_volt, max_volt)
        
        # pH
        self.axes[1, 0].clear()
        self.axes[1, 0].plot(x_indices, self.ph_data, 'b-')
        self.axes[1, 0].set_title("pH Value")
        self.axes[1, 0].set_xlabel("Time")
        self.axes[1, 0].set_ylabel("pH")
        self.axes[1, 0].grid(True)
        self.axes[1, 0].set_ylim(0, 14)
        
        # Temperature
        self.axes[1, 1].clear()
        self.axes[1, 1].plot(x_indices, self.temp_data, 'y-')
        self.axes[1, 1].set_title("Temperature")
        self.axes[1, 1].set_xlabel("Time")
        self.axes[1, 1].set_ylabel("Temperature (°C)")
        self.axes[1, 1].grid(True)
        if self.temp_data:
            min_temp = min(self.temp_data) - 5
            max_temp = max(self.temp_data) + 5
            self.axes[1, 1].set_ylim(min_temp, max_temp)
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    def save_data(self):
        if not self.timestamps:
            messagebox.showinfo("No Data", "No data available to save")
            return
        
        filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Timestamp", "LDR Value", "Voltage", "pH Value", "Temperature"])
                for i in range(len(self.timestamps)):
                    writer.writerow([
                        self.timestamps[i],
                        self.ldr_data[i],
                        self.voltage_data[i],
                        self.ph_data[i],
                        self.temp_data[i]
                    ])
            messagebox.showinfo("Save Successful", f"Data saved to {filename}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save data: {str(e)}")
    
    def clear_data(self):
        self.timestamps = []
        self.ldr_data = []
        self.voltage_data = []
        self.ph_data = []
        self.temp_data = []
        
        self.data_text.config(state="normal")
        self.data_text.delete("1.0", tk.END)
        self.data_text.config(state="disabled")
        
        self.ldr_value.config(text="--")
        self.voltage_value.config(text="-- V")
        self.ph_value.config(text="--")
        self.temp_value.config(text="-- °C")
        
        for ax in self.axes.flat:
            ax.clear()
            ax.grid(True)
        
        self.axes[0, 0].set_title("LDR Value")
        self.axes[0, 0].set_xlabel("Time")
        self.axes[0, 0].set_ylabel("Value")
        
        self.axes[0, 1].set_title("Voltage")
        self.axes[0, 1].set_xlabel("Time")
        self.axes[0, 1].set_ylabel("Volts (V)")
        
        self.axes[1, 0].set_title("pH Value")
        self.axes[1, 0].set_xlabel("Time")
        self.axes[1, 0].set_ylabel("pH")
        
        self.axes[1, 1].set_title("Temperature")
        self.axes[1, 1].set_xlabel("Time")
        self.axes[1, 1].set_ylabel("Temperature (°C)")
        
        self.canvas.draw()
    
    def release_camera(self):
        """Release the camera resources"""
        if self.camera is not None:
            self.camera.release()
            self.camera = None

    def on_closing(self):
        """Clean up resources before closing"""
        # Cancel any pending auto-capture
        if hasattr(self, 'auto_capture_after') and self.auto_capture_after is not None:
            self.image_tab.after_cancel(self.auto_capture_after)
            self.auto_capture_after = None
        
        # Release camera
        self.release_camera()

        if self.serial_connection:
            self.toggle_connection()
        self.root.destroy()

        
class ImageAnalysisModule:

    def __init__(self, parent_app, tab_control):
        self.parent_app = parent_app
        # Copy color attributes from parent_app or define them if not available
        self.auto_capture_enabled = False
        self.auto_capture_interval = 30  # seconds between auto-captures
        self.auto_capture_after = None  # timer object

        if hasattr(parent_app, 'header_color'):
            self.header_color = parent_app.header_color
        else:
            self.header_color = "#3498db"  # Default blue

        if hasattr(parent_app, 'accent_color'):
            self.accent_color = parent_app.accent_color
        else:
            self.accent_color = "#e74c3c"  # Default red

        if hasattr(parent_app, 'bg_color'):
            self.bg_color = parent_app.bg_color
        else:
            self.bg_color = "#f5f5f5"  # Default light gray

        if hasattr(parent_app, 'text_color'):
            self.text_color = parent_app.text_color
        else:
            self.text_color = "#2c3e50"  # Default dark blue/gray
        
        self.tab_control = tab_control
        
        # Create image analysis tab
        self.image_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.image_tab, text="Image Analysis")
        
        # OpenAI API settings
        self.api_key = ""
        self.client = None
        
        # Image storage
        self.reference_image = None
        self.anomaly_image = None
        self.reference_image_path = "reference_image.jpg"
        self.anomaly_image_path = "anomaly_image.jpg"
        
        # Camera variables
        self.camera = None
        self.camera_active = False
        self.camera_thread = None
        
        # Anomaly detection settings
        self.anomaly_thresholds = {
            'ldr': {'min': 20, 'max': 600},
            'voltage': {'min': 4.5, 'max': 5.5},
            'ph': {'min': 5.5, 'max': 9.5},
            'temp': {'min': 18, 'max': 26}
        }
        
        # Flags for tracking anomaly states
        self.last_anomaly_time = 0
        self.min_anomaly_interval = 30  # Seconds between anomaly captures
        

        
        # Create the UI
        self.create_image_analysis_ui()
        
        # Load saved API key if it exists
        self.load_api_key()

    def create_image_analysis_ui(self):
        """Create UI for the image analysis tab with improved layout management"""
        # Main container with grid layout
        main_frame = ttk.Frame(self.image_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure grid layout for main_frame
        main_frame.columnconfigure(0, weight=1)  # Left section
        main_frame.columnconfigure(1, weight=2)  # Right section (larger)
        main_frame.rowconfigure(0, weight=1)     # Top section for controls and images - take all available space
        
        # Left section - Controls column
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=0)  # API section (fixed height)
        left_frame.rowconfigure(1, weight=1)  # Thresholds section (expandable)
        
        # Right section - Images column (takes more space now)
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)  # Reference image (top)
        right_frame.rowconfigure(1, weight=1)  # Anomaly image (bottom)
        
        # ===== LEFT COLUMN =====
        
        # API Settings section
        api_frame = ttk.LabelFrame(left_frame, text="API Settings", padding=(10, 5))
        api_frame.grid(row=0, column=0, sticky="new", pady=(0, 10))
        api_frame.columnconfigure(0, weight=1)
        
        # API key controls
        api_content = ttk.Frame(api_frame)
        api_content.pack(fill="x", pady=5)
        
        ttk.Label(api_content, text="OpenAI API Key:").pack(side="top", anchor="w", padx=5, pady=(0, 5))
        
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(api_content, textvariable=self.api_key_var, show="*")
        self.api_key_entry.pack(side="top", fill="x", expand=True, padx=5, pady=(0, 5))
        
        ttk.Button(api_content, text="Save API Key", command=self.save_api_key).pack(side="top", anchor="e", padx=5, pady=(0, 5))
        
        # Threshold controls - with scrollbar
        threshold_frame = ttk.LabelFrame(left_frame, text="Anomaly Thresholds", padding=(10, 5))
        threshold_frame.grid(row=1, column=0, sticky="nsew")
        threshold_frame.columnconfigure(0, weight=1)
        
        # Create a canvas with scrollbar for thresholds
        threshold_canvas = tk.Canvas(threshold_frame, highlightthickness=0)
        threshold_scrollbar = ttk.Scrollbar(threshold_frame, orient="vertical", command=threshold_canvas.yview)
        
        # Configure scrolling
        threshold_canvas.configure(yscrollcommand=threshold_scrollbar.set)
        threshold_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        threshold_scrollbar.pack(side="right", fill="y")
        
        # Grid for thresholds
        threshold_grid = ttk.Frame(threshold_canvas)
        
        # Create window inside canvas
        canvas_frame = threshold_canvas.create_window((0, 0), window=threshold_grid, anchor="nw", tags="threshold_grid")
        threshold_grid.bind("<Configure>", lambda e: threshold_canvas.configure(scrollregion=threshold_canvas.bbox("all")))
        threshold_canvas.bind("<Configure>", lambda e: threshold_canvas.itemconfig(canvas_frame, width=e.width-5))
        
        # Configure columns for threshold grid
        for i in range(5):
            threshold_grid.columnconfigure(i, weight=1 if i in (2, 4) else 0)
        
        # Column headers
        ttk.Label(threshold_grid, text="Sensor").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Label(threshold_grid, text="Min").grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(threshold_grid, text="Max").grid(row=0, column=3, padx=5, pady=2)
        
        # Create threshold controls for each sensor
        self.threshold_vars = {}
        row = 1
        for sensor, values in self.anomaly_thresholds.items():
            # Sensor name
            ttk.Label(threshold_grid, text=sensor.upper()).grid(row=row, column=0, padx=5, pady=5, sticky="w")
            
            # Min value
            min_var = tk.DoubleVar(value=values['min'])
            min_entry = ttk.Entry(threshold_grid, textvariable=min_var, width=5)
            min_entry.grid(row=row, column=1, padx=5, pady=5)
            
            # Min slider - adjust scale range based on the sensor type
            max_scale_value = 1000 if sensor == 'ldr' else 100
            min_scale = ttk.Scale(threshold_grid, from_=0, to=max_scale_value, variable=min_var, 
                            orient="horizontal")
            min_scale.grid(row=row, column=2, padx=5, pady=5, sticky="ew")
            
            # Max value
            max_var = tk.DoubleVar(value=values['max'])
            max_entry = ttk.Entry(threshold_grid, textvariable=max_var, width=5)
            max_entry.grid(row=row, column=3, padx=5, pady=5)
            
            # Max slider - adjust scale range based on the sensor type
            max_scale = ttk.Scale(threshold_grid, from_=0, to=max_scale_value, variable=max_var, 
                            orient="horizontal")
            max_scale.grid(row=row, column=4, padx=5, pady=5, sticky="ew")
            
            # Store variables
            self.threshold_vars[sensor] = {'min': min_var, 'max': max_var}
            row += 1
        
        # Apply button
        ttk.Button(threshold_grid, text="Apply Thresholds", 
                command=self.apply_thresholds).grid(row=row, column=0, columnspan=5, 
                                                pady=(10, 5), sticky="e")
        
        # Ensure the threshold_grid has proper spacing
        for i in range(row+1):
            threshold_grid.rowconfigure(i, minsize=30)
        
        # ===== RIGHT COLUMN (IMAGES) =====
        
        # Reference image (top right) - taller now
        # Reference image (top right)
        ref_frame = ttk.LabelFrame(right_frame, text="Reference Image")
        ref_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(0, 5))

        # Create a horizontal layout within the frame
        ref_content_frame = ttk.Frame(ref_frame)
        ref_content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure the content frame columns - image on left, button on right
        ref_content_frame.columnconfigure(0, weight=3)  # Image takes 75% width
        ref_content_frame.columnconfigure(1, weight=1)  # Button area takes 25% width
        ref_content_frame.rowconfigure(0, weight=1)     # Single row takes all height

        # Create a container for the reference image
        ref_container = ttk.Frame(ref_content_frame)
        ref_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ref_container.pack_propagate(False)  # Prevent container from shrinking

        # Image label
        self.ref_image_label = ttk.Label(ref_container)
        self.ref_image_label.pack(fill="both", expand=True)

        # Button area to the right of the image
        ref_button_area = ttk.Frame(ref_content_frame)
        ref_button_area.grid(row=0, column=1, sticky="nsew")

        # Take Reference Image button with hardcoded colors
        take_ref_btn = tk.Button(
            ref_button_area, 
            text="Take\nReference\nImage", 
            command=self.take_reference_image, 
            bg="#3498db",  # Blue color
            fg="white",
            font=('Arial', 10),
            activebackground='#2980b9',
            activeforeground='white',
            relief='raised',
            bd=2
        )
        take_ref_btn.pack(fill="both", expand=True, padx=5, pady=5)

        
        # Anomaly image with similar layout (buttons to the right)
        anomaly_frame = ttk.LabelFrame(right_frame, text="Latest Anomaly Image")
        anomaly_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(5, 0))

        # Create a horizontal layout within the frame
        anomaly_content_frame = ttk.Frame(anomaly_frame)
        anomaly_content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure the content frame columns - image on left, button on right
        anomaly_content_frame.columnconfigure(0, weight=3)  # Image takes 75% width
        anomaly_content_frame.columnconfigure(1, weight=1)  # Button area takes 25% width
        anomaly_content_frame.rowconfigure(0, weight=1)     # Single row takes all height

        # Create a container for the anomaly image
        anomaly_container = ttk.Frame(anomaly_content_frame)
        anomaly_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        anomaly_container.pack_propagate(False)  # Prevent container from shrinking

        # Image label
        self.anomaly_image_label = ttk.Label(anomaly_container)
        self.anomaly_image_label.pack(fill="both", expand=True)

        # Button area to the right of the image
        anomaly_button_area = ttk.Frame(anomaly_content_frame)
        anomaly_button_area.grid(row=0, column=1, sticky="nsew")

        # Take Test Image button with hardcoded colors
        take_test_btn = tk.Button(
            anomaly_button_area, 
            text="Take\nTest\nImage", 
            command=self.take_anomaly_image, 
            bg="#3498db",  # Blue color
            fg="white",
            font=('Arial', 10),
            activebackground='#2980b9',
            activeforeground='white',
            relief='raised',
            bd=2
        )
        take_test_btn.pack(fill="both", expand=True, padx=5, pady=5)
        
        # ===== BOTTOM SECTION (ANALYSIS) =====
        
        # Analysis and results - below all content, expanded vertically
        analysis_frame = ttk.Frame(main_frame)
        analysis_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        analysis_frame.columnconfigure(0, weight=1)
        analysis_frame.rowconfigure(0, weight=0)  # Fixed height for controls
        analysis_frame.rowconfigure(1, weight=1)  # Expandable for results
        
        # Analysis controls - making button more prominent
        control_frame = ttk.Frame(analysis_frame)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        # Use a standard Tkinter button for better visibility
        analyze_btn = tk.Button(
            control_frame, 
            text="Analyze Images", 
            command=self.analyze_images, 
            width=20,
            bg=self.accent_color,  # Using accent color for emphasis
            fg="white",
            font=('Arial', 10, 'bold'),
            activebackground='#c0392b',
            activeforeground='white',
            relief='raised',
            bd=2
        )
        analyze_btn.pack(side="left", padx=10, pady=5)
        
        self.auto_capture_switch = tk.Button(
            control_frame,
            text="Auto-Capture: OFF",
            command=self.toggle_auto_capture,
            width=16,
            bg="#3498db",
            fg="white",
            font=('Arial', 10),
            activebackground='#2980b9',
            activeforeground='white'
        )
        self.auto_capture_switch.pack(side="left", padx=10, pady=5)

        interval_btn = tk.Button(
            control_frame,
            text="Set Interval",
            command=self.set_auto_capture_interval,
            width=12,
            bg="#3498db",
            fg="white",
            font=('Arial', 10),
            activebackground='#2980b9',
            activeforeground='white'
        )
        interval_btn.pack(side="left", padx=10, pady=5)

        # Add a status label
        self.status_label = ttk.Label(control_frame, text="Ready")
        self.status_label.pack(side="left", padx=10, pady=5, fill="x", expand=True)

        # Set the analyze button to disabled initially
        self.analyze_btn = analyze_btn  # Save reference to the button
        self.analyze_btn.config(state="disabled")



        # Analysis results with increased height
        results_frame = ttk.LabelFrame(analysis_frame, text="Analysis Results")
        results_frame.grid(row=1, column=0, sticky="nsew")
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Text widget with scrollbar for analysis results - taller
        self.analysis_text = tk.Text(results_frame, wrap="word", 
                                font=("Segoe UI", 10),
                                padx=10, pady=10,
                                height=15)  # Increased height
        
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", 
                                command=self.analysis_text.yview)
        scrollbar.pack(side="right", fill="y")
        
        self.analysis_text.pack(side="left", fill="both", expand=True)
        self.analysis_text.config(yscrollcommand=scrollbar.set)
        
        # Configure text styling
        self.analysis_text.tag_configure("heading", font=("Segoe UI", 12, "bold"))
        self.analysis_text.tag_configure("subheading", font=("Segoe UI", 11, "bold"))
        self.analysis_text.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        self.analysis_text.tag_configure("normal", font=("Segoe UI", 10))
        self.analysis_text.tag_configure("bullet", lmargin1=20, lmargin2=30)
        
        self.analysis_text.config(state="disabled")

    def initialize_camera(self):
        """Initialize the camera if not already initialized"""
        if self.camera is None:
            try:
                self.camera = cv2.VideoCapture(0)
                if not self.camera.isOpened():
                    messagebox.showerror("Camera Error", "Could not open webcam")
                    return False
                return True
            except Exception as e:
                messagebox.showerror("Camera Error", f"Could not initialize camera: {str(e)}")
                return False
        return True

    def release_camera(self):
        """Release the camera resources"""
        if self.camera is not None:
            self.camera.release()
            self.camera = None

    def take_reference_image(self):
        """
        Take a reference image from the webcam and start the auto-capture timer
        for test images if enabled
        """
        if not self.initialize_camera():
            return
            
        ret, frame = self.camera.read()
        if ret:
            cv2.imwrite(self.reference_image_path, frame)
            self.reference_image = frame
            
            # Update the display
            self.display_image(self.reference_image_path, self.ref_image_label)
            
            # Force UI update to ensure buttons remain visible
            self.image_tab.update_idletasks()
            
            # Enable auto-capture of test images if not already enabled
            if not self.auto_capture_enabled:
                self.auto_capture_enabled = True
                self.status_label.config(text="Auto-capture enabled: Waiting for test image")
                
                # Schedule the first auto-capture
                self.schedule_auto_capture()
            
            messagebox.showinfo("Success", "Reference image captured successfully")
        else:
            messagebox.showerror("Camera Error", "Failed to capture reference image")
        
        self.release_camera()

    def schedule_auto_capture(self):
        """Schedule the next auto-capture of a test image"""

        # Only schedule auto-capture if the reference image exists
        if not os.path.exists(self.reference_image_path):
            self.status_label.config(text="Reference image required to enable auto-capture")
            return

        if self.auto_capture_after is not None:
            # Cancel any existing scheduled auto-capture
            self.image_tab.after_cancel(self.auto_capture_after)
        
        if self.auto_capture_enabled:
            # Schedule the next auto-capture
            self.auto_capture_after = self.image_tab.after(
                self.auto_capture_interval * 1000,  # convert to milliseconds
                self.auto_capture_test_image
            )

    def auto_capture_test_image(self):
        """Automatically capture a test image if auto-capture is enabled"""
        if self.auto_capture_enabled and os.path.exists(self.reference_image_path):
            # Take a test image
            self.take_anomaly_image(auto_mode=True)
            
            # Schedule the next auto-capture
            self.schedule_auto_capture()

    def toggle_auto_capture(self):
        """Toggle the auto-capture feature on/off"""
        self.auto_capture_enabled = not self.auto_capture_enabled
        
        if self.auto_capture_enabled:
            if not os.path.exists(self.reference_image_path):
                messagebox.showwarning("Reference Image Required", 
                                    "Please take a reference image first before enabling auto-capture.")
                self.auto_capture_enabled = False
                self.auto_capture_switch.config(text="Auto-Capture: OFF")
                return
                
            self.auto_capture_switch.config(text="Auto-Capture: ON")
            self.status_label.config(text=f"Auto-capture enabled. Interval: {self.auto_capture_interval}s")
            self.schedule_auto_capture()
        else:
            self.auto_capture_switch.config(text="Auto-Capture: OFF")
            self.status_label.config(text="Auto-capture disabled")
            
            # Cancel any pending auto-capture
            if self.auto_capture_after is not None:
                self.image_tab.after_cancel(self.auto_capture_after)
                self.auto_capture_after = None

    def set_auto_capture_interval(self):
        """Open a dialog to set the auto-capture interval"""
        try:
            new_interval = simpledialog.askinteger(
                "Auto-Capture Interval", 
                "Enter interval in seconds (5-3600):",
                minvalue=5, maxvalue=3600,
                initialvalue=self.auto_capture_interval
            )
            
            if new_interval is not None:
                self.auto_capture_interval = new_interval
                if self.auto_capture_enabled:
                    self.status_label.config(text=f"Auto-capture enabled. Interval: {self.auto_capture_interval}s")
                    # Reschedule with the new interval
                    self.schedule_auto_capture()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set interval: {str(e)}")

    def display_image(self, image_path, label_widget):
        """Display an image in the specified label widget with dynamic scaling"""
        if os.path.exists(image_path):
            try:
                # Open the image with PIL
                img = Image.open(image_path)
                
                # Get the current size of the container
                label_widget.update_idletasks()  # Ensure geometry info is updated
                container_width = label_widget.winfo_width()
                container_height = label_widget.winfo_height()
                
                # If the container dimensions are too small (not yet properly sized),
                # use reasonable defaults that take advantage of the larger space
                if container_width < 10:
                    container_width = 450  # Increased from 350
                if container_height < 10:
                    container_height = 300  # Increased from 200
                
                # Calculate new dimensions while maintaining aspect ratio
                width, height = img.size
                
                # Calculate the scale factor
                width_ratio = container_width / width
                height_ratio = container_height / height
                
                # Use the smaller ratio to fit the image
                scale = min(width_ratio, height_ratio)
                
                new_width = int(width * scale)
                new_height = int(height * scale)
                
                # Resize the image with high quality
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                # Update the label
                label_widget.config(image=photo)
                label_widget.image = photo  # Keep a reference to prevent garbage collection
            except Exception as e:
                messagebox.showerror("Image Error", f"Error displaying image: {str(e)}")

    def save_api_key(self):
        """Save the API key to a file for persistence between sessions"""
        api_key = self.api_key_var.get().strip()
        if api_key:
            self.api_key = api_key
            try:
                # Initialize the OpenAI client to test the key
                self.client = OpenAI(api_key=self.api_key)
                
                # Save the API key to a file
                config_dir = os.path.join(os.path.expanduser("~"), ".arduino_sensor_app")
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir)
                    
                key_file = os.path.join(config_dir, "api_key.txt")
                
                # Simple encryption (not secure, but adds some obfuscation)
                # In a real app, you should use a more secure method
                encoded_key = ''.join([chr(ord(c) + 1) for c in api_key])
                
                with open(key_file, 'w') as f:
                    f.write(encoded_key)
                    
                messagebox.showinfo("Success", "API key saved successfully")
            except Exception as e:
                messagebox.showerror("API Error", f"Error initializing OpenAI client: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Please enter a valid API key")

    def load_api_key(self):
        """Load the saved API key at launch"""
        config_dir = os.path.join(os.path.expanduser("~"), ".arduino_sensor_app")
        key_file = os.path.join(config_dir, "api_key.txt")
        
        if os.path.exists(key_file):
            try:
                with open(key_file, 'r') as f:
                    encoded_key = f.read().strip()
                
                # Simple decryption
                api_key = ''.join([chr(ord(c) - 1) for c in encoded_key])
                
                # Set the API key in the UI
                self.api_key_var.set(api_key)
                
                # Initialize client
                self.api_key = api_key
                self.client = OpenAI(api_key=self.api_key)
                
                print("API key loaded successfully")
                return True
            except Exception as e:
                print(f"Error loading API key: {str(e)}")
                return False
        return False

    def apply_thresholds(self):
        """Apply the threshold values from the UI to the settings"""
        for sensor, vars in self.threshold_vars.items():
            try:
                min_val = float(vars['min'].get())
                max_val = float(vars['max'].get())
                
                if min_val >= max_val:
                    messagebox.showwarning("Invalid Threshold", 
                                        f"Min value must be less than max value for {sensor}")
                    continue
                
                self.anomaly_thresholds[sensor]['min'] = min_val
                self.anomaly_thresholds[sensor]['max'] = max_val
            except ValueError:
                messagebox.showwarning("Invalid Input", 
                                    f"Please enter valid numbers for {sensor} thresholds")
        
        messagebox.showinfo("Success", "Thresholds updated successfully")

    def analyze_images(self, auto_mode=False):
        """
        Analyze the reference and anomaly images using OpenAI API
        
        Parameters:
        auto_mode (bool): If True, this is an automated analysis
        """
        if not self.client:
            if not auto_mode:
                messagebox.showwarning("API Error", "Please set your OpenAI API key first")
            return
        
        # Ensure both images are available in the UI before analysis
        if self.reference_image is None or self.anomaly_image is None:
            if not auto_mode:
                messagebox.showwarning("Missing Images", 
                                    "Both reference and test images must be captured first.")
            return

        if not os.path.exists(self.reference_image_path) or not os.path.exists(self.anomaly_image_path):
            if not auto_mode:
                messagebox.showwarning("Missing Images", 
                                    "Both reference and anomaly images must be captured first")
            return
        
        # Get the base64 encoded images
        ref_b64 = self.encode_image(self.reference_image_path)
        anomaly_b64 = self.encode_image(self.anomaly_image_path)
        
        if not ref_b64 or not anomaly_b64:
            if not auto_mode:
                messagebox.showerror("Image Error", "Error encoding images")
            return
        
        # Get latest sensor values for context
        latest_values = {}
        if hasattr(self.parent_app, 'ldr_data') and self.parent_app.ldr_data:
            latest_values['ldr'] = self.parent_app.ldr_data[-1]
        if hasattr(self.parent_app, 'voltage_data') and self.parent_app.voltage_data:
            latest_values['voltage'] = self.parent_app.voltage_data[-1]
        if hasattr(self.parent_app, 'ph_data') and self.parent_app.ph_data:
            latest_values['ph'] = self.parent_app.ph_data[-1]
        if hasattr(self.parent_app, 'temp_data') and self.parent_app.temp_data:
            latest_values['temp'] = self.parent_app.temp_data[-1]
        
        # Prepare the prompt with context about algae growing system
        prompt = f"""
        # Image Analysis for Algae Growing System
        
        Compare these two images of an algae growing system prototype. The first image shows the reference setup with normal conditions.
        The second image shows the current state where sensors may have detected an anomaly.
        
        ## Current Sensor Readings
        - **LDR Value:** {latest_values.get('ldr', 'N/A')}
        - **Voltage:** {latest_values.get('voltage', 'N/A')} V
        - **pH Value:** {latest_values.get('ph', 'N/A')}
        - **Temperature:** {latest_values.get('temp', 'N/A')} °C
        
        ## Analysis Tasks
        
        1. **Light Source Status:** Is the light source ON or OFF in each image? If it changed, this indicates a light source problem.
        2. **Sensor Placement:** Are the pH and temperature sensors still inserted in the container in both images?
        3. **Algae Condition:** Does the algae appearance look different between images?
        4. **Other Changes:** Identify any other visible changes that might explain sensor readings.
        
        ## Response Format
        
        Please structure your response with the following sections:
        
        ### Temperature Analysis
        (Your observations about temperature readings and visible evidence)
        
        ### Possible Causes of Anomalies
        1. **Light Source Issue:** (Your analysis)
        2. **pH and Temperature Changes:** (Your analysis)
        
        ### Recommendations
        - **Check Light Source:** (Your recommendation)
        - **Verify Sensor Placement:** (Your recommendation)
        
        Use markdown formatting in your response.
        """
        
        # Set the status
        capture_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        analysis_mode = "Auto-analyzing" if auto_mode else "Analyzing"
        self.update_analysis_text(f"# {analysis_mode} images...\n\nTimestamp: {capture_time}\n\nPlease wait while the images are being analyzed.")
        self.image_tab.update()
        
        # Create a thread to handle the API call
        def call_api():
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt,
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{ref_b64}"},
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{anomaly_b64}"},
                                },
                            ],
                        }
                    ],
                    max_tokens=1000
                )
                
                analysis_text = response.choices[0].message.content
                
                # Update the UI in the main thread
                self.parent_app.root.after(0, lambda: self.update_analysis_text(analysis_text))
                
                # Save the analysis to HTML file
                self.parent_app.root.after(100, lambda: self.save_analysis_to_html(analysis_text))
                
                # Update status
                if auto_mode:
                    self.parent_app.root.after(0, lambda: self.status_label.config(
                        text=f"Auto-analysis completed at {datetime.now().strftime('%H:%M:%S')}"))
                
            except Exception as e:
                error_message = f"# API Error\n\n{str(e)}"
                self.parent_app.root.after(0, lambda: self.update_analysis_text(error_message))
                if auto_mode:
                    self.parent_app.root.after(0, lambda: self.status_label.config(
                        text=f"Auto-analysis failed: {str(e)[:50]}..."))
        
        # Start the API call in a separate thread
        threading.Thread(target=call_api, daemon=True).start()

    def encode_image(self, image_path):
        """Encode an image to base64"""
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        return None
    
    def update_analysis_text(self, text):
            """Update the analysis text widget with formatted results"""
            self.analysis_text.config(state="normal")
            self.analysis_text.delete("1.0", tk.END)
            
            # Process the text to apply markdown-like formatting
            lines = text.split('\n')
            for line in lines:
                # Headings (### style)
                if line.startswith('###'):
                    self.analysis_text.insert(tk.END, line[3:].strip() + "\n", "heading")
                
                # Subheadings (## style)
                elif line.startswith('##'):
                    self.analysis_text.insert(tk.END, line[2:].strip() + "\n", "subheading")
                
                # Main headings (# style)
                elif line.startswith('#'):
                    self.analysis_text.insert(tk.END, line[1:].strip() + "\n\n", "heading")
                
                # Bullet points
                elif line.strip().startswith('-') or line.strip().startswith('*'):
                    bullet_text = line.strip()[1:].strip()
                    self.analysis_text.insert(tk.END, "• " + bullet_text + "\n", "bullet")
                
                # Numbered points
                elif line.strip() and line.strip()[0].isdigit() and '. ' in line:
                    self.analysis_text.insert(tk.END, line + "\n", "bullet")
                
                # Bold text (**text**)
                elif '**' in line:
                    parts = line.split('**')
                    for i, part in enumerate(parts):
                        if i % 2 == 1:  # Odd parts are inside ** markers
                            self.analysis_text.insert(tk.END, part, "bold")
                        else:
                            self.analysis_text.insert(tk.END, part, "normal")
                    self.analysis_text.insert(tk.END, "\n")
                
                # Regular text
                else:
                    if line.strip():  # Not empty
                        self.analysis_text.insert(tk.END, line + "\n", "normal")
                    else:
                        self.analysis_text.insert(tk.END, "\n")
            
            self.analysis_text.config(state="disabled")

    def check_for_anomalies(self, sensor_values):
        """
        Check if current sensor values indicate an anomaly
        Returns True if an anomaly is detected, False otherwise
        """
        # Skip if we took an image recently (to avoid too many captures)
        current_time = time.time()
        if current_time - self.last_anomaly_time < self.min_anomaly_interval:
            return False
        
        # Check each sensor against its thresholds
        anomaly_detected = False
        
        if 'ldr' in sensor_values:
            ldr_value = sensor_values['ldr']
            if ldr_value < self.anomaly_thresholds['ldr']['min'] or ldr_value > self.anomaly_thresholds['ldr']['max']:
                anomaly_detected = True
        
        if 'voltage' in sensor_values:
            voltage_value = sensor_values['voltage']
            if voltage_value < self.anomaly_thresholds['voltage']['min'] or voltage_value > self.anomaly_thresholds['voltage']['max']:
                anomaly_detected = True
        
        if 'ph' in sensor_values:
            ph_value = sensor_values['ph']
            if ph_value < self.anomaly_thresholds['ph']['min'] or ph_value > self.anomaly_thresholds['ph']['max']:
                anomaly_detected = True
        
        if 'temp' in sensor_values:
            temp_value = sensor_values['temp']
            if temp_value < self.anomaly_thresholds['temp']['min'] or temp_value > self.anomaly_thresholds['temp']['max']:
                anomaly_detected = True
        
        if anomaly_detected:
            self.last_anomaly_time = current_time
            return True
        
        return False

    # def capture_anomaly_image(self):
        """Capture an image when an anomaly is detected and trigger analysis"""
        if not os.path.exists(self.reference_image_path):
            # Can't compare without a reference image
            return
        
        if not self.initialize_camera():
            return
            
        ret, frame = self.camera.read()
        if ret:
            # Save the anomaly image
            cv2.imwrite(self.anomaly_image_path, frame)
            self.anomaly_image = frame
            
            # Update the display in the main thread
            self.parent_app.root.after(0, lambda: self.display_image(
                self.anomaly_image_path, self.anomaly_image_label))
            
            # Auto-analyze if we have an API key
            if self.client:
                # Create a descriptive timestamp for this auto-capture event
                capture_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Log the auto-capture event
                print(f"Auto-captured anomaly image at {capture_time}")
                
                # Add a note to the analysis text about auto-capture
                self.update_analysis_text(f"# Auto-captured anomaly detected\n\nTimestamp: {capture_time}\n\nAnalyzing images...")
                
                # Trigger analysis which will also save the HTML report
                self.parent_app.root.after(1000, self.analyze_images)
        else:
            print("Failed to capture anomaly image")
        
        self.release_camera()

    def take_anomaly_image(self, auto_mode=False):
        # Check if the reference image has been captured and loaded
        if self.reference_image is None or not os.path.exists(self.reference_image_path):
            if not auto_mode:
                messagebox.showwarning("Reference Image Required", 
                                    "Please capture a reference image first.")
            return

        if not self.initialize_camera():
            return

        ret, frame = self.camera.read()
        if ret:
            cv2.imwrite(self.anomaly_image_path, frame)
            self.anomaly_image = frame

            # Update the display
            self.display_image(self.anomaly_image_path, self.anomaly_image_label)

            # Force UI update to ensure buttons remain visible
            self.image_tab.update_idletasks()

            if not auto_mode:
                messagebox.showinfo("Success", "Test image captured successfully")
            else:
                self.status_label.config(text=f"Auto-captured test image at {datetime.now().strftime('%H:%M:%S')}")
            
            # Enable the analyze button only if both images are available
            if self.reference_image is not None and self.anomaly_image is not None:
                self.analyze_btn.config(state="normal")
                # Auto-analyze if in auto mode and API client is available
                if auto_mode and self.client:
                    self.analyze_images(auto_mode=True)
        else:
            if not auto_mode:
                messagebox.showerror("Camera Error", "Failed to capture test image")
            else:
                print("Failed to auto-capture test image")

        self.release_camera()

    def save_analysis_to_html(self, analysis_text):
        """
        Save the reference image, anomaly image, and analysis text to an HTML file
        """
        try:
            # Create a timestamp for the filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_report_{timestamp}.html"
            
            # Convert images to base64 for embedding in HTML
            ref_image_b64 = self.encode_image(self.reference_image_path)
            anomaly_image_b64 = self.encode_image(self.anomaly_image_path)
            
            if not ref_image_b64 or not anomaly_image_b64:
                messagebox.showerror("Image Error", "Error encoding images for HTML report")
                return False
            
            # Get latest sensor values for context
            latest_values = {}
            if hasattr(self.parent_app, 'ldr_data') and self.parent_app.ldr_data:
                latest_values['ldr'] = self.parent_app.ldr_data[-1]
            if hasattr(self.parent_app, 'voltage_data') and self.parent_app.voltage_data:
                latest_values['voltage'] = self.parent_app.voltage_data[-1]
            if hasattr(self.parent_app, 'ph_data') and self.parent_app.ph_data:
                latest_values['ph'] = self.parent_app.ph_data[-1]
            if hasattr(self.parent_app, 'temp_data') and self.parent_app.temp_data:
                latest_values['temp'] = self.parent_app.temp_data[-1]
            
            # Create HTML content
            html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Analysis Report {timestamp}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .header {{
                background-color: #3498db;
                color: white;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }}
            .images-container {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
            }}
            .image-box {{
                width: 48%;
                border: 1px solid #ddd;
                padding: 10px;
                border-radius: 5px;
            }}
            .image-box img {{
                max-width: 100%;
                height: auto;
            }}
            .image-caption {{
                text-align: center;
                margin-top: 10px;
                font-weight: bold;
            }}
            .sensor-data {{
                background-color: #f8f8f8;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .analysis {{
                padding: 15px;
                background-color: #f0f7ff;
                border-radius: 5px;
            }}
            h1, h2, h3 {{
                color: #2c3e50;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            table, th, td {{
                border: 1px solid #ddd;
            }}
            th, td {{
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Algae Growing System Analysis Report</h1>
                <p>Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
            
            <div class="images-container">
                <div class="image-box">
                    <img src="data:image/jpeg;base64,{ref_image_b64}" alt="Reference Image">
                    <div class="image-caption">Reference Image</div>
                </div>
                <div class="image-box">
                    <img src="data:image/jpeg;base64,{anomaly_image_b64}" alt="Test Image">
                    <div class="image-caption">Test Image</div>
                </div>
            </div>
            
            <div class="sensor-data">
                <h2>Current Sensor Readings</h2>
                <table>
                    <tr>
                        <th>Sensor</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>LDR Value</td>
                        <td>{latest_values.get('ldr', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td>Voltage</td>
                        <td>{latest_values.get('voltage', 'N/A')} V</td>
                    </tr>
                    <tr>
                        <td>pH Value</td>
                        <td>{latest_values.get('ph', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td>Temperature</td>
                        <td>{latest_values.get('temp', 'N/A')} °C</td>
                    </tr>
                </table>
            </div>
            
            <div class="analysis">
                <h2>Analysis Results</h2>
                {analysis_text.replace('\n', '<br>').replace('# ', '<h2>').replace('## ', '<h3>').replace('### ', '<h4>').replace('</h2>', '</h2>').replace('</h3>', '</h3>').replace('</h4>', '</h4>')}
            </div>
        </div>
    </body>
    </html>"""
            
            # Save the HTML file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            messagebox.showinfo("Success", f"Analysis report saved to {filename}")
            return True
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save HTML report: {str(e)}")
            return False


# Function to integrate the module into the main application
def integrate_image_analysis(main_app):
    """
    Integrate the image analysis module into the main application
    
    Parameters:
    main_app - The main ArduinoSensorDashboard instance
    """
    
    # Find the existing tab control in the main_app or create a new one
    tab_control = None
    for widget in main_app.root.winfo_children():
        if isinstance(widget, ttk.Notebook):
            tab_control = widget
            break
    
    if tab_control is None:
        # Look in main frames
        for widget in main_app.root.winfo_children():
            if isinstance(widget, ttk.Frame) or isinstance(widget, ttk.LabelFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Notebook):
                        tab_control = child
                        break
    
    # If still not found, create a new tab control
    if tab_control is None:
        # Find main content area
        main_frame = None
        for widget in main_app.root.winfo_children():
            if isinstance(widget, ttk.Frame) or isinstance(widget, ttk.LabelFrame):
                if hasattr(widget, 'winfo_children') and widget.winfo_children():
                    main_frame = widget
                    break
        
        if main_frame is None:
            main_frame = main_app.root
        
        # Create new tab control
        tab_control = ttk.Notebook(main_frame)
        tab_control.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Create the image analysis module
    image_module = ImageAnalysisModule(main_app, tab_control)
    
    # Store a reference to the module in the main app
    main_app.image_module = image_module
    
    # Store the original process_data method
    original_process_data = main_app.process_data
    
    # Define a new process_data function that wraps the original
    def new_process_data(data, timestamp):
        # Call the original method
        original_process_data(data, timestamp)
        
        # Check for anomalies
        if hasattr(main_app, 'image_module') and hasattr(main_app, 'timestamps') and main_app.timestamps:
            # Get latest values
            latest_values = {}
            if hasattr(main_app, 'ldr_data') and main_app.ldr_data:
                latest_values['ldr'] = main_app.ldr_data[-1]
            if hasattr(main_app, 'voltage_data') and main_app.voltage_data:
                latest_values['voltage'] = main_app.voltage_data[-1]
            if hasattr(main_app, 'ph_data') and main_app.ph_data:
                latest_values['ph'] = main_app.ph_data[-1]
            if hasattr(main_app, 'temp_data') and main_app.temp_data:
                latest_values['temp'] = main_app.temp_data[-1]
            
            # Check for anomalies
            if main_app.image_module.check_for_anomalies(latest_values):
                # Capture image in a separate thread to avoid blocking the UI
                threading.Thread(
                    target=main_app.image_module.take_anomaly_image, 
                    daemon=True
                ).start()
    
    # Replace the process_data method with our new one
    main_app.process_data = new_process_data



def main():
    root = tk.Tk()
    app = ArduinoSensorDashboard(root)

    # Integrate the image analysis module
    integrate_image_analysis(app)

    root.mainloop()

if __name__ == "__main__":
    main()