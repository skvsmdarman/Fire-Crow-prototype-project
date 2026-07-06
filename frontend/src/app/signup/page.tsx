import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthConsole } from "../../components/auth/AuthConsole";

export const metadata: Metadata = {
  title: "Create Account — Fire Crow",
  description: "Create your Fire Crow account using GitHub or Google. Start scanning your code for security vulnerabilities in minutes.",
};

export default function SignUpPage() {
  return (
    <Suspense fallback={null}>
      <AuthConsole mode="signup" />
    </Suspense>
  );
}
