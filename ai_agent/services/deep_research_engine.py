# ai_agent/services/deep_research_engine.py

import os
import logging
from typing import Tuple, Dict

from dotenv import load_dotenv
import requests
from crewai.tools import tool
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from xhtml2pdf import pisa
import pathlib
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Environment & constants
# -------------------------------------------------------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not OPENAI_API_KEY or not SERPER_API_KEY:
    raise ValueError("Missing required API keys. Check your .env file.")

MAX_SEARCH_RESULTS = 8
SEARCH_TIMEOUT = 30
MAX_QUERY_LENGTH = 500


# -------------------------------------------------------------------
# Serper-based web_search tool
# -------------------------------------------------------------------
@tool("web_search")
def web_search(**tool_args) -> str:
    """
    Perform a web search on Serper for the given query, focusing on automotive
    information (car models, prices, reliability, specs, market trends), and
    return a short textual summary of the top organic results (titles, links,
    and snippets).

    This tool is intentionally tolerant to how the LLM / CrewAI passes
    arguments: it can receive 'query', 'description', or a 'metadata' dict.
    """

    # ---- Recover query from various possible keys ---------------------------------
    query = None

    # 1) Direct 'query'
    if "query" in tool_args and isinstance(tool_args["query"], str):
        query = tool_args["query"]

    # 2) Sometimes CrewAI may pass the text as "description"
    if (not query) and isinstance(tool_args.get("description"), str):
        query = tool_args["description"]

    # 3) Or inside metadata
    metadata = tool_args.get("metadata")
    if (not query) and isinstance(metadata, dict):
        for k in ("query", "text", "angle", "prompt"):
            val = metadata.get(k)
            if isinstance(val, str) and val.strip():
                query = val
                break

    if not query or not str(query).strip():
        return "ERROR: Missing search query for web_search tool."

    query = str(query).strip()

    if len(query) > MAX_QUERY_LENGTH:
        logger.warning(f"Query truncated to {MAX_QUERY_LENGTH} characters")
        query = query[:MAX_QUERY_LENGTH]

    # ---- Call Serper ---------------------------------------------------------------
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": MAX_SEARCH_RESULTS}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=SEARCH_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return "ERROR: Search request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error(f"Search API error: {e}")
        return f"ERROR: Search failed – {e}"

    try:
        data = resp.json()
    except ValueError:
        return "ERROR: Invalid response from search API."

    organic = data.get("organic", [])
    if not organic:
        return "No results found for this query. Try rephrasing or using different keywords."

    results: list[str] = []
    for r in organic[:MAX_SEARCH_RESULTS]:
        title = r.get("title", "N/A")
        link = r.get("link", "N/A")
        snippet = r.get("snippet", "No description available")
        results.append(f"- **{title}**\n  {link}\n  {snippet}\n")

    return "\n".join(results)




# -------------------------------------------------------------------
# Optional: HTML → PDF helper (for future use, e.g. download button)
# -------------------------------------------------------------------
def html_to_pdf_xhtml2pdf(html_content: str, output_path: str) -> str:
    """
    Convert HTML to PDF using xhtml2pdf (pisa).
    """
    output_path = str(pathlib.Path(output_path).absolute())
    pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as pdf_file:
        result = pisa.CreatePDF(
            html_content,
            dest=pdf_file,
            encoding="utf-8",
        )

    if result.err:
        logger.error(f"xhtml2pdf conversion failed: {result.err}")
        raise RuntimeError("Failed to generate PDF with xhtml2pdf")

    logger.info(f"✅ PDF created successfully: {output_path}")
    return output_path


# Optional: local saving utility (not used by Django view, but available)
def save_reports(
    query: str,
    markdown_report: str,
    html_report: str,
    output_dir: str = ".",
) -> Dict[str, str]:
    """
    Save markdown, HTML and PDF reports to files with proper error handling.
    The PDF is generated from the HTML using html_to_pdf_xhtml2pdf().
    """
    safe_query = re.sub(r"[^\w\s-]", "", query)[:50]
    safe_query = re.sub(r"[-\s]+", "_", safe_query)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = (
        f"car_research_{safe_query}_{timestamp}"
        if safe_query
        else f"car_research_{timestamp}"
    )

    os.makedirs(output_dir, exist_ok=True)
    paths: Dict[str, str] = {}

    try:
        md_path = os.path.join(output_dir, f"{base_name}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        paths["markdown"] = md_path
        logger.info(f"Markdown saved: {md_path}")

        html_path = os.path.join(output_dir, f"{base_name}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_report)
        paths["html"] = html_path
        logger.info(f"HTML saved: {html_path}")

        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        try:
            html_to_pdf_xhtml2pdf(html_report, pdf_path)
            paths["pdf"] = pdf_path
            logger.info(f"PDF saved: {pdf_path}")
        except Exception as e:
            logger.warning(
                f"PDF generation failed: {e}. Markdown and HTML were saved successfully."
            )

        return paths

    except IOError as e:
        logger.error(f"Failed to save reports: {e}")
        raise


# -------------------------------------------------------------------
# LLM + Agents
# -------------------------------------------------------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=4096,
)

# 1. Planner
planner_agent = Agent(
    role="Advanced Automotive Research Planner",
    goal=(
        "Transform any car-related admin query into EXACTLY three ultra-precise and "
        "high-impact research angles covering: "
        "(1) technical/product engineering, "
        "(2) pricing & market dynamics (Tunisia-focused when applicable), "
        "(3) reliability, ownership patterns & competitive landscape. "
        "Each angle must be actionable, data-oriented, and optimized for deep web research."
    ),
    backstory=(
        "You are an elite automotive strategist working for a high-traffic car marketplace "
        "similar to automobile.tn. You design research plans that maximize factual depth, "
        "SEO value, model comparison clarity, and decision usefulness for platform admins."
    ),
    llm=llm,
    verbose=True,
    max_iter=3,
)

# 2. Parallel search agents
search_agent_1 = Agent(
    role="Technical Automotive Researcher",
    goal=(
        "Extract SPECIFIC engineering and technical facts: engine specs, gearbox options, "
        "dimensions, safety ratings, official documentation, and manufacturer-verified details. "
        "Use the web_search tool aggressively."
    ),
    backstory="You are a precision-focused vehicle specification analyst.",
    tools=[web_search],
    llm=llm,
    max_iter=6,
    verbose=True,
)

search_agent_2 = Agent(
    role="Market & Pricing Automotive Researcher",
    goal=(
        "Extract Tunisia-market pricing, import trends, regional comparisons, resale patterns, "
        "and demand signals. Provide numbers, ranges, and cited sources."
    ),
    backstory="You analyze automotive market behavior with near-journalistic precision.",
    tools=[web_search],
    llm=llm,
    max_iter=6,
    verbose=True,
)

search_agent_3 = Agent(
    role="Reliability & Ownership Analyst",
    goal=(
        "Extract real-world reliability insights: common problems, maintenance intervals, "
        "owner reviews, TCO, and long-term weaknesses. Must cite sources."
    ),
    backstory="You specialize in aggregating real-world automotive reliability insights.",
    tools=[web_search],
    llm=llm,
    max_iter=6,
    verbose=True,
)

# 3. Writer
writer_agent = Agent(
    role="Senior Automotive Insights Writer",
    goal=(
        "Transform research notes into a premium-grade 1000+ word automotive report "
        "formatted in rich Markdown optimized for admins AND SEO-ready blog usage."
    ),
    backstory=(
        "You write automotive reports at a professional automotive-magazine level. "
        "You combine engineering, market, and ownership insights with clarity and structure."
    ),
    llm=llm,
    max_iter=4,
    verbose=True,
)

# 4. Visualisation (Plotly)
visual_agent = Agent(
    role="Automotive Data Visualisation Architect",
    goal=(
        "Generate Plotly.js chart blocks (div + script) WITHOUT enclosing them in any "
        "markdown code fences (no ```html, no ```). "
        "Charts must be directly embeddable inside HTML as raw <div> and <script> blocks. "
        "Produce 2–4 charts based on the markdown report content."
    ),
    backstory=(
        "You output clean HTML components ONLY. Never add ```html or anything similar. "
        "Your charts must work immediately in a browser using Plotly.newPlot()."
    ),
    llm=llm,
    max_iter=3,
    verbose=True,
)

# 5. Formatter
formatter_agent = Agent(
    role="HTML Report Formatter with Plotly Support",
    goal=(
        "Transform the markdown report + Plotly chart blocks into a fully styled HTML5 "
        "document WITHOUT including any ```html or code fences. "
        "Embed all charts cleanly using the Plotly CDN "
        "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>. "
        "Add a footer at the bottom of the page that reads exactly:\n"
        "Report compiled by DeepDrive Insights. All rights reserved."
    ),
    backstory=(
        "You are a senior web designer. You NEVER output markdown code fences such as "
        "```html or ``` anywhere in the final HTML. You produce clean, valid HTML only. "
        "You ensure Plotly charts are inserted directly after relevant sections using "
        "their <div> and <script> blocks."
    ),
    llm=llm,
    max_iter=3,
    verbose=True,
)

# 6. Quality agent
quality_agent = Agent(
    role="Automotive Research Quality Auditor",
    goal=(
        "Audit the markdown report for factual precision, market applicability, structure, "
        "completeness, and insightfulness. Ensure Tunisia-market relevance when applicable."
    ),
    backstory="You are a strict automotive content auditor ensuring excellence.",
    llm=llm,
    max_iter=2,
    verbose=True,
)


# -------------------------------------------------------------------
# Public API: deep_research()
# -------------------------------------------------------------------
def deep_research(query: str) -> Tuple[str, str]:
    """
    Main entry point used by Django views.
    Returns (markdown_report, html_report).
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    if len(query) > MAX_QUERY_LENGTH:
        logger.warning(
            f"Query truncated from {len(query)} to {MAX_QUERY_LENGTH} characters"
        )
        query = query[:MAX_QUERY_LENGTH]

    query = query.strip()
    logger.info(f"Starting automotive deep research: {query}")

    # 1. Planning
    plan = Task(
        description=(
            f"Generate EXACTLY 3 strategic research angles for:\n'{query}'\n"
            "Angles must cover technical, market/pricing, and reliability/competitors."
        ),
        agent=planner_agent,
        expected_output="Three numbered research angles with actionable focus points.",
    )

    # 2. Parallel searches
    search_task_1 = Task(
        description="Perform technical automotive research for the planned angle 1.",
        agent=search_agent_1,
        context=[plan],
        expected_output="Technical findings with citations.",
    )

    search_task_2 = Task(
        description="Perform market & pricing automotive research for angle 2.",
        agent=search_agent_2,
        context=[plan],
        expected_output="Market/pricing findings with citations.",
    )

    search_task_3 = Task(
        description="Perform reliability & ownership research for angle 3.",
        agent=search_agent_3,
        context=[plan],
        expected_output="Reliability/ownership findings with citations.",
    )

    # 3. Writing
    write = Task(
        description=(
            "Write a highly detailed, structured 1000+ word car research report "
            "in Markdown using the outputs of all search tasks. "
            "Respect Tunisia-market orientation when applicable."
        ),
        agent=writer_agent,
        context=[search_task_1, search_task_2, search_task_3],
        expected_output="Markdown automotive report (1000+ words).",
        markdown=True,
    )

    # 4. Visualisation (Plotly)
    visuals = Task(
        description=(
            "Based on the contents of the markdown report, generate 2–4 meaningful Plotly charts. "
            "Produce final HTML blocks including:\n"
            "<div id='chartX'></div>\n"
            "<script> Plotly.newPlot(...) </script>\n"
            "Charts must match pricing, technical specs, fuel economy, or reliability data."
        ),
        agent=visual_agent,
        context=[write],
        expected_output="Plotly HTML blocks for charts.",
    )

    # 5. Formatting (HTML with Plotly)
    format_task = Task(
        description=(
            "Transform the markdown report + Plotly chart blocks into a complete HTML5 page. "
            "Include:\n"
            "- <script src='https://cdn.plot.ly/plotly-latest.min.js'></script>\n"
            "- Professional automotive CSS\n"
            "- Insert chart blocks after relevant sections"
        ),
        agent=formatter_agent,
        context=[write, visuals],
        expected_output="Fully styled HTML report with embedded Plotly charts.",
    )

    # 6. Quality audit (not returned, but logged)
    qc = Task(
        description=(
            "Audit the markdown report (structure, data quality, Tunisia relevance)."
        ),
        agent=quality_agent,
        context=[write],
        expected_output="Short audit summary.",
    )

    # Run workflow
    crew = Crew(
        agents=[
            planner_agent,
            search_agent_1,
            search_agent_2,
            search_agent_3,
            writer_agent,
            visual_agent,
            formatter_agent,
            quality_agent,
        ],
        tasks=[
            plan,
            search_task_1,
            search_task_2,
            search_task_3,
            write,
            visuals,
            format_task,
            qc,
        ],
        verbose=True,
        max_rpm=25,
    )

    crew.kickoff()

    markdown_report = write.output.raw if write.output else ""
    html_report = format_task.output.raw if format_task.output else ""

    if not markdown_report:
        raise RuntimeError("Markdown report is empty.")
    if not html_report:
        raise RuntimeError("HTML report is empty.")

    # Safety cleanup: remove any leftover markdown code fences the model may have produced
    html_report = html_report.replace("```html", "").replace("```", "")

    return markdown_report, html_report
