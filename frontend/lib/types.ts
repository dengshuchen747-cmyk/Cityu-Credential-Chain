export type Campaign = {
  id: number;
  slug: string;
  title: string;
  description: string;
  credential_type: string;
  issuer_wallet: string;
  status: string;
  starts_at: string | null;
  ends_at: string | null;
  max_claims: number | null;
  metadata_uri: string;
  created_at: string;
};

export type Claim = {
  id: number;
  campaign_id: number;
  student_wallet: string;
  student_name: string;
  student_email: string;
  evidence_hash: string;
  status: string;
  review_note: string;
  submitted_at: string;
  reviewed_at: string | null;
};

export type Verification = {
  token_id: number;
  chain_available: boolean;
  valid: boolean;
  hash_matches: boolean;
  revoked: boolean;
  student_wallet: string;
  issuer_wallet: string;
  issued_at: string | null;
  metadata_uri: string;
  transaction_hash: string;
};

export type Credential = {
  id: number;
  claim_id: number;
  token_id: number;
  contract_address: string;
  network: string;
  transaction_hash: string;
  data_hash: string;
  metadata_uri: string;
  issuer_wallet: string;
  issued_at: string;
  revoked_at: string | null;
};

export type ChainTransaction = {
  to: string;
  data: string;
  chain_id: number;
};

export type CredentialIssuePreparation = {
  claim_id: number;
  student_wallet: string;
  data_hash: string;
  metadata_uri: string;
  transaction: ChainTransaction;
};

export type CredentialRevokePreparation = {
  token_id: number;
  reason: string;
  reason_hash: string;
  transaction: ChainTransaction;
};

export type PublicCredential = {
  token_id: number;
  campaign_title: string;
  campaign_description: string;
  credential_type: string;
  student_wallet: string;
  issuer_wallet: string;
  issued_at: string | null;
  valid: boolean;
  revoked: boolean;
  chain_available: boolean;
  metadata_uri: string;
  transaction_hash: string;
  contract_address: string;
  network: string;
};

export type StudentCredentialPortfolio = {
  student_wallet: string;
  credentials: PublicCredential[];
};

export type IssuerRoleRecord = {
  wallet_address: string;
  label: string;
  active: boolean;
  transaction_hash: string;
  updated_at: string | null;
};

export type IssuerRolePreparation = {
  wallet_address: string;
  action: "grant" | "revoke";
  transaction: ChainTransaction;
};

export type ShareView = {
  token_id: number;
  credential_type: string;
  student_name: string;
  student_email: string;
  issuer_wallet: string;
  issued_at: string;
  revoked: boolean;
};
