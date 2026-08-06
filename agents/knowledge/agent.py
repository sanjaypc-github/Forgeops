from typing import Dict, Any
from memory.state import InvestigationState, KnowledgeFindings
from tools.rag.tool import KnowledgeTool

class KnowledgeAgent:
    """
    Knowledge Agent (RAG Agent)
    Fetches runbooks and architectural specifications relevant to the current incident details.
    """
    def __init__(self, tool: KnowledgeTool = None):
        self.tool = tool or KnowledgeTool()

    def run(self, state: InvestigationState) -> Dict[str, Any]:
        incident = state.get("incident_description", "")
        print(f"[Knowledge Agent] Performing vector store search for: '{incident}'")
        
        # Query docs based on incident description
        docs = self.tool.query_docs(incident, limit=3)
        
        # Parse docs into lists
        suggested_runbooks = []
        architecture_references = []
        
        for doc in docs:
            title = doc.get("title", "")
            source = doc.get("source", "")
            if "runbook" in source.lower() or "runbook" in title.lower():
                suggested_runbooks.append(title)
            else:
                architecture_references.append(title)
                
        knowledge_findings: KnowledgeFindings = {
            "retrieved_documents": docs,
            "suggested_runbooks": suggested_runbooks,
            "architecture_references": architecture_references,
            "error": None
        }

        logs = state.get("logs_trace", [])
        logs.append(f"Knowledge Agent retrieved {len(docs)} documents from vector store.")

        return {
            "knowledge": knowledge_findings,
            "logs_trace": logs
        }
