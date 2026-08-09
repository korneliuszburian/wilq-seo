import {
  WorkflowRunSchema,
  WorkflowSchema,
  type Workflow,
  type WorkflowRun
} from "@wilq/shared-schemas";
import { z } from "zod";

import { apiGet } from "./common";

export function getWorkflows(): Promise<Workflow[]> {
  return apiGet("/api/workflows", z.array(WorkflowSchema));
}

export function getWorkflowRuns(): Promise<WorkflowRun[]> {
  return apiGet("/api/workflow-runs", z.array(WorkflowRunSchema));
}
