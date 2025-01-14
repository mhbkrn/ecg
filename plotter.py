class AutoClearLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.clear()  # Clears the text when the field is focused

class RealTimePlotApp(QMainWindow):
    MAX_PLOT_POINTS = adjust
    UPDATE_INTERVAL_MS = adjust 

    def __init__(self):
        super().__init__()

        # Initialize variables for BPM calculation
        self.last_peak_time = time.time()  # Timestamp of the last detected peak
        self.BPM =   # Initialize BPM value
        self.last_BPM_update_time = time.time()  # Timestamp of the last BPM update
        self.min_BPM_update_interval = 4  # Minimum interval between BPM updates (in seconds)

        self.beep_enabled = True  # Add this attribute to control the beep sound

        self.setWindowTitle("ECG Realtime Plotter")
        self.setGeometry(100, 100, 800, 600)

        # Create menu bar
        menubar = self.menuBar()
        about_menu = menubar.addMenu("About")

        # Add action for About menu
        about_action = QAction("Creator & App Info", self)
        about_action.triggered.connect(self.show_about_info)
        about_menu.addAction(about_action)

        main_layout = QVBoxLayout()
        self.setCentralWidget(QWidget(self))
        

        # Group box for patient data fields
        patient_data_group = QGroupBox("Patient Data")
        patient_data_layout = QVBoxLayout(patient_data_group)

        # First line of patient data fields
        first_line_layout = QHBoxLayout()
        self.name_input = QLineEdit("Name")
        first_line_layout.addWidget(self.name_input)
        self.weight_input = QLineEdit("Weight (kg)")
        first_line_layout.addWidget(self.weight_input)
        patient_data_layout.addLayout(first_line_layout)

        # Second line of patient data fields
        second_line_layout = QHBoxLayout()
        self.height_input = QLineEdit("Height (cm)")
        second_line_layout.addWidget(self.height_input)
        self.age_input = QLineEdit("Age")
        second_line_layout.addWidget(self.age_input)
        patient_data_layout.addLayout(second_line_layout)

        main_layout.addWidget(patient_data_group)

        # MQTT and plotting controls
        controls_layout = QHBoxLayout()

        self.broker_input = AutoClearLineEdit("broker adress")
        controls_layout.addWidget(self.broker_input)

        self.topic_input = AutoClearLineEdit("topic")
        controls_layout.addWidget(self.topic_input)

        self.connect_button = QPushButton("Connect")
        controls_layout.addWidget(self.connect_button)
        self.connect_button.clicked.connect(self.setup_mqtt)

        self.disconnect_button = QPushButton("Disconnect")
        controls_layout.addWidget(self.disconnect_button)
        self.disconnect_button.clicked.connect(self.disconnect_mqtt)
        self.disconnect_button.setEnabled(False)

        self.save_button = QPushButton("Save to Excel")
        controls_layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.save_data_to_excel)

        self.save_as_button = QPushButton("Save As")
        controls_layout.addWidget(self.save_as_button)
        self.save_as_button.clicked.connect(self.save_data_as_excel)

        self.load_button = QPushButton("Load Data")
        controls_layout.addWidget(self.load_button)
        self.load_button.clicked.connect(self.load_data_from_excel)

        self.pause_button = QPushButton("Pause Plotting")
        controls_layout.addWidget(self.pause_button)
        self.pause_button.setCheckable(True)
        self.pause_button.clicked.connect(self.toggle_plotting)
        self.plotting_paused = False

        self.refresh_button = QPushButton("Refresh Plot")
        controls_layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self.refresh_plot)

        main_layout.addLayout(controls_layout)

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=1.0)
        self.plot_widget.setLabel('bottom', 'Time (ms)')
        self.plot_widget.setLabel('left', 'Voltage (mV)')
        self.plot_widget.plotItem.setDownsampling(mode='peak')  # Set interpolation mode to peak
        
        main_layout.addWidget(self.plot_widget)

        self.plot = self.plot_widget.plot(pen='g')
        self.plot.setOpacity(1.0)

        self.centralWidget().setLayout(main_layout)

        self.data = deque(maxlen=self.MAX_PLOT_POINTS)
        self.x_data = []

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(self.UPDATE_INTERVAL_MS)

        self.mqtt_client = None
        self.saved_data = []
        self.patient_data = {}
        self.data_processing_enabled = True
        self.patient_data_saved = False

        # Adding sliders for adjusting max plot points and update interval
        settings_group = QGroupBox("Settings Plotter")
        settings_layout = QVBoxLayout(settings_group)

        # BPM display label
        self.bpm_display_label = QLabel("BPM: ", self)
        settings_layout.addWidget(self.bpm_display_label)
        
        self.sample_window =   # Number of samples to calculate average BPM
        self.sample_count = 
        self.peak_count = 
        self.BPM = 
        
        main_layout.addWidget(settings_group)

    def setup_mqtt(self):
        if self.mqtt_client is None:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_message = self.on_mqtt_message
            broker = self.broker_input.text()
            topic = self.topic_input.text()
            self.mqtt_client.connect(broker)
            self.mqtt_client.subscribe(topic)
            self.mqtt_client.loop_start()
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)

    def disconnect_mqtt(self):
        if self.mqtt_client:
            self.mqtt_client.disconnect()
            self.mqtt_client.loop_stop()
            self.mqtt_client = None
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            
            # Clear patient data upon disconnection
            self.clear_patient_data()

    def clear_patient_data(self):
        # Clear patient data fields
        self.name_input.setText("Name")
        self.weight_input.setText("Weight (kg)")
        self.height_input.setText("Height (cm)")
        self.age_input.setText("Age")
        self.patient_data_saved = False

        # Clear saved data and plot
        self.saved_data = []
        self.data.clear()
        self.x_data.clear()
        self.plot.clear()

    def on_mqtt_message(self, client, userdata, message):
        try:
            value = float(message.payload) / x  # Adjust scale if necessary

            if self.data_processing_enabled:
                # Add data to the buffer
                self.data.append(value)
                self.x_data = list(range(len(self.data)))
                self.saved_data.append((datetime.datetime.now()[:-3], value))

                # BPM calculation logic
                if self.is_peak(value):
                    # Calculate time elapsed since the last peak
                    current_time = time.time()
                    time_elapsed = current_time - self.last_peak_time

                    # Calculate BPM based on the time elapsed between peaks
                    self.BPM = 60 / time_elapsed

                    # Update the timestamp of the last detected peak
                    self.last_peak_time = current_time
                    
                    # Check if enough time has elapsed since the last BPM update
                    if current_time - self.last_BPM_update_time >= self.min_BPM_update_interval:
                        # Update BPM display
                        print(f"BPM: {self.BPM}")  # Debugging: Print BPM value
                        self.bpm_display_label.setText(f"BPM: {self.BPM:.2f}")
                        self.last_BPM_update_time = current_time  # Update the timestamp of the last BPM update
                      
        except ValueError as e:
            print(f"Failed to process MQTT message: {e}")


    def is_peak(self, value, threshold=1):
        # Implement peak detection logic
        if len(self.data) < 3:
            return False
        
        # Consider the current value and its neighbors for peak detection
        current_value = self.data[-2]  # Current value
        prev_value = self.data[-3]     # Previous value
        next_value = self.data[-1]     # Next value
        
        if current_value > threshold and current_value > prev_value and current_value > next_value:
            return True
        
        return False

    def update_plot(self):
        if not self.plotting_paused:
            # Divide data by 10000 before setting in the plot
            data_divided = [value / 1 for value in self.data]
            self.plot.setData(self.x_data, data_divided)

    def refresh_plot(self):
        self.data.clear()
        self.x_data.clear()
        self.plot.clear()
        if self.plotting_paused:
            self.plot.setData([], [])

    def toggle_plotting(self):
        self.plotting_paused = not self.plotting_paused
        self.pause_button.setText("Resume Plotting" if self.plotting_paused else "Pause Plotting")
        self.data_processing_enabled = not self.plotting_paused

    def save_data_as_excel(self):
        try:
            options = "Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;Text Files (*.txt)"
            file, _ = QFileDialog.getSaveFileName(self, "Save As", "", options)
            
            if file:
                file_extension = file.split('.')[-1].lower()
                if file_extension in ['xlsx', 'xls']:
                    self.save_data_to_excel(file)
                elif file_extension == 'csv':
                    self.save_data_to_csv(file)
                elif file_extension == 'txt':
                    self.save_data_to_txt(file)
                else:
                    print("Unsupported file format.")
        except Exception as e:
            print(f"Failed to save data: {e}")

    def save_data_to_csv(self, file_name=None):
        # Save data to CSV file
        if self.saved_data:
            data = {
                "Timestamp": [timestamp for timestamp, _ in self.saved_data],
                "Value": [value for _, value in self.saved_data]
            }
            df_data = pd.DataFrame(data)
            df_data.to_csv(file_name, index=False)
            print(f"Data saved to {file_name} as CSV.")
            self.show_save_success_message(file_name)

    def save_data_to_txt(self, file_name=None):
        # Save data to TXT file
        if self.saved_data:
            with open(file_name, 'w') as file:
                for timestamp, value in self.saved_data:
                    file.write(f"{timestamp}, {value}\n")
            print(f"Data saved to {file_name} as TXT.")
            self.show_save_success_message(file_name)

    def save_data_to_excel(self, file_name=None):
        if self.saved_data:
            self.save_patient_data()

            data = {
                "Timestamp": [timestamp for timestamp, _ in self.saved_data],
                "Value": [value for _, value in self.saved_data]
            }
            df_data = pd.DataFrame(data)

            if self.patient_data_saved:
                patient_df = pd.DataFrame(self.patient_data, index=[0])
                df = pd.concat([df_data, patient_df], axis=1)
            else:
                df = df_data

            timestamp = datetime.datetime.now()
            if not file_name:
                file_name = f"data_{timestamp}.xlsx"
            df.to_excel(file_name, engine='openpyxl', index=False)
            print(f"Data saved to {file_name}")

            # Show prompt box on successful save
            self.show_save_success_message(file_name)

    def show_save_success_message(self, file_name):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"Data saved successfully to {file_name}")
        msg.setWindowTitle("Save Successful")
        msg.exec_()

    def save_patient_data(self):
        self.patient_data = {
            "Name": self.name_input.text(),
            "Weight (kg)": self.weight_input.text(),
            "Height (cm)": self.height_input.text(),
            "Age": self.age_input.text()
        }
        print("Patient data saved.")
        self.patient_data_saved = True

    def load_data_from_file(self, file_name):
        try:
            if file_name.lower().endswith('.xlsx') or file_name.lower().endswith('.xls'):
                excel_data = pd.read_excel(file_name)
            elif file_name.lower().endswith('.csv'):
                excel_data = pd.read_csv(file_name)
            elif file_name.lower().endswith('.txt'):
                excel_data = pd.read_csv(file_name, sep=",", header=None, names=['Timestamp', 'Value'])
            else:
                print("Unsupported file format.")
                return

            new_saved_data = [(str(row['Timestamp']), row['Value']) for _, row in excel_data.iterrows()]

            if 'Timestamp' in excel_data.columns and 'Value' in excel_data.columns:
                self.saved_data = new_saved_data
                self.data = [value for _, value in self.saved_data]
                self.x_data = list(range(len(self.data)))

                # Update the plot after changing the data
                self.adjust_data_points()
                print("Data loaded from file and plotted.")

                # Set maximum plot points based on loaded data size
                self.set_max_plot_points(len(self.data))

            else:
                print("Invalid data format in the file.")

        except Exception as e:
            print(f"Failed to load data from file: {e}")

    def load_data_from_excel(self):
        try:
            file, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;Text Files (*.txt)")
            if file:
                self.load_data_from_file(file)
                
                if file.lower().endswith(('.csv', '.txt')):
                    self.load_patient_data(file)

        except Exception as e:
            print(f"Failed to load data from file: {e}")

    def load_patient_data(self, file_name):
        try:
            if file_name.lower().endswith('.xlsx') or file_name.lower().endswith('.xls'):
                patient_data = pd.read_excel(file_name, nrows=1).to_dict(orient='records')[0]
            elif file_name.lower().endswith('.csv'):
                patient_data = pd.read_csv(file_name, nrows=1).to_dict(orient='records')[0]
            elif file_name.lower().endswith('.txt'):
                with open(file_name, 'r') as file:
                    lines = file.readlines()
                    patient_data = {}
                    start_index = lines.index('Patient Information:\n') + 1
                    for line in lines[start_index:]:
                        key, value = line.strip().split(": ")
                        patient_data[key] = value
            else:
                print("Unsupported file format for patient data.")
                return

            self.name_input.setText(patient_data.get('Name', ''))
            self.weight_input.setText(patient_data.get('Weight (kg)', ''))
            self.height_input.setText(patient_data.get('Height (cm)', ''))
            self.age_input.setText(patient_data.get('Age', ''))
            self.patient_data_saved = True
            print("Patient data loaded.")

        except Exception as e:
            print(f"Failed to load patient data from file: {e}")
            
    def show_about_info(self):
        about_text = "Real-Time EKG 3 Lead Plotter\n\n" \
                     "Created by \n\n" \
                     "Version: 1.3"
        QMessageBox.about(self, "About Real-Time Plotter", about_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    plotter = RealTimePlotApp()
    plotter.show()
    sys.exit(app.exec_())
