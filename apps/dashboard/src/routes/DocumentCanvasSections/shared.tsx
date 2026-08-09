import type {
  ContentDocumentWorkspace,
  ContentTargetDiscovery,
  ContentTargetDraftPreview,
  ContentTargetMappingPreview
} from "../../lib/api";

export type {
  ContentDocumentWorkspace,
  ContentTargetDiscovery,
  ContentTargetDraftPreview,
  ContentTargetMappingPreview
};

export type TargetMappingTarget = NonNullable<ContentTargetMappingPreview["target"]>;

export type TargetMappingSelection = {
  layoutName: string;
  targetSectionIndex: number | null;
  fields: Record<string, string>;
};

export type TargetMappingSelections = Record<string, TargetMappingSelection>;
