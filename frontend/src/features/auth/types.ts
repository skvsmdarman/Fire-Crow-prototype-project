export interface PolicyContext {
  privacy_policy_version: string;
  terms_version: string;
  providers: {
    github: boolean;
    google: boolean;
    password: boolean;
  };
}

export interface AuthSessionPayload {
  access_token: string;
  user_id: string;
  username: string;
}

export interface UserMe {
  id: string;
  username: string;
  email?: string;
}
