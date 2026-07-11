import { SignalsConsole } from "../../../components/dashboard/SignalsConsole";
import { Suspense } from "react";

export default function SignalsPage() {
  return (
    <Suspense fallback={null}>
      <SignalsConsole />
    </Suspense>
  );
}
