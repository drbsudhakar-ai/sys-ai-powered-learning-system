/**
 * Shared course form fields — SYS brand kit classes.
 */
export default function CourseForm({
  formData,
  onChange,
  onSubmit,
  submitLabel,
  disabled,
  error,
  success,
}) {
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
          Title <span className="text-red-600">*</span>
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

      <div className="flex flex-wrap gap-3 pt-2">
        <button type="submit" className="btn-primary" disabled={disabled}>
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
