export function ContentWorkflowControlButton({
  label,
  disabledReason,
  pending,
  onClick
}: {
  label: string;
  disabledReason: string | null;
  pending: boolean;
  onClick: () => void;
}) {
  const disabled = Boolean(disabledReason) || pending;
  return (
    <div>
      <button
        type="button"
        className="w-full rounded-md border border-action bg-action px-4 py-2 text-sm font-semibold text-white disabled:border-line disabled:bg-surface disabled:text-slate-500"
        disabled={disabled}
        onClick={onClick}
      >
        {pending ? "Zapisywanie..." : label}
      </button>
      {disabledReason ? <p className="mt-1 text-xs leading-5 text-slate-500">{disabledReason}</p> : null}
    </div>
  );
}
