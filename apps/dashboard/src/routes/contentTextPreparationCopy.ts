/**
 * Internal planning blockers may mention proposals, digests, or legacy review
 * stages. The marketer only needs a concrete recovery action before creating
 * text; the planning machinery remains server-owned.
 */
export function textPreparationRecovery(code: string | undefined): string {
  if (code === "service_card_not_approved") {
    return "Wybierz zatwierdzone źródło wiedzy, na którym ma oprzeć się tekst.";
  }
  if (code?.includes("source") || code?.includes("inventory")) {
    return "Odśwież źródła tej strony, a potem spróbuj ponownie przygotować tekst.";
  }
  return "Odśwież dane do tekstu i spróbuj ponownie.";
}
