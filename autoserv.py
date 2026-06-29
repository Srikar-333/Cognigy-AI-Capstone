from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import random
import os
import json

app = Flask(__name__)
CORS(app)

# =============================================
# FILE PERSISTENCE HELPERS
# =============================================

DATA_FILE = "data_store.json"

DEFAULT_DATA = {
    "customers": [
        {"id": "CUST001", "name": "John Smith",    "phone_number": "8333077740", "license_plate": "ABC1234", "postal_code": "90310", "email": "john@email.com",  "vehicle": {"plate": "ABC1234", "make": "Toyota", "model": "Camry",   "year": 2022}},
        {"id": "CUST002", "name": "Sarah Johnson", "phone_number": "8333077741", "license_plate": "XYZ5678", "postal_code": "10501", "email": "sarah@email.com", "vehicle": {"plate": "XYZ5678", "make": "Honda",  "model": "Civic",   "year": 2023}},
        {"id": "CUST003", "name": "Raj Patel",     "phone_number": "8333077742", "license_plate": "DEF9012", "postal_code": "63601", "email": "raj@email.com",   "vehicle": {"plate": "DEF9012", "make": "Ford",   "model": "Mustang", "year": 2021}},
        {"id": "CUST004", "name": "Maria Garcia",  "phone_number": "8333077743", "license_plate": "GHI3456", "postal_code": "35301", "email": "maria@email.com", "vehicle": {"plate": "GHI3456", "make": "BMW",    "model": "X5",      "year": 2024}},
        {"id": "CUST005", "name": "David Lee",     "phone_number": "8333077744", "license_plate": "JKL7890", "postal_code": "94108", "email": "david@email.com", "vehicle": {"plate": "JKL7890", "make": "Tesla",  "model": "Model 3", "year": 2025}},
    ],
    "appointments": [
        {"id": "APT001", "customer_id": "CUST001", "license_plate": "ABC1234", "service_type": "oil_change",      "location": "Downtown Service Center", "date_time": "2026-05-01T10:00:00", "status": "confirmed", "technician": "Mike Torres", "duration": "45 minutes"},
        {"id": "APT002", "customer_id": "CUST002", "license_plate": "XYZ5678", "service_type": "brake_inspection", "location": "Westside Auto Hub",       "date_time": "2026-05-03T14:00:00", "status": "confirmed", "technician": "Lisa Chen",   "duration": "60 minutes"},
        {"id": "APT003", "customer_id": "CUST003", "license_plate": "DEF9012", "service_type": "full_service",     "location": "North Park Auto Care",    "date_time": "2026-05-05T09:00:00", "status": "confirmed", "technician": "David Kim",   "duration": "120 minutes"},
    ],
    "inspections": []
}

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return {k: list(v) for k, v in DEFAULT_DATA.items()}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_collection(name):
    return load_data()[name]

def update_collection(name, updated_list):
    data = load_data()
    data[name] = updated_list
    save_data(data)


# =============================================
# STT NORMALIZATION HELPERS
# =============================================

def normalize_plate(raw):
    """Strip all non-alphanumeric chars and uppercase. 'ABC 1234' → 'ABC1234'"""
    return ''.join(ch for ch in str(raw) if ch.isalnum()).upper().strip()

def normalize_phone(raw):
    """Keep only digits. '833 307 7740' → '8333077740'"""
    return ''.join(ch for ch in str(raw) if ch.isdigit())

def normalize_postal(raw):
    """Keep only digits. '9 0 3 1 0' → '90310'"""
    return ''.join(ch for ch in str(raw) if ch.isdigit())

def normalize_id(raw):
    """Remove spaces and hyphens and uppercase. 'APT 607 EAD' → 'APT607EAD'"""
    return str(raw).replace(" ", "").replace("-", "").upper().strip()


# =============================================
# MOCK DATA
# =============================================

technicians = ["Mike Torres", "Lisa Chen", "David Kim", "Ana Rodriguez", "James Wilson"]

durations = {
    "oil_change":          "45 min",
    "tire_rotation":       "30 min",
    "brake_inspection":    "60 min",
    "full_service":        "120 min",
    "engine_diagnostic":   "90 min",
    "ac_service":          "60 min",
    "battery_replacement": "30 min",
    "wheel_alignment":     "45 min",
    "inspection":          "60 min",
}


# =============================================
# 1. VERIFY CUSTOMER (ID&V)
# =============================================
@app.route("/api/identity/verify", methods=["POST"])
def verify_customer():
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "Please provide your phone number, license plate, and postal code."
        }), 400

    input_phone  = normalize_phone(data.get("phone_number", ""))
    input_plate  = normalize_plate(data.get("license_plate", ""))
    input_postal = normalize_postal(data.get("postal_code", ""))

    customers = get_collection("customers")

    customer = next(
        (c for c in customers
         if normalize_phone(c["phone_number"])  == input_phone
         and normalize_plate(c["license_plate"]) == input_plate
         and normalize_postal(c["postal_code"])  == input_postal),
        None
    )

    if customer:
        return jsonify({
            "success":     True,
            "customer_id": customer["id"],
            "name":        customer["name"],
            "email":       customer["email"],
            "vehicle":     customer["vehicle"],
            "message":     "Customer verified successfully"
        })
    else:
        return jsonify({
            "success": False,
            "error": "The phone number, license plate, or postal code you entered is incorrect. Please check and try again."
        }), 401


# =============================================
# 2. GET AVAILABLE SLOTS
# =============================================
@app.route("/api/vehicle/slots", methods=["GET"])
def get_slots():
    location = request.args.get("location", "")
    service  = request.args.get("service_type", "")
    date     = request.args.get("date", "")

    if not location or not service or not date:
        return jsonify({"success": False, "error": "location, service_type, and date are all required"}), 400

    times = ["09:00", "09:30", "10:00", "10:30", "11:00", "13:00", "14:00", "14:30", "15:00", "16:00"]
    slots = [{"date_time": f"{date}T{t}:00", "location": location} for t in times if random.random() > 0.3]

    return jsonify({
        "success":            True,
        "location":           location,
        "service_type":       service,
        "date":               date,
        "estimated_duration": durations.get(service, "60 min"),
        "available_slots":    slots,
        "total_available":    len(slots)
    })


# =============================================
# 3. GET CUSTOMER APPOINTMENTS
# =============================================
@app.route("/api/vehicle/appointments", methods=["GET"])
def get_appointments():
    plate = request.args.get("plate", "")

    if not plate:
        return jsonify({"success": False, "error": "plate query parameter is required"}), 400

    plate_normalized = normalize_plate(plate)
    appointments     = get_collection("appointments")
    results          = [
        a for a in appointments
        if normalize_plate(a["license_plate"]) == plate_normalized
        and a["status"] != "cancelled"
    ]

    return jsonify({
        "success":       True,
        "license_plate": plate_normalized,
        "appointments":  results,
        "total":         len(results)
    })


# =============================================
# 4. BOOK APPOINTMENT
# =============================================
@app.route("/api/vehicle/appointments", methods=["POST"])
def book_appointment():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "Send JSON body"}), 400

    required = ["customer_id", "license_plate", "service_type", "location", "date_time"]
    missing  = [f for f in required if not data.get(f)]

    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

    new_appt = {
        "id":            f"APT{uuid.uuid4().hex[:6].upper()}",
        "customer_id":   data["customer_id"],
        "license_plate": normalize_plate(data["license_plate"]),
        "service_type":  data["service_type"],
        "location":      data["location"],
        "date_time":     data["date_time"],
        "status":        "confirmed",
        "technician":    random.choice(technicians),
        "duration":      durations.get(data["service_type"], "60 min"),
    }

    appointments = get_collection("appointments")
    appointments.append(new_appt)
    update_collection("appointments", appointments)

    return jsonify({
        "success":     True,
        "message":     "Appointment booked successfully!",
        "appointment": new_appt
    }), 201


# =============================================
# 5. CANCEL APPOINTMENT
# =============================================
@app.route("/api/vehicle/appointments/<appt_id>", methods=["DELETE"])
def cancel_appointment(appt_id):
    appt_id      = normalize_id(appt_id)
    appointments = get_collection("appointments")
    appt         = next((a for a in appointments if normalize_id(a["id"]) == appt_id), None)

    if not appt:
        return jsonify({"success": False, "error": f"Appointment '{appt_id}' not found"}), 404

    if appt["status"] == "cancelled":
        return jsonify({"success": False, "error": "This appointment is already cancelled"}), 400

    appt["status"] = "cancelled"
    update_collection("appointments", appointments)

    return jsonify({
        "success":               True,
        "message":               "Appointment cancelled successfully",
        "cancelled_appointment": appt
    })


# =============================================
# 6. CHECK APPOINTMENT STATUS
# =============================================
@app.route("/api/vehicle/status/<appt_id>", methods=["GET"])
def check_status(appt_id):
    appt_id      = normalize_id(appt_id)
    appointments = get_collection("appointments")
    appt         = next((a for a in appointments if normalize_id(a["id"]) == appt_id), None)

    if not appt:
        return jsonify({"success": False, "error": f"Appointment '{appt_id}' not found"}), 404

    return jsonify({
        "success":             True,
        "appointment":         appt,
        "technician_assigned": appt["technician"],
        "estimated_duration":  appt["duration"],
        "arrival_tip":         "Please arrive 10-15 minutes early"
    })


# =============================================
# 6B. CHECK TECHNICIAN ASSIGNMENT
# =============================================
@app.route("/api/vehicle/technician/<appt_id>", methods=["GET"])
def check_technician(appt_id):
    appt_id      = normalize_id(appt_id)
    appointments = get_collection("appointments")
    appt         = next((a for a in appointments if normalize_id(a["id"]) == appt_id), None)

    if not appt:
        return jsonify({"success": False, "error": f"Appointment '{appt_id}' not found"}), 404

    if appt["status"] == "cancelled":
        return jsonify({"success": False, "error": "This appointment has been cancelled. No technician is assigned."}), 400

    return jsonify({
        "success":             True,
        "appointment_id":      appt["id"],
        "license_plate":       appt["license_plate"],
        "service_type":        appt["service_type"],
        "technician_assigned": appt["technician"],
        "date_time":           appt["date_time"],
        "location":            appt["location"],
        "status":              appt["status"],
        "duration":            appt["duration"],
        "message":             f"Technician {appt['technician']} is assigned to your appointment"
    })


# =============================================
# 7. RESCHEDULE APPOINTMENT
# =============================================
@app.route("/api/vehicle/appointments/<appt_id>", methods=["PUT"])
def reschedule_appointment(appt_id):
    appt_id = normalize_id(appt_id)
    data    = request.get_json()

    if not data or not data.get("new_date_time"):
        return jsonify({"success": False, "error": "new_date_time is required"}), 400

    appointments = get_collection("appointments")
    appt         = next((a for a in appointments if normalize_id(a["id"]) == appt_id), None)

    if not appt:
        return jsonify({"success": False, "error": f"Appointment '{appt_id}' not found"}), 404

    if appt["status"] == "cancelled":
        return jsonify({"success": False, "error": "Cannot reschedule a cancelled appointment"}), 400

    old_time          = appt["date_time"]
    appt["date_time"] = data["new_date_time"]
    appt["status"]    = "rescheduled"
    update_collection("appointments", appointments)

    return jsonify({
        "success":            True,
        "message":            "Appointment rescheduled successfully!",
        "appointment":        appt,
        "previous_date_time": old_time,
        "crm_notification":   "Service advisor has been notified"
    })


# =============================================
# 8. BOOK GOVERNMENT INSPECTION
# =============================================
@app.route("/api/vehicle/inspections", methods=["POST"])
def book_inspection():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "Send JSON body"}), 400

    required = ["customer_id", "license_plate", "inspection_center", "preferred_date"]
    missing  = [f for f in required if not data.get(f)]

    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

    inspection = {
        "id":                 f"INS{uuid.uuid4().hex[:6].upper()}",
        "customer_id":        data["customer_id"],
        "license_plate":      normalize_plate(data["license_plate"]),
        "inspection_center":  data["inspection_center"],
        "date_time":          f"{data['preferred_date']}T10:00:00",
        "type":               "government_mandated_inspection",
        "status":             "confirmed",
        "required_documents": [
            "Vehicle Registration Certificate",
            "Insurance Proof",
            "Emission Test Certificate",
            "Photo ID",
        ],
        "duration": "60 minutes",
    }

    inspections = get_collection("inspections")
    inspections.append(inspection)
    update_collection("inspections", inspections)

    return jsonify({
        "success":    True,
        "message":    "Inspection booked successfully!",
        "inspection": inspection
    }), 201


# =============================================
# 9. RESCHEDULE GOVERNMENT INSPECTION
# =============================================
@app.route("/api/vehicle/inspections/<inspection_id>", methods=["PUT"])
def reschedule_inspection(inspection_id):
    inspection_id = normalize_id(inspection_id)
    data          = request.get_json()

    if not data or not data.get("reschedule_inspec_date"):
        return jsonify({"success": False, "error": "reschedule_inspec_date is required"}), 400

    inspections = get_collection("inspections")
    inspection  = next((i for i in inspections if normalize_id(i["id"]) == inspection_id), None)

    if not inspection:
        return jsonify({"success": False, "error": f"Inspection '{inspection_id}' not found"}), 404

    if inspection["status"] == "cancelled":
        return jsonify({"success": False, "error": "Cannot reschedule a cancelled inspection"}), 400

    old_date_time           = inspection["date_time"]
    inspection["date_time"] = f"{data['reschedule_inspec_date']}T10:00:00"
    inspection["status"]    = "rescheduled"
    update_collection("inspections", inspections)

    return jsonify({
        "success":            True,
        "message":            "Government inspection rescheduled successfully!",
        "inspection":         inspection,
        "previous_date_time": old_date_time,
        "required_documents": inspection.get("required_documents", []),
        "crm_notification":   "Inspection center has been notified of the new date"
    })


# =============================================
# HEALTH CHECK
# =============================================
@app.route("/", methods=["GET"])
def home():
    customers = get_collection("customers")
    return jsonify({
        "status": "running",
        "service": "AutoServ National Mock API",
        "test_customers": [
            {"name": c["name"], "plate": c["license_plate"], "postal": c["postal_code"]}
            for c in customers
        ]
    })

from flask import jsonify
from datetime import datetime

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "autoserv-api",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0"
    }), 200


# =============================================
# START SERVER
# =============================================
if __name__ == "__main__":
    load_data()

    print("\n🚗 AutoServ API running at http://localhost:6000\n")
    print("Test Customers:")
    print("-" * 50)
    for c in get_collection("customers"):
        print(f"  {c['name']:15}  Plate: {c['license_plate']}  Postal: {c['postal_code']}")
    print("-" * 50)
    print("\nEndpoints:")
    print("  POST   /api/identity/verify")
    print("  GET    /api/vehicle/slots?location=X&service_type=Y&date=Z")
    print("  GET    /api/vehicle/appointments?plate=X")
    print("  POST   /api/vehicle/appointments")
    print("  DELETE /api/vehicle/appointments/<id>")
    print("  GET    /api/vehicle/status/<id>")
    print("  PUT    /api/vehicle/appointments/<id>")
    print("  POST   /api/vehicle/inspections")
    print("  PUT    /api/vehicle/inspections/<id>")
    print("  GET    /api/vehicle/technician/<id>\n")

    port = int(os.environ.get("PORT", 6000))
    app.run(host="0.0.0.0", port=port, debug=False)