import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { getCurrentMaterialText, type ActionObject } from "../lib/api";

const PreviewIdentitySchema = z.object({ work_item_id: z.string().min(1) });

export function useCurrentMaterialText(action: ActionObject) {
  const parsed = PreviewIdentitySchema.safeParse(action.payload.material_review_preview);
  const workItemId = parsed.success ? parsed.data.work_item_id : null;
  const query = useQuery({
    queryKey: ["current-material-text", action.id, workItemId],
    queryFn: () => getCurrentMaterialText(workItemId!, action.id),
    enabled: workItemId !== null
  });
  return { query, workItemId };
}
