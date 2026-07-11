import { FindingsConsole } from "../../../components/dashboard/FindingsConsole";
import { Suspense } from "react";

export default function FindingsPage() {
  return (
    <Suspense fallback={null}>
      <FindingsConsole />
    </Suspense>
  );
}
