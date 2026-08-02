export type Role = "ADMIN" | "DEVELOPER" | "CUSTOMER";

export interface Profile {
  profile_picture_url: string;
  phone: string;
  country: string;
  timezone: string;
  language: string;
}

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  is_email_verified: boolean;
  date_joined: string;
  profile: Profile;
}

export interface Session {
  id: number;
  user_agent: string;
  ip_address: string | null;
  created_at: string;
  last_seen_at: string;
  is_current: boolean;
}

export interface ApiErrorBody {
  detail?: string;
  code?: string;
  [field: string]: unknown;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  body: ApiErrorBody;

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail ?? "Request failed");
    this.status = status;
    this.code = body.code;
    this.body = body;
  }
}