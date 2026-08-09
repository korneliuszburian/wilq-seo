import {
  KnowledgeCardSchema,
  KnowledgeOperatingMapResponseSchema,
  KnowledgeSourceFactViewSchema,
  KnowledgeSourceMaterialReadinessSchema,
  KnowledgeSourceMaterialViewSchema,
  MarketingPlaybookSchema,
  type KnowledgeCard,
  type KnowledgeOperatingMapResponse,
  type KnowledgeSourceFactView,
  type KnowledgeSourceMaterialReadiness,
  type KnowledgeSourceMaterialView,
  type MarketingPlaybook
} from "@wilq/shared-schemas";
import { z } from "zod";

import { apiGet } from "./common";

export function getKnowledgeCards(): Promise<KnowledgeCard[]> {
  return apiGet("/api/knowledge/cards", z.array(KnowledgeCardSchema));
}

export function getKnowledgeSourceFacts(): Promise<KnowledgeSourceFactView[]> {
  return apiGet("/api/knowledge/source-facts", z.array(KnowledgeSourceFactViewSchema));
}

export function getKnowledgeSourceMaterials(): Promise<KnowledgeSourceMaterialView[]> {
  return apiGet(
    "/api/knowledge/source-materials",
    z.array(KnowledgeSourceMaterialViewSchema)
  );
}

export function getKnowledgeSourceMaterialReadiness(): Promise<KnowledgeSourceMaterialReadiness> {
  return apiGet(
    "/api/knowledge/source-materials/readiness",
    KnowledgeSourceMaterialReadinessSchema
  );
}

export function getKnowledgePlaybooks(): Promise<MarketingPlaybook[]> {
  return apiGet("/api/knowledge/playbooks", z.array(MarketingPlaybookSchema));
}

export function getKnowledgeOperatingMap(): Promise<KnowledgeOperatingMapResponse> {
  return apiGet("/api/knowledge/operating-map", KnowledgeOperatingMapResponseSchema);
}
