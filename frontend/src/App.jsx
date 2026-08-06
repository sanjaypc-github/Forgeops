import React, { useState, useEffect } from 'react';

// Custom lightweight SVG Icons to avoid import issues
const PlayIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
);
const RefreshIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path></svg>
);
const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
);
const XIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
);
const BookIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>
);
const GitIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="18" r="3"></circle><circle cx="6" cy="6" r="3"></circle><path d="M13 6h3a2 2 0 0 1 2 2v7"></path><line x1="6" y1="9" x2="6" y2="21"></line></svg>
);
const TerminalIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
);
const ShieldIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
);

// Pre-defined Sandbox Mock Response in case the backend server isn't run locally
const SANDBOX_INCIDENT_REPONSE = {
  investigation_id: "sandbox-eops-session-8821a",
  state: {
    incident_description: "Checkout API latency increased significantly after recent merge",
    investigation_plan: {
      steps: [
        "Fetch recent commits and pull requests to isolate code deployments.",
        "Search and parse system logs for connection issues, HTTP errors, and service spikes.",
        "Query ChromaDB documentation store for corresponding service architecture or troubleshooting runbooks."
      ],
      strategy: "Concurrent sub-agent dispatch followed by state synthesis."
    },
    active_agents: ["github", "logs", "knowledge"],
    github: {
      recent_commits: [
        {
          sha: "a1b2c3d4e5f6g7h8",
          author: "sanjay-developer",
          date: "2026-08-06T14:30:00Z",
          message: "feat(checkout): add redis cache layer to checkout api",
          files_changed: ["services/checkout/main.go", "services/checkout/cache.go"]
        },
        {
          sha: "9z8y7x6w5v4u3t2s",
          author: "dev-team-lead",
          date: "2026-08-05T09:15:00Z",
          message: "fix(db): update postgres connection pool configuration",
          files_changed: ["config/database.yml"]
        }
      ],
      recent_prs: [
        {
          id: 1024,
          title: "feat(checkout): add redis cache layer to checkout api",
          author: "sanjay-developer",
          merged_at: "2026-08-06T14:45:00Z",
          url: "https://github.com/example/repo/pull/1024"
        }
      ],
      changed_files: ["services/checkout/main.go", "services/checkout/cache.go", "config/database.yml"],
      author: "sanjay-developer",
      timestamp: "2026-08-06T14:30:00Z",
      error: null
    },
    logs: {
      raw_anomalies: [
        "[2026-08-06 14:52:10] ERROR checkout_service: Redis connection timed out after 3000ms",
        "[2026-08-06 14:52:12] WARNING checkout_service: Cache pool unavailable. Attempting direct PostgreSQL fallback query...",
        "[2026-08-06 14:52:15] ERROR api_gateway: GET /checkout/pay - Internal Server Error (500) - Connection timeout waiting for pool resources."
      ],
      parsed_errors: [
        {timestamp: "2026-08-06 14:52:10", level: "ERROR", component: "checkout_service", message: "Redis connection timed out after 3000ms"},
        {timestamp: "2026-08-06 14:52:15", level: "ERROR", component: "api_gateway", message: "GET /checkout/pay - Internal Server Error (500)"}
      ],
      redis_timeouts: true,
      cache_miss_rate: 0.85,
      status_500_count: 2,
      error: null
    },
    knowledge: {
      retrieved_documents: [
        {
          title: "Services/Checkout API Specification",
          content: "Checkout service uses Redis cache to store item details and pricing to reduce DB pressure. Redis host: redis.internal.net, port: 6379. Default connection timeout: 1000ms. If Redis is unavailable, the service fallback is configured to retrieve data directly from PostgreSQL, potentially saturating DB resources.",
          source: "knowledge/obsidian_vault/Services/checkout_api.md"
        },
        {
          title: "Runbooks/Redis Cache Latency Issues",
          content: "Symptom: High API latency or HTTP 500 errors on checkout. Action: Verify Redis CPU load and connection pools. If Redis connection errors occur, check if the latest deployment changed connection timeouts or network policies.",
          source: "knowledge/obsidian_vault/Runbooks/redis_troubleshooting.md"
        }
      ],
      suggested_runbooks: ["Runbooks/Redis Cache Latency Issues"],
      architecture_references: ["Services/Checkout API Specification"],
      error: null
    },
    root_cause: {
      probable_cause: "The incident was triggered by commit a1b2c3d4e5f6g7h8 ('feat(checkout): add redis cache layer to checkout api') authored by sanjay-developer. The checkout API is encountering a 3000ms timeout trying to reach redis.internal.net, which forces a fallback to PostgreSQL database query. The sudden database query spikes saturated postgres resource pools, causing severe latency and subsequent HTTP 500 timeouts.",
      evidence_points: [
        "Logs confirm Redis connection timeouts (3000ms duration limit exceeded).",
        "GitHub changes identify recent merge PR #1024 modifying checkout services cache configurations.",
        "RAG documents suggest fallback path leads to resource pooling exhaustion on PostgreSQL main server."
      ],
      confidence_score: 0.95,
      remediation_steps: [
        "Revert cache configuration PR #1024 to restore normal checkout paths immediately.",
        "Check network route mappings and security policy settings for TCP port 6379 outbound connections.",
        "Tune connection timeouts and fallback pool capacity for SQL database routes."
      ],
      references: [
        "knowledge/obsidian_vault/Services/checkout_api.md",
        "knowledge/obsidian_vault/Runbooks/redis_troubleshooting.md"
      ]
    },
    approval_status: "pending",
    human_feedback: null,
    current_step: "AwaitingHumanApproval",
    logs_trace: [
      "Investigation initiated.",
      "Supervisor plan generated. Dispatching agents: ['github', 'logs', 'knowledge']",
      "GitHub Agent successfully fetched 2 commits and 1 PRs.",
      "Logs Agent found 2 unique error events.",
      "Knowledge Agent retrieved 2 documents from vector store.",
      "Root Cause Analysis agent successfully finished reasoning."
    ]
  }
};

function App() {
  const [incidentText, setIncidentText] = useState('Checkout API latency increased significantly');
  const [isSandbox, setIsSandbox] = useState(true);
  const [investigationId, setInvestigationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [state, setState] = useState(null);
  const [feedbackText, setFeedbackText] = useState('');
  const [activeTab, setActiveTab] = useState('summary'); // 'summary', 'github', 'logs', 'knowledge', 'history'

  const handleStartInvestigation = async (e) => {
    e.preventDefault();
    if (!incidentText.trim()) return;

    setLoading(true);
    setInvestigationId(null);
    setState(null);

    if (isSandbox) {
      // Simulate API call lag
      setTimeout(() => {
        setInvestigationId(SANDBOX_INCIDENT_REPONSE.investigation_id);
        setState(SANDBOX_INCIDENT_REPONSE.state);
        setLoading(false);
      }, 1200);
    } else {
      try {
        const response = await fetch('/api/investigate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ incident_description: incidentText }),
        });
        if (!response.ok) throw new Error('API server returned error');
        const data = await response.json();
        setInvestigationId(data.investigation_id);
        setState(data.state);
      } catch (err) {
        alert("Failed to reach FastAPI backend. Switching back to Sandbox Mode to demonstrate functionality.");
        setIsSandbox(true);
        setInvestigationId(SANDBOX_INCIDENT_REPONSE.investigation_id);
        setState(SANDBOX_INCIDENT_REPONSE.state);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleApproval = async (approved) => {
    if (!investigationId) return;

    const bodyData = {
      approved,
      feedback: approved ? null : feedbackText
    };

    if (isSandbox) {
      const updatedState = { ...state };
      if (approved) {
        updatedState.approval_status = "approved";
        updatedState.current_step = "ReportGenerated";
        updatedState.logs_trace = [...updatedState.logs_trace, "Human approved the RCA. Generating report...", "Report written to disk: reports/RCA_sandbox-eops.md"];
      } else {
        updatedState.approval_status = "rejected";
        updatedState.current_step = "AwaitingMoreInfo";
        updatedState.human_feedback = feedbackText;
        updatedState.logs_trace = [...updatedState.logs_trace, `Human rejected the RCA. Feedback: ${feedbackText}`];
      }
      setState(updatedState);
      setFeedbackText('');
    } else {
      try {
        const response = await fetch(`/api/approve/${investigationId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(bodyData),
        });
        const data = await response.json();
        setState(data.state);
        setFeedbackText('');
      } catch (err) {
        alert("Failed to submit approval choice.");
      }
    }
  };

  // Check backend server availability on mount
  useEffect(() => {
    fetch('/api/status/health-check')
      .then(() => setIsSandbox(false))
      .catch(() => setIsSandbox(true));
  }, []);

  return (
    <div className="app-container">
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '2rem' }}>🛡️</span>
            <h1 style={{ margin: 0, fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.05rem' }}>
              EOPS <span className="gradient-text">Studio</span>
            </h1>
          </div>
          <p style={{ color: 'var(--text-secondary)', margin: '0.25rem 0 0 0', fontSize: '0.95rem' }}>
            Engineering Operations Multi-Agent Triage Platform & Incident Operating System
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Mode:</span>
          <button 
            onClick={() => setIsSandbox(!isSandbox)}
            className="glass-card" 
            style={{ 
              padding: '0.4rem 0.9rem', 
              fontSize: '0.8rem', 
              fontWeight: 600,
              cursor: 'pointer',
              background: isSandbox ? 'rgba(255, 145, 0, 0.15)' : 'rgba(0, 230, 118, 0.15)',
              borderColor: isSandbox ? 'var(--accent-orange)' : 'var(--accent-green)',
              borderRadius: '20px',
              color: isSandbox ? 'var(--accent-orange)' : 'var(--accent-green)'
            }}
          >
            {isSandbox ? 'Sandbox Simulation' : 'Connected API Backend'}
          </button>
        </div>
      </header>

      {/* Main Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
        
        {/* Left Side: Input and Graph Execution Visualizer */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Incident Trigger Card */}
          <div className="glass-card" style={{ padding: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', fontWeight: 600 }}>Triage Incident</h3>
            <form onSubmit={handleStartInvestigation}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  Incident Description
                </label>
                <textarea 
                  value={incidentText}
                  onChange={(e) => setIncidentText(e.target.value)}
                  placeholder="e.g., Checkout latency spiked to 5s after recent deployment"
                  style={{
                    width: '94%',
                    minHeight: '80px',
                    backgroundColor: 'rgba(0, 0, 0, 0.2)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '0.75rem',
                    color: 'var(--text-primary)',
                    fontFamily: 'inherit',
                    resize: 'vertical'
                  }}
                />
              </div>
              <button 
                type="submit" 
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: 'none',
                  background: 'linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-purple) 100%)',
                  color: '#000',
                  fontWeight: 'bold',
                  fontSize: '0.95rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  opacity: loading ? 0.7 : 1
                }}
              >
                {loading ? <span className="active-pulse">Running Graph...</span> : <><PlayIcon /> Run Investigation</>}
              </button>
            </form>
          </div>

          {/* Graph Agents Status Tracker */}
          <div className="glass-card" style={{ padding: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1.25rem 0', fontSize: '1.2rem', fontWeight: 600 }}>Active Graph Nodes</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', position: 'relative' }}>
              
              {/* Supervisor Agent status */}
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <div style={{ 
                  width: '32px', height: '32px', borderRadius: '50%', 
                  background: state ? 'rgba(0, 242, 254, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${state ? 'var(--accent-cyan)' : 'var(--border-color)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <ShieldIcon />
                </div>
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Supervisor Agent</div>
                  <div style={{ fontSize: '0.75rem', color: state ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                    {state ? 'Plan Formulated' : 'Idle'}
                  </div>
                </div>
              </div>

              {/* Parallel Subagents status */}
              <div style={{ paddingLeft: '1.5rem', borderLeft: '1px dashed var(--border-color)', marginLeft: '16px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                
                {/* GitHub Agent */}
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <div style={{ 
                    width: '24px', height: '24px', borderRadius: '50%',
                    background: state?.github?.recent_commits?.length > 0 ? 'rgba(155, 81, 224, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${state?.github?.recent_commits?.length > 0 ? 'var(--accent-purple)' : 'var(--border-color)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}>
                    <GitIcon />
                  </div>
                  <span style={{ fontSize: '0.85rem', color: state?.github?.recent_commits?.length > 0 ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                    GitHub Code Inspector
                  </span>
                </div>

                {/* Logs Agent */}
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <div style={{ 
                    width: '24px', height: '24px', borderRadius: '50%',
                    background: state?.logs?.parsed_errors?.length > 0 ? 'rgba(255, 23, 68, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${state?.logs?.parsed_errors?.length > 0 ? 'var(--accent-red)' : 'var(--border-color)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}>
                    <TerminalIcon />
                  </div>
                  <span style={{ fontSize: '0.85rem', color: state?.logs?.parsed_errors?.length > 0 ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                    Log Analyzer Node
                  </span>
                </div>

                {/* Knowledge Agent */}
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <div style={{ 
                    width: '24px', height: '24px', borderRadius: '50%',
                    background: state?.knowledge?.retrieved_documents?.length > 0 ? 'rgba(0, 230, 118, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${state?.knowledge?.retrieved_documents?.length > 0 ? 'var(--accent-green)' : 'var(--border-color)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}>
                    <BookIcon />
                  </div>
                  <span style={{ fontSize: '0.85rem', color: state?.knowledge?.retrieved_documents?.length > 0 ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                    Knowledge Base RAG
                  </span>
                </div>
              </div>

              {/* Synthesis node */}
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <div style={{ 
                  width: '32px', height: '32px', borderRadius: '50%', 
                  background: state?.root_cause?.probable_cause ? 'rgba(0, 230, 118, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${state?.root_cause?.probable_cause ? 'var(--accent-green)' : 'var(--border-color)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  🛡️
                </div>
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Root Cause Analysis Node</div>
                  <div style={{ fontSize: '0.75rem', color: state?.root_cause?.probable_cause ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                    {state?.root_cause?.probable_cause ? 'Hypothesis Ready' : 'Idle'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Detailed Investigation Insights */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {state ? (
            <>
              {/* Tab Navigation */}
              <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                {['summary', 'github', 'logs', 'knowledge', 'history'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: activeTab === tab ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                      padding: '0.5rem 1rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      fontSize: '0.9rem',
                      borderBottom: activeTab === tab ? '2px solid var(--accent-cyan)' : 'none'
                    }}
                  >
                    {tab.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Tab Contents */}
              <div className="glass-card" style={{ padding: '1.5rem', minHeight: '350px' }}>
                
                {activeTab === 'summary' && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                      <h4 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 600 }}>RCA Synthesis</h4>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Confidence:</span>
                        <span style={{ 
                          color: 'var(--accent-cyan)', 
                          fontWeight: 'bold',
                          padding: '0.2rem 0.5rem',
                          background: 'rgba(0, 242, 254, 0.1)',
                          border: '1px solid rgba(0, 242, 254, 0.3)',
                          borderRadius: '4px'
                        }}>
                          {Math.round(state.root_cause.confidence_score * 100)}%
                        </span>
                      </div>
                    </div>
                    
                    <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                      {state.root_cause.probable_cause}
                    </p>

                    <h5 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-primary)' }}>Evidence Matrix</h5>
                    <ul style={{ paddingLeft: '1.25rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                      {state.root_cause.evidence_points.map((pt, idx) => (
                        <li key={idx} style={{ marginBottom: '0.4rem' }}>{pt}</li>
                      ))}
                    </ul>

                    <h5 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-primary)' }}>Remediation Recommendation</h5>
                    <ol style={{ paddingLeft: '1.25rem', color: 'var(--text-secondary)' }}>
                      {state.root_cause.remediation_steps.map((step, idx) => (
                        <li key={idx} style={{ marginBottom: '0.4rem' }}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {activeTab === 'github' && (
                  <div>
                    <h4 style={{ margin: '0 0 1rem 0' }}>Code Repository Changes</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      <div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Recent Commits</div>
                        {state.github.recent_commits.map((commit, idx) => (
                          <div key={idx} className="mono" style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '6px', marginTop: '0.5rem', fontSize: '0.85rem' }}>
                            <div style={{ color: 'var(--accent-purple)', fontWeight: 'bold' }}>{commit.sha.substring(0, 8)}</div>
                            <div style={{ margin: '0.2rem 0', color: 'var(--text-primary)' }}>{commit.message}</div>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Author: {commit.author} | {commit.date}</div>
                          </div>
                        ))}
                      </div>

                      <div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Affected Code Paths</div>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                          {state.github.changed_files.map((file, idx) => (
                            <span key={idx} className="mono" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>
                              {file}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'logs' && (
                  <div>
                    <h4 style={{ margin: '0 0 1rem 0' }}>Telemetry & Logs</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                      <div className="glass-card" style={{ padding: '1rem', background: 'rgba(0,0,0,0.1)' }}>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>HTTP 500 Count</div>
                        <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: 'var(--accent-red)' }}>{state.logs.status_500_count}</div>
                      </div>
                      <div className="glass-card" style={{ padding: '1rem', background: 'rgba(0,0,0,0.1)' }}>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Cache Miss Rate</div>
                        <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: 'var(--accent-orange)' }}>{Math.round(state.logs.cache_miss_rate * 100)}%</div>
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Anomalous Log Streams</div>
                      <div className="mono" style={{ background: 'rgba(0,0,0,0.3)', padding: '0.75rem', borderRadius: '6px', overflowX: 'auto', fontSize: '0.8rem', color: 'var(--accent-red)' }}>
                        {state.logs.raw_anomalies.map((line, idx) => (
                          <div key={idx} style={{ marginBottom: '0.5rem', whiteSpace: 'pre' }}>{line}</div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'knowledge' && (
                  <div>
                    <h4 style={{ margin: '0 0 1rem 0' }}>Knowledge Base Matches (RAG)</h4>
                    {state.knowledge.retrieved_documents.map((doc, idx) => (
                      <div key={idx} style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '1rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{doc.title}</span>
                          <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{doc.source}</span>
                        </div>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.5rem', lineHeight: '1.5' }}>
                          {doc.content}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'history' && (
                  <div>
                    <h4 style={{ margin: '0 0 1rem 0' }}>Orchestrator Execution Log Trace</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {state.logs_trace.map((logLine, idx) => (
                        <div key={idx} className="mono" style={{ display: 'flex', gap: '0.5rem', fontSize: '0.85rem' }}>
                          <span style={{ color: 'var(--accent-cyan)' }}>&gt;</span>
                          <span style={{ color: 'var(--text-secondary)' }}>{logLine}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>

              {/* Action Approval Bar */}
              <div className="glass-card" style={{ padding: '1.5rem', marginTop: '0.25rem' }}>
                {state.approval_status === 'pending' ? (
                  <div>
                    <h4 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem' }}>Review Required</h4>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>
                      Please review the agent findings and root cause hypothesis. Approving will generate the final operations report.
                    </p>
                    
                    <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                      <input 
                        type="text" 
                        value={feedbackText}
                        onChange={(e) => setFeedbackText(e.target.value)}
                        placeholder="Add feedback notes (optional if approving, required if rejecting)..."
                        style={{
                          flex: 1,
                          backgroundColor: 'rgba(0, 0, 0, 0.2)',
                          border: '1px solid var(--border-color)',
                          borderRadius: '6px',
                          padding: '0.5rem 0.75rem',
                          color: '#fff'
                        }}
                      />
                    </div>
                    
                    <div style={{ display: 'flex', gap: '1rem' }}>
                      <button 
                        onClick={() => handleApproval(true)}
                        style={{
                          flex: 1, padding: '0.6rem', borderRadius: '6px', border: 'none',
                          background: 'rgba(0, 230, 118, 0.2)', color: 'var(--accent-green)',
                          border: '1px solid rgba(0, 230, 118, 0.4)', fontWeight: 'bold',
                          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem'
                        }}
                      >
                        <CheckIcon /> Approve RCA
                      </button>
                      <button 
                        onClick={() => handleApproval(false)}
                        disabled={!feedbackText.trim()}
                        style={{
                          flex: 1, padding: '0.6rem', borderRadius: '6px', border: 'none',
                          background: feedbackText.trim() ? 'rgba(255, 23, 68, 0.2)' : 'rgba(255, 255, 255, 0.02)',
                          color: feedbackText.trim() ? 'var(--accent-red)' : 'var(--text-muted)',
                          border: `1px solid ${feedbackText.trim() ? 'rgba(255, 23, 68, 0.4)' : 'var(--border-color)'}`,
                          fontWeight: 'bold', cursor: feedbackText.trim() ? 'pointer' : 'not-allowed',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem'
                        }}
                      >
                        <XIcon /> Request Info
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ 
                      width: '36px', height: '36px', borderRadius: '50%',
                      background: state.approval_status === 'approved' ? 'rgba(0, 230, 118, 0.15)' : 'rgba(255, 23, 68, 0.15)',
                      display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center'
                    }}>
                      {state.approval_status === 'approved' ? <span style={{ color: 'var(--accent-green)', fontSize: '1.2rem' }}>✓</span> : <span style={{ color: 'var(--accent-red)', fontSize: '1.2rem' }}>✗</span>}
                    </div>
                    <div>
                      <h4 style={{ margin: 0 }}>Investigation {state.approval_status === 'approved' ? 'Approved & Closed' : 'Rejected'}</h4>
                      <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {state.approval_status === 'approved' 
                          ? `Markdown report successfully generated on disk in /reports/RCA_${investigationId.substring(0,8)}.md`
                          : `Workflow paused. Requested revision feedback: "${state.human_feedback}"`
                        }
                      </p>
                    </div>
                  </div>
                )}
              </div>

            </>
          ) : (
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '450px', color: 'var(--text-secondary)' }}>
              <span style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>📡</span>
              <p style={{ fontSize: '1.1rem', margin: 0 }}>Awaiting investigation trigger...</p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Enter an incident description on the left panel to execute the graph.
              </p>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}

export default App;
