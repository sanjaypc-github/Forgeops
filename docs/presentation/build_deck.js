/* EOPS conference deck — 8-minute assertion-evidence talk + backup slides. */
const pptxgen = require("pptxgenjs");

const THEME = {
  name: "EOPS Incident Investigation",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0B1F2A", lt1: "FFFFFF", dk2: "0F3D56", lt2: "EEF3F6",
    accent1: "0F3D56", accent2: "1C7293", accent3: "E08A1E",
    accent4: "2E7D5B", accent5: "B3261E", accent6: "5A6B75",
    hlink: "1C7293", folHlink: "5A6B75",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Sanjay P C";
pres.title = "EOPS: A Multi-Agent AI Engineering Operations Platform";
const C = pres.SchemeColor;

const FOOTER = "EOPS — Multi-Agent Incident Investigation · ICSIE 2026";

/* ---------- layouts ---------- */
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: THEME.colors.dk1 },
  objects: [
    { placeholder: {
      options: { name: "title", type: "title", x: 0.9, y: 1.7, w: 11.6, h: 1.9,
        fontSize: 38, bold: true, color: C.background1, valign: "bottom", align: "left" }, text: "" } },
    { placeholder: {
      options: { name: "body", type: "body", x: 0.9, y: 3.95, w: 11.6, h: 2.4,
        fontSize: 16, color: "C5D4DD", valign: "top" }, text: "" } },
  ],
});

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: THEME.colors.lt1 },
  objects: [
    { placeholder: {
      options: { name: "title", type: "title", x: 0.6, y: 0.42, w: 12.1, h: 0.95,
        fontSize: 26, bold: true, color: C.accent1, valign: "top", align: "left" }, text: "" } },
    { text: { text: FOOTER, options: { x: 0.6, y: 6.95, w: 9.5, h: 0.3, fontSize: 10,
      color: THEME.colors.accent6, isTextBox: true, margin: 0 } } },
  ],
  slideNumber: { x: 12.5, y: 6.95, fontSize: 10, color: THEME.colors.accent6 },
});

pres.defineSlideMaster({
  title: "CLOSING_DARK",
  background: { color: THEME.colors.dk1 },
  objects: [
    { placeholder: {
      options: { name: "title", type: "title", x: 0.9, y: 0.6, w: 11.5, h: 1.4,
        fontSize: 29, bold: true, color: C.background1, valign: "top", align: "left" }, text: "" } },
  ],
});

/* ---------- helpers ---------- */
const card = (slide, { x, y, w, h, fill = THEME.colors.lt2, name }) =>
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08, fill: { color: fill },
    line: { color: "DCE5EA", width: 0.75 }, objectName: name,
  });

const dot = (slide, { x, y, d = 0.42, color = THEME.colors.accent2, label, name }) => {
  slide.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color }, objectName: name });
  slide.addText(label, { x, y, w: d, h: d, align: "center", valign: "middle",
    fontSize: 13, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
};

/* ================= 1. TITLE ================= */
pres.addSection({ title: "Opening" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
s.addText("EOPS: A Multi-Agent AI Engineering Operations Platform for Automated Incident Investigation and Root Cause Analysis",
  { placeholder: "title", fontSize: 30 });
s.addText([
  { text: "Ms D. Hemamalini · Sanjay P C · Sam Benadick J · Praveenkumar S · Nibuna A", options: { fontSize: 15, breakLine: true, color: "FFFFFF" } },
  { text: "Department of Artificial Intelligence & Data Science, Sri Eshwar College of Engineering, Coimbatore", options: { fontSize: 13, breakLine: true } },
  { text: " ", options: { fontSize: 8, breakLine: true } },
  { text: "ICSIE 2026 · Paper presentation (8 min)", options: { fontSize: 13, color: THEME.colors.accent3, bold: true } },
], { placeholder: "body" });
s.addNotes("Good morning. I am Sanjay. I will present EOPS, a multi-agent platform for incident investigation. The paper contributes the architecture; the system is implemented and our evaluation protocol is defined.");

/* ================= 2. PROBLEM ================= */
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Opening" });
s.addText("Finding the cause takes far longer than fixing it", { placeholder: "title" });

card(s, { x: 0.6, y: 1.5, w: 4.3, h: 2.95, fill: THEME.colors.dk2, name: "statCard" });
s.addText("52.5 h", { x: 0.6, y: 1.95, w: 4.3, h: 1.1, align: "center", fontSize: 54, bold: true,
  color: "FFFFFF", margin: 0, isTextBox: true });
s.addText("median time to mitigate a production incident\n(one year of incidents, Microsoft, 2025)",
  { x: 0.85, y: 3.15, w: 3.8, h: 1.0, align: "center", fontSize: 12, color: "C5D4DD", margin: 0, isTextBox: true });

s.addText("A single investigation spans six disconnected systems",
  { x: 5.3, y: 1.5, w: 7.4, h: 0.35, fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });

const sources = [
  ["Source code", "which commit changed what"],
  ["Deploy & hosting", "what shipped, when, did it fail"],
  ["Database", "schema, slow queries, advisors"],
  ["Logs & errors", "what the system reported"],
  ["Runbooks & docs", "what the team already knows"],
  ["Chat history", "what a colleague saw last week"],
];
sources.forEach(([head, sub], i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = 5.3 + col * 3.75, y = 2.05 + row * 0.85;
  dot(s, { x, y: y + 0.04, d: 0.3, label: String(i + 1), name: `src${i}` });
  s.addText([{ text: head + "  ", options: { bold: true, color: C.text1 } },
             { text: sub, options: { color: THEME.colors.accent6 } }],
    { x: x + 0.42, y, w: 3.2, h: 0.42, fontSize: 11.5, margin: 0, isTextBox: true, valign: "middle" });
});

card(s, { x: 0.6, y: 4.75, w: 12.1, h: 1.6, fill: "FBF1E0", name: "painCard" });
s.addText([
  { text: "The cost is not the fix. ", options: { bold: true, color: C.text1 } },
  { text: "Engineers switch tools, hold partial evidence in their heads, and depend on whoever remembers the system best. Diagnostic quality varies with who is on call.",
    options: { color: C.text1 } },
], { x: 0.95, y: 4.95, w: 11.4, h: 1.2, fontSize: 15, margin: 0, isTextBox: true, valign: "middle" });
s.addNotes("Open with this number: 52.5 hours median time to mitigate, from a year of Microsoft production incidents. Most of that is not fixing — it is finding. The engineer opens six tabs and correlates by hand.");

/* ================= 3. GAP ================= */
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Opening" });
s.addText("Existing AI helps with one source at a time, not with the investigation", { placeholder: "title" });

const prior = [
  { h: "Code agents", e: "SWE-agent, SWE-bench", d: "Edit repositories and resolve issues", gap: "No live system, no incident context" },
  { h: "One-shot LLM RCA", e: "Ahmed ICSE'23 · RCACopilot EuroSys'24", d: "Predict a root-cause category from collected telemetry", gap: "Provider-side; a handler per alert type" },
  { h: "Chat assistants", e: "General copilots", d: "Answer questions about systems", gap: "Hold no tools, gather no evidence" },
];
prior.forEach((p, i) => {
  const x = 0.6 + i * 4.07;
  card(s, { x, y: 1.5, w: 3.8, h: 3.45, name: `prior${i}` });
  s.addText(p.h, { x: x + 0.25, y: 1.72, w: 3.3, h: 0.35, fontSize: 16, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText(p.e, { x: x + 0.25, y: 2.08, w: 3.3, h: 0.3, fontSize: 10.5, italic: true, color: THEME.colors.accent6, margin: 0, isTextBox: true });
  s.addText(p.d, { x: x + 0.25, y: 2.48, w: 3.3, h: 0.75, fontSize: 12.5, color: C.text1, margin: 0, isTextBox: true });
  s.addText([{ text: "Gap: ", options: { bold: true, color: THEME.colors.accent5 } },
             { text: p.gap, options: { color: C.text1 } }],
    { x: x + 0.25, y: 3.4, w: 3.3, h: 0.95, fontSize: 12, margin: 0, isTextBox: true });
});

card(s, { x: 0.6, y: 5.25, w: 12.1, h: 1.1, fill: THEME.colors.dk2, name: "gapCard" });
s.addText([
  { text: "Open problem:  ", options: { bold: true, color: THEME.colors.accent3 } },
  { text: "no system investigates a customer's own heterogeneous stack with several specialised agents working in parallel on one shared body of evidence.", options: { color: "FFFFFF" } },
], { x: 0.95, y: 5.4, w: 11.4, h: 0.8, fontSize: 15, margin: 0, isTextBox: true, valign: "middle" });
s.addNotes("Three buckets of prior work. Code agents fix code but never see the live system. One-shot RCA — Ahmed and RCACopilot — is provider-side, inside Microsoft's own telemetry, with a handler written per alert type. Chat assistants hold no tools. The gap is coordinated, multi-source, customer-side investigation.");

/* ================= 4. ARCHITECTURE ================= */
pres.addSection({ title: "Approach" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Approach" });
s.addText("A supervisor splits one incident across desks that work in parallel", { placeholder: "title" });

// incident input
card(s, { x: 0.6, y: 1.65, w: 2.15, h: 0.95, fill: THEME.colors.lt2, name: "incident" });
s.addText("Incident\ndescribed in chat", { x: 0.6, y: 1.65, w: 2.15, h: 0.95, align: "center", valign: "middle",
  fontSize: 12, bold: true, color: C.text1, margin: 0, isTextBox: true });

// supervisor
card(s, { x: 3.1, y: 1.65, w: 2.15, h: 0.95, fill: THEME.colors.accent1, name: "supervisor" });
s.addText("Supervisor\nplans the work", { x: 3.1, y: 1.65, w: 2.15, h: 0.95, align: "center", valign: "middle",
  fontSize: 12, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });

// desks
const desks = ["Code", "Frontend &\nHosting", "Backend &\nServices", "Database", "Observability", "Knowledge"];
desks.forEach((d, i) => {
  const x = 0.6 + i * 2.08;
  card(s, { x, y: 3.1, w: 1.9, h: 0.95, fill: "E3EDF2", name: `desk${i}` });
  s.addText(d, { x, y: 3.1, w: 1.9, h: 0.95, align: "center", valign: "middle", fontSize: 11.5,
    bold: true, color: THEME.colors.dk2, margin: 0, isTextBox: true });
});
s.addText("run concurrently · each holds only its own read tools · may ask another desk one precise question",
  { x: 0.6, y: 4.12, w: 12.1, h: 0.3, align: "center", fontSize: 11, italic: true,
    color: THEME.colors.accent6, margin: 0, isTextBox: true });

// shared state
card(s, { x: 0.6, y: 4.55, w: 12.1, h: 0.62, fill: "FBF1E0", name: "state" });
s.addText("Shared investigation state — every finding carries the tool call that produced it",
  { x: 0.6, y: 4.55, w: 12.1, h: 0.62, align: "center", valign: "middle", fontSize: 13,
    bold: true, color: C.text1, margin: 0, isTextBox: true });

// rca + human
card(s, { x: 2.3, y: 5.4, w: 4.1, h: 0.85, fill: THEME.colors.accent2, name: "rca" });
s.addText("RCA agent — root cause, failure point, confidence",
  { x: 2.3, y: 5.4, w: 4.1, h: 0.85, align: "center", valign: "middle", fontSize: 12, bold: true,
    color: "FFFFFF", margin: 0, isTextBox: true });
card(s, { x: 6.9, y: 5.4, w: 4.1, h: 0.85, fill: THEME.colors.accent4, name: "human" });
s.addText("Engineer approves before any write happens",
  { x: 6.9, y: 5.4, w: 4.1, h: 0.85, align: "center", valign: "middle", fontSize: 12, bold: true,
    color: "FFFFFF", margin: 0, isTextBox: true });

[[2.75, 2.12, 3.1, 2.12], [4.18, 2.6, 4.18, 3.1], [6.35, 5.82, 6.9, 5.82]].forEach(([x1, y1, x2, y2], i) => {
  s.addShape(pres.ShapeType.line, { x: x1, y: y1, w: x2 - x1, h: y2 - y1,
    line: { color: THEME.colors.accent6, width: 1.5, endArrowType: "triangle" }, objectName: `arrow${i}` });
});
s.addNotes("One agent per system area, not one agent per task. The supervisor may only assign desks that actually have a connected tool. Desks run concurrently and write into one shared state. The RCA agent reads only that evidence. Nothing is written to the customer's systems without approval.");

/* ================= 5. HARNESS ================= */
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Approach" });
s.addText("The harness, not the model, is what makes the answers trustworthy", { placeholder: "title" });

const mech = [
  { n: "1", t: "Evidence or silence", d: "A finding is rejected by the harness unless it cites a tool call that really succeeded. The RCA may cite only evidence that exists." },
  { n: "2", t: "Read-only by construction", d: "Investigating desks hold read tools only. A write tool needs an opted-in connection, the Action desk, and human approval." },
  { n: "3", t: "Bounded budgets", d: "8 tool calls and 300 s per desk, 30 min per run. On exhaustion the desk is forced to report what it has, never to hang." },
  { n: "4", t: "Calibrated by code", d: "Confidence is capped outside the model: no evidence ≤ 0.2, a single source type ≤ 0.6, any contradiction −0.1." },
];
mech.forEach((m, i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = 0.6 + col * 6.2, y = 1.5 + row * 2.25;
  card(s, { x, y, w: 5.9, h: 2.05, name: `mech${i}` });
  dot(s, { x: x + 0.3, y: y + 0.28, d: 0.42, label: m.n, color: THEME.colors.accent1, name: `mechDot${i}` });
  s.addText(m.t, { x: x + 0.88, y: y + 0.25, w: 4.7, h: 0.4, fontSize: 15.5, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText(m.d, { x: x + 0.88, y: y + 0.68, w: 4.8, h: 1.0, fontSize: 12.5, color: C.text1, margin: 0, isTextBox: true });
});
s.addText("Roy et al. (FSE 2024) measured hallucination at 49% for retrieval baselines and 6% for a tool-grounded agent — EOPS makes that grounding structural, not hopeful.",
  { x: 0.6, y: 6.15, w: 12.1, h: 0.55, fontSize: 13, italic: true, color: THEME.colors.dk2, margin: 0, isTextBox: true });
s.addNotes("This is the contribution I most want you to remember. Four mechanisms. The literature says tool grounding cuts hallucination from about half to under one in ten; we enforce it in the harness rather than hoping the model behaves.");

/* ================= 6. MEMORY LAYER ================= */
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Approach" });
s.addText("Team documentation becomes evidence the agents can cite", { placeholder: "title" });

const steps = [
  ["Markdown runbooks", "architecture notes, postmortems, guides"],
  ["Chunk & embed", "offline preprocessing into Chroma"],
  ["Hybrid retrieval", "dense vectors + BM25, fused by RRF"],
  ["Cited evidence", "treated like any other tool result"],
];
steps.forEach(([h, d], i) => {
  const x = 0.6 + i * 3.14;
  card(s, { x, y: 1.6, w: 2.85, h: 2.2, name: `mem${i}` });
  dot(s, { x: x + 0.25, y: 1.85, d: 0.4, label: String(i + 1), color: THEME.colors.accent2, name: `memDot${i}` });
  s.addText(h, { x: x + 0.25, y: 2.4, w: 2.4, h: 0.4, fontSize: 14, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText(d, { x: x + 0.25, y: 2.82, w: 2.4, h: 0.9, fontSize: 11.5, color: THEME.colors.accent6, margin: 0, isTextBox: true });
  if (i < 3) s.addShape(pres.ShapeType.line, { x: x + 2.9, y: 2.6, w: 0.2, h: 0,
    line: { color: THEME.colors.accent6, width: 1.5, endArrowType: "triangle" }, objectName: `memArrow${i}` });
});

card(s, { x: 0.6, y: 4.1, w: 12.1, h: 2.2, fill: THEME.colors.lt2, name: "memWhy" });
s.addText("Why it matters", { x: 0.95, y: 4.32, w: 5, h: 0.35, fontSize: 15, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText([
  { text: "Most operational knowledge is not in the code — it is in runbooks and past postmortems.", options: { breakLine: true, bullet: true } },
  { text: "Retrieval keeps the answer grounded in the team's own words, without fine-tuning a model.", options: { breakLine: true, bullet: true } },
  { text: "A knowledge finding cites its document, so a reviewer can check the claim in seconds.", options: { bullet: true } },
], { x: 0.95, y: 4.78, w: 11.4, h: 1.4, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, paraSpaceAfter: 4 });
s.addNotes("The Engineering Memory Layer. Markdown documentation is chunked, embedded into Chroma, and retrieved with a hybrid of dense vectors and BM25 fused by reciprocal rank fusion. The knowledge desk cites documents exactly like any other tool.");

/* ================= 7. IMPLEMENTATION ================= */
pres.addSection({ title: "Evidence" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("The architecture is not a sketch — it runs", { placeholder: "title" });

const stats = [["9", "agent roles"], ["3", "live connectors"], ["229", "automated tests"], ["~7.7 min", "pilot run, end to end"]];
stats.forEach(([big, lab], i) => {
  const x = 0.6 + i * 3.14;
  card(s, { x, y: 1.5, w: 2.85, h: 1.75, fill: THEME.colors.dk2, name: `stat${i}` });
  s.addText(big, { x, y: 1.68, w: 2.85, h: 0.75, align: "center", fontSize: 34, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addText(lab, { x, y: 2.58, w: 2.85, h: 0.45, align: "center", fontSize: 12, color: "C5D4DD", margin: 0, isTextBox: true });
});

card(s, { x: 0.6, y: 3.55, w: 5.9, h: 2.75, name: "built" });
s.addText("Built and working", { x: 0.95, y: 3.78, w: 5.2, h: 0.35, fontSize: 15, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText([
  { text: "FastAPI + LangGraph orchestration, durable checkpoints", options: { breakLine: true, bullet: true } },
  { text: "Connector catalog over MCP: GitHub, Supabase, knowledge vault", options: { breakLine: true, bullet: true } },
  { text: "Live War Room: agents, evidence wall, approval in chat", options: { breakLine: true, bullet: true } },
  { text: "Per-agent token accounting built into every run", options: { bullet: true } },
], { x: 0.95, y: 4.22, w: 5.3, h: 1.95, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, paraSpaceAfter: 5 });

card(s, { x: 6.8, y: 3.55, w: 5.9, h: 2.75, fill: "FBF1E0", name: "honest" });
s.addText("Stated honestly", { x: 7.15, y: 3.78, w: 5.2, h: 0.35, fontSize: 15, bold: true, color: THEME.colors.accent5, margin: 0, isTextBox: true });
s.addText([
  { text: "The pilot run is an engineering observation, not an evaluation result", options: { breakLine: true, bullet: true } },
  { text: "No large-scale empirical study yet — that is the next phase", options: { breakLine: true, bullet: true } },
  { text: "Measured on our own deployment, one stack, one team", options: { bullet: true } },
], { x: 7.15, y: 4.22, w: 5.3, h: 1.95, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, paraSpaceAfter: 5 });
s.addNotes("The system exists. Nine agent roles, three connectors live, 229 automated tests, and a pilot investigation that ran end to end in about seven and a half minutes. I am careful here: that is an engineering observation, not an evaluation result.");

/* ================= 8. EVALUATION ================= */
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("Evaluation measures four things against published baselines", { placeholder: "title" });

const rows = [
  [{ text: "What we measure", options: { bold: true } }, { text: "Metric", options: { bold: true } }, { text: "Compared against", options: { bold: true } }],
  ["Correctness", "Root-cause accuracy @1 / @3; failure-point localisation", "Single agent, same tools; one-shot prompt"],
  ["Honesty", "Unsupported-claim rate; citation validity", "Roy et al. FSE'24: 6% vs 18% vs 49%"],
  ["Cost", "Tokens and USD per investigation, per desk", "Same architecture without compaction"],
  ["Time", "Wall-clock to root cause; human time to decision", "Manual investigation of the same fault"],
];
s.addTable(rows, {
  x: 0.6, y: 1.5, w: 12.1, colW: [2.3, 5.1, 4.7], rowH: 0.5,
  fontSize: 12, color: THEME.colors.dk1, fontFace: "Calibri",
  border: { type: "solid", color: "DCE5EA", pt: 0.75 },
  fill: { color: "FFFFFF" },
  valign: "middle", margin: 0.08,
});

card(s, { x: 0.6, y: 4.45, w: 12.1, h: 1.95, fill: THEME.colors.lt2, name: "benchCard" });
s.addText("Three settings, strongest last", { x: 0.95, y: 4.65, w: 6, h: 0.35, fontSize: 15, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText([
  { text: "Public benchmarks — OpenRCA (ICLR'25, 335 failures) and AIOpsLab (MLSys'25) fault scenarios", options: { breakLine: true, bullet: true } },
  { text: "Controlled fault injection — 20–30 known faults on a live stack, all four metric families", options: { breakLine: true, bullet: true } },
  { text: "Human study — engineers diagnosing with and without EOPS, time to correct diagnosis", options: { bullet: true } },
], { x: 0.95, y: 5.08, w: 11.4, h: 1.25, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, paraSpaceAfter: 4 });
s.addNotes("Four metric families. Note the second one: unsupported-claim rate is directly comparable with Roy's published numbers. And ablations — multi-agent versus single agent, with and without retrieval, with and without citation enforcement — isolate the architecture rather than the model.");

/* ================= 9. EFFICIENCY ================= */
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("We claim bounded context and parallel time — not fewer total tokens", { placeholder: "title" });

s.addChart(pres.ChartType.bar, [{
  name: "Input characters resent per desk",
  labels: ["Without compaction", "With compaction"],
  values: [288000, 175500],
}], {
  x: 0.6, y: 1.5, w: 6.1, h: 4.2,
  barDir: "col", chartColors: [THEME.colors.accent6, THEME.colors.accent2],
  showTitle: true, title: "One desk, eight tool calls", titleFontSize: 13,
  titleColor: THEME.colors.dk1, titleFontFace: "+mn-lt",
  showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 12,
  dataLabelColor: THEME.colors.dk1, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "#,##0",
  showLegend: false, catAxisLabelColor: THEME.colors.dk1, catAxisLabelFontSize: 12,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelColor: THEME.colors.accent6,
  valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt",
  valGridLine: { color: "E6ECEF", size: 0.75 }, catGridLine: { style: "none" },
  valAxisMaxVal: 320000, valAxisMinVal: 0, valAxisMajorUnit: 80000,
});

const effects = [
  ["39% less input resent", "older tool output collapses to its opening, keeping its citation id"],
  ["Context never grows with the run", "each desk sees only its own tools; the RCA agent reads one-line evidence"],
  ["Wall-clock follows the slowest desk", "not the sum of all of them — a single prompt cannot parallelise"],
];
effects.forEach(([h, d], i) => {
  const y = 1.85 + i * 1.35;
  s.addText(h, { x: 7.05, y, w: 5.6, h: 0.35, fontSize: 15, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText(d, { x: 7.05, y: y + 0.36, w: 5.6, h: 0.6, fontSize: 12.5, color: C.text1, margin: 0, isTextBox: true });
});
s.addText("Honest framing: a multi-agent system spends more total tokens than one prompt. The gain is bounded context per step, parallel wall-clock, and hours of human time.",
  { x: 0.6, y: 6.0, w: 12.1, h: 0.6, fontSize: 13, italic: true, color: THEME.colors.dk2, margin: 0, isTextBox: true });
s.addNotes("Be precise here. We do not claim fewer total tokens than one giant prompt — that would be false. We claim a 39 percent reduction against the same architecture without compaction, bounded context per step, and parallel wall-clock.");

/* ================= 10. CLOSING ================= */
pres.addSection({ title: "Closing" });
s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Closing" });
s.addText("Investigation becomes coordinated and cited; the engineer still decides", { placeholder: "title" });

const takeaways = [
  ["Contribution", "A supervisor-driven, customer-side multi-agent architecture with a shared, citation-enforced investigation state"],
  ["Why it is credible", "Published agents resolve only 11–15% of real scenarios autonomously — decision support is the right target today"],
  ["Next", "Measurement on OpenRCA and injected faults, graph-augmented retrieval, learning from accepted vs rejected recommendations"],
];
takeaways.forEach(([h, d], i) => {
  const y = 2.35 + i * 1.12;
  dot(s, { x: 0.9, y: y + 0.05, d: 0.4, label: String(i + 1), color: THEME.colors.accent3, name: `take${i}` });
  s.addText(h, { x: 1.5, y, w: 3.0, h: 0.42, fontSize: 16, bold: true, color: THEME.colors.accent3, margin: 0, isTextBox: true });
  s.addText(d, { x: 4.3, y: y - 0.02, w: 8.2, h: 0.9, fontSize: 14, color: "FFFFFF", margin: 0, isTextBox: true });
});
s.addText("Thank you — questions welcome", { x: 0.9, y: 6.1, w: 11.5, h: 0.5, fontSize: 17, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
s.addNotes("Close with the one-sentence takeaway, then invite questions. If you overran, skip straight to this slide.");

/* ================= BACKUP ================= */
pres.addSection({ title: "Backup" });

// B1 — novelty table
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Backup" });
s.addText("Backup — how EOPS differs from prior systems", { placeholder: "title" });
const EO = { color: "FFFFFF", fill: { color: "0F3D56" }, bold: true };
const b1 = [
  [{ text: "Capability", options: { bold: true } }, { text: "Ahmed'23", options: { bold: true } },
   { text: "RCACopilot", options: { bold: true } }, { text: "Roy'24 agent", options: { bold: true } },
   { text: "RCAgent", options: { bold: true } }, { text: "SWE-agent", options: { bold: true } },
   { text: "EOPS", options: EO }],
  ["Multi-source investigation", "no", "via handlers", "partial", "yes", "no", { text: "yes", options: EO }],
  ["Parallel specialised agents", "no", "no", "no", "no", "no", { text: "yes", options: EO }],
  ["Agent-to-agent questions", "no", "no", "no", "no", "no", { text: "yes", options: EO }],
  ["Customer-side, any stack", "no", "no", "no", "no", "no", { text: "yes", options: EO }],
  ["Enforced evidence citation", "no", "no", "partial", "partial", "no", { text: "yes", options: EO }],
  ["Writes need approval", "n/a", "n/a", "n/a", "partial", "no", { text: "yes", options: EO }],
  ["Token accounting per agent", "no", "no", "no", "no", "no", { text: "yes", options: EO }],
];
s.addTable(b1, {
  x: 0.6, y: 1.5, w: 12.1, colW: [3.1, 1.4, 1.6, 1.6, 1.4, 1.5, 1.5], rowH: 0.52,
  fontSize: 11.5, color: THEME.colors.dk1, fontFace: "Calibri", valign: "middle", margin: 0.06,
  border: { type: "solid", color: "DCE5EA", pt: 0.75 },
});
s.addText("Every prior system is provider-side, built inside one company's own telemetry. EOPS is customer-side and tool-agnostic.",
  { x: 0.6, y: 5.85, w: 12.1, h: 0.5, fontSize: 13, italic: true, color: THEME.colors.dk2, margin: 0, isTextBox: true });
s.addNotes("Use this if asked what is new. The honest single answer: every prior system is provider-side; EOPS is customer-side and tool-agnostic with enforced citation.");

// B2 — numbers
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Backup" });
s.addText("Backup — the numbers from the literature", { placeholder: "title" });
const nums = [
  ["52.5 h", "median time to mitigate", "one year of Microsoft production incidents"],
  ["0.766", "RCACopilot Micro-F1", "root-cause category prediction, EuroSys 2024"],
  ["6% vs 49%", "hallucination, agent vs retrieval", "Roy et al., FSE 2024 industry track"],
  ["11.34%", "best score on OpenRCA", "335 real failures, ICLR 2025"],
];
nums.forEach(([big, lab, src], i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = 0.6 + col * 6.2, y = 1.55 + row * 2.45;
  card(s, { x, y, w: 5.9, h: 2.2, name: `num${i}` });
  s.addText(big, { x: x + 0.3, y: y + 0.2, w: 5.3, h: 0.7, fontSize: 32, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText(lab, { x: x + 0.3, y: y + 0.95, w: 5.3, h: 0.35, fontSize: 14, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(src, { x: x + 0.3, y: y + 1.3, w: 5.3, h: 0.45, fontSize: 11.5, color: THEME.colors.accent6, margin: 0, isTextBox: true });
});
s.addNotes("Memorise these four. They show you know the field.");

// B3 — algorithms
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Backup" });
s.addText("Backup — the algorithmic components", { placeholder: "title" });
const algos = [
  ["Constrained planning", "The planner may assign only desks with connected tools; the plan is a typed object, validated, one repair attempt, then it fails loudly"],
  ["Budgeted ReAct per desk", "Think → read tool → observe, bounded by 8 calls and a time budget; on exhaustion the harness forces a report"],
  ["Fan-out / fan-in on shared state", "Map over desks, reduce into merged state channels, durable checkpoint so the run survives restart and the approval pause"],
  ["Bounded inter-agent questions", "Per-agent and global question budgets prevent the unbounded chat loops of free-form multi-agent frameworks"],
  ["Hybrid retrieval with RRF", "Dense embeddings and BM25 fused by reciprocal rank fusion for the Engineering Memory Layer"],
  ["Deterministic calibration", "Confidence capped in code: no evidence ≤ 0.2, single source ≤ 0.6, contradiction −0.1"],
];
algos.forEach(([h, d], i) => {
  const y = 1.5 + i * 0.9;
  dot(s, { x: 0.6, y: y + 0.08, d: 0.36, label: String(i + 1), color: THEME.colors.accent2, name: `alg${i}` });
  s.addText(h, { x: 1.12, y, w: 3.5, h: 0.4, fontSize: 13.5, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText(d, { x: 4.7, y, w: 8.0, h: 0.75, fontSize: 12, color: C.text1, margin: 0, isTextBox: true });
});
s.addNotes("If asked what algorithm: name these six. The novelty is a coordination and verification protocol, not a new learning algorithm.");

// B4 — safety
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Backup" });
s.addText("Backup — safety, injection and the approval gate", { placeholder: "title" });
const safety = [
  ["Tool output is data, never instruction", "Results are wrapped and treated as untrusted text; an injected instruction inside a log line is not followed"],
  ["Read-only investigation", "Even a successful injection cannot change the customer's systems — investigating desks hold no write tools"],
  ["Writes are opt-in and approved", "The one write in the MVP, creating an issue, needs an opted-in connection and an explicit human approval"],
  ["Secrets stay server-side", "Connector tokens are encrypted at rest and never returned to the browser or placed in a prompt"],
];
safety.forEach(([h, d], i) => {
  const y = 1.6 + i * 1.32;
  card(s, { x: 0.6, y, w: 12.1, h: 1.18, name: `safe${i}` });
  s.addText(h, { x: 1.0, y: y + 0.13, w: 4.6, h: 0.4, fontSize: 14, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText(d, { x: 5.7, y: y + 0.13, w: 6.7, h: 0.8, fontSize: 12.5, color: C.text1, margin: 0, isTextBox: true });
});
s.addNotes("Security question answer. Four layers, and the key point: read-only by construction means an injection has nothing to act on.");

// B5 — connectors
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Backup" });
s.addText("Backup — a new tool needs no new agent", { placeholder: "title" });
const routing = [
  [{ text: "Connector ability", options: { bold: true } }, { text: "Capability", options: { bold: true } }, { text: "Desk it reaches", options: { bold: true } }],
  ["github.list_commits, get_file_contents", "code", "Code"],
  ["github.actions_list, get_job_logs", "hosting", "Frontend & Hosting"],
  ["supabase.execute_sql, list_migrations", "database", "Database"],
  ["supabase.query_logs", "logs", "Observability"],
  ["supabase.list_edge_functions", "backend", "Backend & Services"],
  ["knowledge.search", "knowledge", "Knowledge"],
  ["github.create_issue", "write", "Action — only after approval"],
];
s.addTable(routing, {
  x: 0.6, y: 1.5, w: 12.1, colW: [5.6, 2.6, 3.9], rowH: 0.56,
  fontSize: 12.5, color: THEME.colors.dk1, fontFace: "Calibri", valign: "middle", margin: 0.08,
  border: { type: "solid", color: "DCE5EA", pt: 0.75 },
});
s.addText("Each connector is an MCP server. Its abilities are allowlisted and routed by capability, so adding Cloudflare, Sentry or Datadog adds no agent code.",
  { x: 0.6, y: 5.95, w: 12.1, h: 0.6, fontSize: 13, italic: true, color: THEME.colors.dk2, margin: 0, isTextBox: true });
s.addNotes("This answers both the scalability question and the novelty question: capability-to-desk routing is what makes the system tool-agnostic.");

/* ---------- write ---------- */
(async () => {
  await pres.writeFile({ fileName: "EOPS_ICSIE_presentation.pptx" });
  const { applyTheme } = require("./apply_theme.js");
  await applyTheme("EOPS_ICSIE_presentation.pptx", THEME);
  console.log("written");
})();
