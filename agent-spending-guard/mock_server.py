"""Mock payment server simulating Stripe and PayPal API endpoints."""

import json
import uuid
import time
from flask import Flask, request, jsonify

app = Flask(__name__)


# --- Stripe-style endpoints ---

@app.route("/v1/charges", methods=["POST"])
def stripe_create_charge():
    data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}
    amount = int(data.get("amount", 0))
    currency = data.get("currency", "usd")

    return jsonify({
        "id": f"ch_{uuid.uuid4().hex[:24]}",
        "object": "charge",
        "amount": amount,
        "currency": currency,
        "status": "succeeded",
        "created": int(time.time()),
        "description": data.get("description", ""),
    })


@app.route("/v1/payment_intents", methods=["POST"])
def stripe_create_payment_intent():
    data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}
    amount = int(data.get("amount", 0))
    currency = data.get("currency", "usd")

    return jsonify({
        "id": f"pi_{uuid.uuid4().hex[:24]}",
        "object": "payment_intent",
        "amount": amount,
        "currency": currency,
        "status": "succeeded",
        "created": int(time.time()),
    })


# --- PayPal-style endpoints ---

@app.route("/v2/checkout/orders", methods=["POST"])
def paypal_create_order():
    data = request.get_json(force=True, silent=True) or {}
    purchase_units = data.get("purchase_units", [{}])
    amount_obj = purchase_units[0].get("amount", {}) if purchase_units else {}

    return jsonify({
        "id": f"ORDER-{uuid.uuid4().hex[:16].upper()}",
        "status": "CREATED",
        "purchase_units": [{
            "amount": {
                "currency_code": amount_obj.get("currency_code", "USD"),
                "value": amount_obj.get("value", "0.00"),
            }
        }],
        "create_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9000, debug=False)
