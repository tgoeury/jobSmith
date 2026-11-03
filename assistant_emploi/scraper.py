"""Téléchargement de la copie locale d'une annonce.

Best-effort, en deux temps :

1. requête HTTP simple (rapide) ;
2. si la page obtenue ne semble pas contenir l'annonce (site en JavaScript, mur de
   cookies, blocage HTTP 403…), rendu dans un Chromium headless (Playwright, optionnel)
   avec acceptation automatique du bandeau de cookies.

Le contenu est ensuite évalué : une page qui ne contient manifestement pas l'annonce
n'est plus enregistrée comme un succès silencieux. Quand la page embarque des données
structurées schema.org `JobPosting` (JSON-LD, très répandu sur les job-boards), elles
servent de repli pour produire une copie lisible.

Aucune fonction de ce module ne lève d'exception : le résultat porte un statut
('ok', 'partial', 'failed') et une note lisible expliquant l'échec éventuel.
"""
from __future__ import annotations

import html as html_lib
import json
import re
import unicodedata
from html.parser import HTMLParser
from typing import NamedTuple
from urllib.parse import urlparse

import requests

from .config import ANNONCES_DIR, CONFIG


class AnnonceResult(NamedTuple):
    status: str            # 'ok', 'partial' (copie douteuse) ou 'failed'
    path: str | None       # chemin relatif dans data/annonces/
    note: str              # explication lisible (affichée dans l'interface)


class _Page(NamedTuple):
    html: str
    url: str               # URL finale (après redirections)
    http_status: int | None
    via: str               # 'http' ou 'navigateur'


def is_http_url(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = urlparse(value.strip())
    except (ValueError, AttributeError):
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _inject_base_tag(html: str, url: str) -> str:
    """Injecte une balise <base> pour que CSS/images relatifs pointent vers l'origine."""
    base_tag = f'<base href="{html_lib.escape(url, quote=True)}">'
    lower = html.lower()
    idx = lower.find("<head")
    if idx != -1:
        end = lower.find(">", idx)
        if end != -1:
            return html[: end + 1] + base_tag + html[end + 1 :]
    # Pas de <head> : on préfixe.
    return base_tag + html


# ---------------------------------------------------------------------------
# Analyse du HTML
# ---------------------------------------------------------------------------

_HIDDEN_TAGS = {"script", "style", "noscript", "template", "svg", "head"}


class _PageParser(HTMLParser):
    """Extrait le texte visible et les blocs JSON-LD d'une page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self._in_ld_json = False
        self._ld_buffer: list[str] = []
        self.text_parts: list[str] = []
        self.ld_blocks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self._hidden_depth = 0  # filet de sécurité : </head> parfois absent
        if tag in _HIDDEN_TAGS:
            self._hidden_depth += 1
        if tag == "script":
            kind = (dict(attrs).get("type") or "").lower()
            self._in_ld_json = kind == "application/ld+json"
            self._ld_buffer = []

    def handle_endtag(self, tag):
        if tag in _HIDDEN_TAGS:
            self._hidden_depth = max(0, self._hidden_depth - 1)
        if tag == "script" and self._in_ld_json:
            self.ld_blocks.append("".join(self._ld_buffer))
            self._in_ld_json = False

    def handle_data(self, data):
        if self._in_ld_json:
            self._ld_buffer.append(data)
        elif not self._hidden_depth:
            self.text_parts.append(data)


def _parse(html: str) -> _PageParser:
    parser = _PageParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 - HTML arbitraire : on garde ce qui a été lu
        pass
    return parser


def _visible_text(parser: _PageParser) -> str:
    return re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()


def _iter_ld_objects(node):
    """Parcourt récursivement un JSON-LD (listes, @graph) et produit chaque objet."""
    if isinstance(node, list):
        for item in node:
            yield from _iter_ld_objects(item)
    elif isinstance(node, dict):
        yield node
        if "@graph" in node:
            yield from _iter_ld_objects(node["@graph"])


def _find_job_posting(parser: _PageParser) -> dict | None:
    """Renvoie le premier objet schema.org JobPosting avec une description, ou None."""
    for block in parser.ld_blocks:
        try:
            data = json.loads(block.strip(), strict=False)
        except ValueError:
            continue
        for obj in _iter_ld_objects(data):
            kind = obj.get("@type")
            kinds = kind if isinstance(kind, list) else [kind]
            if "JobPosting" in kinds and obj.get("description"):
                return obj
    return None


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _title_found(title: str | None, text: str) -> bool:
    """True si l'essentiel des mots de l'intitulé saisi figure dans le texte de la page."""
    if not title:
        return False
    words = {w for w in re.findall(r"[a-z0-9]{3,}", _normalize(title))}
    if not words:
        return False
    page_words = set(re.findall(r"[a-z0-9]{3,}", _normalize(text)))
    return len(words & page_words) / len(words) >= 0.6


# Indices d'une page qui ne contient pas l'annonce elle-même.
_JS_REQUIRED = re.compile(
    r"enable javascript|activer (le )?javascript|javascript (is|est) (required|requis|"
    r"n[ée]cessaire|d[ée]sactiv[ée])|please enable js|javascript must be enabled",
    re.I,
)
_BLOCKED = re.compile(
    r"just a moment|attention required|access denied|acc[eè]s refus[ée]|"
    r"verify you are (a )?human|v[ée]rifi\w* que vous (n'[eê]tes pas un robot|[eê]tes humain)|"
    r"captcha|are you a robot",
    re.I,
)

# Seuils (en caractères de texte visible).
_MIN_TEXT = 500        # en dessous : page vide
_GOOD_TEXT = 1500      # au-dessus : contenu substantiel


def _assess(page: _Page, title: str | None) -> tuple[str, str, dict | None, int]:
    """Évalue une page : (qualité, raison, JobPosting éventuel, longueur du texte).

    Qualité : 'good' (annonce présente), 'doubtful' (contenu présent mais l'annonce
    n'est pas reconnue) ou 'empty' (page vide, bloquée ou nécessitant JavaScript).
    """
    parser = _parse(page.html)
    text = _visible_text(parser)
    job = _find_job_posting(parser)
    size = len(text)

    if job:
        return "good", "", job, size
    if page.http_status in (401, 403, 429, 503) or (_BLOCKED.search(text) and size < 3000):
        return "empty", "accès bloqué par le site (protection anti-robot)", None, size
    if _JS_REQUIRED.search(text) and size < 3000:
        return "empty", "le site exige JavaScript", None, size
    if size < _MIN_TEXT:
        return "empty", "page vide (contenu chargé en JavaScript ?)", None, size
    if _title_found(title, text):
        return "good", "", None, size
    if not title and size >= _GOOD_TEXT:
        return "good", "", None, size
    return "doubtful", "l'intitulé du poste n'apparaît pas dans la page", None, size


_RANK = {"good": 2, "doubtful": 1, "empty": 0}


# ---------------------------------------------------------------------------
# Récupération : HTTP simple puis navigateur headless
# ---------------------------------------------------------------------------

def _fetch_http(url: str) -> tuple[_Page | None, str]:
    scraper_cfg = CONFIG.get("scraper", {})
    headers = {
        "User-Agent": scraper_cfg.get("user_agent", "Mozilla/5.0"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }
    timeout = scraper_cfg.get("timeout_seconds", 20)
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return None, f"échec de la connexion ({type(exc).__name__})"

    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and "html" not in content_type:
        # Contenu non-HTML (PDF, etc.) : page enveloppe avec un lien.
        wrapper = (
            f'<!doctype html><meta charset="utf-8"><title>Annonce</title>'
            f'<p>Contenu non-HTML ({html_lib.escape(content_type)}). '
            f'<a href="{html_lib.escape(url, quote=True)}">Ouvrir l\'annonce '
            f"d'origine</a></p>"
        )
        return _Page(wrapper, response.url, response.status_code, "http"), ""

    if "charset" not in content_type:
        # Sans charset déclaré, requests suppose ISO-8859-1 : on devine plutôt.
        response.encoding = response.apparent_encoding or "utf-8"
    return _Page(response.text, response.url, response.status_code, "http"), ""


# Boutons « Tout accepter » des gestionnaires de consentement les plus courants.
_CONSENT_SELECTORS = [
    "#didomi-notice-agree-button",
    "#onetrust-accept-btn-handler",
    "#axeptio_btn_acceptAll",
    "#tarteaucitronPersonalize2",
    "#tarteaucitronAllAllowed",
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    "#CybotCookiebotDialogBodyButtonAccept",
    "button[data-testid='uc-accept-all-button']",
    "#hw-cc-consent-modal-accept-btn",
    ".fc-cta-consent",
    "button[mode='primary']",  # Sourcepoint
]
_CONSENT_TEXT = re.compile(
    r"^\s*(tout accepter|accepter tout|tout autoriser|accepter et (fermer|continuer)|"
    r"accepter les cookies|j'accepte|accepter|accept all( cookies)?|allow all( cookies)?|"
    r"accept( cookies)?|i agree|agree|ok)\s*$",
    re.I,
)
# Restes de bandeaux de consentement à retirer du DOM avant la capture.
_CONSENT_LEFTOVERS_JS = """() => {
  const sel = '#didomi-host, .didomi-popup-backdrop, #onetrust-consent-sdk, #axeptio_overlay,'
    + ' #tarteaucitronRoot, #CybotCookiebotDialog, #usercentrics-root, #appconsent,'
    + ' [id^="sp_message_container"], .fc-consent-root, #hw-cc-consent-modal';
  document.querySelectorAll(sel).forEach(e => e.remove());
  for (const el of [document.documentElement, document.body]) {
    if (el) { el.style.overflow = 'auto'; el.style.position = ''; }
  }
}"""
# Retire les scripts exécutables : la capture doit rester figée (pas de re-rendu, ni
# de bandeau de cookies qui réapparaît). Les blocs JSON-LD sont conservés.
_SCRIPT_RE = re.compile(r"<script\b(?![^>]*application/ld\+json)[^>]*>.*?</script\s*>",
                        re.I | re.S)
# Servies depuis l'origine de l'application, les feuilles de style marquées
# `crossorigin`/`integrity` seraient refusées par le CDN (CORS) : page sans style.
_LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
_CORS_ATTR_RE = re.compile(r"\s(?:crossorigin|integrity)(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?",
                           re.I)


def _freeze(html: str) -> str:
    """Prépare une capture pour l'affichage local : sans scripts, styles chargeables."""
    html = _SCRIPT_RE.sub("", html)
    return _LINK_RE.sub(lambda m: _CORS_ATTR_RE.sub("", m.group(0)), html)


def _settle(page, timeout_ms: int) -> None:
    """Attend que le réseau se calme (sans échouer si le site ne se calme jamais)."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:  # noqa: BLE001 - délai dépassé : on prend la page en l'état
        pass
    page.wait_for_timeout(500)


def _click_first_visible(locator) -> bool:
    try:
        target = locator.first
        if target.is_visible(timeout=300):
            target.click(timeout=2000)
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _accept_cookies(page) -> bool:
    """Clique sur « Tout accepter » dans la page ou l'une de ses iframes."""
    for frame in page.frames:
        for selector in _CONSENT_SELECTORS:
            if _click_first_visible(frame.locator(selector)):
                return True
        if _click_first_visible(frame.get_by_role("button", name=_CONSENT_TEXT)):
            return True
    return False


def _fetch_browser(url: str) -> tuple[_Page | None, str]:
    scraper_cfg = CONFIG.get("scraper", {})
    if not scraper_cfg.get("browser_fallback", True):
        return None, "rendu navigateur désactivé"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "rendu navigateur indisponible (Playwright non installé)"

    timeout_ms = int(scraper_cfg.get("browser_timeout_seconds", 30) * 1000)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                # UA d'un Chrome classique (celui par défaut annonce « HeadlessChrome »).
                user_agent = (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    f"(KHTML, like Gecko) Chrome/{browser.version} Safari/537.36"
                )
                context = browser.new_context(
                    user_agent=user_agent,
                    locale="fr-FR",
                    viewport={"width": 1366, "height": 900},
                )
                page = context.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                _settle(page, 8000)
                if _accept_cookies(page):
                    _settle(page, 5000)
                page.evaluate(_CONSENT_LEFTOVERS_JS)
                html = page.content()
                return _Page(html, page.url, response.status if response else None,
                             "navigateur"), ""
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001 - navigateur absent, délai dépassé…
        first_line = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
        return None, f"échec du rendu navigateur ({first_line[:120] or type(exc).__name__})"


# ---------------------------------------------------------------------------
# Copie de repli à partir des données structurées JobPosting
# ---------------------------------------------------------------------------

_UNSAFE_HTML_RE = re.compile(
    r"<(script|style|iframe|object|embed)\b.*?(</\1\s*>|$)|\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|\S+)",
    re.I | re.S,
)


def _ld_text(value) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("@value") or "")
    if isinstance(value, list):
        return ", ".join(t for t in (_ld_text(v) for v in value) if t)
    return str(value or "")


def _ld_location(job: dict) -> str:
    places = job.get("jobLocation") or []
    places = places if isinstance(places, list) else [places]
    labels = []
    for place in places:
        address = place.get("address", {}) if isinstance(place, dict) else {}
        if isinstance(address, str):
            labels.append(address)
            continue
        parts = [address.get("addressLocality"), address.get("postalCode"),
                 address.get("addressRegion")]
        label = " ".join(_ld_text(p) for p in parts if p)
        if label:
            labels.append(label)
    if job.get("jobLocationType") == "TELECOMMUTE":
        labels.append("Télétravail")
    return " · ".join(dict.fromkeys(labels))


def _ld_salary(job: dict) -> str:
    salary = job.get("baseSalary")
    if not isinstance(salary, dict):
        return _ld_text(salary)
    value = salary.get("value", {})
    currency = salary.get("currency", "")
    if isinstance(value, dict):
        low, high = value.get("minValue"), value.get("maxValue")
        amount = f"{low} – {high}" if low and high else str(low or high or value.get("value") or "")
        unit = value.get("unitText", "")
    else:
        amount, unit = str(value or ""), ""
    return " ".join(p for p in (amount, currency, f"/ {unit.lower()}" if unit else "") if p)


def _job_posting_page(job: dict, url: str) -> str:
    """Page HTML autonome et lisible construite à partir d'un JobPosting."""
    esc = html_lib.escape
    description = str(job.get("description") or "")
    if "<" not in description and "&lt;" in description:
        description = html_lib.unescape(description)  # HTML échappé deux fois
    if "<" not in description:
        description = f'<div style="white-space:pre-wrap">{esc(description)}</div>'
    description = _UNSAFE_HTML_RE.sub("", description)

    facts = [
        ("Entreprise", _ld_text(job.get("hiringOrganization"))),
        ("Lieu", _ld_location(job)),
        ("Contrat", _ld_text(job.get("employmentType"))),
        ("Salaire", _ld_salary(job)),
        ("Publiée le", _ld_text(job.get("datePosted"))[:10]),
        ("Valable jusqu'au", _ld_text(job.get("validThrough"))[:10]),
    ]
    facts_html = "".join(
        f"<li><strong>{esc(label)} :</strong> {esc(value)}</li>"
        for label, value in facts if value
    )
    title = esc(_ld_text(job.get("title")) or "Annonce")
    return (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        f"<title>{title}</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;"
        "padding:0 1rem;line-height:1.55;color:#222}"
        ".src{color:#777;font-size:.85rem}ul.facts{padding-left:1.1rem}</style></head><body>"
        f'<p class="src">Copie reconstruite à partir des données structurées de '
        f'<a href="{esc(url, quote=True)}">l\'annonce d\'origine</a>.</p>'
        f"<h1>{title}</h1><ul class=\"facts\">{facts_html}</ul><hr>{description}"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def _write(app_id: int, html: str) -> str:
    filename = f"{app_id}.html"
    (ANNONCES_DIR / filename).write_text(html, encoding="utf-8", errors="replace")
    return filename


def download_annonce(url: str, app_id: int, title: str | None = None) -> AnnonceResult:
    """Télécharge `url` et l'enregistre dans data/annonces/<app_id>.html.

    `title` (intitulé saisi) sert à vérifier que la page contient bien l'annonce.
    """
    if not is_http_url(url):
        return AnnonceResult("failed", None, "URL non téléchargeable")

    candidates: list[tuple[_Page, tuple]] = []
    errors: list[str] = []

    page, error = _fetch_http(url)
    if page is not None:
        if page.http_status in (404, 410):
            return AnnonceResult(
                "failed", None, f"annonce introuvable ou expirée (HTTP {page.http_status})"
            )
        candidates.append((page, _assess(page, title)))
    else:
        errors.append(error)

    if not candidates or candidates[0][1][0] != "good":
        page, error = _fetch_browser(url)
        if page is not None:
            candidates.append((page, _assess(page, title)))
        else:
            errors.append(error)

    if not candidates:
        return AnnonceResult("failed", None, " ; ".join(errors))

    # Meilleure capture : qualité d'abord, puis quantité de texte.
    best, (quality, reason, _job, size) = max(
        candidates, key=lambda c: (_RANK[c[1][0]], c[1][3])
    )
    job = next((c[1][2] for c in candidates if c[1][2]), None)

    if quality == "empty" and not job:
        return AnnonceResult("failed", None, reason)

    if job and size < _GOOD_TEXT:
        # Page quasi vide mais données structurées présentes : copie reconstruite.
        html = _job_posting_page(job, best.url)
        status, note = "ok", "copie reconstruite (données structurées de l'annonce)"
    else:
        html = _inject_base_tag(_freeze(best.html), best.url)
        status = "ok" if quality == "good" else "partial"
        note = f"copie via {best.via}" if status == "ok" else f"copie douteuse : {reason}"

    try:
        path = _write(app_id, html)
    except OSError as exc:
        return AnnonceResult("failed", None, f"écriture impossible : {exc}")
    return AnnonceResult(status, path, note)


def save_manual_annonce(app_id: int, text: str, url: str | None = None) -> AnnonceResult:
    """Enregistre comme copie locale un texte d'annonce collé à la main."""
    esc = html_lib.escape
    source = (
        f'<p class="src">Source : <a href="{esc(url, quote=True)}">{esc(url)}</a></p>'
        if is_http_url(url) else ""
    )
    html = (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Annonce</title>'
        "<style>body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;"
        "padding:0 1rem;line-height:1.55;color:#222}.src{color:#777;font-size:.85rem}"
        "</style></head><body>"
        f'{source}<div style="white-space:pre-wrap">{esc(text.strip())}</div></body></html>'
    )
    try:
        path = _write(app_id, html)
    except OSError as exc:
        return AnnonceResult("failed", None, f"écriture impossible : {exc}")
    return AnnonceResult("ok", path, "copie saisie manuellement")
