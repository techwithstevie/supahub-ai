from __future__ import annotations

from models.schemas import ResumeDocument

_QUOTE_CHARS = "\"'“”‘’"


def _clean_summary(text: str) -> str:
    s = (text or "").strip()
    return s.strip(_QUOTE_CHARS).strip()


def _join_links(doc: ResumeDocument) -> str:
    parts: list[str] = []
    if doc.phone:
        parts.append(doc.phone)
    if doc.email:
        parts.append(doc.email)
    if doc.linkedin:
        parts.append("LinkedIn")
    if doc.github:
        parts.append("GitHub")
    if doc.portfolio:
        parts.append("Portfolio")
    return "  |  ".join(parts)


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_markdown(doc: ResumeDocument) -> str:
    lines: list[str] = []
    lines.append(f"# {(doc.full_name or '').upper()}")
    lines.append(_join_links(doc))
    lines.append("")
    lines.append(f"## {(doc.target_title or '').upper()}")
    if doc.headline_tech:
        lines.append("  •  ".join(doc.headline_tech))
    lines.append("")
    if doc.summary:
        summary = _clean_summary(doc.summary)
        lines.append(f'"{summary}"')
    lines.append("")
    lines.append("---")
    lines.append("## SKILLS")
    for cat in doc.skills:
        items = ", ".join(cat.items)
        lines.append(f"**{cat.category}:**  {items}")
    lines.append("")
    lines.append("---")
    lines.append("## EXPERIENCE")
    for exp in doc.experience:
        header = (
            f"**{(exp.company or '').upper()}** — {exp.title}  |  "
            f"{exp.location}  |  {exp.start} – {exp.end}"
        )
        lines.append(header)
        for bullet in exp.bullets:
            lines.append(f"● {bullet}")
        lines.append("")
    lines.append("---")
    lines.append("## PROJECTS")
    for proj in doc.projects:
        stack = ", ".join(proj.stack)
        link_bit = f"  |  {'  |  '.join(proj.links)}" if proj.links else ""
        lines.append(f"**{proj.name}**{link_bit}")
        if stack:
            lines.append(stack)
        for bullet in proj.bullets:
            lines.append(f"● {bullet}")
        lines.append("")
    if doc.education:
        lines.append("---")
        lines.append("## EDUCATION")
        for edu in doc.education:
            lines.append(f"**{edu.school}**  —  {edu.credential}")
    return "\n".join(lines).strip() + "\n"


def render_html(doc: ResumeDocument) -> str:
    """Print-ready HTML matching the professional sample layout."""
    contact = _join_links(doc)
    tech = "  •  ".join(_esc(t) for t in doc.headline_tech)
    summary = _esc(_clean_summary(doc.summary))

    skills_html_parts: list[str] = []
    for cat in doc.skills:
        skills_html_parts.append(
            '<div class="skill-row">'
            f'<span class="skill-cat">{_esc(cat.category)}:</span> '
            f'<span class="skill-items">{_esc(", ".join(cat.items))}</span>'
            "</div>"
        )
    skills_html = "\n".join(skills_html_parts)

    exp_html_parts: list[str] = []
    for exp in doc.experience:
        bullets = "".join(f"<li>{_esc(b)}</li>" for b in exp.bullets)
        exp_html_parts.append(
            f"""
        <div class="block">
          <div class="block-head">
            <span class="company">{_esc((exp.company or "").upper())}</span>
            <span class="meta"> — {_esc(exp.title)}  |  {_esc(exp.location)}  |  {_esc(exp.start)} – {_esc(exp.end)}</span>
          </div>
          <ul class="bullets">{bullets}</ul>
        </div>
        """
        )
    exp_html = "\n".join(exp_html_parts)

    proj_html_parts: list[str] = []
    for proj in doc.projects:
        link_bit = ""
        if proj.links:
            link_bit = "  |  " + "  |  ".join(_esc(x) for x in proj.links)
        stack = _esc(", ".join(proj.stack))
        bullets = "".join(f"<li>{_esc(b)}</li>" for b in proj.bullets)
        proj_html_parts.append(
            f"""
        <div class="block">
          <div class="block-head">
            <span class="company">{_esc(proj.name)}</span>
            <span class="meta">{link_bit}</span>
          </div>
          <div class="stack">{stack}</div>
          <ul class="bullets">{bullets}</ul>
        </div>
        """
        )
    proj_html = "\n".join(proj_html_parts)

    edu_html_parts: list[str] = []
    for edu in doc.education:
        edu_html_parts.append(
            f'<div class="edu-row">'
            f"<strong>{_esc(edu.school)}</strong>  —  {_esc(edu.credential)}"
            f"</div>"
        )
    edu_html = "\n".join(edu_html_parts)

    name = _esc(doc.full_name or "")
    title = _esc(doc.target_title or "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{name} — Resume</title>
<style>
  @page {{ margin: 0.55in 0.65in; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Calibri", "Segoe UI", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.35;
    color: #111;
    background: #fff;
  }}
  .page {{
    max-width: 8.5in;
    margin: 0 auto;
    padding: 0.5in 0.65in;
  }}
  .name {{
    text-align: center;
    font-size: 18pt;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin: 0 0 4px 0;
  }}
  .contact {{
    text-align: center;
    font-size: 9.5pt;
    color: #222;
    margin-bottom: 10px;
  }}
  .title {{
    text-align: center;
    font-size: 12pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin: 0 0 4px 0;
  }}
  .tech-line {{
    text-align: center;
    font-size: 9.5pt;
    color: #222;
    margin-bottom: 10px;
  }}
  .summary {{
    font-style: italic;
    text-align: left;
    margin: 0 0 12px 0;
    color: #1a1a1a;
  }}
  .section {{
    font-size: 10.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid #222;
    margin: 14px 0 8px 0;
    padding-bottom: 2px;
  }}
  .skill-row {{ margin: 2px 0; }}
  .skill-cat {{
    display: inline-block;
    min-width: 5.2rem;
    font-weight: 700;
  }}
  .block {{ margin-bottom: 10px; }}
  .block-head {{ margin-bottom: 2px; }}
  .company {{ font-weight: 700; }}
  .meta {{ font-weight: 400; }}
  .stack {{
    font-size: 9.5pt;
    color: #333;
    margin: 1px 0 2px 0;
  }}
  ul.bullets {{
    margin: 2px 0 0 0;
    padding-left: 1.1rem;
  }}
  ul.bullets li {{
    margin: 2px 0;
  }}
  .edu-row {{ margin: 3px 0; }}
</style>
</head>
<body>
  <div class="page">
    <h1 class="name">{name}</h1>
    <div class="contact">{_esc(contact)}</div>
    <div class="title">{title}</div>
    <div class="tech-line">{tech}</div>
    <p class="summary">"{summary}"</p>

    <div class="section">Skills</div>
    {skills_html}

    <div class="section">Experience</div>
    {exp_html}

    <div class="section">Projects</div>
    {proj_html}

    <div class="section">Education</div>
    {edu_html}
  </div>
</body>
</html>
"""