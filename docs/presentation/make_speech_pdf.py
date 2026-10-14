"""Speech script PDF — one page per speaker, printable separately."""

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

NAVY = colors.HexColor("#1F4E79")
DEEP = colors.HexColor("#143655")
INK = colors.HexColor("#1A1A1A")
GREY = colors.HexColor("#5A5A5A")
LIGHT = colors.HexColor("#F1F5F9")
LINE = colors.HexColor("#D3DDE6")
AMBER = colors.HexColor("#A85E00")

styles = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=DEEP,
                         spaceAfter=2),
    "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=10.5, leading=14, textColor=GREY,
                          spaceAfter=10),
    "speaker": ParagraphStyle("speaker", fontName="Helvetica-Bold", fontSize=19, leading=22,
                              textColor=DEEP, spaceAfter=1),
    "role": ParagraphStyle("role", fontName="Helvetica", fontSize=10.5, leading=14, textColor=AMBER,
                           spaceAfter=12),
    "slide": ParagraphStyle("slide", fontName="Helvetica-Bold", fontSize=12, leading=15,
                            textColor=NAVY, spaceBefore=10, spaceAfter=5),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=11, leading=16, textColor=INK,
                           alignment=TA_LEFT, spaceAfter=7),
    "hand": ParagraphStyle("hand", fontName="Helvetica-Bold", fontSize=11.5, leading=17,
                           textColor=DEEP, spaceBefore=4, spaceAfter=8),
    "note": ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=10, leading=14,
                           textColor=GREY, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=DEEP,
                         spaceBefore=12, spaceAfter=6),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=10, leading=13, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=INK),
    "run": ParagraphStyle("run", fontName="Helvetica-Bold", fontSize=9.5, leading=12,
                          textColor=colors.HexColor("#8A95A0"), spaceBefore=0, spaceAfter=0),
    "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=10, leading=13,
                            textColor=colors.white),
}

CUE = '<font color="#7A8793"><i>{}</i></font>  '


def P(text, style="body"):
    return Paragraph(text, styles[style])


def table(rows, widths, header=True):
    data = []
    for r, row in enumerate(rows):
        data.append([Paragraph(c, styles["cellh" if (header and r == 0) else
                                         ("cellb" if c.startswith("<b>") else "cell")]) for c in row])
    t = Table(data, colWidths=widths, hAlign="LEFT")
    style = [("GRID", (0, 0), (-1, -1), 0.6, LINE),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), DEEP)]
        for r in range(1, len(rows)):
            if r % 2 == 0:
                style.append(("BACKGROUND", (0, r), (-1, r), LIGHT))
    else:
        for r in range(len(rows)):
            if r % 2:
                style.append(("BACKGROUND", (0, r), (-1, r), LIGHT))
    t.setStyle(TableStyle(style))
    return t


def box(flowables, fill=LIGHT, border=LINE, width=170 * mm):
    t = Table([[flowables]], colWidths=[width], hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), fill),
                           ("BOX", (0, 0), (-1, -1), 0.6, border),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


story = []

# ───────────────── page 1: plan ─────────────────
story += [
    P("EOPS — Presentation Script for Four Speakers", "h1"),
    P("ICSIE 2026 · 8 minutes of presentation + 2 minutes of questions · two slides per speaker", "sub"),
    table([
        ["Speaker", "Slides", "Clock", "Their job in one line"],
        ["<b>Sanjay P C</b>", "1 Title<br/>2 Introduction", "0:00 – 2:00",
         "Open the talk and make the problem feel real"],
        ["<b>Sam Benadick J</b>", "3 Literature review<br/>4 Methodology", "2:00 – 4:20",
         "Show the gap in prior work, then our architecture"],
        ["<b>Praveenkumar S</b>", "5 Experimental analysis<br/>6 Results &amp; discussion", "4:20 – 6:40",
         "How we measure it, and what is measured so far"],
        ["<b>Nibuna A</b>", "7 Conclusion<br/>8 References", "6:40 – 8:00",
         "Land the contribution and invite questions"],
    ], [34 * mm, 38 * mm, 24 * mm, 74 * mm]),
    Spacer(1, 12),
    P("Rules for everyone", "h2"),
    box([
        P("•  Speak <b>slower than feels natural</b>. Pause wherever you see a grey cue.", "body"),
        P("•  Finish with your handover sentence — that is how the next speaker knows to start.", "body"),
        P("•  If the chair signals time, jump straight to the last paragraph of your part.", "body"),
        P("•  Do not read the slide aloud. The slide is the evidence; you are the explanation.", "body"),
        P("•  Four numbers you may state: <b>52.5 hours</b>, <b>0.766</b>, <b>6% versus 49%</b>, "
          "<b>11.34%</b>. Never guess any other number.", "body"),
    ]),
    Spacer(1, 10),
    P("The same script is saved inside the .pptx as speaker notes, so it appears in PowerPoint's "
      "Presenter View during the talk.", "note"),
    PageBreak(),
]

# ───────────────── speaker pages ─────────────────
speakers = [
    ("SANJAY P C", "Speaker 1 of 4  ·  slides 1 – 2  ·  0:00 – 2:00", [
        ("Slide 1 — Title  ·  0:00 – 0:45", [
            ("body", "Good morning, respected chairpersons and everyone present."),
            ("body", "I am Sanjay P C. With me are Sam Benadick, Praveenkumar and Nibuna — final year "
                     "students of Artificial Intelligence and Data Science at Sri Eshwar College of "
                     "Engineering. Our work is guided by Ms D. Hemamalini."),
            ("body", "Our paper is titled <b>“EOPS: A Multi-Agent AI Engineering Operations Platform "
                     "for Automated Incident Investigation and Root Cause Analysis”</b>."),
            ("body", "In the next eight minutes we will cover four things: the problem we are solving, "
                     "the existing work and the gap in it, our proposed architecture and how we will "
                     "evaluate it, and what we have already built. I will begin with the problem."),
        ]),
        ("Slide 2 — Introduction  ·  0:45 – 2:00", [
            ("body", "When a software product breaks in production, the hardest part is not fixing it. "
                     "The hardest part is <b>finding</b> what broke."),
            ("cue", "point to the dark box"),
            ("body", "A study of one full year of production incidents at Microsoft reported a median "
                     "time to mitigate of <b>fifty-two and a half hours</b>. Most of that time is spent "
                     "searching, not repairing."),
            ("body", "The reason is that evidence is scattered. A single investigation touches six "
                     "disconnected systems: the source code, the deployment history, the database, the "
                     "application logs, the team’s runbooks, and old chat messages. The engineer opens "
                     "all of them, holds partial clues in memory, and connects them by hand. It is slow, "
                     "and the quality of the answer depends on which engineer happens to be on call that "
                     "day."),
            ("body", "Today’s AI assistants do not solve this. They generate code, or they answer "
                     "questions. They do not run an investigation."),
            ("cue", "point to the Objective box"),
            ("body", "So our objective is a supervisor-driven multi-agent platform. Several specialised "
                     "agents investigate the team’s own tools in parallel and return a root cause "
                     "supported by evidence — with a human approving before anything is changed."),
            ("hand", "I will now hand over to Sam, who will present the related work."),
        ]),
    ]),
    ("SAM BENADICK J", "Speaker 2 of 4  ·  slides 3 – 4  ·  2:00 – 4:20", [
        ("Slide 3 — Literature review  ·  2:00 – 3:10", [
            ("body", "Thank you, Sanjay."),
            ("cue", "point to the top three rows"),
            ("body", "We studied the literature in two groups. The first group is the foundation. "
                     "Retrieval-Augmented Generation grounds a model’s answer in retrieved documents, but "
                     "it does not investigate anything. ReAct lets one agent reason and act using tools, "
                     "but on a single task. AutoGen coordinates several agents in conversation, but the "
                     "conversation is unbounded and nothing forces an agent to prove its claims."),
            ("cue", "point to the lower rows"),
            ("body", "The second group is our own domain. Ahmed and colleagues, at ICSE 2023, fine-tuned "
                     "a model to suggest a root cause from the incident title and summary — a single shot, "
                     "with no evidence gathering. RCACopilot, at EuroSys 2024, is the closest work to "
                     "ours: it collects diagnostics through handlers and predicts a root-cause category "
                     "with a <b>Micro-F1 of 0.766</b>. But it is provider-side, inside one company’s own "
                     "telemetry, and every alert type needs its own hand-written handler."),
            ("body", "The most useful finding for us came from Roy and colleagues at FSE 2024. A "
                     "tool-using agent was not much more accurate than the baselines — but its "
                     "hallucination rate was <b>six percent, against forty-nine percent</b> for "
                     "retrieval-based methods. Grounding, not model size, is what buys trust."),
            ("cue", "point to the gap bar"),
            ("body", "So the gap is clear. No system coordinates several specialised agents over a "
                     "customer’s own tools, sharing one investigation state in which every finding must "
                     "cite the tool call that produced it."),
        ]),
        ("Slide 4 — Methodology  ·  3:10 – 4:20", [
            ("body", "This is our proposed architecture."),
            ("cue", "point to the top row"),
            ("body", "The engineer describes the problem in a chat bar. A <b>Supervisor</b> agent reads it "
                     "and plans the investigation. Importantly, the Supervisor may assign work only to "
                     "desks that actually have a connected tool — it cannot invent an investigation it has "
                     "no means to perform."),
            ("cue", "point to the six boxes"),
            ("body", "We then have one agent per system area — code, frontend and hosting, backend "
                     "services, database, observability and knowledge. We call them desks. They run "
                     "concurrently, each holding read-only tools for its own area, and a desk may ask one "
                     "colleague a precise question when it needs information outside its area."),
            ("cue", "point to the shared state bar"),
            ("body", "Every desk writes into one shared investigation state, and every finding carries the "
                     "identifier of the tool call that produced it. This is the core of our design: a "
                     "claim without evidence is rejected by the system itself."),
            ("cue", "point to the bottom row"),
            ("body", "The RCA agent then reads only that collected evidence and produces the root cause, "
                     "the exact failure point and a confidence value. Finally, the engineer approves "
                     "before anything is written back to the company’s systems."),
            ("cue", "point to the five numbered phases"),
            ("body", "These are the five phases of the methodology. Each desk runs a budgeted "
                     "reason-and-act loop — at most eight tool calls and three hundred seconds — and when a "
                     "budget is reached the system forces the desk to report what it has, so an "
                     "investigation can never hang."),
            ("hand", "Praveenkumar will now explain how we evaluate this."),
        ]),
    ]),
    ("PRAVEENKUMAR S", "Speaker 3 of 4  ·  slides 5 – 6  ·  4:20 – 6:40", [
        ("Slide 5 — Experimental analysis  ·  4:20 – 5:25", [
            ("body", "Thank you, Sam. Our evaluation is designed as four experiments."),
            ("cue", "point to each card in turn"),
            ("body", "<b>Experiment one</b> tests orchestration: does the Supervisor coordinate the desks "
                     "correctly and keep one consistent state? We measure orchestration latency, state "
                     "consistency and the agent completion rate."),
            ("body", "<b>Experiment two</b> tests the Engineering Memory Layer, our retrieval component. "
                     "We measure Mean Reciprocal Rank, Recall at K, Precision at K and response latency, "
                     "using real runbooks and postmortems."),
            ("body", "<b>Experiment three</b> tests reasoning quality. Human evaluators compare our "
                     "generated reports against expert analyses of the same incident, judging evidence "
                     "use, completeness, explanation quality and confidence calibration."),
            ("body", "<b>Experiment four</b> tests the complete workflow on injected faults — API latency, "
                     "a slow query, a failed deployment, broken content — measuring time to root cause, "
                     "evidence completeness, usability, and what we call the unsupported-claim rate."),
            ("cue", "point to the dark bar"),
            ("body", "We compare against three baselines: a single agent with the same tools, a one-shot "
                     "prompt containing all the context, and our own architecture without compaction. We "
                     "use the public <b>OpenRCA</b> benchmark with its three hundred and thirty-five real "
                     "failures, <b>AIOpsLab</b> fault scenarios, and faults we inject into a live stack. "
                     "The ablations isolate the architecture itself, rather than the model behind it."),
        ]),
        ("Slide 6 — Results and discussion  ·  5:25 – 6:40", [
            ("body", "I will be precise about what we have measured and what we have not."),
            ("cue", "point to the chart"),
            ("body", "This is a measurement from our implementation. For one desk making eight tool calls, "
                     "the earlier design resent two hundred and eighty-eight thousand characters of "
                     "context across the task. With our compaction mechanism — where older tool results "
                     "collapse to their opening but keep their citation identifier — it is one hundred and "
                     "seventy-five thousand. About <b>thirty-nine percent less input</b>, with no loss of "
                     "traceability."),
            ("cue", "point to the three cards"),
            ("body", "Second, context never grows with the length of the investigation, because each desk "
                     "sees only its own tools and the RCA agent reads one-line evidence rather than raw "
                     "logs. Third, because the desks run in parallel, total time follows the slowest desk, "
                     "not the sum of all of them."),
            ("cue", "point to the grey bar"),
            ("body", "On implementation: nine agent roles, three live connectors, two hundred and twenty-"
                     "nine automated tests, and a pilot investigation that ran end to end in about seven "
                     "point seven minutes."),
            ("cue", "point to the red line"),
            ("body", "I want to state the limitation honestly. This is a position paper with a working "
                     "prototype. That pilot timing is an engineering observation, <b>not</b> an evaluation "
                     "result. The large-scale empirical study is our next phase, and its protocol is the "
                     "one on the previous slide."),
            ("hand", "Nibuna will present the conclusion."),
        ]),
    ]),
    ("NIBUNA A", "Speaker 4 of 4  ·  slides 7 – 8  ·  6:40 – 8:00", [
        ("Slide 7 — Conclusion  ·  6:40 – 7:40", [
            ("body", "Thank you, Praveenkumar. Four conclusions."),
            ("body", "<b>First</b>, our contribution is a coordination protocol, not a bigger model. A "
                     "supervisor plans, specialised desks investigate the team’s own tools in parallel, "
                     "and one shared state carries every finding together with its citation."),
            ("body", "<b>Second</b>, trust comes from the harness, not from the model. Uncited findings "
                     "are rejected. Investigating desks are read-only by construction. Every loop is "
                     "bounded by a budget. And confidence is capped by code — for example, a conclusion "
                     "supported by only one kind of source can never be reported above zero point six, no "
                     "matter how certain the model sounds."),
            ("body", "<b>Third</b>, decision support is the right target today. Published results show "
                     "that even the best agents resolve only eleven to fifteen percent of real scenarios "
                     "on their own. A system that acts on that would be dangerous. A system that "
                     "investigates and hands the engineer cited evidence is useful right now."),
            ("body", "<b>Fourth</b>, our future work: measurement on OpenRCA and on injected faults, "
                     "graph-augmented retrieval across code, services and documents, and learning from "
                     "which recommendations engineers accept and which they reject."),
        ]),
        ("Slide 8 — References and thanks  ·  7:40 – 8:00", [
            ("body", "These are our references. Works eight to twelve position EOPS against the current "
                     "state of the art in LLM-based root cause analysis."),
            ("body", "On behalf of our team and our guide Ms D. Hemamalini, thank you for your time and "
                     "attention."),
            ("hand", "We would be happy to take your questions."),
        ]),
    ]),
]

for name, role, blocks in speakers:
    story.append(P(name, "speaker"))
    story.append(P(role, "role"))
    for n, (heading, lines) in enumerate(blocks):
        if n:  # keep a slide's script whole: move it over rather than split it
            story.append(CondPageBreak(110 * mm))
            story.append(P(name + "  ·  continued", "run"))
        story.append(P(heading, "slide"))
        for kind, text in lines:
            story.append(P(CUE.format("[ " + text + " ]"), "note") if kind == "cue"
                         else P(text, kind))
    story.append(PageBreak())

# ───────────────── last page: Q&A ─────────────────
story += [
    P("Question time — who answers what", "h1"),
    P("Two minutes. Only one person answers each question; the others stay quiet unless invited.", "sub"),
    table([
        ["Question is about…", "Answers", "Opening words"],
        ["The problem, motivation, who the users are", "<b>Sanjay</b>",
         "“The teams we are targeting are …”"],
        ["Related work, “have you seen X?”, novelty, architecture", "<b>Sam</b>",
         "“Yes — the closest work is …”"],
        ["Evaluation, metrics, baselines, datasets, cost, latency", "<b>Praveen</b>",
         "“We measure that as …”"],
        ["Contribution, limitations, future work, human approval", "<b>Nibuna</b>",
         "“Our contribution there is …”"],
    ], [66 * mm, 26 * mm, 78 * mm]),
    Spacer(1, 14),
    P("Three sentences that save you", "h2"),
    box([
        P("<b>When the question is unclear:</b> “May I confirm — are you asking about …?”", "body"),
        P("<b>When you do not know:</b> “We have not measured that yet; it is part of our evaluation "
          "plan.”", "body"),
        P("<b>When the criticism is fair:</b> “That is a good point; we will include it in the next "
          "version.”", "body"),
    ]),
    Spacer(1, 14),
    P("The hardest question, and its answer", "h2"),
    box([
        P("<b>“You have no results. Why should we accept this?”</b>", "body"),
        P("“The contribution is the architecture and a working implementation; the paper states that "
          "explicitly. Our evaluation protocol is defined against OpenRCA, AIOpsLab and controlled fault "
          "injection, with four metric families. We would rather report a measured eleven percent than "
          "an unmeasured claim.”", "body"),
    ], fill=colors.HexColor("#FBF2E2"), border=colors.HexColor("#EBD9BC")),
    Spacer(1, 14),
    P("Before you walk in", "h2"),
    box([
        P("□   Each speaker has read their page aloud with a timer, finishing ten seconds early", "body"),
        P("□   The three handovers are rehearsed — that is where teams lose time", "body"),
        P("□   One person holds the clicker and advances slides for everyone", "body"),
        P("□   Presenter View opened once, so the notes layout is familiar", "body"),
        P("□   Deck copied to a pen drive <i>and</i> emailed to yourself as a backup", "body"),
    ]),
]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(20 * mm, 12 * mm, "EOPS — ICSIE 2026 · speaker script")
    canvas.drawRightString(190 * mm, 12 * mm, f"page {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


doc = BaseDocTemplate("EOPS_speech_script.pdf", pagesize=A4,
                      leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=18 * mm, bottomMargin=20 * mm,
                      title="EOPS — Presentation Script for Four Speakers",
                      author="Sanjay P C, Sam Benadick J, Praveenkumar S, Nibuna A")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=footer)])
doc.build(story)
print("written EOPS_speech_script.pdf")
