import MasterBulkUploadModal from "./MasterBulkUploadModal";

export default function StudentBulkUploadModal({ onClose, onUploaded }) {
  return <MasterBulkUploadModal kind="student" onClose={onClose} onUploaded={onUploaded} />;
}
