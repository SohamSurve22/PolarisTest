export function primaryMatch(row) {
  const matches = row.matched_clauses || [];
  const counters = row.counter_evidence || [];
  if ((row.status === "violation" || row.status === "conflict") && counters.length) {
    return counters[0];
  }
  if (matches.length) {
    return matches[0];
  }
  if (counters.length) {
    return counters[0];
  }
  return null;
}
