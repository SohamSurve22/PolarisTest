export function countsBanner(counts) {
  const parts = [
    `Covered ${counts.covered ?? 0}`,
    `Partial ${counts.partial ?? 0}`,
    `Missing ${counts.missing ?? 0}`,
    `Violation ${counts.violation ?? 0}`,
    `Conflict ${counts.conflict ?? 0}`,
    `N/A ${counts.not_applicable ?? 0}`,
  ];
  if (counts.undetermined) {
    parts.push(`Undetermined ${counts.undetermined}`);
  }
  return parts.join(" · ");
}
