import { BlockerNotice } from "../components/OperatorPrimitives";

export function ErrorState() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="rounded-md border border-risk/30 bg-risk/10 p-4 text-sm text-risk">
        Nie udało się połączyć z WILQ.
      </div>
    </main>
  );
}

export function InlineErrorState({ message }: { message: string }) {
  return <BlockerNotice message={message} />;
}
