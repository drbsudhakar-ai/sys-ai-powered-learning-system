export function profileInitials(name) {
  const words = String(name || "SYS")
    .replace(/\b(?:dr|mr|mrs|ms|prof)\.?\s*/gi, "")
    .trim()
    .split(/[\s.]+/)
    .filter(Boolean);
  return (words.length > 1 ? `${words[0][0]}${words[words.length - 1][0]}` : words[0]?.slice(0, 2) || "SY").toUpperCase();
}

export function safeProfilePhotoUrl(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const photo = value.trim();
  if (/^\/(?!\/)/.test(photo)) return photo;
  try {
    const parsed = new URL(photo);
    return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : null;
  } catch {
    return null;
  }
}

export function profilePhotoUrl(record, kind) {
  const configuredPhoto = safeProfilePhotoUrl(record?.photo_url);
  if (configuredPhoto) return configuredPhoto;
  if (record?.photo_url) return null;

  const identifier = kind === "student" ? record?.roll_number : record?.employee_code;
  if (!["student", "faculty"].includes(kind) || !/^[A-Za-z0-9_-]+$/.test(String(identifier || ""))) return null;
  return `/photos/${kind}-${identifier}.jpg`;
}

export function profileStatusLabel(value) {
  const status = String(value || "").trim();
  if (!status) return "Not available";
  if (status.startsWith("PENDING")) return "Pending registration";
  return status.replaceAll("_", " ").toLowerCase().replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}

export function profileDateLabel(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" }).format(date)} IST`;
}

export function profileDownloadFilename(response, kind, identifier) {
  const disposition = response?.headers?.["content-disposition"] || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return match?.[1] || `SYS_${kind === "student" ? "Student" : "Faculty"}_Profile_${identifier || "record"}.pdf`;
}
