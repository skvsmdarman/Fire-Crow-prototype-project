import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthConsole } from "../../components/auth/AuthConsole";

export const metadata: Metadata = {
  title: "Sign In — Fire Crow",
  description: "Sign in to your Fire Crow workspace using GitHub or Google. Access your security audits, findings, and client-ready reports.",
};

export default function SignInPage() {
  return (
    <Suspense fallback={null}>
      <AuthConsole mode="signin" />
    </Suspense>
  );
}
