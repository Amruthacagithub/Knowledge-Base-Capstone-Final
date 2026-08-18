import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";

import TrustDetails from "./TrustDetails";


describe("TrustDetails", () => {
  test("renders verification states, evidence links, and route trace", () => {
    const html = renderToStaticMarkup(
      <TrustDetails
        claims={[
          {
            id: "claim-1",
            text: "PTO is 20 days.",
            status: "supported",
            confidence: 0.98,
            evidence_ids: ["chunk-1"],
          },
          {
            id: "claim-2",
            text: "PTO carries over.",
            status: "insufficient",
            confidence: 0.81,
            evidence_ids: [],
          },
        ]}
        citations={[{ marker: 1, chunk_id: "chunk-1" }]}
        queryPlan={{
          route: "temporal",
          subqueries: ["PTO history"],
          corrective_retrieval_used: true,
          trace_ids: [],
          execution_trace_id: "trace-1",
        }}
        evidenceGraph={{
          paths: [{
            entity_ids: ["billing", "stripe"],
            relationship_ids: ["rel-1"],
            entities: [
              { id: "billing", name: "Billing Service" },
              { id: "stripe", name: "Stripe" },
            ],
            relationships: [{ id: "rel-1", source_entity_id: "billing", target_entity_id: "stripe", type: "depends_on" }],
            score: 0.91,
          }],
        }}
        onCitationClick={() => {}}
      />
    );

    expect(html).toContain("Supported");
    expect(html).toContain("Insufficient");
    expect(html).toContain("Evidence [1]");
    expect(html).toContain("temporal");
    expect(html).toContain("trace-1");
    expect(html).toContain("Billing Service");
    expect(html).toContain("depends on");
    expect(html).toContain("Stripe");
  });
});