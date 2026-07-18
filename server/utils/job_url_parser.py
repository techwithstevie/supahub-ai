from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from models.job_schemas import (
    HiringTeamMember,
    JobSource,
    LinkedInJobDetails,
    ParseJobUrlResponse,
)

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

_NA = "N/A"

_SECTION_ORDER: list[tuple[str, tuple[str, ...]]] = [
    ("about_the_role", ("about the role",)),
    ("compensation", ("compensation",)),
    ("location", ("location",)),
    ("primary_responsibilities", ("primary responsibilities",)),
    ("candidate_qualifications", ("candidate qualifications",)),
    ("why_join", ("why join this opportunity",)),
    (
        "benefits",
        (
            "benefits found in job post",
            "benefits found in the job post",
        ),
    ),
    (
        "requirements_added_by_poster",
        (
            "requirements added by the job poster",
            "requirements added by job poster",
        ),
    ),
]

_STRUCTURAL = {
    "about the job",
    "meet the hiring team",
    "people you can reach out to",
    "job poster",
    "similar jobs",
    "people also viewed",
    "show more",
    "show less",
    "message",
    "connect",
    "follow",
    "save",
}

_EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
_PHONE_RE = re.compile(
    r"(?:\+?1[\s.\-]?)?(?:\(?\d{3}\)?[\s.\-]?)\d{3}[\s.\-]?\d{4}"
)
_DEGREE_RE = re.compile(r"\b([123])(st|nd|rd)\b", re.I)
_IN_URL_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_\-%]+",
    re.I,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _norm(s: str) -> str:
    s = unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\xa0", " ").strip().lower()
    s = re.sub(r"\s+", " ", s).rstrip(":")
    return s


def _expand_contact_links(html: str) -> str:
    """Resolve mailto:/tel: before stripping tags so emails are never truncated."""
    if not html:
        return ""

    def mailto_sub(m: re.Match) -> str:
        addr = unquote(m.group(1) or "").strip()
        addr = addr.split("?", 1)[0].strip()
        return f" {addr} "

    def tel_sub(m: re.Match) -> str:
        num = unquote(m.group(1) or "").strip()
        digits = re.sub(r"\D", "", num)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) == 10:
            return f" {digits[0:3]}-{digits[3:6]}-{digits[6:10]} "
        return f" {num} "

    s = html
    s = re.sub(
        r'(?is)<a\s+[^>]*href=["\']mailto:([^"\']+)["\'][^>]*>.*?</a>',
        mailto_sub,
        s,
    )
    s = re.sub(
        r'(?is)<a\s+[^>]*href=["\']tel:([^"\']+)["\'][^>]*>.*?</a>',
        tel_sub,
        s,
    )
    s = re.sub(
        r'(?i)href=["\']mailto:([^"\']+)["\']',
        lambda m: f'data-mail="{unquote(m.group(1)).split("?", 1)[0]}"',
        s,
    )
    return s


def _clean(s: str) -> str:
    s = unescape(s or "")
    s = _expand_contact_links(s)
    s = re.sub(r"(?is)<script[^>]*>.*?</script>", "\n", s)
    s = re.sub(r"(?is)<style[^>]*>.*?</style>", "\n", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|section)>", "\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "• ", s)
    s = re.sub(r"(?is)<a\s+[^>]*>(.*?)</a>", r"\1", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
    s = s.replace("\u200c", "").replace("\u200d", "").replace("\xad", "")
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    lines = []
    for ln in s.splitlines():
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if ln:
            lines.append(ln)
    return "\n".join(lines).strip()


def _is_linkedin(url: str) -> bool:
    try:
        return "linkedin.com" in urlparse(url).netloc.lower()
    except Exception:
        return False


def _make_member(
    *,
    name: str,
    title: str = _NA,
    headline: str = "",
    company: str = "",
    email: str = "",
    phone: str = "",
    profile_url: str = "",
    connection_degree: str = "",
    extra: str = "",
) -> HiringTeamMember:
    headline = (headline or "").strip()
    title = (title or "").strip()
    if headline and (not title or title == _NA):
        title = headline
    if not title:
        title = headline or _NA
    data = {
        "name": (name or "").strip() or _NA,
        "title": title,
        "headline": headline or title,
        "company": (company or "").strip(),
        "email": (email or "").strip(),
        "phone": (phone or "").strip(),
        "profile_url": (profile_url or "").strip(),
        "connection_degree": (connection_degree or "").strip(),
        "extra": (extra or "").strip(),
    }
    try:
        return HiringTeamMember(**data)
    except TypeError:
        extra_bits = [
            data["headline"] if data["headline"] != data["title"] else "",
            data["email"],
            data["phone"],
            data["extra"],
        ]
        try:
            return HiringTeamMember(
                name=data["name"],
                title=data["title"],
                profile_url=data["profile_url"],
                connection_degree=data["connection_degree"],
                extra=" | ".join(x for x in extra_bits if x),
            )
        except TypeError:
            return HiringTeamMember(name=data["name"], title=data["title"])


def _match_section(line: str) -> str | None:
    h = _norm(line)
    if not h:
        return None
    for key, aliases in _SECTION_ORDER:
        if h in aliases:
            return key
    if h.startswith("about "):
        rest = h[6:].strip()
        if rest and rest not in {
            "the job",
            "this job",
            "the role",
            "this role",
            "this opportunity",
        }:
            return "about_company"
    return None


def _is_struct(line: str) -> bool:
    return _norm(line) in _STRUCTURAL


def _force_header_breaks(text: str) -> str:
    labels: list[str] = []
    for _, als in _SECTION_ORDER:
        labels.extend(als)
    labels.extend(sorted(_STRUCTURAL, key=len, reverse=True))
    labels = sorted(set(labels), key=len, reverse=True)
    out = text
    for lab in labels:
        out = re.sub(
            rf"(?im)^[ \t]*({re.escape(lab)})[ \t]*:?[ \t]*$",
            r"\n\1\n",
            out,
        )
    out = re.sub(
        r"(?m)^[ \t]*(About\s+[A-Z][\w .,&'\-]{1,60})[ \t]*:?[ \t]*$",
        r"\n\1\n",
        out,
    )
    return out


def _scan_sections(plain: str) -> dict[str, str]:
    if not plain:
        return {}
    lines = [
        ln.strip()
        for ln in _force_header_breaks(plain).splitlines()
        if ln.strip()
    ]
    headers: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        key = _match_section(line)
        if key:
            headers.append((i, key))
        elif _is_struct(line):
            headers.append((i, f"__s__:{_norm(line)}"))

    raw: dict[str, str] = {}
    for hi, (idx, key) in enumerate(headers):
        if key.startswith("__s__:"):
            continue
        start = idx + 1
        end = headers[hi + 1][0] if hi + 1 < len(headers) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        body = re.sub(
            r"(?im)^(show more|show less|see more|see less)$",
            "",
            body,
        ).strip()
        if not body:
            continue
        if key in raw and raw[key]:
            raw[key] = raw[key] + "\n\n" + body
        else:
            raw[key] = body

    about_role = (raw.pop("about_the_role", "") or "").strip()
    primary = (raw.get("primary_responsibilities") or "").strip()
    if about_role and primary:
        raw["primary_responsibilities"] = f"{about_role}\n\n{primary}"
    elif about_role:
        raw["primary_responsibilities"] = about_role
    return raw


def _details_dict(raw: dict[str, str]) -> dict[str, str]:
    keys = (
        "compensation",
        "location",
        "primary_responsibilities",
        "candidate_qualifications",
        "why_join",
        "about_company",
        "benefits",
        "requirements_added_by_poster",
    )
    return {k: (raw.get(k) or "").strip() or _NA for k in keys}


def _parse_headline(headline: str) -> dict[str, str]:
    raw = _clean(headline)
    raw = raw.replace("\n", " | ")
    emails = _EMAIL_RE.findall(raw)
    phones = _PHONE_RE.findall(raw)

    parts = [p.strip() for p in re.split(r"\s*\|\s*", raw) if p.strip()]
    fixed_parts: list[str] = []
    for p in parts:
        if emails and "@" not in p and re.fullmatch(r"[A-Za-z0-9._%+\-]{1,32}", p):
            if any(e.lower().startswith(p.lower()) for e in emails):
                continue
        fixed_parts.append(p)

    full = " | ".join(fixed_parts) if fixed_parts else raw.strip()
    for e in emails:
        if e not in full:
            full = f"{full} | {e}" if full else e
    for p in phones:
        if re.sub(r"\D", "", p) not in re.sub(r"\D", "", full):
            full = f"{full} | {p}" if full else p

    parts2 = [p.strip() for p in re.split(r"\s*\|\s*", full) if p.strip()]
    full = " | ".join(parts2)
    company = parts2[0] if len(parts2) >= 2 else ""

    return {
        "headline": full or _NA,
        "title": full or _NA,
        "company": company,
        "email": emails[0] if emails else "",
        "phone": phones[0] if phones else "",
    }


def _collect_tail_text(tail_html: str, limit: int = 2500) -> str:
    chunk = tail_html[:limit]
    plain = _clean(chunk)

    scored: list[tuple[float, str]] = []
    for ln in plain.splitlines():
        ln = ln.strip()
        if not ln or len(ln) < 3:
            continue
        if _norm(ln) in _STRUCTURAL:
            break
        if re.match(r"^[•\-\*]?\s*[123](st|nd|rd)\s*$", ln, re.I):
            continue
        score = 0.0
        if "|" in ln:
            score += 5
        if _EMAIL_RE.search(ln):
            score += 8
        if _PHONE_RE.search(ln):
            score += 6
        if re.search(r"recruit|manager|engineer|director|solutions", ln, re.I):
            score += 3
        score += min(len(ln), 200) / 200.0
        scored.append((score, ln))

    if not scored:
        return ""

    scored.sort(key=lambda x: x[0], reverse=True)

    def uniq(xs: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for x in xs:
            k = x.lower()
            if k not in seen:
                seen.add(k)
                out.append(x)
        return out

    emails: list[str] = []
    phones: list[str] = []
    for _sc, ln in scored:
        emails.extend(_EMAIL_RE.findall(ln))
        phones.extend(_PHONE_RE.findall(ln))
    emails, phones = uniq(emails), uniq(phones)

    pipe_lines = [ln for sc, ln in scored if "|" in ln and sc >= 5]

    def line_rank(ln: str) -> tuple:
        return (
            1 if _EMAIL_RE.search(ln) else 0,
            1 if _PHONE_RE.search(ln) else 0,
            ln.count("|"),
            len(ln),
        )

    if pipe_lines:
        best = max(pipe_lines, key=line_rank)
    else:
        best = scored[0][1]

    if emails and not _EMAIL_RE.search(best):
        best = f"{best} | {emails[0]}"
    if phones and not _PHONE_RE.search(best):
        best = f"{best} | {phones[0]}"

    return best.strip()


def _headline_from_tail(tail_html: str, name: str) -> tuple[str, str, str]:
    tail_plain = _clean(tail_html[:2500])
    degree = ""
    dm = _DEGREE_RE.search(tail_plain[:120])
    if dm:
        degree = f"{dm.group(1)}{dm.group(2).lower()}"

    extra = ""
    if re.search(r"(?i)\bjob\s*poster\b", tail_plain[:300]):
        extra = "Job poster"

    headline = _collect_tail_text(tail_html, limit=2500)

    class_pats = (
        r'class=["\'][^"\']*(?:headline|subtitle|secondary-subtitle|'
        r'hirer-card|job-poster|actor-sub-description|text-body-small|'
        r'jobs-poster|hiring-team)[^"\']*["\'][^>]*>([\s\S]{0,800}?)</(?:div|span|p)>',
        r'data-anonymize=["\'](?:headline|title|job-title)["\'][^>]*>([\s\S]{0,500}?) <',
    )

    def richness(s: str) -> tuple:
        return (
            1 if _EMAIL_RE.search(s) else 0,
            1 if _PHONE_RE.search(s) else 0,
            s.count("|"),
            len(s),
        )

    for pat in class_pats:
        m = re.search(pat, tail_html[:2500], re.I)
        if not m:
            continue
        cand = _clean(m.group(1))
        if not cand or _norm(cand) == _norm(name):
            continue
        if _norm(cand) in _STRUCTURAL:
            continue
        if not headline or richness(cand) > richness(headline):
            headline = cand

    if headline:
        lines = [
            ln
            for ln in headline.splitlines()
            if _norm(ln) != _norm(name)
            and not re.match(r"^[•\-\*]?\s*[123](st|nd|rd)\s*$", ln, re.I)
        ]
        if any("|" in ln for ln in lines):
            headline = " | ".join(
                p.strip()
                for ln in lines
                for p in re.split(r"\s*\|\s*", ln)
                if p.strip()
            )
        else:
            headline = "\n".join(lines)
        parsed_preview = _parse_headline(headline)
        headline = parsed_preview["headline"]

    return headline, degree, extra


def _hiring_html_slice(html: str) -> str:
    if not html:
        return ""
    lower = html.lower()
    start = -1
    for mk in (
        "meet the hiring team",
        "people you can reach out to",
        "hirer-card",
        "job-poster",
        "hiring team",
    ):
        pos = lower.find(mk)
        if pos != -1:
            start = pos if start == -1 else min(start, pos)
    if start == -1:
        return html
    return html[start : start + 40000]


def _enrich_from_tail_contacts(parsed: dict[str, str], tail: str) -> dict[str, str]:
    for mm in re.finditer(r'(?i)mailto:([^"\'?\s]+)', tail):
        addr = unquote(mm.group(1)).split("?", 1)[0]
        if _EMAIL_RE.fullmatch(addr) and not parsed.get("email"):
            parsed["email"] = addr
            h = parsed.get("headline") or ""
            if h == _NA:
                h = ""
            if addr not in h:
                parsed["headline"] = f"{h} | {addr}".strip(" |") if h else addr
                parsed["title"] = parsed["headline"]

    for mm in re.finditer(r'(?i)tel:([^"\'?\s]+)', tail):
        num = unquote(mm.group(1))
        digits = re.sub(r"\D", "", num)
        if len(digits) >= 10 and not parsed.get("phone"):
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]
            pretty = (
                f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
                if len(digits) == 10
                else num
            )
            parsed["phone"] = pretty
            h = parsed.get("headline") or ""
            if h == _NA:
                h = ""
            if pretty not in h and digits not in re.sub(r"\D", "", h):
                parsed["headline"] = f"{h} | {pretty}".strip(" |") if h else pretty
                parsed["title"] = parsed["headline"]
    return parsed


def _extract_hiring_from_html(html: str) -> list[HiringTeamMember]:
    if not html:
        return []

    blob = _hiring_html_slice(html)
    members: list[HiringTeamMember] = []
    seen: set[str] = set()

    for m in re.finditer(
        r'href=["\'](https?://(?:www\.)?linkedin\.com/in/[^"\']+)["\'][^>]*>(.*?)</a>',
        blob,
        re.I | re.S,
    ):
        url = m.group(1).split("?")[0].rstrip("/")
        name = _clean(m.group(2))
        if len(name) < 2 or len(name) > 80:
            continue
        if "linkedin.com/in/" in name.lower():
            continue
        if _norm(name) in _STRUCTURAL:
            continue
        if name.lower() in {"linkedin", "profile"}:
            continue

        key = _norm(name)
        if key in seen:
            continue

        tail = blob[m.end() : m.end() + 2500]
        headline, degree, extra = _headline_from_tail(tail, name)
        if headline:
            parsed = _parse_headline(headline)
        else:
            parsed = {
                "headline": _NA,
                "title": _NA,
                "company": "",
                "email": "",
                "phone": "",
            }
        parsed = _enrich_from_tail_contacts(parsed, tail)

        seen.add(key)
        members.append(
            _make_member(
                name=name,
                title=parsed["title"],
                headline=parsed["headline"],
                company=parsed.get("company", ""),
                email=parsed.get("email", ""),
                phone=parsed.get("phone", ""),
                profile_url=url,
                connection_degree=degree,
                extra=extra,
            )
        )

    for m in re.finditer(
        r'data-anonymize=["\']person-name["\'][^>]*>([^<]+)<',
        blob,
        re.I,
    ):
        name = _clean(m.group(1))
        key = _norm(name)
        if not name or key in seen:
            continue
        tail = blob[m.end() : m.end() + 2500]
        headline, degree, extra = _headline_from_tail(tail, name)
        hm = re.search(
            r'data-anonymize=["\'](?:headline|title)["\'][^>]*>([^<]+)<',
            tail,
            re.I,
        )
        if hm:
            headline = _clean(hm.group(1)) or headline
        if headline:
            parsed = _parse_headline(headline)
        else:
            parsed = {
                "headline": _NA,
                "title": _NA,
                "company": "",
                "email": "",
                "phone": "",
            }
        parsed = _enrich_from_tail_contacts(parsed, tail)
        seen.add(key)
        members.append(
            _make_member(
                name=name,
                title=parsed["title"],
                headline=parsed["headline"],
                company=parsed.get("company", ""),
                email=parsed.get("email", ""),
                phone=parsed.get("phone", ""),
                connection_degree=degree,
                extra=extra,
            )
        )

    for m in re.finditer(
        r'"firstName"\s*:\s*"([^"]+)"\s*,\s*"lastName"\s*:\s*"([^"]+)"',
        blob,
    ):
        name = f"{m.group(1)} {m.group(2)}".strip()
        key = _norm(name)
        if key in seen:
            continue
        window = blob[max(0, m.start() - 100) : m.end() + 900]
        headline = ""
        for fld in (
            "headline",
            "localizedHeadline",
            "title",
            "occupation",
            "subtitle",
        ):
            hm = re.search(rf'"{fld}"\s*:\s*"((?:\\.|[^"\\])*)"', window)
            if hm:
                try:
                    headline = json.loads(f'"{hm.group(1)}"')
                except json.JSONDecodeError:
                    headline = hm.group(1)
                break
        url = ""
        um = re.search(
            r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_\-%]+",
            window,
        )
        if um:
            url = um.group(0).rstrip("/")
        if headline:
            parsed = _parse_headline(headline)
        else:
            parsed = {
                "headline": _NA,
                "title": _NA,
                "company": "",
                "email": "",
                "phone": "",
            }
        parsed = _enrich_from_tail_contacts(parsed, window)
        if parsed.get("email") or parsed.get("phone") or (
            parsed.get("headline") and parsed["headline"] != _NA
        ):
            seen.add(key)
            members.append(
                _make_member(
                    name=name,
                    title=parsed["title"],
                    headline=parsed["headline"],
                    company=parsed.get("company", ""),
                    email=parsed.get("email", ""),
                    phone=parsed.get("phone", ""),
                    profile_url=url,
                )
            )

    return members


def _extract_hiring_from_plain(plain: str) -> list[HiringTeamMember]:
    if not plain:
        return []

    m = re.search(
        r"(?is)(?:people you can reach out to\s*)?meet the hiring team\s*(.+?)"
        r"(?=about the (?:job|role)\b|^compensation\b|^location\b|"
        r"^primary responsibilities\b|similar jobs\b|$)",
        plain,
    )
    if not m:
        m = re.search(
            r"(?is)people you can reach out to\s*(.+?)"
            r"(?=about the (?:job|role)\b|^compensation\b|meet the hiring team\b|$)",
            plain,
        )
    block = m.group(1).strip() if m else ""
    if not block:
        return []

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    members: list[HiringTeamMember] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        low = _norm(line)
        if low in _STRUCTURAL or _match_section(line):
            i += 1
            continue
        if _DEGREE_RE.fullmatch(line.strip("• ").strip()):
            i += 1
            continue

        if (
            "|" in line
            or _EMAIL_RE.search(line)
            or _PHONE_RE.search(line)
            or line.lower().startswith("http")
            or len(line) > 80
        ):
            i += 1
            continue

        name = re.sub(r"^[•\-\*]+\s*", "", line).strip()
        i += 1
        degree = ""
        if i < len(lines):
            dm = re.match(r"^[•\-\*]?\s*([123])(st|nd|rd)\s*$", lines[i], re.I)
            if dm:
                degree = f"{dm.group(1)}{dm.group(2).lower()}"
                i += 1

        headline = ""
        if i < len(lines):
            cand = lines[i]
            if _norm(cand) not in _STRUCTURAL and not _match_section(cand):
                if (
                    "|" in cand
                    or _EMAIL_RE.search(cand)
                    or _PHONE_RE.search(cand)
                    or len(cand) > 15
                ):
                    headline = cand
                    i += 1

        extra = ""
        if i < len(lines) and _norm(lines[i]) == "job poster":
            extra = "Job poster"
            i += 1

        if headline:
            parsed = _parse_headline(headline)
        else:
            parsed = {
                "headline": _NA,
                "title": _NA,
                "company": "",
                "email": "",
                "phone": "",
            }

        url = ""
        um = re.search(
            rf"{re.escape(name)}.{{0,200}}?({_IN_URL_RE.pattern})",
            plain,
            re.I | re.S,
        )
        if um:
            url = um.group(1).rstrip("/")

        members.append(
            _make_member(
                name=name,
                title=parsed["title"],
                headline=parsed["headline"],
                company=parsed.get("company", ""),
                email=parsed.get("email", ""),
                phone=parsed.get("phone", ""),
                profile_url=url,
                connection_degree=degree,
                extra=extra,
            )
        )

    return members


def _merge_hiring(
    primary: list[HiringTeamMember],
    secondary: list[HiringTeamMember],
) -> list[HiringTeamMember]:
    by: dict[str, HiringTeamMember] = {}

    def rank(p: HiringTeamMember) -> int:
        h = getattr(p, "headline", "") or getattr(p, "title", "") or ""
        score = len(h)
        if getattr(p, "email", ""):
            score += 50
        if getattr(p, "phone", ""):
            score += 50
        if getattr(p, "profile_url", ""):
            score += 20
        if "|" in h:
            score += 30
        return score

    for src in (primary, secondary):
        for p in src:
            key = _norm(p.name or "")
            if not key or key == "n/a":
                continue
            if key not in by or rank(p) > rank(by[key]):
                by[key] = p
    return list(by.values())


def extract_hiring_team(html: str, plain: str) -> list[HiringTeamMember]:
    from_html = _extract_hiring_from_html(html)
    from_plain = _extract_hiring_from_plain(plain)
    if not from_plain and html:
        from_plain = _extract_hiring_from_plain(_html_to_plain(html))
    return _merge_hiring(from_html, from_plain)


def _meta(html: str, *keys: str) -> str:
    for key in keys:
        for pat in (
            rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(key)}["\']',
            rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(key)}["\']',
        ):
            m = re.search(pat, html or "", re.I)
            if m:
                return _clean(m.group(1))
    return ""


def _tag_text(html: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html or "", re.I | re.S)
    return _clean(m.group(1)) if m else ""


def _json_ld(html: str) -> list[Any]:
    out: list[Any] = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html or "",
        re.I | re.S,
    ):
        try:
            data = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            out.extend(data)
        else:
            out.append(data)
    return out


def _walk_jobs(obj: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        t = obj.get("@type")
        types = t if isinstance(t, list) else [t]
        if any(x and "jobposting" in str(x).lower() for x in types):
            found.append(obj)
        for v in obj.values():
            found.extend(_walk_jobs(v))
    elif isinstance(obj, list):
        for it in obj:
            found.extend(_walk_jobs(it))
    return found


def _role_company(plain: str, html: str) -> tuple[str, str]:
    role, company = "", ""
    for block in _json_ld(html):
        for job in _walk_jobs(block):
            role = role or str(job.get("title") or "").strip()
            org = job.get("hiringOrganization")
            if isinstance(org, dict):
                company = company or str(org.get("name") or "").strip()
            elif isinstance(org, str):
                company = company or org.strip()

    for pat, which in (
        (
            r'class=["\'][^"\']*job-details-jobs-unified-top-card__job-title[^"\']*["\'][^>]*>(.*?)</div>',
            "role",
        ),
        (
            r'class=["\'][^"\']*topcard__title[^"\']*["\'][^>]*>([^<]+)<',
            "role",
        ),
        (
            r'class=["\'][^"\']*job-details-jobs-unified-top-card__company-name[^"\']*["\'][^>]*>(.*?)</div>',
            "company",
        ),
        (
            r'class=["\'][^"\']*topcard__org-name-link[^"\']*["\'][^>]*>([^<]+)<',
            "company",
        ),
    ):
        m = re.search(pat, html or "", re.I | re.S)
        if not m:
            continue
        val = _clean(m.group(1)).split("\n")[0].strip()
        if which == "role" and val and not role:
            role = val
        if which == "company" and val and not company:
            company = val

    og = _meta(html or "", "og:title") or _tag_text(html or "", "title")
    if og:
        parts = [
            p.strip()
            for p in re.split(r"\s*[|\-–—]\s*", og)
            if p.strip().lower() not in {"linkedin", "job", "jobs"}
        ]
        if parts and not role:
            role = parts[0]
        if len(parts) >= 2 and not company:
            company = parts[1]

    if plain:
        am = re.search(
            r"(?im)^[ \t]*About\s+(?!the job|the role|this opportunity)(.+)$",
            plain,
        )
        if am and not company:
            company = am.group(1).strip()
        hm = re.search(
            r"(?is)^[ \t]*([^\n]{2,80})\s*\n\s*([^\n]{2,100})\s*\n\s*"
            r"(?:People you can reach out to|Meet the hiring team)\b",
            plain[:1500],
        )
        if hm:
            c_cand, r_cand = _clean(hm.group(1)), _clean(hm.group(2))
            if c_cand and "linkedin.com" not in c_cand.lower() and not company:
                company = c_cand.split("\n")[0]
            if r_cand and "linkedin.com" not in r_cand.lower() and not role:
                if _norm(r_cand) not in _STRUCTURAL:
                    role = r_cand.split("\n")[0]

    role = re.sub(r"\s*\|\s*LinkedIn.*$", "", role or "", flags=re.I).strip()
    return role, (company or "").strip()


def _html_to_plain(html: str) -> str:
    if not html:
        return ""
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", "\n", html)
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", "\n", t)
    return _clean(t)


def _description(html: str) -> str:
    cands: list[str] = []
    for pat in (
        r'class=["\'][^"\']*show-more-less-html__markup[^"\']*["\'][^>]*>(.*?)</div>',
        r'class=["\'][^"\']*jobs-description-content__text[^"\']*["\'][^>]*>(.*?)</div>',
        r'class=["\'][^"\']*jobs-box__html-content[^"\']*["\'][^>]*>(.*?)</div>',
        r'id=["\']job-details["\'][^>]*>(.*?)</div>',
    ):
        for m in re.finditer(pat, html or "", re.I | re.S):
            t = _clean(m.group(1))
            if len(t) > 80:
                cands.append(t)
    for block in _json_ld(html or ""):
        for job in _walk_jobs(block):
            desc = job.get("description")
            if isinstance(desc, str):
                t = _clean(desc)
                if len(t) > 80:
                    cands.append(t)
    return max(cands, key=len) if cands else ""


def _score(t: str) -> tuple:
    low = (t or "").lower()
    return (
        "benefits found in job post" in low,
        "requirements added by the job poster" in low,
        "about the role" in low,
        "meet the hiring team" in low,
        len(t or ""),
    )


def _build_details(
    sections: dict[str, str],
    hiring: list[HiringTeamMember],
) -> LinkedInJobDetails:
    d = _details_dict(sections)
    return LinkedInJobDetails(
        compensation=d["compensation"],
        location=d["location"],
        primary_responsibilities=d["primary_responsibilities"],
        candidate_qualifications=d["candidate_qualifications"],
        why_join=d["why_join"],
        about_company=d["about_company"],
        benefits=d["benefits"],
        requirements_added_by_poster=d["requirements_added_by_poster"],
        hiring_team=list(hiring),
    )


def _notes(details: LinkedInJobDetails) -> str:
    order = [
        ("Compensation", details.compensation),
        ("Location", details.location),
        ("Primary Responsibilities", details.primary_responsibilities),
        ("Candidate Qualifications", details.candidate_qualifications),
        ("Why Join This Opportunity", details.why_join),
        ("About Company", details.about_company),
        ("Benefits found in job post", details.benefits),
        ("Requirements added by the job poster", details.requirements_added_by_poster),
    ]
    parts = ["About the job", ""]
    for label, val in order:
        parts.extend([label, val or _NA, ""])
    parts.append("Meet the hiring team")
    team = list(details.hiring_team or [])
    if not team:
        parts.append(_NA)
    for p in team:
        h = getattr(p, "headline", "") or getattr(p, "title", "") or _NA
        lines = [p.name or _NA]
        deg = getattr(p, "connection_degree", "") or ""
        if deg:
            lines.append(deg)
        if h and h != _NA:
            lines.append(h)
        ex = getattr(p, "extra", "") or ""
        if ex:
            lines.append(ex)
        url = getattr(p, "profile_url", "") or ""
        if url:
            lines.append(url)
        parts.append("\n".join(lines))
        parts.append("")
    return "\n".join(parts).strip()


def _salary(comp: str) -> str:
    if not comp or comp == _NA:
        return ""
    for ln in comp.splitlines():
        if "$" in ln:
            return ln.strip()[:160]
    return comp.splitlines()[0][:160]


def parse_linkedin_plain_text(plain: str, job_url: str = "") -> ParseJobUrlResponse:
    now = _now()
    plain = _clean(plain or "")
    sections = _scan_sections(plain)
    hiring = extract_hiring_team(html="", plain=plain)
    role, company = _role_company(plain, html="")
    details = _build_details(sections, hiring)
    warnings = []
    for k, label in (
        ("benefits", "Benefits found in job post"),
        ("requirements_added_by_poster", "Requirements added by the job poster"),
    ):
        if getattr(details, k) == _NA:
            warnings.append(f"Missing section: {label}")
    if not hiring:
        warnings.append("Missing section: Meet the hiring team")

    filled = sum(
        1
        for k in _details_dict({}).keys()
        if getattr(details, k) not in ("", _NA)
    )
    conf = round(min(0.99, 0.25 + filled * 0.09 + (0.15 if hiring else 0)), 2)
    loc = details.location if details.location != _NA else "Remote"

    return ParseJobUrlResponse(
        job_url=job_url or "",
        company=company,
        role_title=role,
        location=loc,
        source=JobSource.linkedin,
        salary_range=_salary(details.compensation),
        notes=_notes(details),
        applied_date=now.date(),
        applied_at=now,
        confidence=conf,
        warnings=warnings,
        linkedin_details=details,
        raw={"mode": "plain", "hiring_count": len(hiring), "filled": filled},
    )


async def parse_job_url(url: str) -> ParseJobUrlResponse:
    url = (url or "").strip()
    if not url:
        raise ValueError("url is required")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    if not _is_linkedin(url):
        raise ValueError(
            "Only LinkedIn job URLs are supported "
            "(https://www.linkedin.com/jobs/view/...)."
        )

    now = _now()
    warnings: list[str] = []
    raw_meta: dict[str, Any] = {}
    html = ""

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=25.0,
            headers={
                "User-Agent": _UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            resp = await client.get(url)
            raw_meta["status_code"] = resp.status_code
            html = resp.text or ""
            if resp.status_code >= 400:
                warnings.append(f"LinkedIn HTTP {resp.status_code}")
    except Exception as exc:
        warnings.append(f"Fetch failed: {exc}")
        html = ""

    desc = _description(html)
    page = _html_to_plain(html)
    plain = max([desc, page], key=_score)

    sections = _scan_sections(plain)
    for k, v in _scan_sections(page).items():
        if v and v != _NA and sections.get(k) in (None, "", _NA):
            sections[k] = v

    hiring = extract_hiring_team(html=html, plain=plain)
    raw_meta["hiring_html_count"] = len(_extract_hiring_from_html(html))
    raw_meta["hiring_plain_count"] = len(_extract_hiring_from_plain(plain))
    raw_meta["hiring_count"] = len(hiring)

    role, company = _role_company(plain, html)
    details = _build_details(sections, hiring)

    for k, label in (
        ("compensation", "Compensation"),
        ("location", "Location"),
        ("primary_responsibilities", "About The Role / Primary Responsibilities"),
        ("candidate_qualifications", "Candidate Qualifications"),
        ("why_join", "Why Join This Opportunity"),
        ("about_company", "About Company"),
        ("benefits", "Benefits found in job post"),
        ("requirements_added_by_poster", "Requirements added by the job poster"),
    ):
        if getattr(details, k) == _NA:
            warnings.append(f"Missing section: {label}")

    if not hiring:
        warnings.append(
            "Missing section: Meet the hiring team "
            "(no /in/ anchors or plain cards found in fetch)."
        )
    if not html:
        warnings.append("Empty HTML from LinkedIn fetch.")

    filled = sum(
        1
        for k in _details_dict({}).keys()
        if getattr(details, k) not in ("", _NA)
    )
    conf = 0.2 + filled * 0.09 + (0.15 if hiring else 0)
    if hiring and any(
        getattr(p, "email", "")
        or getattr(p, "phone", "")
        or "|" in (getattr(p, "headline", "") or getattr(p, "title", "") or "")
        for p in hiring
    ):
        conf += 0.08
    if not html:
        conf = min(conf, 0.35)
    conf = round(min(0.99, conf), 2)

    raw_meta.update(
        {
            "mode": "url",
            "plain_len": len(plain),
            "filled": filled,
            "section_keys": [k for k, v in sections.items() if v],
        }
    )

    loc = details.location if details.location != _NA else "Remote"

    return ParseJobUrlResponse(
        job_url=url,
        company=company,
        role_title=role,
        location=loc,
        source=JobSource.linkedin,
        salary_range=_salary(details.compensation),
        notes=_notes(details),
        applied_date=now.date(),
        applied_at=now,
        confidence=conf,
        warnings=warnings,
        linkedin_details=details,
        raw=raw_meta,
    )