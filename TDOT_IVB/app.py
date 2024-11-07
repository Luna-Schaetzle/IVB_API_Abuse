from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import re

app = Flask(__name__)

# URLs der APIs
PASSAGE_API_URL = "https://smartinfo.ivb.at/api/JSON/PASSAGE"
STOPS_API_URL = "https://smartinfo.ivb.at/api/JSON/STOPS"

# Caching der Haltestellenliste
def fetch_stops():
    """
    Holt alle Haltestellen von der STOPS API.
    Gibt eine Liste von Haltestellen zurück.
    """
    try:
        response = requests.get(STOPS_API_URL)
        response.raise_for_status()
        data = response.json()
        stops = [item['stop'] for item in data if 'stop' in item]
        return stops
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Haltestellen: {e}")
        return []

# Holen und Cachen der Haltestellen beim Start der Anwendung
cached_stops = fetch_stops()

def fetch_passage(stop_id):
    """
    Holt die Passagen-Daten für eine gegebene Haltestelle von der PASSAGE API.
    Gibt die JSON-Daten zurück oder None bei einem Fehler.
    """
    try:
        params = {'stopID': stop_id}
        response = requests.get(PASSAGE_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Passagen-Daten: {e}")
        return None

def determine_color_class(time_str):
    """
    Bestimmt die CSS-Klasse basierend auf der Zeit bis zur Abfahrt.
    - Rot: 0 min
    - Gelb: 1 min
    - Grün: mehr als 1 min
    - Grau: andere Formate (z.B. geplante Abfahrten)
    """
    # Regex, um Minuten aus dem String zu extrahieren
    match = re.match(r'(\d+)\s*min', time_str)
    if match:
        minutes = int(match.group(1))
        if minutes == 0:
            return 'text-danger'  # Rot
        elif minutes == 1:
            return 'text-warning'  # Gelb
        else:
            return 'text-success'  # Grün
    else:
        # Falls die Zeit nicht im erwarteten Format ist (z.B. "13:42")
        return 'text-secondary'  # Grau

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_stop_id = request.form.get('stop_id')
        return redirect(url_for('index', stop_id=selected_stop_id))

    stop_id = request.args.get('stop_id', '1187')  # Standard-Haltestelle: Hauptbahnhof
    data = fetch_passage(stop_id)

    if data is None:
        return "Fehler beim Abrufen der Daten."

    # Initialisiere Listen für verschiedene Datentypen
    smartinfo_list = []
    linedirections_list = []
    alerts = []
    stop_name = "Unbekannter Haltepunkt"

    for item in data:
        if 'smartinfo' in item:
            bus = item['smartinfo']
            # Bestimme die CSS-Klasse basierend auf der Zeit
            bus['color_class'] = determine_color_class(bus.get('time', ''))
            smartinfo_list.append(bus)
        elif 'linedirections' in item:
            linedirections_list.append(item['linedirections'])
        elif 'palert' in item:
            alerts.append(item['palert'])
        elif 'stopidname' in item:
            stop_name = item['stopidname']

    return render_template('index.html',
                           stops=cached_stops,
                           selected_stop_id=stop_id,
                           stop_name=stop_name,
                           alerts=alerts,
                           smartinfo=smartinfo_list,
                           linedirections=linedirections_list)

@app.route('/api/passage/<stop_id>')
def api_passage(stop_id):
    data = fetch_passage(stop_id)
    if data is None:
        return jsonify({"error": "Fehler beim Abrufen der Daten."}), 500

    smartinfo_list = []
    for item in data:
        if 'smartinfo' in item:
            bus = item['smartinfo']
            bus['color_class'] = determine_color_class(bus.get('time', ''))
            smartinfo_list.append(bus)
    return jsonify(smartinfo_list)

if __name__ == '__main__':
    app.run(debug=True)
