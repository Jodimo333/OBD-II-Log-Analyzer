import csv
import random
from datetime import datetime, timedelta

data = []
current_time = datetime.now()
current_temp = 90.0  # starting engine temperature

for i in range(10000):
    # polling rate (100-300 ms apart)
    current_time += timedelta(milliseconds=random.randint(100, 300))
    time_string = current_time.strftime("%H:%M:%S.%f")[:-3]

    # stress test (normal driving vs anomalies)
    if 8000 <= i <= 8500: # extended the anomaly window so the temp has time to rise
        speed = round(random.uniform(100.0, 115.0), 1)
        rpm = random.randint(5000, 6500)
        throttle_pos = round(random.uniform(85.0, 100.0), 1) 
        engine_load = round(random.uniform(85.0, 98.0), 1)   
        battery_volt = round(random.uniform(11.5, 12.2), 2)  
        
        # temperature rises under heavy load
        current_temp += random.uniform(0.5, 1.5)
    else:
        speed = round(random.uniform(50.0, 75.0), 1)
        rpm = random.randint(1800, 2600)
        throttle_pos = round(random.uniform(15.0, 25.0), 1)
        engine_load = round(random.uniform(20.0, 40.0), 1)
        battery_volt = round(random.uniform(13.8, 14.2), 2)
        
        # stabilizes around 90 when driving normally
        if current_temp > 90.0:
            current_temp -= random.uniform(0.3, 0.8)
        elif current_temp < 88.0:
            current_temp += random.uniform(0.1, 0.3)

    # MAF calculation
    maf = round((rpm * engine_load) / 8500 + random.uniform(-1.0, 1.0), 1)
    row_temp = round(current_temp, 1)

    # messing up (sensor short, dropped packet format, blank data format, total bus freeze)
    if random.random() < 0.02:
        row_temp = -99.0  
        
    if random.random() < 0.05:
        rpm = "NaN"       
        
    if random.random() < 0.05:
        battery_volt = "" 

    if random.random() < 0.02:
        speed, rpm, row_temp, throttle_pos, engine_load, battery_volt, maf = "", "", "", "", "", "", ""

    data.append([
        time_string, speed, rpm, row_temp,
        throttle_pos, engine_load, battery_volt, maf
    ])

# header
with open('data.csv', 'w', newline='') as file:
    writer = csv.writer(file)

    writer.writerow(["# OBD-II Telemetry Log v1.4"])
    writer.writerow([f"# Today's Date: {datetime.now().strftime('%Y-%m-%d')}"])
    writer.writerow(["# Vehicle ID: PSHE-GT3RS-001"])
    writer.writerow([]) 
    
    writer.writerow([
        'Timestamp', 'Speed (km/h)', 'Engine RPM (rpm)', 'Coolant Temp (°C)', 
        'Throttle Pos (%)', 'Engine Load (%)', 'Battery Voltage (V)', 'MAF (g/s)'
    ])
    writer.writerows(data)

print("done")
