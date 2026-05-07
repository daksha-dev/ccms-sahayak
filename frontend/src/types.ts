export type Decision = "APPROVED" | "EDITED" | "REJECTED";

export type ReviewField = {
  id: number;
  field_name: string;
  extracted_value: unknown;
  confidence_score: number;
  source_page: number | null;
  source_bbox: number[] | null;
  extraction_source: string;
  conflict: boolean;
  decision: Decision | null;
};

export type ActionPlanItem = {
  directive_type: string;
  recommended_action: string;
  responsible_authority: string | null;
  deadline_date: string | null;
  priority_level: string;
  notes: string | null;
};

export type ReviewResponse = {
  job_id: number;
  pdf_url: string;
  extraction_status: string;
  overall_confidence: number;
  fields: ReviewField[];
  action_plan: ActionPlanItem[];
};

export type DashboardRecord = {
  id: number;
  judgment_id: number;
  case_number: string | null;
  department: string | null;
  urgency_band: string;
  appeal_deadline: string | null;
  action_summary_en: string;
  action_summary_kn: string | null;
  verified_at: string;
  audit_trail: Array<Record<string, unknown>>;
};

export type DashboardStats = {
  total_active_cases: number;
  red_urgency: number;
  amber_urgency: number;
  pending_appeals: number;
};
