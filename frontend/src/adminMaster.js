export const MASTER_STATUS_TABS = Object.freeze([
  Object.freeze({ value: "all", label: "All" }),
  Object.freeze({ value: "pending_registration", label: "Pending Registration" }),
  Object.freeze({ value: "active", label: "Active" }),
  Object.freeze({ value: "inactive", label: "Inactive" }),
  Object.freeze({ value: "needs_attention", label: "Needs Attention" }),
]);

export const MASTER_PAGE_SIZES = Object.freeze([25, 50, 100]);

const firstValue = (value) => (Array.isArray(value) ? value[0] : value);

export function queryValue(query, key, fallback = "") {
  const value = firstValue(query?.[key]);
  return typeof value === "string" ? value : fallback;
}

export function positiveInteger(value, fallback) {
  const parsed = Number.parseInt(firstValue(value), 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export function masterQueryFromRouter(query, kind) {
  const defaultSort = "name";
  const result = {
    search: queryValue(query, "search"),
    status: MASTER_STATUS_TABS.some((tab) => tab.value === queryValue(query, "status"))
      ? queryValue(query, "status")
      : "all",
    college: queryValue(query, "college"),
    registration_status: queryValue(query, "registration_status"),
    sort: queryValue(query, "sort", defaultSort),
    order: queryValue(query, "order", "asc") === "desc" ? "desc" : "asc",
    page: positiveInteger(query?.page, 1),
    page_size: MASTER_PAGE_SIZES.includes(positiveInteger(query?.page_size, 25))
      ? positiveInteger(query?.page_size, 25)
      : 25,
  };
  if (kind === "student") {
    Object.assign(result, {
      programme_id: queryValue(query, "programme_id"),
      admission_year: queryValue(query, "admission_year"),
      present_year: queryValue(query, "present_year"),
      academic_status: queryValue(query, "academic_status"),
    });
  } else {
    Object.assign(result, {
      department: queryValue(query, "department"),
      designation: queryValue(query, "designation"),
      employment_status: queryValue(query, "employment_status"),
      responsibility: queryValue(query, "responsibility"),
    });
  }
  return result;
}

export function compactQuery(query) {
  return Object.fromEntries(
    Object.entries(query).filter(([, value]) => value !== "" && value !== null && value !== undefined),
  );
}

export function isMasterPageResponse(value) {
  return Boolean(value)
    && typeof value === "object"
    && Array.isArray(value.items)
    && Number.isInteger(value.total)
    && value.total >= 0
    && Number.isInteger(value.page)
    && MASTER_PAGE_SIZES.includes(value.page_size)
    && value.items.every((item) => (
      item
      && typeof item === "object"
      && Number.isInteger(item.id)
      && typeof item.name === "string"
      && typeof item.registration_status === "string"
      && typeof item.is_active === "boolean"
      && (item.mobile_masked === null || typeof item.mobile_masked === "string")
    ));
}

export function isOperationsSummary(value) {
  const validMetric = (metric, fields) => metric
    && typeof metric === "object"
    && fields.every((field) => Number.isInteger(metric[field]) && metric[field] >= 0);
  const validRecent = (collection) => Array.isArray(collection)
    && collection.every((item) => item && Number.isInteger(item.id) && typeof item.title === "string" && typeof item.status === "string");
  return Boolean(value)
    && typeof value === "object"
    && typeof value.generated_at === "string"
    && validMetric(value.students, ["total", "active", "pending_activation"])
    && validMetric(value.faculty, ["total", "active", "pending_activation"])
    && validMetric(value.programmes, ["total", "active", "draft"])
    && validMetric(value.attention_required, ["total"])
    && Array.isArray(value.attention)
    && value.attention.every((item) => item && typeof item.key === "string" && typeof item.label === "string" && Number.isInteger(item.count) && typeof item.href === "string")
    && Array.isArray(value.readiness)
    && value.readiness.every((item) => item && typeof item.key === "string" && typeof item.label === "string" && ["complete", "needs_attention", "unavailable"].includes(item.status) && typeof item.detail === "string")
    && validMetric(value.academic_operations, ["programmes", "subjects", "coordinator_assignments", "expert_assignments"])
    && value.recent_operations
    && validRecent(value.recent_operations.assessments)
    && validRecent(value.recent_operations.learning_sessions)
    && validMetric(value.early_warning, ["students_requiring_attention"])
    && value.recent_admin_activity
    && typeof value.recent_admin_activity.available === "boolean"
    && Array.isArray(value.recent_admin_activity.items)
    && Number.isInteger(value.unread_notifications)
    && value.unread_notifications >= 0;
}

export function downloadBlob(blob, filename) {
  if (typeof window === "undefined") return;
  const href = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(href);
}
