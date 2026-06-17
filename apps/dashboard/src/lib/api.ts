import {
  ActionObjectSchema,
  ActionValidationResultSchema,
  CommandCenterResponseSchema,
  ConnectorRefreshRunSchema,
  ConnectorStatusSchema,
  EvidenceSchema,
  ExpertRuleSchema,
  KnowledgeCardSchema,
  MarketingBriefSchema,
  MarketingPlaybookSchema,
  MetricFactSchema,
  MetricStoreStatusSchema,
  OpportunitySchema,
  WorkflowRunSchema,
  WorkflowSchema,
  type ActionObject,
  type ActionValidationResult,
  type CommandCenterResponse,
  type ConnectorRefreshRun,
  type ConnectorStatus,
  type Evidence,
  type ExpertRule,
  type KnowledgeCard,
  type MarketingBrief,
  type MarketingBriefItem,
  type MarketingPlaybook,
  type MetricFact,
  type MetricStoreStatus,
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

async function apiPost<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }
  return schema.parse(await response.json());
}

export function getCommandCenter(): Promise<CommandCenterResponse> {
  return apiGet("/api/dashboard/command-center", CommandCenterResponseSchema);
}

export function getMarketingBrief(): Promise<MarketingBrief> {
  return apiGet("/api/marketing/brief", MarketingBriefSchema);
}

export function getConnectors(): Promise<ConnectorStatus[]> {
  return apiGet("/api/connectors", z.array(ConnectorStatusSchema));
}

export function getConnectorRefreshRuns(): Promise<ConnectorRefreshRun[]> {
  return apiGet("/api/connectors/refresh-runs", z.array(ConnectorRefreshRunSchema));
}

export function getMetricFacts(limit = 24): Promise<MetricFact[]> {
  return apiGet(`/api/metrics?limit=${limit}`, z.array(MetricFactSchema));
}

export function getMetricStoreStatus(): Promise<MetricStoreStatus> {
  return apiGet("/api/metrics/status", MetricStoreStatusSchema);
}

export function getOpportunities(): Promise<Opportunity[]> {
  return apiGet("/api/opportunities", z.array(OpportunitySchema));
}

export function getActions(): Promise<ActionObject[]> {
  return apiGet("/api/actions", z.array(ActionObjectSchema));
}

export function validateAction(actionId: string): Promise<ActionValidationResult> {
  return apiPost(`/api/actions/${actionId}/validate`, ActionValidationResultSchema);
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
  ActionValidationResult,
  CommandCenterResponse,
  ConnectorRefreshRun,
  ConnectorStatus,
  Evidence,
  ExpertRule,
  KnowledgeCard,
  MarketingBrief,
  MarketingBriefItem,
  MarketingPlaybook,
  MetricFact,
  MetricStoreStatus,
  Opportunity,
  Workflow,
  WorkflowRun
};
