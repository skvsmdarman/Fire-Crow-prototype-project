import { AuthConsole } from "../../components/auth/AuthConsole";
import { Suspense } from "react";

export default function SignInPage() {
  return (
    <Suspense fallback={null}>
      <AuthConsole mode="signin" />
    </Suspense>
  );
}
