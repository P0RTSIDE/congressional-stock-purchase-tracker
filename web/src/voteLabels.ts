/** Plain labels for congressional roll-call positions. */
const VOTE_LABELS: Record<string, string> = {
  yea: "Yea",
  nay: "Nay",
  present: "Present",
  not_voting: "Did not vote",
};

export function votePositionLabel(
  position?: string | null,
  label?: string | null,
): string | undefined {
  if (label && label !== "Not available") return label;
  if (!position) return undefined;
  return VOTE_LABELS[position.toLowerCase()] ?? position.replace(/_/g, " ");
}
