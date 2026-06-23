import os
import re

def rewrite_signin():
    path = "frontend/src/app/signin/page.tsx"
    with open(path, "r") as f:
        content = f.read()

    replacement = """
  const oauthHref = (provider: "github" | "google") => {
    let authUrl = buildApiUrl(`/auth/${provider}?privacy_policy_accepted=true&privacy_policy_version=${activePrivacyVersion}`);
    if (typeof window !== "undefined") {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      authUrl += `&timezone=${encodeURIComponent(tz)}&region=${encodeURIComponent(detectRegionFromTimezone(tz))}`;
    }
    return authUrl;
  };
"""
    # Regex to replace the entire `const oauthHref = ... };` block
    pattern = re.compile(r'const oauthHref = \(provider: "github" \| "google"\) => \{[\s\S]*?\n  \};\n')
    new_content = pattern.sub(replacement.lstrip() + "\n", content)

    with open(path, "w") as f:
        f.write(new_content)
    print(f"Updated {path}")

def rewrite_dashboard():
    path = "frontend/src/app/dashboard/page.tsx"
    with open(path, "r") as f:
        content = f.read()

    # Find the hook useAuthSession
    # and add a useEffect for redirecting if not authenticated.

    # We will inject this right after `const session = useAuthSession();`
    # Also we will early return null to prevent flashing if !session.hasDashboardSession

    injection = """
  useEffect(() => {
    if (!session.hasDashboardSession) {
      router.push("/signin");
    }
  }, [session.hasDashboardSession, router]);

  if (!session.hasDashboardSession) return null;
"""

    if "if (!session.hasDashboardSession) return null;" not in content:
        content = content.replace(
            "const session = useAuthSession();",
            "const session = useAuthSession();\n" + injection
        )

        with open(path, "w") as f:
            f.write(content)
        print(f"Updated {path}")

def rewrite_client_audit_run():
    path = "frontend/src/app/dashboard/audits/[jobId]/ClientAuditRunPage.tsx"
    with open(path, "r") as f:
        content = f.read()

    injection = """
  useEffect(() => {
    if (!session.hasDashboardSession) {
      router.push("/signin");
    }
  }, [session.hasDashboardSession, router]);

  if (!session.hasDashboardSession) return null;
"""

    if "if (!session.hasDashboardSession) return null;" not in content:
        content = content.replace(
            "const session = useAuthSession();",
            "const session = useAuthSession();\n" + injection
        )

        with open(path, "w") as f:
            f.write(content)
        print(f"Updated {path}")

def rewrite_endpoints():
    path = "frontend/src/shared/api/endpoints.ts"
    with open(path, "r") as f:
        content = f.read()

    new_content = content.replace(
        'cancel: (jobId: string) => "/audit/job/" + jobId + "/cancel",',
        'cancel: (jobId: string) => "/audit/job/" + jobId,'
    )
    with open(path, "w") as f:
        f.write(new_content)
    print(f"Updated {path}")

def rewrite_backend_env():
    path = "backend/.env.example"
    with open(path, "r") as f:
        content = f.read()

    # The user asked to ensure specific variables are present:
    # FRONTEND_URL=<frontend origin>
    # CORS_ORIGINS=<frontend origin>
    # GITHUB_CLIENT_ID
    # GITHUB_CLIENT_SECRET
    # GOOGLE_CLIENT_ID
    # GOOGLE_CLIENT_SECRET
    # SECRET_KEY
    # ENCRYPTION_KEY
    # DATABASE_URL
    # And add OAuth provider console redirect URI notes.

    notes = """
# OAuth Provider Console Redirect URI Notes:
# GitHub callback: <backend-origin>/api/v1/auth/github/callback
# Google callback: <backend-origin>/api/v1/auth/google/callback
"""
    if "OAuth Provider Console" not in content:
        content += notes

    with open(path, "w") as f:
        f.write(content)
    print(f"Updated {path}")

def rewrite_frontend_env():
    path = "frontend/.env.example"
    with open(path, "r") as f:
        content = f.read()

    if "NEXT_PUBLIC_API_URL=" not in content:
        content += "\nNEXT_PUBLIC_API_URL=<backend origin>/api/v1\n"
    elif "NEXT_PUBLIC_API_URL=<backend origin>/api/v1" not in content:
        content = content.replace(
            "NEXT_PUBLIC_API_URL=https://fire-crow.onrender.com/api/v1",
            "NEXT_PUBLIC_API_URL=<backend origin>/api/v1"
        )
    with open(path, "w") as f:
        f.write(content)
    print(f"Updated {path}")

def main():
    rewrite_signin()
    rewrite_dashboard()
    rewrite_client_audit_run()
    rewrite_endpoints()
    rewrite_backend_env()
    rewrite_frontend_env()

if __name__ == "__main__":
    main()
