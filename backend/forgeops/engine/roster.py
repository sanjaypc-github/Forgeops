"""Who each agent is. The same roster serves every customer; only their connectors differ."""

from pydantic import BaseModel

from forgeops.engine.models import AgentId


class AgentProfile(BaseModel):
    id: AgentId
    title: str
    area: str
    focus: str


PROFILES: dict[AgentId, AgentProfile] = {
    p.id: p
    for p in [
        AgentProfile(
            id=AgentId.supervisor, title="Supervisor", area="Planning and coordination",
            focus="Understands the problem, decides which desks investigate what, reviews their "
                  "evidence and answers the user's follow-up questions.",
        ),
        AgentProfile(
            id=AgentId.code, title="Code", area="Source code and changes",
            focus="Recent commits, diffs, pull requests and changed files in the incident window; "
                  "which change introduced the behaviour; exact file and line of suspicious code.",
        ),
        AgentProfile(
            id=AgentId.frontend_hosting, title="Frontend & Hosting",
            area="Site builds, deployments, CDN/edge, domains and SSL",
            focus="Which deployment was live when the problem started, failed or slow builds, "
                  "edge/CDN cache and routing rules, redirects and headers, domain and certificate "
                  "problems, edge function errors.",
        ),
        AgentProfile(
            id=AgentId.backend_services, title="Backend & Services",
            area="APIs, serverless functions, auth, CMS and other backend services",
            focus="Failing or slow functions and API routes, auth/session errors, configuration and "
                  "environment changes, CMS content changes that pages depend on.",
        ),
        AgentProfile(
            id=AgentId.database, title="Database", area="Databases and data access",
            focus="Slow queries and missing indexes, connection limits and pool exhaustion, locks, "
                  "recent migrations and schema changes, access policies (for example row-level "
                  "security) that block reads or writes.",
        ),
        AgentProfile(
            id=AgentId.observability, title="Observability", area="Errors, logs, metrics and traces",
            focus="When errors started and how often, stack traces and the release they point to, "
                  "error spikes and latency changes, which endpoint or page is affected.",
        ),
        AgentProfile(
            id=AgentId.knowledge, title="Knowledge", area="Runbooks, docs and past incidents",
            focus="Runbooks and architecture notes for the affected service, known failure modes, "
                  "past incidents with the same symptoms and how they were fixed.",
        ),
        AgentProfile(
            id=AgentId.rca, title="RCA analyst", area="Root-cause analysis",
            focus="Combines every desk's evidence into the root cause, exact failure point, "
                  "timeline, confidence and recommendations.",
        ),
        AgentProfile(
            id=AgentId.action, title="Action", area="Approved changes",
            focus="Carries out only the actions a human approved, such as opening an issue, with "
                  "exactly the parameters that were approved.",
        ),
    ]
}
