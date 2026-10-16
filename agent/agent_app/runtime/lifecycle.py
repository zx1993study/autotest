from __future__ import annotations

from agent_app.api.client import AgentApiClient
from agent_app.api.nodes import AgentNodeApi
from agent_app.api.tasks import AgentTaskApi
from agent_app.config import AgentConfig
from agent_app.runtime.heartbeat import HeartbeatTicker
from agent_app.runtime.task_poller import AgentTaskPoller
from agent_app.runtime.task_runner import AgentTaskRunner


def build_poller(config: AgentConfig) -> AgentTaskPoller:
    """Create the runtime poller with all API and executor dependencies."""

    client = AgentApiClient(config.server_url, config.token)
    node_api = AgentNodeApi(client, config)
    task_api = AgentTaskApi(client, config)
    node_api.register()
    heartbeat = HeartbeatTicker(node_api, config.heartbeat_interval_sec)
    heartbeat.send_now("online")
    return AgentTaskPoller(
        task_api=task_api,
        heartbeat=heartbeat,
        runner=AgentTaskRunner(config, task_api),
        poll_interval_sec=config.poll_interval_sec,
    )
