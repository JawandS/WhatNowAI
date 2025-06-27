import os
import json
import logging
from flask import Flask, render_template, request, jsonify, abort
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

# ----------------------------------------
# App and logging configuration
# ----------------------------------------
app = Flask(__name__)
app.config.from_mapping(
    DEBUG=True,
)

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
    # allow env var override
    if "OPENAI_API_KEY" in os.environ:
        secrets["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
    return secrets

secrets = load_secrets()
openai_key = secrets.get("OPENAI_API_KEY")
if not openai_key:
    logger.critical("OPENAI_API_KEY not found in secrets.txt or env")
    raise RuntimeError("Missing OpenAI API key")

# ----------------------------------------
# Mock tool definition
# ----------------------------------------
def search_events(query: str) -> str:
    """Stub tool to simulate event discovery."""
    return json.dumps([
        {"title": "Visit a local museum", 
         "description": "Explore history and art at your city’s top museum.", 
         "link": "https://example.com/museum"},
        {"title": "Try a yoga class", 
         "description": "Find balance and energy at a local yoga studio.", 
         "link": "https://example.com/yoga"},
        {"title": "Attend a tech meetup", 
         "description": "Connect with innovators at a free community meetup.", 
         "link": "https://example.com/meetup"}
    ])

tools = [
    Tool(
        name="search_events",
        func=search_events,
        description="Finds activities based on the user's location, interests, and context"
    )
]

# ----------------------------------------
# LLM & agent setup
# ----------------------------------------
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    api_key=openai_key
)

# Force JSON-only replies
prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are WhatNowAI, a friendly local guide.  
When you reply, output _only_ a JSON array of objects with keys:
  • title (string)  
  • description (string)  
  • link (string)  
No extra text, no markdown, no apologies.
"""),
    ("user", "{input}"),
    ("assistant", "{agent_scratchpad}")
])

agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    return_intermediate_steps=True,
    verbose=False
)

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

    user_input = payload["message"]
    logger.debug("User input: %r", user_input)

    suggestions = None
    try:
        # invoke the agent
        res = agent_executor.invoke({"input": user_input})
        logger.debug("Agent invoke result keys: %s", list(res.keys()))

        # Prefer the last tool observation if present
        if res.get("intermediate_steps"):
            _, last_obs = res["intermediate_steps"][-1]
            raw_output = last_obs
        else:
            raw_output = res.get("output", "")

        logger.info("Raw AI output: %s", raw_output)

        # parse JSON
        suggestions = json.loads(raw_output)
        if not isinstance(suggestions, list):
            raise ValueError("AI returned non-list JSON")

    except Exception as e:
        logger.error("Failed to get suggestions from AI: %s", e, exc_info=True)
        # fallback defaults
        suggestions = [
            {
                "title": "Explore a nearby café",
                "description": "Find a cozy spot and try something new.",
                "link": "https://example.com/cafe"
            },
            {
                "title": "Take a walk in the park",
                "description": "Unplug with a scenic stroll.",
                "link": "https://maps.google.com"
            },
            {
                "title": "Attend a free community event",
                "description": "Discover something happening near you.",
                "link": "https://example.com/community"
            }
        ]

    return jsonify({"suggestions": suggestions})


# ----------------------------------------
# App entrypoint
# ----------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
