import { describe, expect, it } from "vitest";

import { createWilqQueryClient } from "../lib/queryClient";

describe("WILQ query client defaults", () => {
  it("uses short server-state cache defaults without overriding test config", () => {
    const client = createWilqQueryClient({
      defaultOptions: {
        queries: {
          gcTime: Infinity,
          retry: false
        }
      }
    });

    expect(client.getDefaultOptions().queries?.staleTime).toBe(30_000);
    expect(client.getDefaultOptions().queries?.refetchOnWindowFocus).toBe(false);
    expect(client.getDefaultOptions().queries?.gcTime).toBe(Infinity);
    expect(client.getDefaultOptions().queries?.retry).toBe(false);
    client.clear();
  });
});
