from forgeops.engine.models import AgentId, Capability

# Every capability belongs to exactly one desk. One connector may provide several.
CAPABILITY_AGENT: dict[Capability, AgentId] = {
    Capability.code: AgentId.code,
    Capability.hosting: AgentId.frontend_hosting,
    Capability.backend: AgentId.backend_services,
    Capability.content: AgentId.backend_services,
    Capability.database: AgentId.database,
    Capability.errors: AgentId.observability,
    Capability.logs: AgentId.observability,
    Capability.metrics: AgentId.observability,
    Capability.knowledge: AgentId.knowledge,
    Capability.write: AgentId.action,
}


def agent_for_capability(capability: Capability) -> AgentId:
    return CAPABILITY_AGENT[capability]
