import tkinter as tk
from tkinter import ttk
import datetime

def decode_metar(metar):
    # Simplified decoding logic, should be expanded as needed
    parts = metar.split()
    data = {
        'ICAO': parts[0],
        'Time': parts[1],
        'Wind': parts[2],
        'Visibility': parts[3],
        'Weather': parts[4],
        'Clouds': parts[5],
        'Temperature/Dewpoint': parts[6],
        'QNH': parts[7],
        'Remarks': ' '.join(parts[8:])
    }
    return data

def decode_taf(taf):
    # Simplified decoding logic, should be expanded as needed
    parts = taf.split()
    data = {
        'ICAO': parts[0],
        'Time': parts[1],
        'Validity': parts[2],
        'Wind': parts[3],
        'Visibility': parts[4],
        'Weather': parts[5],
        'Clouds': parts[6],
        'Changes': ' '.join(parts[7:])
    }
    return data

def analyze_weather(metar, taf):
    metar_data = decode_metar(metar)
    taf_data = decode_taf(taf)

    current_time = datetime.datetime.utcnow()
    metar_time = datetime.datetime.strptime(metar_data['Time'], '%d%H%MZ')
    taf_start_time = datetime.datetime.strptime(taf_data['Validity'][:6], '%d%H%M')
    taf_end_time = datetime.datetime.strptime(taf_data['Validity'][7:], '%d%H%M')

    warnings = []

    if metar_time < current_time - datetime.timedelta(hours=1):
        warnings.append('METAR is out of date.')

    if taf_end_time < current_time:
        warnings.append('TAF is out of date.')

    if 'TS' in metar_data['Weather'] or 'TS' in taf_data['Weather']:
        warnings.append('Thunderstorm detected.')

    # Example of extracting specific weather details
    lowest_visibility = min(int(metar_data['Visibility']), int(taf_data['Visibility']))
    lowest_cloud_base = min(int(metar_data['Clouds'][3:6]), int(taf_data['Clouds'][3:6]))

    return metar_data, taf_data, lowest_visibility, lowest_cloud_base, warnings

def submit():
    metar = metar_entry.get()
    taf = taf_entry.get()
    metar_data, taf_data, visibility, cloud_base, warnings = analyze_weather(metar, taf)

    for key, value in metar_data.items():
        metar_table.insert("", "end", values=(key, value))
    
    for key, value in taf_data.items():
        taf_table.insert("", "end", values=(key, value))

    result_label.config(text=f"Lowest Visibility: {visibility}m\nLowest Cloud Base: {cloud_base}ft\nWarnings: {', '.join(warnings)}")

app = tk.Tk()
app.title("METAR/TAF Decoder")

tk.Label(app, text="Enter METAR:").pack()
metar_entry = tk.Entry(app, width=100)
metar_entry.pack()

tk.Label(app, text="Enter TAF:").pack()
taf_entry = tk.Entry(app, width=100)
taf_entry.pack()

submit_button = tk.Button(app, text="Submit", command=submit)
submit_button.pack()

metar_table = ttk.Treeview(app, columns=("Field", "Value"), show="headings")
metar_table.heading("Field", text="Field")
metar_table.heading("Value", text="Value")
metar_table.pack()

taf_table = ttk.Treeview(app, columns=("Field", "Value"), show="headings")
taf_table.heading("Field", text="Field")
taf_table.heading("Value", text="Value")
taf_table.pack()

result_label = tk.Label(app, text="", wraplength=400)
result_label.pack()

app.mainloop()
