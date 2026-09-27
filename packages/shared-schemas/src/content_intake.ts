import { z } from "zod";

const Hex64Schema = z.string().regex(/^[0-9a-f]{64}$/);

function compareCodePoints(left: string, right: string): number {
  const leftPoints = Array.from(left);
  const rightPoints = Array.from(right);
  const shared = Math.min(leftPoints.length, rightPoints.length);
  for (let index = 0; index < shared; index += 1) {
    const difference = (leftPoints[index].codePointAt(0) ?? 0) - (rightPoints[index].codePointAt(0) ?? 0);
    if (difference !== 0) return difference;
  }
  return leftPoints.length - rightPoints.length;
}

export function isSortedAndUnique(values: readonly string[]): boolean {
  return values.every(
    (value, index) => index === 0 || compareCodePoints(values[index - 1], value) < 0
  );
}

export function codePointBoundedString(minimum: number, maximum: number) {
  return z.string().refine(
    (value) => {
      const length = Array.from(value).length;
      return length >= minimum && length <= maximum;
    },
    { message: `String must have ${minimum}..${maximum} Unicode code points.` }
  );
}

export const ContentIntakeAskRequestSchema = z.strictObject({
  request_id: z.guid(),
  ask: codePointBoundedString(3, 2000)
});

export const ContentIntakeFieldProvenanceSchema = z.strictObject({
  field: codePointBoundedString(1, 120),
  provenance: z.enum(["user_input", "evidence", "inference", "unknown"]),
  detail: codePointBoundedString(1, 600),
  evidence_ids: z.array(z.string()).default([])
}).refine(
  (value) => isSortedAndUnique(value.evidence_ids),
  {
    path: ["evidence_ids"],
    message: "Intake provenance evidence IDs must be sorted and unique."
  }
);

export const ContentIntakeBlockerSchema = z.strictObject({
  code: codePointBoundedString(1, 160),
  owner: codePointBoundedString(1, 160),
  detail: codePointBoundedString(1, 600)
});

export const ContentIntakeQueueItemSchema = z.strictObject({
  schema_version: z.literal("wilq_content_intake_v1"),
  queue_id: codePointBoundedString(1, 240),
  request_id: z.guid(),
  input_digest: Hex64Schema,
  actor_id: z.string(),
  actor_trust_level: z.literal("local_unverified"),
  status: z.enum(["queued", "blocked"]),
  ask: codePointBoundedString(3, 2000),
  provenance: z.array(ContentIntakeFieldProvenanceSchema).min(1),
  candidate_work_item_ids: z.array(z.string()).default([]),
  candidate_paths: z.array(z.string()).default([]),
  candidate_public_urls: z.array(z.string()).default([]),
  blockers: z.array(ContentIntakeBlockerSchema).default([]),
  safe_next_step: codePointBoundedString(1, 600),
  generation_allowed: z.literal(false),
  created_at: z.string().datetime({ offset: true })
}).superRefine((item, context) => {
  if (
    item.candidate_work_item_ids.length !== item.candidate_paths.length
    || item.candidate_paths.length !== item.candidate_public_urls.length
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["candidate_paths"],
      message: "Intake candidates must align work item, path and URL."
    });
  }
  if (!isSortedAndUnique(item.candidate_paths)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["candidate_paths"],
      message: "Intake candidate paths must be sorted and unique."
    });
  }
  if (new Set(item.blockers.map((blocker) => blocker.code)).size !== item.blockers.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blockers"],
      message: "Intake blockers must be unique."
    });
  }
  if (item.status === "blocked" && item.blockers.length === 0) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blockers"],
      message: "Blocked intake requests need at least one typed blocker."
    });
  }
  if (item.status === "queued" && item.blockers.length > 0) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blockers"],
      message: "Queued intake requests cannot carry blockers."
    });
  }
});

export type ContentIntakeAskRequest = z.infer<typeof ContentIntakeAskRequestSchema>;
export type ContentIntakeQueueItem = z.infer<typeof ContentIntakeQueueItemSchema>;
