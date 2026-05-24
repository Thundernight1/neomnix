"""
Remediation AI — mevcut Ollama servisine bağlanır.
AWS yok. Redis cache var (mevcut).
"""
from __future__ import annotations
import hashlib, json, os, logging
import httpx

log = logging.getLogger(__name__)
OLLAMA_BASE = os.getenv("LLM_API_BASE", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("LLM_MODEL", "llama3")
REDIS_TTL = int(os.getenv("REMEDIATION_CACHE_TTL", "86400"))


def _cache_key(ucl_id, framework):
    raw = f"remediation:{ucl_id}:{framework}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _build_prompt(ucl_id, title, description, frameworks, citations):
    citation_lines = "\n".join(
        f"  {fw.upper()}: {', '.join(cits)}" for fw, cits in citations.items()
    )
    return f"""You are a senior GRC consultant specializing in HIPAA, SOC2, NIST 800-53 and Washington MHMDA.

Gap detected:
  Control ID: {ucl_id}
  Title: {title}
  Description: {description}
  Frameworks: {', '.join(fw.upper() for fw in frameworks)}
  Legal refs:
{citation_lines}

Respond with JSON only:
{{
  "why_critical": "<one sentence>",
  "fix_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "estimated_days": <integer>,
  "evidence_needed": "<document name>",
  "grant_impact": "<SBIR/FedRAMP impact>"
}}"""


def get_recommendation(ucl_id, title, description, frameworks, citations, redis_client=None):
    cache_key = _cache_key(ucl_id, "-".join(sorted(frameworks)))
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            log.warning("Redis read failed: %s", e)

    prompt = _build_prompt(ucl_id, title, description, frameworks, citations)
    try:
        resp = httpx.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"},
            timeout=120.0
        )
        resp.raise_for_status()
        result = json.loads(resp.json().get("response", "{}"))
    except Exception as e:
        log.error("Ollama failed for %s: %s", ucl_id, e)
        result = {
            "why_critical": "Ollama servisi erişilemiyor. docker compose ps ile kontrol et.",
            "fix_steps": ["Ollama container'ının çalıştığını doğrula"],
            "estimated_days": 0,
            "evidence_needed": "N/A",
            "grant_impact": "N/A",
        }

    if redis_client:
        try:
            redis_client.setex(cache_key, REDIS_TTL, json.dumps(result))
        except Exception as e:
            log.warning("Redis write failed: %s", e)

    return result
