export interface Application {
  id: string;
  name: string;
  purpose: string;
  owner: string;
  expected_behavior: string;
  application_version: string;
  model_version: string;
  prompt_version: string;
  supported_fields: string[];
  demo: boolean;
}
export interface Source {
  id: string;
  document_id: string;
  version: string;
  filename: string;
  content: string;
  content_hash: string;
  created_at: string;
}
export interface SourceRef {
  source_id: string;
  start: number;
  end: number;
  quote: string;
  content_hash: string;
}
export interface Case {
  id: string;
  question: string;
  category: string;
  expected_behavior: string;
  reference_answer: string | null;
  references: SourceRef[];
  relevant_source_ids: string[] | null;
  provenance: string;
  review_status: string;
  group_id: string;
  split: string;
  revision: number;
}
export interface Dataset {
  id: string;
  cases: Case[];
  sources: Source[];
  version: number;
  checksum: string;
  actor: string;
  created_at: string;
}
export interface Metric {
  id: string;
  purpose: string;
  required_inputs: string[];
  method: string;
  limitations: string;
  direction: string;
  threshold: number | null;
  evaluator_version: string;
  state: string;
  reason: string;
  missing_inputs: string[];
}
export interface MetricResult {
  metric: string;
  evaluator_version: string;
  status: string;
  value: number | null;
  explanation: string;
  evidence: unknown[];
  failure_tags: string[];
}
export interface Trace {
  id: string;
  case_id: string;
  answer: string | null;
  behavior: string | null;
  citations: string[] | null;
  retrieved_ids: string[] | null;
  latency_ms: number | null;
  error: string | null;
  fault_label: string | null;
}
export interface CaseResult {
  case_id: string;
  metrics: MetricResult[];
  trace: Trace | null;
}
export interface Summary {
  passed: number;
  failed: number;
  skipped: number;
  insufficient_evidence: number;
  evaluator_error: number;
  scored: number;
  selected: number;
  finalized: number;
  pending: number;
  pass_rate: number | null;
}
export interface Run {
  id: string;
  status: string;
  completed: number;
  total: number;
  error: string | null;
  created_at: string;
  updated_at: string;
  request: {
    dataset_id: string;
    target: string;
    split: string;
    sample_size: number;
    max_requests: number;
    sampling_seed: number;
    spending_cap: number;
  };
  dataset_checksum: string;
  summary: Record<string, Summary>;
  results: CaseResult[];
  snapshot?: {
    dataset: Dataset;
    application: Application;
    cases: Case[];
    metrics: Metric[];
    target_version: string;
  };
}
export interface TraceBatch {
  id: string;
  created_at: string;
  traces: Trace[];
}
export interface ReviewEvent {
  id: string;
  object_id: string;
  actor: string;
  action: string;
  revision: number;
  created_at: string;
}
export interface Comparison {
  compatible: boolean;
  reasons: string[];
  matched_cases: number;
  left_cases: number;
  right_cases: number;
  changes: {
    case_id: string;
    metric: string;
    left: MetricResult;
    right: MetricResult;
  }[];
}
