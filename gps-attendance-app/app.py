from flask import Flask, request, render_template_string
import math

app = Flask(__name__)

# ✅ Updated office coordinates (Phoenix SEZ Access Rd, Hitech City, Hyderabad)
OFFICE_LAT = 17.446236
OFFICE_LON = 78.373474
GEOFENCE_RADIUS_METERS = 200  # Geofence radius

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi/2)**2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

html_page = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Timesheet & WFH Geofence</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
  <style> #map { height: 300px; margin-top: 20px; border-radius: 12px; } </style>
</head>
<body class="bg-gradient-to-r from-blue-500 to-indigo-600 min-h-screen flex items-center justify-center">
  <div class="bg-white shadow-2xl rounded-2xl p-10 w-full max-w-lg text-center">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">📍 Live Geofence Check</h1>
    <button onclick="getLocation()" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-xl shadow-lg">
      Check My Access
    </button>
    <p id="status" class="mt-6 text-lg text-gray-700">Waiting...</p>
    <div id="coords" class="mt-4 text-sm text-gray-500"></div>
    <div id="distance" class="mt-2 text-sm text-gray-500"></div>
    <div class="mt-6"><button id="clockBtn" disabled style="display:none;" class="bg-green-500 text-white px-6 py-3 rounded-xl shadow-md font-semibold">Clock In / Clock Out</button></div>
    <div id="map"></div>
  </div>
<script>
  let readings = [], NUM_READINGS = 5, map, officeCircle, userMarker;

  function initMap() {
    map = L.map('map').setView([{{OFFICE_LAT}}, {{OFFICE_LON}}], 17);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    officeCircle = L.circle([{{OFFICE_LAT}}, {{OFFICE_LON}}], {color:'red',fillColor:'#f03',fillOpacity:0.2,radius:{{GEOFENCE_RADIUS_METERS}}}).addTo(map);
    L.marker([{{OFFICE_LAT}}, {{OFFICE_LON}}]).addTo(map).bindPopup("🏢 Phoenix Equinox Office");
  }
  initMap();

  function updateOnline() {
    let s = navigator.onLine ? "✅ Connected." : "⚠️ No internet.";
    document.getElementById("status").innerText = s;
    if (!navigator.onLine) document.getElementById("clockBtn").style.display = "none";
  }
  window.addEventListener('offline', updateOnline);
  window.addEventListener('online', updateOnline);
  updateOnline();

  function getLocation(){
    if (!navigator.onLine) {
      document.getElementById("status").innerText="⚠️ No internet.";
      return;
    }
    readings=[]; document.getElementById("status").innerText="📡 Getting GPS samples...";
    for(let i=0;i<NUM_READINGS;i++){
      navigator.geolocation.getCurrentPosition(saveReading, showError,{enableHighAccuracy:true, timeout:20000, maximumAge:0});
    }
  }

  function saveReading(pos){
    readings.push({lat:pos.coords.latitude, lon:pos.coords.longitude});
    if(readings.length===NUM_READINGS){
      let avgLat = readings.reduce((a,b)=>a+b.lat,0)/NUM_READINGS;
      let avgLon = readings.reduce((a,b)=>a+b.lon,0)/NUM_READINGS;
      sendPosition(avgLat, avgLon);
    }
  }

  function sendPosition(lat, lon) {
    fetch("/check_access",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({latitude:lat,longitude:lon})})
      .then(res=>res.json()).then(data=>{
        document.getElementById("status").innerText=data.message;
        document.getElementById("coords").innerHTML="Lat: "+lat.toFixed(8)+"<br>Lon: "+lon.toFixed(8);
        document.getElementById("distance").innerText="Distance: "+data.distance.toFixed(1)+" m";
        const btn=document.getElementById("clockBtn");
        if(data.allowed && navigator.onLine){ btn.style.display="inline-block"; btn.disabled=false; } else btn.style.display="none";
        if(userMarker) map.removeLayer(userMarker);
        userMarker=L.marker([lat,lon]).addTo(map).bindPopup("📍 You").openPopup();
        map.setView([lat,lon],17);
      });
  }

  function showError(err){
    let m="";
    if(err.code===1) m="❌ Permission denied.";
    else if(err.code===2) m="⚠️ Position unavailable.";
    else if(err.code===3) m="⌛ Timeout.";
    else m="❓ Unknown error.";
    document.getElementById("status").innerText=m;
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
    user_lat = float(data['latitude'])
    user_lon = float(data['longitude'])
    distance = haversine(user_lat, user_lon, OFFICE_LAT, OFFICE_LON)
    allowed = distance > GEOFENCE_RADIUS_METERS
    msg = "✅ Outside – Clock enabled" if allowed else "🚫 Inside – Clock disabled"
    return {"allowed": allowed, "message": f"{msg}. Distance: {distance:.1f} m", "distance": distance}

if __name__=="__main__":
    app.run(debug=True)
