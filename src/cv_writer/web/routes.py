"""Criteria 32-35: every route in the flow named by the spec (posting -> match report -> extra
input -> language/page-count confirmation -> generate -> download), plus the track-record
browser (criterion 33).

**Every handler below is a plain `def`, never `async def`** (ADR 0005 decision 2). This is not
a style preference: `ingestion.pipeline.ingest_from_url()` and `generation.render_pdf.render_pdf()`
both use Playwright's *synchronous* API under the hood, which raises at runtime — "It looks like
you are using Playwright Sync API inside the asyncio loop" — the moment it's called from a
running asyncio event loop. Starlette runs a `def` route in a worker threadpool instead of on
the event loop, which sidesteps that entirely and also keeps the blocking `urllib` fetch (tier 1
ingestion) off the loop. Do not "modernise" these to `async def`; it will break at the first
real URL fetch or PDF render.

No web-framework import reaches past this package (criterion 34) — every domain call below goes
through `profile`/`db`/`ingestion`/`matching`/`generation`, mechanically checked by
tests/unit/web/test_core_has_no_web_imports.py.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

from cv_writer.db import connect, get_application, insert_application, list_applications
from cv_writer.generation.build_application import build_application
from cv_writer.generation.language import detect_posting_language
from cv_writer.generation.models import ExtraInput, ExtraInputKind, GeneratedCv, GenerationFailure
from cv_writer.generation.output_paths import build_output_paths
from cv_writer.generation.page_fit import PageFitResult, fit_to_page_budget
from cv_writer.generation.pdf_inspect import page_count as pdf_page_count
from cv_writer.generation.pipeline import generate_cv
from cv_writer.generation.render_html import render_html
from cv_writer.generation.render_pdf import render_pdf
from cv_writer.generation.render_text import render_markdown
from cv_writer.generation.write_output import write_artifacts
from cv_writer.ingestion.fetch_tier3 import ingest_pasted
from cv_writer.ingestion.models import IngestionFailure
from cv_writer.ingestion.requirements import extract_requirements
from cv_writer.matching.matcher import build_match_report
from cv_writer.matching.models import MatchStatus
from cv_writer.profile.loader import load_profile
from cv_writer.profile.models import Profile

from .drafts import Draft, UnknownDraftError

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Its own Jinja2 Environment, separate from generation/render_html.py's module-level one (ADR
# 0005 decision 5) — that one renders a *print* document for Chromium; this one renders
# *screens*. They share a library, not a purpose. Built explicitly (not via Jinja2Templates'
# own directory= shortcut) because jinja2.select_autoescape()'s default enabled_extensions is
# ("html", "htm", "xml") — a template named "index.html.jinja" ends in ".jinja", which that
# default would silently leave *unescaped*. render_html.py hit this same trap first and already
# fixed it by naming "jinja" explicitly; this environment does the same.
_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(enabled_extensions=("html", "jinja")),
)
templates = Jinja2Templates(env=_env)

_DOWNLOAD_KINDS = {"markdown": "markdown_path", "pdf": "pdf_path", "text": "text_path"}

router = APIRouter()


def _profile(request: Request) -> Profile:
    return load_profile(request.app.state.profile_path)


def _db_connect(request: Request):
    return connect(request.app.state.db_path)


def _get_draft(request: Request, draft_id: str) -> Draft:
    try:
        return request.app.state.draft_store.get(draft_id)
    except UnknownDraftError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


def _narrow_cv(cv: GeneratedCv, source_ids: list[str]) -> GeneratedCv:
    """Rebuild a GeneratedCv containing only the bullets in `source_ids`, in that order — used
    to render the "if we drop to one page" candidate during page-fit measurement, and to build
    the final CV once the human has picked 1 or 2 pages."""
    order = {source_id: index for index, source_id in enumerate(source_ids)}
    bullets = sorted(
        (bullet for bullet in cv.accepted_bullets if bullet.source_id in order),
        key=lambda bullet: order[bullet.source_id],
    )
    return GeneratedCv(
        markdown="\n".join(f"- {bullet.text}" for bullet in bullets),
        language=cv.language,
        variant=cv.variant,
        source_ids_used=[bullet.source_id for bullet in bullets],
        accepted_bullets=bullets,
    )


def _measure_page_count(cv: GeneratedCv, profile: Profile, source_ids: list[str]) -> int:
    """Render a candidate bullet subset to a throwaway temp PDF and measure its real page
    count — the render_and_count callable fit_to_page_budget() needs (criterion 24)."""
    narrowed = _narrow_cv(cv, source_ids)
    html = render_html(
        render_markdown(narrowed, profile), language=narrowed.language, title=profile.identity.name
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = Path(tmp_dir) / "page-fit-measurement.pdf"
        render_pdf(html, pdf_path)
        return pdf_page_count(pdf_path)


@router.get("/")
def new_application_form(request: Request):
    """Criterion 32: paste-or-URL a posting — the URL field and the paste form both live here."""
    return templates.TemplateResponse(request, "index.html.jinja", {})


@router.post("/drafts")
def create_draft_from_url(
    request: Request,
    url: str = Form(...),
    company: str = Form(...),
    country: str = Form(...),
    area: str = Form(...),
    role_title: str = Form(...),
):
    """Tier 1 -> tier 2 via the injected `ingest_url` (criteria 9.1-9.2). On IngestionFailure,
    re-render the same page with `.reason` shown and the paste form offered with what the user
    already typed preserved, per criteria 9.3 and 11 (never a silent empty result)."""
    prefill = {
        "url": url,
        "company": company,
        "country": country,
        "area": area,
        "role_title": role_title,
    }

    result = request.app.state.ingest_url(url)
    if isinstance(result, IngestionFailure):
        return templates.TemplateResponse(
            request,
            "index.html.jinja",
            {"ingestion_error": result.reason, "prefill": prefill},
            status_code=422,
        )

    draft = request.app.state.draft_store.create(
        posting=result, company=company, country=country, area=area, role_title=role_title
    )
    return RedirectResponse(f"/drafts/{draft.id}", status_code=303)


@router.post("/drafts/paste")
def create_draft_from_paste(
    request: Request,
    text: str = Form(...),
    company: str = Form(...),
    country: str = Form(...),
    area: str = Form(...),
    role_title: str = Form(...),
):
    """Criterion 8: the paste fallback. Validated *before* calling ingest_pasted(), per
    fetch_tier3.py's own docstring ("the eventual UI is expected to validate its paste form
    before calling this") — ingest_pasted() itself raises ValueError on bad input, which is the
    right contract for a direct call with caller-controlled arguments, but the wrong thing to
    let leak into a 500 for a UI form."""
    prefill = {
        "text": text,
        "company": company,
        "country": country,
        "area": area,
        "role_title": role_title,
    }
    missing = [
        field_name
        for field_name, value in [
            ("posting text", text),
            ("company", company),
            ("country", country),
            ("area", area),
            ("role title", role_title),
        ]
        if not value.strip()
    ]
    if missing:
        return templates.TemplateResponse(
            request,
            "index.html.jinja",
            {"paste_error": f"missing required field(s): {', '.join(missing)}", "prefill": prefill},
            status_code=422,
        )

    posting = ingest_pasted(text, company=company, role_title=role_title, country=country)
    draft = request.app.state.draft_store.create(
        posting=posting, company=company, country=country, area=area, role_title=role_title
    )
    return RedirectResponse(f"/drafts/{draft.id}", status_code=303)


@router.get("/drafts/{draft_id}")
def show_draft(request: Request, draft_id: str):
    """Criteria 13-15, 20: the match report (score + score_formula), the gap list, the
    extra-input form, and the detected language with an override — all re-derived on every load
    from pure functions (criterion 14), never read back from stored state (ADR 0005 decision 3)."""
    draft = _get_draft(request, draft_id)
    profile = _profile(request)
    match_report = build_match_report(profile, extract_requirements(draft.posting.raw_text))
    detection = detect_posting_language(draft.posting.raw_text)

    return templates.TemplateResponse(
        request,
        "draft.html.jinja",
        {
            "draft": draft,
            "match_report": match_report,
            "gaps": match_report.gaps(),
            "detection": detection,
            "profile_languages": [language.name for language in profile.languages],
        },
    )


@router.post("/drafts/{draft_id}/inputs")
def add_extra_input(
    request: Request,
    draft_id: str,
    kind: str = Form(...),
    text: str = Form(...),
    promote_candidate: bool = Form(False),
):
    """Criterion 17: append one piece of per-application extra input, id assigned `extra-1`,
    `extra-2`, ... in submission order (generation/models.py's own ExtraInput docstring).

    `kind` only ever reaches the fixed `<select>` options in draft.html.jinja in normal use,
    but it arrives as a plain form string, so a hand-crafted request can still send a value
    outside `ExtraInputKind`. `ExtraInputKind(kind)` raises a plain `ValueError` on that —
    caught here and turned into the same "re-render the draft page with the reason" pattern
    `/drafts/{draft_id}/generate` already uses for GenerationFailure, rather than an unhandled
    500 (the same class of bug the review flagged for an unwhitelisted `sort_by`)."""
    draft = _get_draft(request, draft_id)

    try:
        extra_input_kind = ExtraInputKind(kind)
    except ValueError:
        profile = _profile(request)
        match_report = build_match_report(profile, extract_requirements(draft.posting.raw_text))
        detection = detect_posting_language(draft.posting.raw_text)
        return templates.TemplateResponse(
            request,
            "draft.html.jinja",
            {
                "draft": draft,
                "match_report": match_report,
                "gaps": match_report.gaps(),
                "detection": detection,
                "profile_languages": [language.name for language in profile.languages],
                "extra_input_error": f"unknown extra-input kind: {kind!r}",
            },
            status_code=422,
        )

    next_id = f"extra-{len(draft.extra_inputs) + 1}"
    draft.extra_inputs.append(
        ExtraInput(
            id=next_id,
            kind=extra_input_kind,
            text=text,
            promote_candidate=promote_candidate,
        )
    )
    request.app.state.draft_store.update(draft)
    return RedirectResponse(f"/drafts/{draft_id}", status_code=303)


@router.post("/drafts/{draft_id}/generate")
def generate_draft_cv(request: Request, draft_id: str, language_override: str = Form("")):
    """Criteria 17-23: run generate_cv(). On GenerationFailure, re-render the draft page with
    the reason and any validation_failures/pt_pt_violations attached. On success, measure page
    fit (criterion 24) immediately and store both the CV and the fit result on the draft
    (ADR 0005 decision 3), then redirect to the page-count choice."""
    draft = _get_draft(request, draft_id)
    profile = _profile(request)
    match_report = build_match_report(profile, extract_requirements(draft.posting.raw_text))
    override = language_override.strip() or None

    result = generate_cv(
        profile=profile,
        posting=draft.posting,
        match_report=match_report,
        extra_inputs=draft.extra_inputs,
        rephraser=request.app.state.rephraser,
        language_override=override,
    )

    if isinstance(result, GenerationFailure):
        detection = detect_posting_language(draft.posting.raw_text)
        return templates.TemplateResponse(
            request,
            "draft.html.jinja",
            {
                "draft": draft,
                "match_report": match_report,
                "gaps": match_report.gaps(),
                "detection": detection,
                "profile_languages": [language.name for language in profile.languages],
                "generation_failure": result,
            },
            status_code=422,
        )

    ordered_source_ids = result.source_ids_used
    if ordered_source_ids:
        fit_result = fit_to_page_budget(
            ordered_source_ids,
            lambda source_ids: _measure_page_count(result, profile, source_ids),
        )
    else:
        fit_result = PageFitResult(
            fitted_source_ids=[], dropped_source_ids=[], page_count=1, achieved_one_page=True
        )

    draft.generated_cv = result
    draft.page_fit = fit_result
    draft.language_override = override
    request.app.state.draft_store.update(draft)
    return RedirectResponse(f"/drafts/{draft_id}/pages", status_code=303)


@router.get("/drafts/{draft_id}/pages")
def show_page_choice(request: Request, draft_id: str):
    """Criterion 24: propose one page, and when it doesn't fit, show exactly what a one-page
    version would drop — the human picks 1 or 2 (the form here posts straight to
    /drafts/{id}/confirm, which is the only place the choice actually gets committed)."""
    draft = _get_draft(request, draft_id)
    if draft.generated_cv is None or draft.page_fit is None:
        raise HTTPException(status_code=409, detail="generate a CV before choosing a page count")

    bullets_by_id = {
        bullet.source_id: bullet.text for bullet in draft.generated_cv.accepted_bullets
    }
    return templates.TemplateResponse(
        request,
        "pages.html.jinja",
        {"draft": draft, "page_fit": draft.page_fit, "bullets_by_id": bullets_by_id},
    )


@router.post("/drafts/{draft_id}/confirm")
def confirm_application(request: Request, draft_id: str, page_count: int = Form(...)):
    """Write the artifacts, build and persist the Application (criteria 25-29), then redirect
    to the result page. `page_count` is the human's choice (criterion 24) — never recomputed or
    silently overridden here, matching build_application()'s own documented contract."""
    draft = _get_draft(request, draft_id)
    if draft.generated_cv is None or draft.page_fit is None:
        raise HTTPException(status_code=409, detail="generate a CV before confirming")
    if page_count not in (1, 2):
        raise HTTPException(status_code=422, detail="page_count must be 1 or 2")

    chosen_source_ids = (
        draft.page_fit.fitted_source_ids if page_count == 1 else draft.generated_cv.source_ids_used
    )
    final_cv = _narrow_cv(draft.generated_cv, chosen_source_ids)

    profile = _profile(request)
    match_report = build_match_report(profile, extract_requirements(draft.posting.raw_text))
    skills_featured = list(
        dict.fromkeys(
            match.evidence_skill
            for match in match_report.matches
            if match.status == MatchStatus.MATCHED and match.evidence_skill
        )
    )

    application_date = date.today()
    output_paths = build_output_paths(
        application_date,
        draft.company,
        draft.role_title,
        output_dir=Path(request.app.state.output_dir),
    )
    write_artifacts(cv=final_cv, profile=profile, paths=output_paths)

    application = build_application(
        generated_cv=final_cv,
        posting=draft.posting,
        company=draft.company,
        country=draft.country,
        area=draft.area,
        role_title=draft.role_title,
        output_paths=output_paths,
        application_date=application_date,
        match_score=match_report.score,
        page_count=page_count,
        skills_featured=skills_featured,
    )
    application_id = insert_application(_db_connect(request), application)
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.get("/applications")
def show_track_record(
    request: Request,
    company: str | None = None,
    country: str | None = None,
    area: str | None = None,
    skill: str | None = None,
    sort_by: str = "application_date",
    descending: bool = True,
):
    """Criterion 33 (-> criterion 30): filter by company/country/area/skill (combinable) and
    sort by date/company/country/area. `skill` is a filter only, never a sort option — offering
    it as one would just surface list_applications()'s own ValueError as this route's error
    banner instead of an unhandled 500, but the sort control itself must not offer it."""
    try:
        applications = list_applications(
            _db_connect(request),
            company=company or None,
            country=country or None,
            area=area or None,
            skill=skill or None,
            sort_by=sort_by,
            descending=descending,
        )
        sort_error = None
    except ValueError as exc:
        applications = []
        sort_error = str(exc)

    return templates.TemplateResponse(
        request,
        "applications.html.jinja",
        {
            "applications": applications,
            "filters": {
                "company": company or "",
                "country": country or "",
                "area": area or "",
                "skill": skill or "",
                "sort_by": sort_by,
                "descending": descending,
            },
            "sort_error": sort_error,
        },
    )


@router.get("/applications/{application_id}")
def show_application(request: Request, application_id: int):
    """Criterion 32: the result page with the three download links."""
    application = get_application(_db_connect(request), application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="unknown application")

    return templates.TemplateResponse(
        request, "application_detail.html.jinja", {"application": application}
    )


@router.get("/applications/{application_id}/download/{kind}")
def download_artifact(request: Request, application_id: int, kind: str):
    """ADR 0005 decision 7: `kind` is matched against a literal whitelist, never used to build a
    path. The stored path is re-resolved and required to sit inside the resolved output
    directory before it is ever served — company/role names flow into filenames through
    build_output_paths()'s slugging, so this guard is what makes serving them safe *by
    construction*, not by trusting the slug function alone."""
    path_field = _DOWNLOAD_KINDS.get(kind)
    if path_field is None:
        raise HTTPException(status_code=404, detail="unknown artifact kind")

    application = get_application(_db_connect(request), application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="unknown application")

    stored_path = getattr(application, path_field)
    if not stored_path:
        raise HTTPException(status_code=404, detail="no artifact of that kind for this application")

    output_dir = Path(request.app.state.output_dir).resolve()
    candidate = Path(stored_path).resolve()
    if candidate != output_dir and output_dir not in candidate.parents:
        raise HTTPException(status_code=404, detail="artifact path is outside the output directory")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="artifact file does not exist")

    return FileResponse(candidate)
