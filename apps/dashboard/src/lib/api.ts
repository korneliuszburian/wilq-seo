import {
  ActionObjectSchema,
  CommandCenterResponseSchema,
  ConnectorStatusSchema,
  ExpertRuleSchema,
  OpportunitySchema,
  WorkflowRunSchema,
  WorkflowSchema,
  type ActionObject,
  type CommandCenterResponse,
  type ConnectorStatus,
  type ExpertRule,
  type Opportunity,
  type Workflow,
  type WorkflowRun
} from "@wilq/shared-schemas";
import { z } from "zod";

const API_BASE = import.meta.env.VITE_WILQ_API_BASE_URL ?? "http://127.0.0.1:8000";

async function apiGet<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }
  return schema.parse(await response.json());
}

export function getCommandCenter(): Promise<CommandCenterResponse> {
  return apiGet("/api/dashboard/command-center", CommandCenterResponseSchema);
}

export function getConnectors(): Promise<ConnectorStatus[]> {
  return apiGet("/api/connectors", z.array(ConnectorStatusSchema));
}

export function getOpportunities(): Promise<Opportunity[]> {
  return apiGet("/api/opportunities", z.array(OpportunitySchema));
}

export function getActions(): Promise<ActionObject[]> {
  return apiGet("/api/actions", z.array(ActionObjectSchema));
}

export function getWorkflows(): Promise<Workflow[]> {
  return apiGet("/api/workflows", z.array(WorkflowSchema));
}

export function getWorkflowRuns(): Promise<WorkflowRun[]> {
  return apiGet("/api/workflow-runs", z.array(WorkflowRunSchema));
}

export function getExpertRules(): Promise<ExpertRule[]> {
  return apiGet("/api/expert/rules", z.array(ExpertRuleSchema));
}

export type {
  ActionObject,
  CommandCenterResponse,
  ConnectorStatus,
  ExpertRule,
  Opportunity,
  Workflow,
  WorkflowRun
};
