import { AuthConsole } from "../../components/auth/AuthConsole";
import { Suspense } from "react";

export default function SignUpPage() {
  return (
    <Suspense fallback={null}>
      <AuthConsole mode="signup" />
    </Suspense>
  );
}
