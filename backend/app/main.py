import os
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

from langgraph.graph import EOPSInvestigationGraph
from memory.state import InvestigationState

app = FastAPI(
    title="EOPS Backend API",
    description="Application server for EOPS AI Operations Incident Triage Platform",
    version="1.0.0"
)

# Enable CORS for local dashboard development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory investigation storage for MVP
INVESTIGATIONS: Dict[str, InvestigationState] = {}
graph = EOPSInvestigationGraph()

class IncidentRequest(BaseModel):
    incident_description: str

class ApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "EOPS Backend API running.", "status": "healthy"}

@app.post("/api/investigate")
async def start_investigation(request: IncidentRequest):
    """
    Initiates the multi-agent orchestration graph to triage the reported incident.
    """
    if not request.incident_description.strip():
        raise HTTPException(status_code=400, detail="Incident description cannot be empty.")
    
    investigation_id = str(uuid.uuid4())
    
    # Initialize the graph state
    initial_state = graph.get_initial_state(request.incident_description)
    INVESTIGATIONS[investigation_id] = initial_state
    
    # Run the initial investigation steps (planning, sub-agent run, rca synthesis)
    try:
        # Step 1: Supervisor plan
        state = graph.execute_step(initial_state)
        # Step 2: Run active sub-agents in parallel
        state = graph.execute_step(state)
        # Step 3: Root cause synthesis
        state = graph.execute_step(state)
        
        INVESTIGATIONS[investigation_id] = state
        
        return {
            "investigation_id": investigation_id,
            "status": "success",
            "state": state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed during graph execution: {str(e)}")

@app.get("/api/status/{investigation_id}")
async def get_investigation_status(investigation_id: str):
    """
    Returns the current execution state of an investigation.
    """
    if investigation_id not in INVESTIGATIONS:
        raise HTTPException(status_code=404, detail="Investigation ID not found.")
    
    return INVESTIGATIONS[investigation_id]

@app.post("/api/approve/{investigation_id}")
async def approve_investigation(investigation_id: str, approval: ApprovalRequest):
    """
    Approves or rejects the RCA findings.
    If approved, generates a Markdown report file.
    """
    if investigation_id not in INVESTIGATIONS:
        raise HTTPException(status_code=404, detail="Investigation ID not found.")
    
    state = INVESTIGATIONS[investigation_id]
    
    if approval.approved:
        state["approval_status"] = "approved"
        state["current_step"] = "ReportGenerated"
        state["logs_trace"].append("Human approved the RCA. Generating report...")
        
        # Write report to reports/
        os.makedirs("reports", exist_ok=True)
        report_markdown = graph.generate_report(state)
        report_path = f"reports/RCA_{investigation_id}.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)
            
        state["logs_trace"].append(f"Report written to disk: {report_path}")
    else:
        state["approval_status"] = "rejected"
        state["current_step"] = "AwaitingMoreInfo"
        state["human_feedback"] = approval.feedback
        state["logs_trace"].append(f"Human rejected the RCA. Feedback: {approval.feedback}")
        
    INVESTIGATIONS[investigation_id] = state
    return {
        "status": "updated",
        "state": state
    }

@app.get("/api/reports/{investigation_id}")
async def get_report(investigation_id: str):
    """
    Retrieves the final markdown report file content.
    """
    if investigation_id not in INVESTIGATIONS:
        raise HTTPException(status_code=404, detail="Investigation ID not found.")
    
    state = INVESTIGATIONS[investigation_id]
    if state["approval_status"] != "approved":
        raise HTTPException(status_code=400, detail="Report has not been approved or generated.")
        
    report_path = f"reports/RCA_{investigation_id}.md"
    if not os.path.exists(report_path):
        raise HTTPException(status_code=500, detail="Report file was not found on disk.")
        
    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()
        
    return {"report_markdown": report_content}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
