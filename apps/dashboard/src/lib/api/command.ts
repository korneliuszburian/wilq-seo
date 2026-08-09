import {
  CommandCenterResponseSchema,
  MarketingBriefSchema,
  OpportunitySchema,
  TacticalQueueResponseSchema,
  type CommandCenterResponse,
  type MarketingBrief,
  type Opportunity,
  type TacticalQueueResponse
} from "@wilq/shared-schemas";
import { z } from "zod";

import { apiGet } from "./common";

export function getCommandCenter(): Promise<CommandCenterResponse> {
  return apiGet("/api/dashboard/command-center", CommandCenterResponseSchema);
}

export function getMarketingBrief(): Promise<MarketingBrief> {
  return apiGet("/api/marketing/brief", MarketingBriefSchema);
}

export function getTacticalQueue(): Promise<TacticalQueueResponse> {
  return apiGet("/api/marketing/tactical-queue", TacticalQueueResponseSchema);
}

export function getOpportunities(): Promise<Opportunity[]> {
  return apiGet("/api/opportunities", z.array(OpportunitySchema));
}
