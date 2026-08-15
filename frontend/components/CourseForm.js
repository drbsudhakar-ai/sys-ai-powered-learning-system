/**
 * Shared course / learning-programme form fields — SYS brand kit classes.
 */
const CATEGORIES = [
  { value: "HIGHER_EDUCATION_ENTRANCE", label: "Higher-education entrance" },
  { value: "EMPLOYMENT_EXAM", label: "Employment examination" },
  { value: "INDEPENDENT_LEARNING", label: "Independent learning" },
  { value: "SKILL_DEVELOPMENT", label: "Skill development" },
];

export default function CourseForm({
  formData,
  onChange,
  onSubmit,
  submitLabel,
  disabled,
  error,
  success,
}) {
  const examMeta =
    formData.programme_category === "HIGHER_EDUCATION_ENTRANCE" ||
    formData.programme_category === "EMPLOYMENT_EXAM";

  return (
    <form onSubmit={onSubmit} className="sys-card w-full max-w-2xl space-y-4" noValidate>
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
      {success && (
        <p className="text-sm text-green-700" role="status">
          {success}
        </p>
      )}

      <div>
        <label htmlFor="title" className="mb-1 block text-sm font-semibold text-[var(--sys-gray)]">
          Programme title <span className="text-red-600">*</span>
        </label>
        <input
          id="title"
          name="title"
          type="text"
          className="input-field"
          value={formData.title}
          onChange={onChange}
          required
          maxLength={200}
          aria-required="true"
          disabled={disabled}
        />
      </div>

      <div>
        <label htmlFor="programme_category" className="mb-1 block text-sm font-semibold text-[var(--sys-gray)]">
          Programme category
        </label>
        <select
          id="programme_category"
          name="programme_category"
          className="input-field"
          value={formData.programme_category || "INDEPENDENT_LEARNING"}
          onChange={onChange}
          disabled={disabled}
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="programme_code" className="mb-1 block text-sm font-semibold text-[var(--sys-gray)]">
          Programme code (optional)
        </label>
        <select
          id="programme_code"
          name="programme_code"
          className="input-field"
          value={formData.programme_code || ""}
          onChange={onChange}
          disabled={disabled}
        >
          <option value="">None</option>
          <option value="ENGLISH_COMMUNICATION">English Communication</option>
        </select>
        <p className="mt-1 text-xs text-[var(--sys-gray)]">
          Use English Communication for the independent language programme. The communication agent is not part of this form.
        </p>
      </div>

      {examMeta ? (
        <>
          <div>
            <label htmlFor="examination_name" className="mb-1 block text-sm font-semibold text-[var(--sys-gray)]">
              Examination name
            </label>
            <input
              id="examination_name"
              name="examination_name"
              type="text"
              className="input-field"
              value={formData.examination_name || ""}
              onChange={onChange}
              maxLength={200}
              disabled={disabled}
              placeholder="e.g. NEET, JEE, SSC"
            />
          </div>
          <div>
            <label htmlFor="examination_authority" className="mb-1 block text-sm font-semibold text-[var(--sys-gray)]">
              Examination authority
            </label>
            <input
              id="examination_authority"
              name="examination_authority"
              type="text"
              className="input-field"
              value={formData.examination_authority || ""}
              onChange={onChange}
              maxLength={200}
              disabled={disabled}
            />
          </div>
        </>
      ) : null}

      <div>
        <label htmlFor="target_purpose" className="mb-1 block text-sm font-semibold text-[var(--sys-gray)]">
          Target purpose
        </label>
        <input
          id="target_purpose"
          name="target_purpose"
          type="text"
          className="input-field"
          value={formData.target_purpose || ""}
          onChange={onChange}
          maxLength={300}
          disabled={disabled}
          placeholder="Admission, employment, independent learning, or skill development"
        />
      </div>

      <div>
        <label htmlFor="description" className="mb-1 block text-sm font-semibold text-[var(--sys-gray)]">
          Description
        </label>
        <textarea
          id="description"
          name="description"
          className="input-field min-h-[120px]"
          value={formData.description}
          onChange={onChange}
          maxLength={500}
          disabled={disabled}
        />
      </div>

      <div>
        <label htmlFor="syllabus_url" className="mb-1 block text-sm font-semibold text-[var(--sys-gray)]">
          Syllabus URL
        </label>
        <input
          id="syllabus_url"
          name="syllabus_url"
          type="url"
          className="input-field"
          value={formData.syllabus_url}
          onChange={onChange}
          maxLength={255}
          placeholder="https://"
          disabled={disabled}
        />
      </div>

      <div>
        <label htmlFor="resources_url" className="mb-1 block text-sm font-semibold text-[var(--sys-gray)]">
          Resources URL
        </label>
        <input
          id="resources_url"
          name="resources_url"
          type="url"
          className="input-field"
          value={formData.resources_url}
          onChange={onChange}
          maxLength={255}
          placeholder="https://"
          disabled={disabled}
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          id="is_active"
          name="is_active"
          type="checkbox"
          checked={formData.is_active !== false}
          onChange={onChange}
          disabled={disabled}
        />
        <label htmlFor="is_active" className="text-sm font-semibold text-[var(--sys-gray)]">
          Active programme
        </label>
      </div>

      <div className="flex flex-wrap gap-3 pt-2">
        <button type="submit" className="btn-primary" disabled={disabled}>
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
