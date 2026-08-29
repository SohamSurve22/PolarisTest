const TO_VIEW = {
  covered: "covered",
  partial: "weak",
  missing: "missing",
};

function childrenOf(edges) {
  const map = new Map();
  for (const edge of edges || []) {
    if (!map.has(edge.source)) {
      map.set(edge.source, []);
    }
    map.get(edge.source).push(edge.target);
  }
  return map;
}

function rollup(statuses) {
  const set = new Set(statuses.filter(Boolean));
  if (!set.size) {
    return null;
  }
  if (set.size === 1) {
    return [...set][0];
  }
  if (set.has("weak") || (set.has("covered") && set.has("missing"))) {
    return "weak";
  }
  if (set.has("missing")) {
    return "missing";
  }
  return "covered";
}

function rollupGraph(nodes, edges, leafKind) {
  const kids = childrenOf(edges);
  const byId = new Map(nodes.map((node) => [node.id, { ...node }]));

  function statusOf(id, seen) {
    if (seen.has(id)) {
      const existing = byId.get(id);
      return existing && existing.status && existing.status !== "neutral" ? existing.status : null;
    }
    seen.add(id);
    const node = byId.get(id);
    if (!node) {
      return null;
    }
    if (node.kind === leafKind) {
      return node.status && node.status !== "neutral" && node.status !== "extra" ? node.status : null;
    }
    const childStatuses = (kids.get(id) || [])
      .map((childId) => statusOf(childId, seen))
      .filter(Boolean);
    const rolled = rollup(childStatuses);
    if (rolled) {
      node.status = rolled;
    }
    return rolled;
  }

  const seen = new Set();
  for (const node of byId.values()) {
    if (node.kind !== leafKind) {
      statusOf(node.id, seen);
    }
  }
  return [...byId.values()];
}

export function paintIdealFromAnalysis(ideal, analysis) {
  if (!ideal?.nodes || !analysis?.obligations?.length) {
    return ideal;
  }
  const byOid = new Map(
    analysis.obligations.map((row) => [row.obligation_id, TO_VIEW[row.status] || "missing"]),
  );
  const leaves = ideal.nodes.map((node) => {
    if (node.kind !== "law_chunk") {
      return { ...node, status: "neutral" };
    }
    return { ...node, status: byOid.get(node.id) || "neutral" };
  });
  return { ...ideal, nodes: rollupGraph(leaves, ideal.edges, "law_chunk") };
}

export function paintPolicyFromAnalysis(policy, analysis) {
  if (!policy?.nodes || !analysis?.obligations?.length) {
    return policy;
  }
  const coveredSections = new Set();
  const gapSections = new Set();
  for (const row of analysis.obligations) {
    const bucket = row.status === "covered" ? coveredSections : gapSections;
    for (const clauseId of row.matched_clause_ids || []) {
      const sectionId = String(clauseId).split("_C")[0];
      if (sectionId) {
        bucket.add(sectionId);
      }
    }
  }

  const leaves = policy.nodes.map((node) => {
    if (node.kind !== "section") {
      return node.kind === "document" ? node : { ...node, status: "neutral" };
    }
    const sectionId = node.extra?.section_id || String(node.id).replace(/^section:/, "");
    const hitCovered = coveredSections.has(sectionId);
    const hitGap = gapSections.has(sectionId);
    let status = "extra";
    if (hitCovered && hitGap) {
      status = "weak";
    } else if (hitCovered) {
      status = "covered";
    } else if (hitGap) {
      status = "missing";
    }
    return { ...node, status };
  });
  return { ...policy, nodes: rollupGraph(leaves, policy.edges, "section") };
}
