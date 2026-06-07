import React from "react";
import Button from "../../components/ui/Button";

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        style={{
          width: "100%",
          maxWidth: "400px",
          background: "#18181b",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: "8px",
          padding: "24px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
        }}
      >
        <h2 id="confirm-dialog-title" style={{ fontSize: "16px", fontWeight: 600, color: "#ffffff", margin: 0 }}>
          {title}
        </h2>
        <p style={{ fontSize: "13px", color: "rgba(255, 255, 255, 0.7)", margin: 0, lineHeight: 1.5 }}>
          {message}
        </p>
        <div style={{ display: "flex", justifyContent: "end", gap: "10px", marginTop: "8px" }}>
          <Button variant="ghost" type="button" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button variant="danger" type="button" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
export default ConfirmDialog;
