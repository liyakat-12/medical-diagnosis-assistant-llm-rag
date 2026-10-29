from __future__ import annotations

import json

import pytest

from app.services import evaluation_service


def _login(client) -> None:
    response = client.post("/api/v1/auth/login", json={"email": "demo@clinic.local", "password": "demo123"})
    assert response.status_code == 200, response.text


def test_rank_metrics_match_evaluation_script_definitions():
    metrics = evaluation_service.rank_metrics([1, 2, 3, None])
    assert metrics["n"] == 4
    assert metrics["found"] == 3
    assert metrics["missed"] == 1
    assert metrics["recall_at_1"] == pytest.approx(0.25)
    assert metrics["recall_at_3"] == pytest.approx(0.75)
    assert metrics["recall_at_4"] == pytest.approx(0.75)
    assert metrics["mrr"] == pytest.approx((1 + 1 / 2 + 1 / 3 + 0) / 4)


def test_rank_metrics_on_empty_dataset_are_unavailable_not_zero():
    metrics = evaluation_service.rank_metrics([])
    assert metrics["n"] == 0
    assert metrics["recall_at_1"] is None
    assert metrics["mrr"] is None


def test_rank_distribution_counts_misses():
    assert evaluation_service.rank_distribution([1, 1, 4, None], depth=4) == {"1": 2, "2": 0, "3": 0, "4": 1, "miss": 1}


def _write_run(results_dir, name: str, per_query: list[dict]) -> None:
    payload = {"corpus_docs": 3, "query_count": len(per_query), "recall@1": 0.5, "recall@4": 1.0, "mrr": 0.75, "per_query": per_query}
    (results_dir / f"kb_phase2_{name}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_retrieval_runs_and_cases_join_expected_labels(tmp_path):
    results = tmp_path / "results"
    datasets = tmp_path / "datasets"
    results.mkdir()
    datasets.mkdir()
    (datasets / evaluation_service.RETRIEVAL_DATASET).write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"id": "q1", "category": "symptom", "query": "fever", "expected_doc_ids": ["what_is_a_fever"]},
                {"id": "q2", "category": "condition", "query": "asthma", "expected_doc_ids": ["asthma_mild"]},
            ]
        ),
        encoding="utf-8",
    )
    _write_run(
        results,
        "after",
        [
            {"id": "q1", "category": "symptom", "query": "fever", "rank": 1, "retrieved": ["what_is_a_fever", "a", "b", "c"]},
            {"id": "q2", "category": "condition", "query": "asthma", "rank": 2, "retrieved": ["x", "asthma_mild", "y", "z"]},
        ],
    )

    runs = evaluation_service.retrieval_runs(results)
    assert [run["id"] for run in runs] == ["after"]
    assert runs[0]["metrics"]["recall_at_1"] == pytest.approx(0.5)
    assert runs[0]["metrics"]["mrr"] == pytest.approx(0.75)
    assert runs[0]["depth"] == 4
    assert runs[0]["categories"]["condition"]["recall_at_3"] == pytest.approx(1.0)

    detail = evaluation_service.retrieval_cases("after", results, datasets)
    assert detail is not None
    second = detail["cases"][1]
    assert second["expected_doc_ids"] == ["asthma_mild"]
    assert second["retrieved_doc_ids"][1] == "asthma_mild"
    assert second["reciprocal_rank"] == pytest.approx(0.5)


def test_missing_result_files_are_reported_as_missing(tmp_path):
    assert evaluation_service.retrieval_runs(tmp_path) == []
    assert evaluation_service.retrieval_cases(None, tmp_path, tmp_path) is None
    assert evaluation_service.embedding_comparison(tmp_path) == []
    assert evaluation_service.quality_reports(tmp_path) == []
    assert evaluation_service.grounding_summary(tmp_path) is None
    status = evaluation_service.retrieval_report_status(tmp_path)
    assert status["valid_runs"] == 0
    assert status["report_files"] == []
    assert "evaluate_kb_phase2.py" in (status["missing_message"] or "")
    assert "Live chat retrieval telemetry" in (status["missing_message"] or "")


def test_malformed_retrieval_reports_are_skipped(tmp_path):
    (tmp_path / "kb_phase2_broken.json").write_text("{not-json", encoding="utf-8")
    (tmp_path / "kb_phase2_empty.json").write_text(json.dumps({"recall@1": 1.0}), encoding="utf-8")
    (tmp_path / "kb_phase2_not_object.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    _write_run(
        tmp_path,
        "ok",
        [{"id": "q1", "category": "symptom", "query": "fever", "rank": 1, "retrieved": ["what_is_a_fever"]}],
    )
    runs = evaluation_service.retrieval_runs(tmp_path)
    assert [run["id"] for run in runs] == ["ok"]
    status = evaluation_service.retrieval_report_status(tmp_path)
    assert status["valid_runs"] == 1
    assert status["missing_message"] is None
    assert "kb_phase2_broken.json" in status["report_files"]


def test_valid_retrieval_report_exposes_dataset_and_config(tmp_path):
    payload = {
        "corpus_docs": 10,
        "query_count": 1,
        "recall@1": 1.0,
        "recall@4": 1.0,
        "mrr": 1.0,
        "dataset": "kb_expansion_phase2.jsonl",
        "config": {
            "embedding_mode": "general",
            "embedding_backend": "fastembed",
            "rerank_enabled": False,
            "top_k": 4,
            "dataset": "kb_expansion_phase2.jsonl",
        },
        "per_query": [
            {"id": "q1", "category": "symptom", "query": "fever", "rank": 1, "retrieved": ["what_is_a_fever", "a", "b", "c"]}
        ],
    }
    (tmp_path / "kb_phase2_production.json").write_text(json.dumps(payload), encoding="utf-8")
    runs = evaluation_service.retrieval_runs(tmp_path)
    assert len(runs) == 1
    assert runs[0]["id"] == "production"
    assert runs[0]["dataset"] == "kb_expansion_phase2.jsonl"
    assert runs[0]["config"]["embedding_backend"] == "fastembed"
    assert runs[0]["config"]["rerank_enabled"] is False
    assert runs[0]["metrics"]["recall_at_1"] == pytest.approx(1.0)


def test_embedding_comparison_reads_ranks_beyond_depth_as_misses(tmp_path):
    (tmp_path / "embedding_eval_general.csv").write_text(
        "query,expected_doc_id,rank_of_correct_doc,top1_doc_id\nq,a,1,a\nq,b,>5,c\nq,c,3,d\n", encoding="utf-8"
    )
    runs = evaluation_service.embedding_comparison(tmp_path)
    assert [run["id"] for run in runs] == ["general"]
    metrics = runs[0]["metrics"]
    assert metrics["n"] == 3
    assert metrics["recall_at_1"] == pytest.approx(1 / 3)
    assert metrics["recall_at_3"] == pytest.approx(2 / 3)
    assert metrics["mrr"] == pytest.approx((1 + 0 + 1 / 3) / 3)


def test_multiple_saved_retrieval_runs_keep_stable_labels(tmp_path):
    _write_run(
        tmp_path,
        "baseline",
        [{"id": "q1", "category": "symptom", "query": "fever", "rank": 1, "retrieved": ["a", "b", "c", "d"]}],
    )
    _write_run(
        tmp_path,
        "after",
        [{"id": "q1", "category": "symptom", "query": "fever", "rank": 2, "retrieved": ["x", "a", "b", "c"]}],
    )
    _write_run(
        tmp_path,
        "batch4",
        [{"id": "q1", "category": "symptom", "query": "fever", "rank": 1, "retrieved": ["a", "b", "c", "d"]}],
    )
    runs = evaluation_service.retrieval_runs(tmp_path)
    by_id = {run["id"]: run for run in runs}
    assert set(by_id) == {"baseline", "after", "batch4"}
    assert by_id["baseline"]["label"] == "Baseline"
    assert by_id["after"]["label"] == "After"
    assert by_id["batch4"]["label"] == "Batch4"
    status = evaluation_service.retrieval_report_status(tmp_path)
    assert status["missing_historical_run_ids"] == []
    assert status["valid_runs"] == 3


def test_missing_historical_runs_are_reported_without_inventing_metrics(tmp_path):
    _write_run(
        tmp_path,
        "production",
        [{"id": "q1", "category": "symptom", "query": "fever", "rank": 1, "retrieved": ["a", "b", "c", "d"]}],
    )
    runs = evaluation_service.retrieval_runs(tmp_path)
    assert [run["id"] for run in runs] == ["production"]
    status = evaluation_service.retrieval_report_status(tmp_path)
    assert status["missing_historical_run_ids"] == ["baseline", "after", "batch4"]
    assert status["missing_message"] is None


def test_embedding_comparison_status_reports_missing_files(tmp_path):
    status = evaluation_service.embedding_comparison_status(tmp_path)
    assert status["valid_runs"] == 0
    assert status["present_files"] == []
    assert "embedding_eval_general.csv" in status["missing_files"]
    assert "evaluate_embeddings.py" in (status["missing_message"] or "")

    (tmp_path / "embedding_eval_general.csv").write_text(
        "query,expected_doc_id,rank_of_correct_doc,top1_doc_id\nq,a,1,a\n", encoding="utf-8"
    )
    status = evaluation_service.embedding_comparison_status(tmp_path)
    assert status["present_files"] == ["embedding_eval_general.csv"]
    assert status["missing_message"] is None
    assert status["valid_runs"] == 1


def test_evaluation_endpoints_require_login(client):
    assert client.get("/api/v1/evaluation/overview").status_code == 401
    assert client.post("/api/v1/evaluation/retrieve", json={"query": "fever"}).status_code == 401


def test_evaluation_overview_reports_knowledge_base_status(client):
    _login(client)
    response = client.get("/api/v1/evaluation/overview")
    assert response.status_code == 200, response.text
    body = response.json()
    knowledge_base = body["knowledge_base"]
    assert knowledge_base["documents"] == 1017
    assert knowledge_base["chunks_indexed"] and knowledge_base["chunks_indexed"] > 0
    assert knowledge_base["index_ready"] is True
    assert body["test_suite"] is None
    assert isinstance(body["retrieval_runs"], list)
    status = body["retrieval_report_status"]
    assert status["dataset"] == evaluation_service.RETRIEVAL_DATASET
    assert status["expected_glob"] == evaluation_service.RETRIEVAL_RUN_GLOB
    assert status["valid_runs"] == len(body["retrieval_runs"])
    if body["retrieval_runs"]:
        assert status["missing_message"] is None
        latest = body["retrieval_runs"][-1]
        assert latest["metrics"]["n"] > 0
        assert latest["file"].startswith("kb_phase2_")
    else:
        assert status["missing_message"]


def test_live_retrieval_uses_the_real_index_and_reports_ranked_sources(client):
    _login(client)
    response = client.post("/api/v1/evaluation/retrieve", json={"query": "How can I prevent food poisoning at home?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["pipeline_retrieves"] is True
    assert body["timings"]["retrieve_ms"] > 0
    ranks = [item["rank"] for item in body["results"]]
    assert ranks == list(range(1, len(ranks) + 1))
    assert "food_safety_at_home" in {item["doc_id"] for item in body["results"]}
    assert all(item["title"] and item["source"] for item in body["results"])


def test_live_retrieval_flags_messages_the_pipeline_would_refuse(client):
    _login(client)
    response = client.post("/api/v1/evaluation/retrieve", json={"query": "What dose of amoxicillin should I take?"})
    assert response.status_code == 200, response.text
    assert response.json()["pipeline_retrieves"] is False


def test_body_regions_are_validated_and_stored_on_the_user_message(client):
    _login(client)
    chat_id = client.post("/api/v1/chats", json={"title": None}).json()["id"]
    rejected = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"content": "my knee hurts", "body_regions": ["spleen"]},
    )
    assert rejected.status_code == 422

    sent = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"content": "My knee hurts on the stairs", "body_regions": ["knee", "knee", "ankle_foot"]},
    )
    assert sent.status_code == 200, sent.text
    user_message = sent.json()[0]
    assert user_message["metadata"]["body_regions"] == ["knee", "ankle_foot"]
    assert user_message["content"] == "My knee hurts on the stairs"


def test_messages_without_body_regions_keep_working(client):
    _login(client)
    chat_id = client.post("/api/v1/chats", json={"title": None}).json()["id"]
    sent = client.post(f"/api/v1/chats/{chat_id}/messages", json={"content": "I have a dry cough at night"})
    assert sent.status_code == 200, sent.text
    assert "body_regions" not in sent.json()[0]["metadata"]
