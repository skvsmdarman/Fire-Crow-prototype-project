import React from "react";

export function generateStaticParams() {
  return [{ jobId: "default" }];
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
