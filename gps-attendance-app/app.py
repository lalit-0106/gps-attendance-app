from flask import Flask, request, render_template_string
import math
import os

app = Flask(__name__)

# ✅ Updated Office coordinates
OFFICE_LAT = 17.436922670529196
OFFICE_LON = 78.37390625737486
GEOFENCE_RADIUS_METERS = 150  # Reduced radius

# Haversine formula to calculate distance in meters
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# HTML + JS frontend
html_page = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Location Based Attendance</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
  <style>#map { height: 300px; margin-top: 20px; border-radius: 12px; }</style>
</head>
<body class="bg-gradient-to-r from-blue-500 to-indigo-600 min-h-screen flex items-center justify-center">
  <div class="bg-white shadow-2xl rounded-2xl p-10 w-full max-w-lg text-center">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">📍 Location Based Attendance</h1>
    <p class="text-gray-600 mb-4">Clock In/Out is enabled only when outside office.</p>
    <button onclick="getLocation()" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-xl shadow-lg transition-transform transform hover:scale-105">Check My Access</button>
    <p id="status" class="mt-6 text-lg font-medium text-gray-700">Waiting for action...</p>
    <div id="coords" class="mt-4 text-sm text-gray-500"></div>
    <div id="distance" class="mt-2 text-sm text-gray-500"></div>
    <div class="mt-6">
      <button id="clockBtn" disabled style="display:none;" class="bg-green-500 text-white px-6 py-3 rounded-xl shadow-md font-semibold disabled:opacity-50 disabled:cursor-not-allowed">Clock In / Clock Out</button>
    </div>
    <div id="map"></div>
  </div>

  <script>
    let readings = [];
    const NUM_READINGS = 5;
    let map, officeCircle, userMarker;

    function initMap() {
      map = L.map('map').setView([{{OFFICE_LAT}}, {{OFFICE_LON}}], 17);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);
      officeCircle = L.circle([{{OFFICE_LAT}}, {{OFFICE_LON}}], {
        color: 'red', fillColor: '#f03', fillOpacity: 0.2, radius: {{GEOFENCE_RADIUS_METERS}}
      }).addTo(map);
      L.marker([{{OFFICE_LAT}}, {{OFFICE_LON}}]).addTo(map).bindPopup("🏢 Office Location");
      map.setZoom(17);
    }

    initMap();

    function updateOnlineStatus() {
      document.getElementById("status").innerText = navigator.onLine ? "✅ Connected. You can check location." : "⚠️ No internet connection.";
      document.getElementById("clockBtn").style.display = navigator.onLine ? "none" : "none";
    }

    window.addEventListener('offline', updateOnlineStatus);
    window.addEventListener('online', updateOnlineStatus);
    updateOnlineStatus();

    function getLocation() {
      if (!navigator.onLine) {
        document.getElementById("status").innerText = "⚠️ Cannot fetch location without internet.";
        return;
      }
      readings = [];
      document.getElementById("status").innerText = "📡 Fetching multiple high-accuracy location samples...";
      if (navigator.geolocation) {
        for (let i = 0; i < NUM_READINGS; i++) {
          navigator.geolocation.getCurrentPosition(saveReading, showError, {
            enableHighAccuracy: true, timeout: 20000, maximumAge: 0
          });
        }
      } else {
        document.getElementById("status").innerText = "❌ Geolocation not supported.";
      }
    }

    function saveReading(position) {
      readings.push({ lat: position.coords.latitude, lon: position.coords.longitude });
      if (readings.length === NUM_READINGS) {
        const avgLat = readings.reduce((a,b)=>a+b.lat,0)/NUM_READINGS;
        const avgLon = readings.reduce((a,b)=>a+b.lon,0)/NUM_READINGS;
        sendPosition(avgLat, avgLon);
      }
    }

    function sendPosition(lat, lon) {
      fetch("/check_access", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ latitude: lat, longitude: lon })
      })
      .then(response => response.json())
      .then(data => {
        document.getElementById("status").innerText = data.message;
        document.getElementById("coords").innerHTML = "Latitude: " + lat.toFixed(8) + "<br>Longitude: " + lon.toFixed(8);
        document.getElementById("distance").innerText = "Distance from office: " + data.distance.toFixed(1) + " meters";
        const btn = document.getElementById("clockBtn");
        btn.style.display = data.allowed ? "inline-block" : "none";
        btn.disabled = !data.allowed;
        if (userMarker) map.removeLayer(userMarker);
        userMarker = L.marker([lat, lon]).addTo(map).bindPopup("📍 Your Location").openPopup();
        map.setView([lat, lon], 17);
      });
    }

    function showError(error) {
      const messages = {
        1: "❌ Permission denied.",
        2: "⚠️ Location unavailable.",
        3: "⌛ Request timed out."
      };
      document.getElementById("status").innerText = messages[error.code] || "❓ Unknown error.";
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(html_page, OFFICE_LAT=OFFICE_LAT, OFFICE_LON=OFFICE_LON, GEOFENCE_RADIUS_METERS=GEOFENCE_RADIUS_METERS)

@app.route("/check_access", methods=["POST"])
def check_access():
    data = request.json
    user_lat = float(data.get("latitude"))
    user_lon = float(data.get("longitude"))
    distance = haversine(user_lat, user_lon, OFFICE_LAT, OFFICE_LON)
    print(f"User at {user_lat}, {user_lon} | Distance from office: {distance:.2f}m")
    if distance > GEOFENCE_RADIUS_METERS:
        return {"allowed": True, "message": "✅ Outside office - Clock In/Out enabled", "distance": distance}
    else:
        return {"allowed": False, "message": "🚫 Inside office - Clock In/Out disabled", "distance": distance}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
