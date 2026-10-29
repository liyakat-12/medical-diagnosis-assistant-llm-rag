export interface RankMetrics {
  n: number;
  found: number;
  missed: number;
  recall_at_1: number | null;
  recall_at_3: number | null;
  recall_at_4?: number | null;
  recall_at_5?: number | null;
  mrr: number | null;
}

export interface SafetyCheck {
  n: number;
  passed: number;
  failed: unknown[];
}

export interface RetrievalRunConfig {
  embedding_mode: string | null;
  embedding_backend: string | null;
  rerank_enabled: boolean | null;
  top_k: number | null;
}

export interface RetrievalRun {
  id: string;
  label: string;
  description: string;
  file: string;
  generated_at: string;
  dataset?: string | null;
  corpus_docs: number | null;
  query_count: number | null;
  depth: number;
  config?: RetrievalRunConfig;
  metrics: RankMetrics;
  stored_metrics: { recall_at_1: number | null; recall_at_4: number | null; mrr: number | null };
  rank_distribution: Record<string, number>;
  categories: Record<string, RankMetrics>;
  safety: Record<string, SafetyCheck>;
}

export interface RetrievalReportStatus {
  directory: string;
  directory_exists: boolean;
  expected_glob: string;
  dataset: string;
  report_files: string[];
  valid_runs: number;
  missing_message: string | null;
}

export interface EmbeddingRun {
  id: string;
  label: string;
  description: string;
  file: string;
  generated_at: string;
  depth: number;
  metrics: RankMetrics;
}

export interface QualityReport {
  id: string;
  suite: string;
  label: string;
  file: string;
  generated_at: string;
  cases: number | null;
  passed: number | null;
  failed: number | null;
  method: string | null;
}

export interface GroundingCase {
  id: string;
  category: string;
  query: string;
  refused: boolean;
  triage: string | null;
  passed: boolean;
}

export interface GroundingSummary {
  report: string;
  generated_at: string;
  cases: number;
  cases_with_citations: number;
  citations_total: number;
  origin_counts: Record<string, number>;
  faithfulness_counts: Record<string, number>;
  checks: Record<string, { n: number; failed: number }>;
  without_evidence: GroundingCase[];
  method: string | null;
}

export interface KnowledgeBaseStatus {
  documents: number | null;
  chunks_indexed: number | null;
  index_ready: boolean;
  embedding_mode: string;
  rerank_enabled: boolean;
  top_k: number;
  rerank_candidates: number;
  error: string | null;
}

export interface EvaluationOverview {
  knowledge_base: KnowledgeBaseStatus;
  retrieval_runs: RetrievalRun[];
  retrieval_report_status?: RetrievalReportStatus;
  embedding_comparison: EmbeddingRun[];
  quality_reports: QualityReport[];
  grounding: GroundingSummary | null;
  test_suite: null;
  definitions: { recall_at_k: string; mrr: string };
}

export interface RetrievalCase {
  id: string;
  category: string;
  query: string;
  expected_doc_ids: string[];
  retrieved_doc_ids: string[];
  rank: number | null;
  reciprocal_rank: number;
}

export interface RetrievalCasesResponse {
  run: RetrievalRun;
  dataset: string | null;
  cases: RetrievalCase[];
}

export interface LiveRetrievalResult {
  rank: number;
  doc_id: string;
  title: string;
  source: string;
  url: string;
  condition: string;
  relevance_score: number;
  vector_score: number;
}

export interface LiveRetrieval {
  query: string;
  search_query: string;
  intent: string;
  question_type: string;
  pipeline_retrieves: boolean;
  pipeline_skip_reason: string | null;
  rerank_enabled: boolean;
  top_k: number;
  timings: { prepare_ms: number; retrieve_ms: number };
  results: LiveRetrievalResult[];
}

export interface ClaimAudit {
  text: string;
  cited_source: string | null;
  status: "supported" | "unsupported" | "fabricated_citation" | "not_a_claim";
  matched_title?: string | null;
}

export interface CitationAudit {
  coverage?: number;
  claim_count?: number;
  supported_count?: number;
  unsupported_count?: number;
  fabricated_count?: number;
  verdict?: "pass" | "partial" | "fail" | "n_a";
  summary?: string;
  claims?: ClaimAudit[];
}

export interface PipelineRun {
  query: string;
  refused: boolean;
  refusal_reason: string | null;
  answer: string;
  citations: { title?: string; source?: string; url?: string; condition?: string; relevance_score?: number }[];
  triage: { level: string; label: string; guidance: string; reason?: string } | null;
  faithfulness: CitationAudit | null;
  evidence_origin: string;
  timings: Partial<Record<"classify_ms" | "retrieve_ms" | "generate_ms" | "total_ms", number>>;
  question_type: string;
  disclaimer?: string;
}
