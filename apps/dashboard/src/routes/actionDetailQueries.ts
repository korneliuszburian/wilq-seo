import { useQuery } from "@tanstack/react-query";

import { getAction, getActionMutationReadiness } from "../lib/api";

export function useActionDetailQueries(actionId: string) {
  const action = useQuery({
    queryKey: ["actions", actionId],
    queryFn: () => getAction(actionId)
  });
  const mutationReadiness = useQuery({
    queryKey: ["actions", actionId, "mutation-readiness"],
    queryFn: () => getActionMutationReadiness(actionId)
  });

  return { action, mutationReadiness };
}
