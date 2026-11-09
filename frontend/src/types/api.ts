export type ScanStatus = "pending" | "clean" | "infected" | "skipped" | "error";
export type DocumentStatus = "active" | "deleted" | "archived" | "purged";
export type Permission = "read" | "edit";
export type UserRole = "admin" | "owner" | "viewer";

export interface DocumentVersion {
  id: string;
  version_number: number;
  original_filename: string;
  file_size_bytes: number;
  verified_content_type: string;
  checksum_sha256: string;
  scan_status: ScanStatus;
  created_at: string;
}

export interface Document {
  id: string;
  display_name: string;
  description: string;
  status: DocumentStatus;
  owner_id: string;
  category_id: string | null;
  created_at: string;
  updated_at: string;
  current_version: DocumentVersion | null;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface Grant {
  id: string;
  document_id: string;
  grantee_id: string;
  grantor_id: string;
  permission: Permission;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  revocation_reason: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface AuditEvent {
  id: string;
  sequence: number;
  occurred_at: string;
  actor_id: string | null;
  actor_email: string | null;
  action: string;
  outcome: string;
  target_type: string | null;
  target_id: string | null;
  correlation_id: string | null;
}

export interface AuditListResponse {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChainVerifyResult {
  valid: boolean;
  events_checked: number;
  from_sequence?: number;
  to_sequence?: number;
  chain_head_hash?: string;
  anomalies: Array<{ type: string; sequence?: number; detail: string }>;
}
