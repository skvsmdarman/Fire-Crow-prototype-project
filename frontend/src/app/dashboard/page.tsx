import { DashboardConsole } from "../../components/dashboard/DashboardConsole";
import { Suspense } from "react";

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardConsole />
    </Suspense>
  );
}
