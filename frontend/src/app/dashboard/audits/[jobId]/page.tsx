import { AuditRunPage } from "../../../../components/dashboard/AuditRunPage";
import { Suspense } from "react";

export function generateStaticParams() {
  return [{ jobId: "default" }];
}

export default async function AuditDetailPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  return (
    <Suspense fallback={null}>
      <AuditRunPage jobId={jobId} />
    </Suspense>
  );
}
