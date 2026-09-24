import type { WriteBackPlan } from "../types/chat";

export function planActionLines(plan: WriteBackPlan): string[] {
  const lines: string[] = [];

  if (plan.needs_doc_update) {
    if (plan.doc_target === "existing" && plan.existing_doc_path) {
      lines.push(`Update ${plan.existing_doc_path}`);
    } else if (plan.doc_target === "new" && plan.new_doc_slug) {
      lines.push(`Create new doc: ${plan.new_doc_slug}`);
    } else {
      lines.push("Update documentation");
    }
  }

  if (plan.needs_roadmap_item) {
    lines.push("Create Linear roadmap item");
  }

  return lines;
}

export function isEmptyWriteBackPlan(plan: WriteBackPlan): boolean {
  return !plan.needs_doc_update && !plan.needs_roadmap_item;
}
