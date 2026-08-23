import MasterBulkUploadModal from "./MasterBulkUploadModal";

export default function FacultyBulkUploadModal({ onClose, onUploaded }) {
  return <MasterBulkUploadModal kind="faculty" onClose={onClose} onUploaded={onUploaded} />;
}
