export interface PolicyContext {
  privacy_policy_version: string;
  providers: {
    github: boolean;
    google: boolean;
    password: boolean;
  };
  terms_version: string;
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
