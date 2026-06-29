import { SettingsConsole } from "../../../components/dashboard/SettingsConsole";
import { Suspense } from "react";

export default function SettingsPage() {
  return (
    <Suspense fallback={null}>
      <SettingsConsole />
    </Suspense>
  );
}
