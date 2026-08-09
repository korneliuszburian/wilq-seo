import type { ActionObject } from "../../lib/api";

export type { ActionObject };

export type ActionPanelProps = {
  action: ActionObject;
};

export type PayloadRecord = Record<string, unknown>;
