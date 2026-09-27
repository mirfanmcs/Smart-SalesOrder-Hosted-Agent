import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request


CLIENT_APP_ROOT = Path(__file__).resolve().parent
load_dotenv(CLIENT_APP_ROOT / ".env")

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "")
HOSTED_AGENT_NAME = os.getenv(
    "HOSTED_AGENT_NAME",
    "order-management-agent-python",
)

app = Flask(__name__)


class AgentNotConfiguredError(RuntimeError):
    pass


def get_project_client() -> AIProjectClient:
    if not PROJECT_ENDPOINT:
        raise AgentNotConfiguredError(
            "The hosted agent is unavailable because PROJECT_ENDPOINT is not "
            "configured."
        )
    return AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )


@app.get("/")
def index():
    return render_template(
        "index.html",
        agent_name=HOSTED_AGENT_NAME,
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "healthy",
            "agent": HOSTED_AGENT_NAME,
            "projectConfigured": bool(PROJECT_ENDPOINT),
        }
    )


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    if not message:
        return jsonify({"error": "A message is required."}), 400

    previous_response_id = body.get("previousResponseId")
    if previous_response_id is not None and not isinstance(
        previous_response_id, str
    ):
        return jsonify({"error": "previousResponseId must be a string."}), 400

    try:
        with get_project_client() as project_client:
            client = project_client.get_openai_client(
                agent_name=HOSTED_AGENT_NAME
            )
            if previous_response_id:
                response = client.responses.create(
                    input=message,
                    previous_response_id=previous_response_id,
                )
            else:
                response = client.responses.create(input=message)
    except AgentNotConfiguredError as error:
        app.logger.warning("Hosted agent is not configured")
        return jsonify({"error": str(error)}), 503
    except Exception as error:
        app.logger.exception("Hosted agent invocation failed")
        return jsonify(
            {
                "error": (
                    "The hosted agent is currently unavailable. "
                    "Verify its deployment and try again."
                )
            }
        ), 503

    if response.status == "failed":
        return jsonify({"error": str(response.error)}), 503

    return jsonify(
        {
            "id": response.id,
            "message": response.output_text or "The agent returned no text.",
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("CLIENT_PORT", "8080")))
    app.run(host="0.0.0.0", port=port)
