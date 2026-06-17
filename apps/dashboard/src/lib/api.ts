import {
  ActionObjectSchema,
  CommandCenterResponseSchema,
  ConnectorStatusSchema,
  EvidenceSchema,
  ExpertRuleSchema,
  KnowledgeCardSchema,
  MarketingPlaybookSchema,
  OpportunitySchema,
  WorkflowRunSchema,
  WorkflowSchema,
  type ActionObject,
  type CommandCenterResponse,
  type ConnectorStatus,
  type Evidence,
  type ExpertRule,
  type KnowledgeCard,
  type MarketingPlaybook,
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

export function getEvidence(): Promise<Evidence[]> {
  return apiGet("/api/evidence", z.array(EvidenceSchema));
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

export function getKnowledgeCards(): Promise<KnowledgeCard[]> {
  return apiGet("/api/knowledge/cards", z.array(KnowledgeCardSchema));
}

export function getKnowledgePlaybooks(): Promise<MarketingPlaybook[]> {
  return apiGet("/api/knowledge/playbooks", z.array(MarketingPlaybookSchema));
}

export type {
  ActionObject,
  CommandCenterResponse,
  ConnectorStatus,
  Evidence,
  ExpertRule,
  KnowledgeCard,
  MarketingPlaybook,
  Opportunity,
  Workflow,
  WorkflowRun
};
