import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router";
import { ApiError } from "../api/client";

async function fetchReport(id: string): Promise<string> {
  const response = await fetch(`/api/investigations/${id}/report`, { credentials: "include" });
  if (!response.ok) throw new ApiError(response.status, response.status === 404 ? "The report is not ready yet." : response.statusText);
  return response.text();
}

export function ReportPage() {
  const { id = "" } = useParams();
  const report = useQuery({ queryKey: ["report", id], queryFn: () => fetchReport(id), retry: false });
  return (
    <article className="report">
      <Link className="text-link" to={`/investigations/${id}`}><ArrowLeft size={15} aria-hidden /> Back to the War Room</Link>
      {report.isPending && <p className="muted">Loading the report…</p>}
      {report.isError && <p className="error">{report.error instanceof ApiError ? report.error.message : "Could not load the report."}</p>}
      {/* Markdown is rendered without raw HTML: report text can contain content from customers' systems. */}
      {report.data && <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.data}</ReactMarkdown>}
    </article>
  );
}
