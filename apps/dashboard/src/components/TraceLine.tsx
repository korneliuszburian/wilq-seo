import { Link } from "@tanstack/react-router";

export function TraceLine({
  label,
  values,
  empty = "WILQ nie podał pozycji; sprawdź źródło danych przed decyzją"
}: {
  label: string;
  values: string[];
  empty?: string;
}) {
  return (
    <div className="break-words">
      {label}: {values.length > 0 ? values.join(", ") : empty}
    </div>
  );
}

export function LinkedTraceLine({
  label,
  values,
  kind,
  empty = "WILQ nie podał pozycji; sprawdź źródło danych przed decyzją"
}: {
  label: string;
  values: string[];
  kind: "actions" | "evidence";
  empty?: string;
}) {
  return (
    <div className="break-words">
      {label}:{" "}
      {values.length > 0
        ? values.map((value, index) => (
            <span key={value}>
              {index > 0 ? ", " : ""}
              <Link
                to={kind === "actions" ? "/actions/$actionId" : "/evidence/$evidenceId"}
                params={kind === "actions" ? { actionId: value } : { evidenceId: value }}
                className="font-medium text-action underline-offset-2 hover:underline"
              >
                {traceLinkLabel(kind, index)}
              </Link>
            </span>
          ))
        : empty}
    </div>
  );
}

function traceLinkLabel(kind: "actions" | "evidence", index: number) {
  return kind === "actions" ? `akcja ${index + 1}` : `dowód ${index + 1}`;
}
