# This script deploys the order management hosted-agent container.

import argparse
import os
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentEndpointConfig,
    AgentEndpointProtocol,
    ContainerConfiguration,
    FixedRatioVersionSelectionRule,
    HostedAgentDefinition,
    ProtocolConfiguration,
    ProtocolVersionRecord,
    ResponsesProtocolConfiguration,
    VersionSelector,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


AGENT_ROOT = Path(__file__).resolve().parent
POLL_INTERVAL_SECONDS = 10
MAX_POLL_ATTEMPTS = 60


def get_required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register and route the order management hosted agent."
    )
    parser.add_argument("--project-endpoint")
    parser.add_argument("--model-deployment")
    parser.add_argument("--image")
    return parser.parse_args()


def wait_for_active_version(
    project_client: AIProjectClient,
    agent_name: str,
    agent_version: str,
) -> None:
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL_SECONDS)
        details = project_client.agents.get_version(
            agent_name=agent_name,
            agent_version=agent_version,
        )
        status = details["status"]
        print(
            f"Provisioning status: {status} "
            f"(attempt {attempt}/{MAX_POLL_ATTEMPTS})"
        )

        if status == "active":
            return
        if status == "failed":
            raise RuntimeError(
                f"Hosted agent provisioning failed: {dict(details)}"
            )

    raise TimeoutError(
        f"Timed out waiting for hosted agent version {agent_version} "
        "to become active."
    )


def deploy(
    project_endpoint: str | None = None,
    model_deployment_name: str | None = None,
    image_uri: str | None = None,
) -> None:
    load_dotenv(AGENT_ROOT / ".env")

    endpoint = project_endpoint or get_required_setting(
        "PROJECT_ENDPOINT"
    )
    model_deployment = model_deployment_name or get_required_setting(
        "DEPLOYMENT_NAME"
    )
    image = image_uri or get_required_setting("HOSTED_AGENT_IMAGE")
    agent_name = os.getenv(
        "HOSTED_AGENT_NAME",
        "order-management-agent-python",
    )

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=endpoint,
            credential=credential,
        ) as project_client,
    ):
        created = project_client.agents.create_version(
            agent_name=agent_name,
            description=(
                "Python-hosted order management agent with direct Product API, "
                "knowledge, Fabric IQ, and Web IQ tools."
            ),
            definition=HostedAgentDefinition(
                cpu="1",
                memory="2Gi",
                container_configuration=ContainerConfiguration(image=image),
                environment_variables={
                    "PROJECT_ENDPOINT": endpoint,
                    "DEPLOYMENT_NAME": model_deployment,
                    "PRODUCT_API_MCP_URL": os.getenv(
                        "PRODUCT_API_MCP_URL",
                        "https://irf-api-mgt.azure-api.net/product-api-mcp/mcp",
                    ),
                    "PRODUCT_API_CONNECTION_ID": os.getenv(
                        "PRODUCT_API_CONNECTION_ID",
                        "product-api-python-agent",
                    ),
                    "FNDY_IQ_MCP_URL": os.getenv(
                        "FNDY_IQ_MCP_URL",
                        (
                            "https://order-mgt-ai-search.search.windows.net/"
                            "knowledgebases/order-mgt-kb/mcp"
                            "?api-version=2026-08-01-preview"
                        ),
                    ),
                    "FNDY_IQ_CONNECTION_ID": os.getenv(
                        "FNDY_IQ_CONNECTION_ID",
                        "order-kb-python-agent",
                    ),
                    "FABRIC_IQ_URL": os.getenv(
                        "FABRIC_IQ_URL",
                        (
                            "https://f74583ebb3e347a28ff38b968c8e02f8."
                            "zf7.w.api.fabric.microsoft.com/v1/mcp/workspaces/"
                            "f74583eb-b3e3-47a2-8ff3-8b968c8e02f8/dataagents/"
                            "0ee863be-0841-42c4-8ef9-d80118aafa1d/agent"
                        ),
                    ),
                    "FABRIC_IQ_CREDENTIAL_CONNECTION_ID": os.getenv(
                        "FABRIC_IQ_CREDENTIAL_CONNECTION_ID",
                        "sales-iq-python-agent-credentials",
                    ),
                    "WEB_IQ_MCP_URL": os.getenv(
                        "WEB_IQ_MCP_URL",
                        "https://api.microsoft.ai/v3/mcp",
                    ),
                    "WEB_IQ_CONNECTION_ID": os.getenv(
                        "WEB_IQ_CONNECTION_ID",
                        "web-iq-python-agent",
                    ),
                },
                protocol_versions=[
                    ProtocolVersionRecord(
                        protocol=AgentEndpointProtocol.RESPONSES,
                        version="2.0.0",
                    )
                ],
            ),
        )
        print(
            f"Created hosted agent {agent_name} version {created.version} "
            f"from {image}."
        )

        wait_for_active_version(
            project_client,
            agent_name,
            created.version,
        )

        project_client.agents.update_details(
            agent_name=agent_name,
            agent_endpoint=AgentEndpointConfig(
                version_selector=VersionSelector(
                    version_selection_rules=[
                        FixedRatioVersionSelectionRule(
                            agent_version=created.version,
                            traffic_percentage=100,
                        )
                    ]
                ),
                protocol_configuration=ProtocolConfiguration(
                    responses=ResponsesProtocolConfiguration()
                ),
            ),
        )
        print(
            f"Routed 100% of {agent_name} traffic to version "
            f"{created.version}."
        )


if __name__ == "__main__":
    arguments = parse_args()
    deploy(
        project_endpoint=arguments.project_endpoint,
        model_deployment_name=arguments.model_deployment,
        image_uri=arguments.image,
    )
