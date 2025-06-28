import os
import json
import logging
from openai import OpenAI
from flask import Flask, render_template, request, jsonify, abort

# ----------------------------------------
# OpenAI client setup
# ----------------------------------------
# Load key from secrets.txt
openai_key = None
if "OPENAI_API_KEY" in os.environ:
    openai_key = os.environ["OPENAI_API_KEY"]
if not openai_key:
    secrets_path = "secrets.txt"
    if os.path.exists(secrets_path):
        with open(secrets_path) as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    openai_key = line.strip().split("=", 1)[1]
if not openai_key:
    raise RuntimeError("Missing OpenAI API key. Set OPENAI_API_KEY in environment or secrets.txt")
client = OpenAI(api_key=openai_key)

# ----------------------------------------
# App and logging configuration
# ----------------------------------------
app = Flask(__name__)
app.config.from_mapping(DEBUG=True)

logging.basicConfig(
    level=logging.DEBUG if app.config["DEBUG"] else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

# ----------------------------------------
# Secrets loading
# ----------------------------------------
def load_secrets(path="secrets.txt"):
    """Load KEY=VALUE pairs from a file, falling back to environment."""
    secrets = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    secrets[k] = v
    if "OPENAI_API_KEY" in os.environ:
        secrets["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
    return secrets

secrets = load_secrets()
openai_key = secrets.get("OPENAI_API_KEY")
if not openai_key:
    logger.critical("OPENAI_API_KEY not found in secrets.txt or env")
    raise RuntimeError("Missing OpenAI API key")


# ----------------------------------------
# Routes
# ----------------------------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")


@app.route("/suggestions", methods=["POST"])
def suggestions():
    payload = request.get_json(silent=True)
    if not payload or "message" not in payload:
        logger.warning("Bad request: missing JSON or 'message' key")
        abort(400, description="Request must be JSON with a 'message' field")

    user_input = payload["message"].strip()
    logger.debug("User input: %r", user_input)

    try:
        # 1) Call OpenAI ChatCompletion directly
        system_prompt = (
            "You are WhatNowAI, a friendly local guide. "
            "Based on the user's request, suggest three fun activities they can do. "
            "Respond *only* with a JSON array of objects, each with keys "
            "`title` (string), `description` (string), and `link` (string)."
            " Do not include any other text or explanations."
            " If you cannot suggest anything, return an empty array."
            " Do not use any markdown formatting or code blocks."
        )
        user_prompt = f"User says: \"{user_input}\""

        resp = client.chat.completions.create(model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=500)

        raw_output = resp.choices[0].message.content
        logger.info("Raw AI output: %s", raw_output)

        # 2) Parse it as JSON
        suggestions = json.loads(raw_output)
        if not isinstance(suggestions, list):
            raise ValueError("AI returned JSON but it was not a list")
        
        if len(suggestions) == 0:
            logger.info("AI returned an empty suggestions list")
            suggestions = [
                {
                    "title": "No suggestions",
                    "description": "The AI could not find any activities based on your input.",
                    "link": ""
                },
            ]
        else:
            logger.info("AI returned %d suggestions", len(suggestions))
            for suggestion in suggestions:
                if not isinstance(suggestion, dict) or \
                   "title" not in suggestion or \
                   "description" not in suggestion or \
                   "link" not in suggestion:
                    raise ValueError("AI returned malformed suggestion: %s" % suggestion)

    except Exception as e:
        logger.error("Failed to get suggestions from AI: %s", e, exc_info=True)
        # fallback defaults
        suggestions = [
            {
                "title": "Sorry",
                "description": "An error occurred while processing your request.",
                "link": ""
            },
        ]

    return jsonify({"suggestions": suggestions})


# ----------------------------------------
# App entrypoint
# ----------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
