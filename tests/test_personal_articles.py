from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.personal.articles import normalize_articles, rank_and_select, render_briefing


FIXTURE = Path(__file__).parents[1] / "docs" / "personal-002" / "api-response.json"


def article(**changes):
    row = {
        "id": 41,
        "guid": "wire-41",
        "provider": "Example News",
        "title": "Bank adopts Bitcoin settlement network for cross-border payments",
        "description": "The bank will use Bitcoin rails for a new settlement service.",
        "content": "The bank will use Bitcoin rails for a new settlement service.",
        "link": "https://news.example/story/41?utm_source=feed",
        "pubDate": "2026-11-10T12:00:00Z",
        "originalPubDate": "2026-11-10T12:00:00Z",
        "fetchedAt": "2026-11-10T12:10:00Z",
        "updatedAt": None,
        "category": "Finance",
        "region": "Global",
        "sentiment": "positive",
        "isTopRanked": False,
        "topics": ["Bitcoin", {"label": "Payments"}],
        "wasUpdated": False,
    }
    row.update(changes)
    return row


def test_normalizes_actual_public_api_fixture_and_keeps_requested_fields():
    payload = json.loads(FIXTURE.read_text())
    normalized = normalize_articles(payload, "2026-11-10T13:00:00Z")
    assert len(normalized) == 100
    first = normalized[0]
    assert first["headline"]
    assert first["publisher"] == "BBC"
    assert first["source_url"].startswith("https://")
    assert first["source_url"].find("utm_") == -1
    assert first["pub_date"].endswith("Z")
    assert first["fetched_at"].endswith("Z")
    assert first["provenance"]["source_identifiers"]["feedId"] == "22"
    assert {
        "article_id",
        "source_id",
        "description",
        "content",
        "original_pub_date",
        "updated_at",
        "category",
        "region",
        "sentiment",
        "is_top_ranked",
        "topics",
        "was_updated",
        "provenance",
        "issues",
    } <= first.keys()


def test_actual_fixture_selects_multiple_distinct_owner_relevant_stories():
    rows = normalize_articles(json.loads(FIXTURE.read_text()), fetched_at=1794315600)
    result = rank_and_select(
        rows,
        {
            "topics": [
                "Bitcoin",
                "Ethereum",
                "institutional digital asset adoption",
                "digital asset regulation",
                "financial infrastructure and tokenization",
                "material market developments",
            ]
        },
        [],
    )
    assert 2 <= len(result["selected"]) <= 5
    assert len({row["article_id"] for row in result["selected"]}) == len(result["selected"])
    assert all(row["preference_evidence"] for row in result["selected"])
    assert all(row["source_url"] and row["publisher"] and row["headline"] for row in result["selected"])
    assert not any(
        row["matched_preferences"] == ["material market developments"]
        and row["matched_preference_tokens"] == ["market"]
        for row in result["selected"]
    )


def test_generic_market_only_does_not_qualify_and_selection_does_not_pad():
    rows = normalize_articles(
        [
            article(
                id=601,
                guid="bitcoin-601",
                title="Bitcoin ETF draws new institutional investors",
                link="https://news.example/bitcoin-601",
                description="Bitcoin ETF sees increased institutional adoption.",
                content="Bitcoin ETF sees increased institutional adoption.",
            ),
            article(
                id=602,
                guid="ethereum-602",
                title="Ethereum tokenization expands to new banks",
                link="https://news.example/ethereum-602",
                description="Ethereum tokenization expands financial infrastructure.",
                content="Ethereum tokenization expands financial infrastructure.",
            ),
            article(
                id=603,
                guid="market-603",
                title="Oil prices move as market chatter grows",
                link="https://news.example/market-603",
                description="Market activity was mixed.",
                content="Market activity was mixed.",
            ),
            article(
                id=604,
                guid="market-604",
                title="Global Market Talk: banks and oil",
                link="https://news.example/market-604",
                description="Market talk covers broad global activity.",
                content="Market talk covers broad global activity.",
            ),
        ]
    )
    result = rank_and_select(rows, ["Bitcoin", "Ethereum", "material market developments"], [])
    assert len(result["selected"]) == 2
    assert result["irrelevant"] == 2
    assert all(
        "market" not in row["matched_preference_tokens"] or row["matched_preferences"] != ["market"]
        for row in result["selected"]
    )


def test_explicit_single_word_markets_preference_matches_text():
    rows = normalize_articles(
        [
            article(
                id=605,
                guid="markets-605",
                title="Equity markets rally after central bank decision",
                link="https://news.example/markets-605",
                description="Equity markets rallied after the central bank decision.",
                content="Equity markets rallied after the central bank decision.",
                topics=[],
            ),
            article(
                id=606,
                guid="market-606",
                title="Oil analysts discuss broad activity",
                link="https://news.example/market-606",
                description="The outlook remains mixed.",
                content="The outlook remains mixed.",
                topics=[],
            ),
        ]
    )
    result = rank_and_select(rows, ["markets"], [])
    assert len(result["selected"]) == 1
    assert result["selected"][0]["headline"] == "Equity markets rally after central bank decision"
    assert result["selected"][0]["matched_preferences"] == ["markets"]


def test_relevant_unsourced_story_is_counted_and_never_selected_or_used_to_pad():
    rows = normalize_articles(
        [
            article(
                id=901,
                guid="bitcoin-901",
                title="Bitcoin institutional adoption expands at banks",
                link="https://news.example/bitcoin-901",
                description="Bitcoin adoption expands across banks.",
                content="Bitcoin adoption expands across banks.",
            ),
            article(
                id=902,
                guid="eth-902",
                title="Ethereum tokenization supports new custody product",
                link="https://news.example/eth-902",
                description="Ethereum tokenization supports a custody product.",
                content="Ethereum tokenization supports a custody product.",
            ),
            article(
                id=903,
                guid="not-a-url",
                title="Bitcoin market gains attention from institutions",
                link="javascript:alert(1)",
                description="Bitcoin attracts institutional interest.",
                content="Bitcoin attracts institutional interest.",
            ),
        ]
    )
    result = rank_and_select(rows, ["Bitcoin", "Ethereum", "institutional adoption"], [], limit=5)
    assert len(result["selected"]) == 2
    assert result["unsourced"] == 1
    assert all(row["source_url"] for row in result["selected"])


def test_valid_guid_url_is_used_when_source_link_is_missing():
    result = normalize_articles(
        [
            article(
                link="",
                guid="https://publisher.example/original-story",
            )
        ]
    )[0]
    assert result["source_url"] == "https://publisher.example/original-story"


def test_custom_noncrypto_owner_preferences_remain_supported():
    rows = normalize_articles(
        [
            article(
                id=701,
                guid="solar-701",
                title="Solar energy project adds new storage capacity",
                link="https://news.example/solar-701",
                description="The solar energy project adds battery storage.",
                content="The solar energy project adds battery storage.",
            ),
            article(
                id=702,
                guid="crypto-702",
                title="Bitcoin market update",
                link="https://news.example/crypto-702",
            ),
        ]
    )
    result = rank_and_select(rows, ["solar energy", "battery storage"], [])
    assert len(result["selected"]) == 1
    assert result["selected"][0]["matched_preferences"] == ["battery storage", "solar energy"]


def test_briefing_shows_matched_tokens_for_partial_multiword_preference():
    rows = normalize_articles(
        [
            article(
                id=801,
                guid="institutional-801",
                title="Institutional asset manager expands digital custody",
                link="https://news.example/institutional-801",
                description="An institutional asset manager expands digital custody services.",
                content="An institutional asset manager expands digital custody services.",
            )
        ]
    )
    result = rank_and_select(rows, ["institutional digital asset adoption"], [])
    assert result["selected"][0]["preference_evidence"][0]["matched_tokens"] == [
        "asset",
        "digital",
        "institutional",
    ]
    rendered = render_briefing(result, "Track adoption", "2026-11-10T13:00:00Z")
    assert "institutional digital asset adoption (matched: asset, digital, institutional)" in rendered


def test_accepts_documented_wrappers_empty_arrays_and_rejects_bad_shapes():
    assert normalize_articles({"articles": []}) == []
    assert normalize_articles({"data": [article()]})[0]["headline"].startswith("Bank")
    for payload in (None, {}, {"items": []}, "[]", [None]):
        with pytest.raises(ValueError):
            normalize_articles(payload)


def test_metadata_html_and_invalid_values_are_tolerant_and_safe():
    item = normalize_articles(
        [
            article(
                guid={"url": "wire-41"},
                topics={"tag": "bitcoin"},
                wasUpdated="false",
                pubDate="not a date",
                updatedAt="bad",
                link="javascript:alert(1)",
                description="<b>Fresh</b><script>ignore()</script>",
                content="<p>Hello &amp; <i>world</i></p><style>.x{}</style>",
            )
        ],
        fetched_at="bad fetched time",
    )[0]
    assert item["source_url"] is None
    assert item["description"] == "Fresh"
    assert item["content"] == "Hello & world"
    assert item["pub_date"] is None
    assert item["updated_at"] is None
    assert item["topics"] == [{"tag": "bitcoin"}]
    assert item["was_updated"] is False
    assert "not a date" == item["provenance"]["invalid_timestamps"]["pubDate"]
    assert item["provenance"]["invalid_fetched_at"] == "bad fetched time"
    assert "unsafe_or_invalid_source_url" in item["issues"]


def test_safe_url_rejects_credentials_and_non_http_schemes():
    for url in ("javascript:alert(1)", "https://user:pass@example.test/a", "file:///tmp/a"):
        assert normalize_articles([article(link=url)])[0]["source_url"] is None


def test_identity_survives_reordering_headline_changes_and_tracks_aliases():
    rows = normalize_articles([article(), article(id=42, title="New bank adopts Bitcoin settlement network")])
    reordered = normalize_articles([article(id=42, title="Another headline on Bitcoin settlement network"), article()])
    assert rows[0]["article_id"] == reordered[1]["article_id"]
    assert rows[1]["article_id"] == reordered[0]["article_id"]
    changed_url_id = normalize_articles([article(id=99, link="https://new.example/story/41")])[0]
    assert (
        rows[0]["alias_ids"][-1] != changed_url_id["alias_ids"][-1]
        or rows[0]["alias_ids"] != changed_url_id["alias_ids"]
    )
    assert any(alias.startswith("url:") for alias in rows[0]["alias_ids"])


def test_feed_identifier_is_provenance_only_and_same_feed_stories_remain_distinct():
    rows = normalize_articles(
        [
            article(
                id=501,
                guid="wire-501",
                feedId=22,
                title="Bitcoin bank settlement expands to new region",
                link="https://news.example/bitcoin-501",
                description="The bank expands its Bitcoin settlement coverage for clients.",
                content="The bank expands its Bitcoin settlement coverage for clients.",
            ),
            article(
                id=502,
                guid="wire-502",
                feedId=22,
                title="Ethereum custody service launches for institutions",
                link="https://news.example/ethereum-502",
                description="An Ethereum custody product is now available to institutional clients.",
                content="An Ethereum custody product is now available to institutional clients.",
            ),
        ]
    )
    assert rows[0]["provenance"]["source_identifiers"]["feedId"] == "22"
    assert rows[1]["provenance"]["source_identifiers"]["feedId"] == "22"
    assert rows[0]["alias_ids"] != rows[1]["alias_ids"]
    selected = rank_and_select(rows, ["Bitcoin", "Ethereum", "custody", "settlement"], [])
    assert len(selected["selected"]) == 2


def test_numeric_fetch_timestamp_is_epoch_time():
    result = normalize_articles([article(fetchedAt=None)], fetched_at=1794315600)[0]
    assert result["fetched_at"] == "2026-11-10T13:00:00Z"
    assert "invalid_fetched_at" not in result["provenance"]


def test_preferences_filter_and_rank_by_owner_profile_not_publisher_rank():
    rows = normalize_articles(
        [
            article(
                id=1,
                guid="wire-1",
                title="Bitcoin institutional adoption expands at major bank",
                link="https://news.example/bitcoin-bank",
                isTopRanked=False,
            ),
            article(
                id=2,
                guid="weather-2",
                title="Local weather forecast turns sunny",
                provider="Weather",
                link="https://weather.example/forecast",
                isTopRanked=True,
                description="Rain ends by noon.",
                content="Rain ends by noon.",
                topics=[],
            ),
            article(
                id=3,
                guid="wire-3",
                title="Ethereum tokenization launches for financial infrastructure",
                link="https://news.example/ethereum-tokenization",
                isTopRanked=True,
                description="",
                content="",
            ),
        ]
    )
    result = rank_and_select(rows, {"topics": ["Bitcoin", "Ethereum", "institutional adoption", "tokenization"]}, [])
    assert result["irrelevant"] == 1
    assert len(result["selected"]) == 2
    assert all(row["status"] == "new" for row in result["selected"])
    assert result["selected"][0]["matched_preferences"]


def test_coverage_suppresses_repeat_and_material_substance_is_updated():
    previous = normalize_articles([article()])[0]
    repeat = normalize_articles([article(updatedAt="2026-11-10T13:00:00Z", wasUpdated=True)])[0]
    repeat_result = rank_and_select([repeat], ["Bitcoin"], [previous])
    assert repeat_result["selected"] == []
    assert repeat_result["already_covered"] == 1

    updated = normalize_articles(
        [
            article(
                updatedAt="2026-11-10T13:00:00Z",
                description=(
                    "The bank will use Bitcoin rails for a new settlement service. "
                    "It will now serve twelve countries and process payments in under five seconds."
                ),
                content=(
                    "The bank will use Bitcoin rails for a new settlement service. "
                    "It will now serve twelve countries and process payments in under five seconds."
                ),
            )
        ]
    )[0]
    result = rank_and_select([updated], ["Bitcoin"], [previous])
    assert result["selected"][0]["status"] == "updated"


def test_duplicate_article_aliases_merge_after_headline_change_deterministically():
    older, newer = normalize_articles(
        [
            article(
                id=77,
                guid="shared-guid",
                title="Bank adds Bitcoin settlement service",
                link="https://news.example/shared",
                pubDate="2026-11-09T12:00:00Z",
                description="The bank adds a Bitcoin settlement service for clients.",
                content="The bank adds a Bitcoin settlement service for clients.",
            ),
            article(
                id=77,
                guid="shared-guid",
                title="Bitcoin service begins at the same bank",
                link="https://news.example/shared?utm_source=feed",
                pubDate="2026-11-10T12:00:00Z",
                description="The bank adds a Bitcoin settlement service for clients.",
                content="The bank adds a Bitcoin settlement service for clients.",
            ),
        ]
    )
    first = rank_and_select([older, newer], ["Bitcoin", "settlement"], [])
    reversed_result = rank_and_select([newer, older], ["Bitcoin", "settlement"], [])
    assert len(first["selected"]) == 1
    assert first["selected"][0]["headline"] == "Bitcoin service begins at the same bank"
    assert first["selected"][0]["cluster_id"] == reversed_result["selected"][0]["cluster_id"]
    assert first["selected"][0]["sources"] == reversed_result["selected"][0]["sources"]


def test_empty_prior_body_and_changed_numeric_claim_are_material_updates():
    prior_empty = normalize_articles([article(description="", content="")])[0]
    populated = normalize_articles(
        [
            article(
                description="The bank will use Bitcoin rails to serve clients across twelve countries.",
                content="The bank will use Bitcoin rails to serve clients across twelve countries.",
            )
        ]
    )[0]
    result = rank_and_select([populated], ["Bitcoin"], [prior_empty])
    assert result["selected"][0]["status"] == "updated"

    prior = normalize_articles(
        [
            article(
                description="The company raises $10 million to expand Bitcoin custody services for clients.",
                content="The company raises $10 million to expand Bitcoin custody services for clients.",
            )
        ]
    )[0]
    changed = normalize_articles(
        [
            article(
                description="The company raises $100 million to expand Bitcoin custody services for clients.",
                content="The company raises $100 million to expand Bitcoin custody services for clients.",
            )
        ]
    )[0]
    result = rank_and_select([changed], ["Bitcoin"], [prior])
    assert result["selected"][0]["status"] == "updated"


def test_new_substantive_sentence_is_detected_inside_a_long_article():
    legacy_terms = [f"legacyterm{index}" for index in range(380)]
    legacy_terms.extend(["Bitcoin", "25"])
    long_body = " ".join(legacy_terms) + "."
    prior = normalize_articles(
        [
            article(
                id=505,
                guid="long-article-505",
                title="Bitcoin institution expands custody access",
                link="https://news.example/long-505",
                description=long_body,
                content=long_body,
            )
        ]
    )[0]
    updated_body = (
        long_body + " The institution expanded custody access to 25 additional pension funds "
        "and announced a new audited settlement pilot."
    )
    updated = normalize_articles(
        [
            article(
                id=505,
                guid="long-article-505",
                title="Bitcoin institution expands custody access",
                link="https://news.example/long-505",
                description=updated_body,
                content=long_body,
                updatedAt="2026-11-10T13:00:00Z",
            )
        ]
    )[0]
    result = rank_and_select([updated], ["Bitcoin"], [prior])
    assert result["selected"][0]["status"] == "updated"

    wording_only = normalize_articles(
        [
            article(
                id=505,
                guid="long-article-505",
                title="Bitcoin institution expands custody access",
                link="https://news.example/long-505",
                description=long_body.replace("legacyterm1", "rewordedterm1", 1),
                content=long_body,
                updatedAt="2026-11-10T14:00:00Z",
            )
        ]
    )[0]
    result = rank_and_select([wording_only], ["Bitcoin"], [prior])
    assert result["selected"] == []
    assert result["already_covered"] == 1


def test_update_keeps_covered_cluster_id_and_followups_rank_ahead_of_same_score():
    prior = normalize_articles([article()])[0]
    prior["cluster_id"] = "saved-event-cluster"
    updated = normalize_articles(
        [
            article(
                description="The bank will use Bitcoin rails for a new settlement service. "
                "It will now serve twelve countries and process payments in under five seconds.",
                content="The bank will use Bitcoin rails for a new settlement service. "
                "It will now serve twelve countries and process payments in under five seconds.",
            )
        ]
    )[0]
    result = rank_and_select([updated], ["Bitcoin"], [prior])
    assert result["selected"][0]["cluster_id"] == "saved-event-cluster"

    rows = normalize_articles(
        [
            article(id=100, title="Bitcoin custody service expands to five banks", pubDate="2026-11-09T12:00:00Z"),
            article(id=101, title="Bitcoin settlement service expands to five banks", pubDate="2026-11-10T12:00:00Z"),
        ]
    )
    result = rank_and_select(rows, ["Bitcoin"], [], followups=[{"text": "custody"}])
    assert result["selected"][0]["follow_up"] is True


def test_changed_source_id_or_url_can_match_coverage_through_aliases():
    old = normalize_articles([article()])[0]
    changed_id = normalize_articles([article(id=987)])[0]
    result = rank_and_select([changed_id], ["Bitcoin"], [old])
    assert result["already_covered"] == 1
    changed_url = normalize_articles([article(id=None, guid=None, link="https://news.example/story/41")])[0]
    result = rank_and_select([changed_url], ["Bitcoin"], [old])
    assert result["already_covered"] == 1


def test_cross_publisher_reports_cluster_but_same_company_distinct_events_do_not():
    rows = normalize_articles(
        [
            article(
                id=1, title="Acme Bank adopts Bitcoin settlement network for cross-border payments", provider="Wire A"
            ),
            article(
                id=2,
                title="Acme Bank adopts Bitcoin settlement network for cross-border payments",
                provider="Wire B",
                link="https://wire-b.example/story",
            ),
            article(
                id=3,
                title="Acme Bank opens Ethereum custody service for institutions",
                provider="Wire C",
                link="https://wire-c.example/story",
            ),
        ]
    )
    result = rank_and_select(rows, ["Bitcoin", "Ethereum", "bank", "institutional"], [])
    assert len(result["selected"]) == 2
    event = next(row for row in result["selected"] if "settlement" in row["headline"])
    assert {source["publisher"] for source in event["sources"]} == {"Wire A", "Wire B"}


def test_briefing_renders_each_distinct_valid_cluster_source_and_available_date():
    rows = normalize_articles(
        [
            article(
                id=201,
                guid="wire-a-201",
                provider="Wire A",
                title="Acme Bank adopts Bitcoin settlement network for cross-border payments",
                link="https://wire-a.example/story/201",
                pubDate="2026-11-10T10:00:00Z",
                description="Acme Bank adopts Bitcoin settlement network for cross-border payments.",
            ),
            article(
                id=202,
                guid="wire-b-202",
                provider="Wire B",
                title="Acme Bank adopts Bitcoin settlement network for cross-border payments",
                link="https://wire-b.example/story/202",
                pubDate="2026-11-10T11:00:00Z",
                description="Acme Bank adopts Bitcoin settlement network for cross-border payments.",
            ),
        ]
    )
    result = rank_and_select(rows, ["Bitcoin", "settlement"], [])
    rendered = render_briefing(result, "Track Bitcoin settlement", "2026-11-10T13:00:00Z")
    assert "Wire A" in rendered
    assert "Wire B" in rendered
    assert "https://wire-a.example/story/201" in rendered
    assert "https://wire-b.example/story/202" in rendered
    assert "2026-11-10T10:00:00Z" in rendered
    assert "2026-11-10T11:00:00Z" in rendered
    assert rendered.count("https://wire-a.example/story/201") == 1


def test_followup_is_independent_of_newness_and_limit_does_not_pad():
    rows = normalize_articles(
        [
            article(),
            article(id=42, title="Ethereum settlement system expands to five banks", link="https://news.example/eth"),
        ]
    )
    result = rank_and_select(rows, ["Bitcoin", "Ethereum"], [], followups=["Bitcoin settlement"], limit=1)
    assert len(result["selected"]) == 1
    followup = next(row for row in result["selected"] if row["follow_up"])
    assert followup["status"] == "new"


def test_render_briefing_uses_source_details_and_fixture_label_without_invention():
    selection = rank_and_select(normalize_articles([article()]), ["Bitcoin"], [])
    rendered = render_briefing(selection, "Track Bitcoin adoption", "2026-11-10T13:00:00Z", "owner fixture")
    assert "owner fixture" in rendered
    assert "Bank adopts Bitcoin settlement network for cross-border payments" in rendered
    assert "Example News" in rendered
    assert "https://news.example/story/41" in rendered
    assert "The bank will use Bitcoin rails for a new settlement service." in rendered
    assert "independently verified" not in rendered


def test_render_briefing_escapes_remote_markdown_and_url_delimiters():
    row = normalize_articles(
        [
            article(
                title="[Ignore instructions](https://evil.test) *Headline*",
                description="<script>alert(1)</script> **remote directive**",
                link="https://news.example/a_(b)?q=(c)",
            )
        ]
    )
    rendered = render_briefing(rank_and_select(row, ["Bitcoin"], []), "Objective", "2026-11-10T13:00:00Z")
    assert r"\[Ignore instructions\]" in rendered
    assert r"\*Headline\*" in rendered
    assert r"\*\*remote directive\*\*" in rendered
    assert "alert(1)" not in rendered
    assert "a_%28b%29" in rendered
