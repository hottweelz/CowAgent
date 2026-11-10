"""Normalization and deterministic selection for personal news articles.

Remote article fields are untrusted data. This module only extracts and ranks
text; it does not interpret article text as instructions.

Relevance uses bounded owner-phrase token matching against headline and body
text. It can miss synonyms and does not prove semantic relevance; callers can
inspect each selected record's preference_evidence fields.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit


_TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
_STOP_WORDS = set(
    (
        "a an and are as at be been being by for from had has have he her hers him his i in into is it its of on or "
        "our "
        "she that the their them they this to was were will with would you your about after against all also am any "
        "article bank company crypto during firm first news new not over report said says shares source than then "
        "today "
        "up us we which who why year"
    ).split()
)
_WORD_RE = re.compile(r"[a-z0-9]+(?:['’][a-z0-9]+)?", re.I)
_TAG_RE = re.compile(r"<[^>]*>")
_MAX_TEXT = 20_000


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self.hidden += 1
        elif tag.lower() in {"p", "div", "br", "li", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self.hidden:
            self.hidden -= 1
        elif tag.lower() in {"p", "div", "br", "li", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _plain_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    text = str(value)[:_MAX_TEXT]
    parser = _TextExtractor()
    try:
        parser.feed(text)
        parser.close()
        clean = " ".join("".join(parser.parts).split())
    except Exception:
        clean = " ".join(_TAG_RE.sub(" ", html.unescape(text)).split())
    return clean[:_MAX_TEXT]


def _scalar(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return _plain_text(value) or None
    value = str(value).strip()
    return value or None


def _boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().casefold() in {"true", "1", "yes"}
    return False


def _safe_url(value: object) -> str | None:
    raw = _scalar(value)
    if not raw or len(raw) > 4096:
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        host = parsed.hostname.lower().rstrip(".")
        port = parsed.port
        if port and not (
            (parsed.scheme.lower() == "http" and port == 80) or (parsed.scheme.lower() == "https" and port == 443)
        ):
            netloc = f"{host}:{port}"
        else:
            netloc = host
        query = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
        ]
        return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", urlencode(query, doseq=True), ""))
    except (ValueError, UnicodeError):
        return None


def _timestamp(value: object) -> tuple[str | None, str | None]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            epoch = float(value)
            if abs(epoch) > 100_000_000_000:
                epoch /= 1000
            parsed = datetime.fromtimestamp(epoch, timezone.utc)
            return parsed.isoformat(timespec="seconds").replace("+00:00", "Z"), None
        except (ValueError, OverflowError, OSError):
            return None, str(value)[:256]
    raw = _scalar(value)
    if not raw:
        return None, None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), None
    except (ValueError, OverflowError):
        return None, raw[:256]


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:24]


def _identity_aliases(publisher: str | None, source_ids: list[str], source_url: str | None) -> list[str]:
    aliases: set[str] = set()
    publisher_key = (publisher or "").casefold().strip()
    for source_id in source_ids:
        aliases.add("src:" + _stable_id(f"{publisher_key}\0{source_id.casefold().strip()}"))
    if source_url:
        aliases.add("url:" + _stable_id(f"{publisher_key}\0{source_url}"))
    return sorted(aliases)


def normalize_articles(payload: object, fetched_at: object = None) -> list[dict]:
    """Return normalized articles from a documented API response shape.

    Accept a direct article array or the documented ``articles``/``data``
    wrappers. A valid empty array returns ``[]``; malformed top-level shapes
    raise ``ValueError`` so callers can distinguish errors from no results.
    """
    if isinstance(payload, dict):
        if isinstance(payload.get("articles"), list):
            payload = payload["articles"]
        elif isinstance(payload.get("data"), list):
            payload = payload["data"]
        else:
            raise ValueError("article response must be an array or contain an articles/data array")
    if not isinstance(payload, list):
        raise ValueError("article response must be an array")
    now, bad_now = _timestamp(fetched_at)
    if now is None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    normalized: list[dict] = []
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            raise ValueError(f"article at index {index} must be an object")
        issues: list[str] = []
        provenance: dict = {"source_fields": sorted(str(key)[:80] for key in raw.keys())[:100]}
        if bad_now:
            provenance["invalid_fetched_at"] = bad_now
        title = _plain_text(raw.get("title", raw.get("headline")))
        description = _plain_text(raw.get("description"))
        content = _plain_text(raw.get("content"))
        publisher = _scalar(raw.get("provider", raw.get("publisher")))
        link_value = raw.get("link", raw.get("url", raw.get("source_url")))
        link_url = _safe_url(link_value)
        guid_url = _safe_url(raw.get("guid"))
        source_url = link_url or guid_url
        if link_value and not link_url:
            issues.append("unsafe_or_invalid_source_url")
        source_ids = []
        for key in ("id", "guid", "sourceId", "source_id"):
            item = _scalar(raw.get(key))
            if item and item not in source_ids:
                source_ids.append(item[:256])
        source_id = next(
            (_scalar(raw.get(key)) for key in ("id", "guid", "sourceId", "source_id") if _scalar(raw.get(key))), None
        )
        aliases = _identity_aliases(publisher, source_ids, source_url)
        provenance["source_identifiers"] = {
            key: _scalar(raw.get(key))[:256]
            for key in ("id", "guid", "sourceId", "source_id", "feedId")
            if _scalar(raw.get(key)) is not None
        }
        canonical = (
            f"src:{(publisher or '').casefold()}:{source_id.casefold()}"
            if source_id
            else f"url:{(publisher or '').casefold()}:{source_url}"
            if source_url
            else f"text:{(publisher or '').casefold()}:{title.casefold()}:{_plain_text(raw.get('pubDate')).casefold()}"
        )
        pub_date, invalid_pub = _timestamp(raw.get("pubDate", raw.get("published_at")))
        original_pub_date, invalid_original = _timestamp(raw.get("originalPubDate", raw.get("original_pub_date")))
        article_fetched_at, invalid_article_fetched = _timestamp(raw.get("fetchedAt"))
        updated_at, invalid_updated = _timestamp(raw.get("updatedAt", raw.get("updated_at")))
        for name, value in (
            ("pubDate", invalid_pub),
            ("originalPubDate", invalid_original),
            ("fetchedAt", invalid_article_fetched),
            ("updatedAt", invalid_updated),
        ):
            if value:
                provenance.setdefault("invalid_timestamps", {})[name] = value
                issues.append(f"invalid_{name}")
        topics = raw.get("topics")
        if topics is None:
            normalized_topics = []
        elif isinstance(topics, list):
            normalized_topics = topics
        else:
            normalized_topics = [topics]
            issues.append("topics_metadata_wrapped")
        normalized.append(
            {
                "article_id": _stable_id(canonical),
                "source_id": source_id,
                "source_url": source_url,
                "publisher": publisher,
                "headline": title,
                "description": description,
                "content": content,
                "pub_date": pub_date,
                "original_pub_date": original_pub_date,
                "fetched_at": article_fetched_at or now,
                "updated_at": updated_at,
                "category": raw.get("category"),
                "region": raw.get("region"),
                "sentiment": raw.get("sentiment"),
                "is_top_ranked": raw.get("isTopRanked", raw.get("is_top_ranked")),
                "topics": normalized_topics,
                "was_updated": _boolean(raw.get("wasUpdated", raw.get("was_updated", False))),
                "alias_ids": aliases,
                "provenance": provenance,
                "issues": issues,
            }
        )
    return normalized


def _terms(value: object) -> set[str]:
    return {
        word.casefold().replace("’", "'")
        for word in _WORD_RE.findall(_plain_text(value))
        if word.casefold() not in _STOP_WORDS and len(word) > 1
    }


def _preference_phrases(preferences: object) -> list[str]:
    values: list[object] = []
    if isinstance(preferences, dict):
        for key in ("topics", "interests", "keywords", "preferences"):
            if key in preferences:
                values.append(preferences[key])
        if not values:
            values.extend(preferences.values())
    else:
        values.append(preferences)

    phrases: set[str] = set()

    def add(value: object) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, bool) and child:
                    add(key)
                add(child)
        elif isinstance(value, (list, tuple, set)):
            for child in value:
                add(child)
        else:
            text = _plain_text(value).strip()
            if text and _terms(text):
                phrases.add(text)

    for value in values:
        add(value)
    return sorted(phrases, key=lambda phrase: (phrase.casefold(), phrase))


def _article_terms(article: dict) -> set[str]:
    values = [
        article.get("headline"),
        article.get("description"),
        article.get("content"),
        article.get("category"),
        article.get("topics"),
    ]
    return _terms(" ".join(_plain_text(value) for value in values if value is not None))


def _preference_evidence(article: dict, phrase: str) -> dict | None:
    evidence_fields = {
        key: _terms(article.get(key)) for key in ("headline", "description", "content") if article.get(key)
    }
    evidence_tokens = set().union(*evidence_fields.values()) if evidence_fields else set()
    phrase_tokens = _terms(phrase)
    if not phrase_tokens:
        return None
    if len(phrase_tokens) == 1:
        token = next(iter(phrase_tokens))
        if token not in evidence_tokens:
            return None
        matched = {token}
    else:
        matched = phrase_tokens & evidence_tokens
        minimum = max(2, (len(phrase_tokens) + 1) // 2)
        if len(matched) < minimum:
            return None
    matched_fields = sorted(key for key, tokens in evidence_fields.items() if tokens & matched)
    return {"preference": phrase, "matched_tokens": sorted(matched), "evidence_fields": matched_fields}


def _event_terms(article: dict) -> set[str]:
    return _terms(" ".join(str(article.get(key) or "") for key in ("headline", "description", "content")))


def _numbers(article: dict) -> set[str]:
    return set(
        re.findall(
            r"\b\d+(?:\.\d+)?\s?(?:%|bn|billion|million|m|b)?\b",
            " ".join(str(article.get(key) or "") for key in ("headline", "description", "content")),
            re.I,
        )
    )


def _event_match(left: dict, right: dict) -> bool:
    lt, rt = _terms(left.get("headline")), _terms(right.get("headline"))
    if len(lt & rt) < 2:
        return False
    ln, rn = _numbers(left), _numbers(right)
    if ln and rn and not (ln & rn):
        return False
    title_similarity = len(lt & rt) / max(1, len(lt | rt))
    if title_similarity >= 0.62:
        return True
    lc, rc = _event_terms(left), _event_terms(right)
    body_similarity = len(lc & rc) / max(1, len(lc | rc))
    return title_similarity >= 0.38 and body_similarity >= 0.55


def _same_article(left: dict, right: dict) -> bool:
    if left.get("article_id") and left.get("article_id") == right.get("article_id"):
        return True
    return bool(set(left.get("alias_ids") or []).intersection(right.get("alias_ids") or []))


def _body_numbers(article: dict) -> set[str]:
    body = " ".join(str(article.get(key) or "") for key in ("description", "content"))
    tokens = re.findall(
        r"(?<![\w])(?:\$|€|£)?\d+(?:,\d{3})*(?:\.\d+)?\s?(?:%|bn|billion|million|thousand|m|b|k)?\b",
        body,
        re.I,
    )
    return {
        re.sub(r"\s+", "", token.casefold()).replace(",", "")
        for token in tokens
        if not re.fullmatch(r"20\d{2}", token.strip())
    }


def _materially_new(current: dict, prior: dict) -> bool:
    old_text = " ".join(str(prior.get(key) or "") for key in ("description", "content"))
    new_texts = [str(current.get(key) or "") for key in ("description", "content")]
    old = _terms(old_text)
    new = _terms(" ".join(new_texts))
    if not new:
        return False
    if not old:
        return len(new) >= 4
    added = new - old
    old_numbers, new_numbers = _body_numbers(prior), _body_numbers(current)
    if old_numbers != new_numbers and len(old & new) >= 2:
        return True
    # Assess new propositions locally so an article's unchanged body length does
    # not dilute a substantive added sentence to an insignificant percentage.
    for text in new_texts:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+|;\s+", text) if part.strip()]
        for width in (1, 2):
            for start in range(max(0, len(sentences) - width + 1)):
                local_terms = _terms(" ".join(sentences[start : start + width]))
                local_additions = local_terms - old
                if len(local_additions) >= 4 and len(local_additions) / max(1, len(local_terms)) >= 0.20:
                    return True
    # A changed numeric claim with shared subject context can be material even
    # when the changed number contributes only one new token. Ignore bare years.
    # A small wording change or publisher metadata is not a substantive update.
    return len(added) >= 4 and len(added) / max(1, len(new)) >= 0.15


def _representative_key(article: dict) -> tuple:
    body = " ".join(str(article.get(key) or "") for key in ("description", "content"))
    return (
        len(_terms(body)),
        str(article.get("pub_date") or ""),
        body.casefold(),
        str(article.get("headline") or "").casefold(),
        str(article.get("article_id") or ""),
    )


def _date_sort_key(value: object) -> float:
    normalized, _ = _timestamp(value)
    if not normalized:
        return 0.0
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return 0.0


def _followup_matches(article: dict, followups: object) -> bool:
    if isinstance(followups, (str, dict)) or followups is None:
        followups = [followups] if followups is not None else []
    for item in followups:
        if isinstance(item, dict):
            ids = {str(item.get(key)) for key in ("article_id", "source_id", "id") if item.get(key) is not None}
            ids.update(str(value) for value in (item.get("article_ids") or []) if value is not None)
            article_aliases = set(article.get("alias_ids") or [])
            if article.get("article_id") in ids or article.get("source_id") in ids or article_aliases.intersection(ids):
                return True
            item = " ".join(str(item.get(k, "")) for k in ("topic", "query", "text", "headline"))
        if _terms(item) & _article_terms(article):
            return True
    return False


def rank_and_select(
    articles: list[dict], preferences: object, coverage: object, followups: object = (), limit: int = 5
) -> dict:
    """Filter, rank and conservatively cluster articles against owner intent."""
    if isinstance(coverage, dict):
        coverage = coverage.get("articles", coverage.get("coverage", []))
    coverage_rows = [row for row in (coverage or []) if isinstance(row, dict)]
    preference_phrases = _preference_phrases(preferences)
    ranked: list[tuple[int, dict]] = []
    irrelevant = 0
    unsourced = 0
    for article in articles:
        evidence = [
            match for phrase in preference_phrases if (match := _preference_evidence(article, phrase)) is not None
        ]
        if not evidence:
            irrelevant += 1
            continue
        if not article.get("source_url") or not article.get("publisher") or not article.get("headline", "").strip():
            unsourced += 1
            continue
        matched_preferences = [match["preference"] for match in evidence]
        matched_tokens = sorted({token for match in evidence for token in match["matched_tokens"]})
        score = len(evidence) * 10 + min(3, len(matched_tokens))
        follow_up = _followup_matches(article, followups)
        if follow_up:
            score += 5
        ranked.append(
            (
                score,
                {
                    **article,
                    "matched_preferences": matched_preferences,
                    "matched_preference_tokens": matched_tokens,
                    "preference_evidence": evidence,
                    "follow_up": follow_up,
                },
            )
        )
    ranked.sort(
        key=lambda pair: (
            -pair[0],
            -_date_sort_key(pair[1].get("pub_date")),
            str(pair[1].get("article_id") or ""),
        )
    )

    groups: list[dict] = []
    for score, article in ranked:
        group = next((item for item in groups if _same_article(item["article"], article)), None)
        if group is None:
            group = next((item for item in groups if _event_match(item["article"], article)), None)
        if group is None:
            groups.append({"article": article, "score": score, "sources": [article]})
        else:
            group["sources"].append(article)
            group["score"] = max(group["score"], score)
            prior_representative = group["article"]
            if _representative_key(article) > _representative_key(prior_representative):
                article["matched_preferences"] = sorted(
                    set(article.get("matched_preferences", []))
                    | set(prior_representative.get("matched_preferences", []))
                )
                article["matched_preference_tokens"] = sorted(
                    set(article.get("matched_preference_tokens", []))
                    | set(prior_representative.get("matched_preference_tokens", []))
                )
                article["preference_evidence"] = article.get("preference_evidence", []) + [
                    match
                    for match in prior_representative.get("preference_evidence", [])
                    if match not in article.get("preference_evidence", [])
                ]
                article["follow_up"] = article.get("follow_up", False) or prior_representative.get("follow_up", False)
                group["article"] = article
            else:
                prior_representative["matched_preferences"] = sorted(
                    set(prior_representative.get("matched_preferences", []))
                    | set(article.get("matched_preferences", []))
                )
                prior_representative["matched_preference_tokens"] = sorted(
                    set(prior_representative.get("matched_preference_tokens", []))
                    | set(article.get("matched_preference_tokens", []))
                )
                prior_representative["preference_evidence"] = prior_representative.get("preference_evidence", []) + [
                    match
                    for match in article.get("preference_evidence", [])
                    if match not in prior_representative.get("preference_evidence", [])
                ]
                prior_representative["follow_up"] = prior_representative.get("follow_up", False) or article.get(
                    "follow_up", False
                )

    selected: list[dict] = []
    already_covered = 0
    output_clusters: list[dict] = []
    for group in groups:
        article = group["article"]
        cluster_id = _stable_id("event:" + " ".join(sorted(_terms(article.get("headline")))))
        covered = next(
            (old for old in coverage_rows if _same_article(article, old) or _event_match(article, old)),
            None,
        )
        if covered:
            material = _materially_new(article, covered)
            status = "updated" if material else "already_covered"
            cluster_id = covered.get("cluster_id") or cluster_id
            if not material:
                already_covered += 1
                output_clusters.append({"article": article, "sources": group["sources"], "status": status})
                continue
        else:
            status = "new"
        result = {
            **article,
            "status": status,
            "cluster_id": cluster_id,
            "_selection_score": group["score"],
            "sources": [
                {
                    "publisher": row.get("publisher"),
                    "source_url": row.get("source_url"),
                    "source_id": row.get("source_id"),
                    "pub_date": row.get("pub_date"),
                }
                for row in group["sources"]
            ],
        }
        selected.append(result)
        output_clusters.append({"article": result, "sources": group["sources"], "status": status})
    selected.sort(
        key=lambda row: (
            -row.get("_selection_score", 0),
            -_date_sort_key(row.get("pub_date")),
            str(row.get("article_id") or ""),
        )
    )
    for row in selected:
        row.pop("_selection_score", None)
    return {
        "selected": selected[: max(0, int(limit))],
        "already_covered": already_covered,
        "irrelevant": irrelevant,
        "unsourced": unsourced,
        "clusters": output_clusters,
    }


def render_briefing(selection: object, objective: str, checked_at: object, fixture_label: str | None = None) -> str:
    """Render a concise, sourced Markdown briefing from selected articles."""
    selected = selection.get("selected", []) if isinstance(selection, dict) else selection
    checked, _ = _timestamp(checked_at)
    parts = ["## News briefing"]
    if objective:
        parts.append(f"For: {_markdown_text(_plain_text(objective)[:500])}")
    if checked:
        parts.append(f"Checked: {checked}")
    if fixture_label:
        parts.append(f"Source data: {_markdown_text(_plain_text(fixture_label)[:200])}")
    rows = list(selected or [])[:5]
    if not rows:
        parts.append("No relevant new or materially updated stories were found.")
    for item in rows:
        headline = _markdown_text(_plain_text(item.get("headline")) or "Untitled story")
        date = _markdown_text(_plain_text(item.get("pub_date")) or "Date not provided")
        status = _markdown_text(str(item.get("status") or "new"))
        description = _markdown_text(_plain_text(item.get("description")) or _plain_text(item.get("content")))
        detail = description or "No description was provided by the source."
        evidence = item.get("preference_evidence") or []
        if evidence:
            relevance_items = []
            for match in evidence:
                if not isinstance(match, dict):
                    continue
                phrase = _markdown_text(_plain_text(match.get("preference")))
                tokens = ", ".join(_markdown_text(_plain_text(token)) for token in (match.get("matched_tokens") or []))
                relevance_items.append(f"{phrase} (matched: {tokens})" if tokens else phrase)
            relevance = "; ".join(relevance_items)
        else:
            relevance = ", ".join(
                _markdown_text(_plain_text(value)) for value in (item.get("matched_preferences") or [])
            )
        source_rows = [
            {
                "publisher": item.get("publisher"),
                "source_url": item.get("source_url"),
                "pub_date": item.get("pub_date"),
            }
        ]
        if isinstance(item.get("sources"), list):
            source_rows.extend(source for source in item["sources"] if isinstance(source, dict))
        rendered_sources: list[str] = []
        seen_urls: set[str] = set()
        seen_publishers: set[str] = set()
        for source_row in source_rows:
            source_publisher = _markdown_text(_plain_text(source_row.get("publisher")) or "Unknown publisher")
            source_url = _safe_url(source_row.get("source_url"))
            source_date = _markdown_text(_plain_text(source_row.get("pub_date")))
            if source_url:
                if source_url in seen_urls:
                    continue
                seen_urls.add(source_url)
                destination = quote(source_url, safe=":/?&=%#@!$&'*+,;[]~.-_")
                rendered_source = f"[{source_publisher}](<{destination}>)"
            else:
                publisher_key = source_publisher.casefold()
                if publisher_key in seen_publishers:
                    continue
                rendered_source = source_publisher
            seen_publishers.add(source_publisher.casefold())
            if source_date:
                rendered_source += f" ({source_date})"
            rendered_sources.append(rendered_source)
        source_line = (
            "Sources: " + " · ".join(rendered_sources)
            if rendered_sources
            else "Sources: No validated source URL provided."
        )
        parts.extend([f"### {headline}", f"{date} · {status}", source_line, f"{detail}"])
        if relevance:
            parts.append(f"Relevant to: {relevance}")
    return "\n\n".join(parts)


def _markdown_text(value: str) -> str:
    """Escape remote/plain text before placing it in generated Markdown."""
    return re.sub(r"([\\`*_{}\[\]<>()#+!|])", r"\\\1", value)
