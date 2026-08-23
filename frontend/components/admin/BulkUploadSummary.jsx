export default function BulkUploadSummary({ result, onClose }) {
    if (!result) {
      return (
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Bulk Upload Summary</h2>
          <p className="text-red-600">No result data available.</p>
          <button onClick={onClose} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded">
            Close
          </button>
        </div>
      );
    }
  
    return (
      <div className="p-6">
        <h2 className="text-xl font-bold mb-4">Bulk Upload Summary</h2>
        <p><strong>Status:</strong> {result.status ?? "Unknown"}</p>
        <p><strong>Total Uploaded:</strong> {result.log_entry?.total_uploaded ?? 0}</p>
        <p><strong>Inserted:</strong> {result.inserted ?? 0}</p>
        <p><strong>Skipped:</strong> {result.skipped ?? 0}</p>
        <p><strong>Invalid:</strong> {result.invalid ?? 0}</p>
  
        <button onClick={onClose} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded">
          Close
        </button>
      </div>
    );
  }
  