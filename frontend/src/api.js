import axios from "axios";

const API = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000",
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function getApiErrorMessage(err, fallback = "Something went wrong.") {
  if (!err) return fallback;
  const status = err.response?.status;
  const detail = err.response?.data?.detail;
  if (status === 401) return "Please log in to continue.";
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "Not found.";
  if (status === 409) return typeof detail === "string" ? detail : "Conflict with existing data.";
  if (status === 422) {
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg || JSON.stringify(d)).join(" ");
    }
    if (detail && typeof detail === "object" && Array.isArray(detail.errors)) {
      return detail.errors.join(" ");
    }
    return typeof detail === "string" ? detail : "Please check the form fields and try again.";
  }
  if (typeof detail === "string") return detail;
  return fallback;
}

export const registerUser = (data) => API.post("/auth/register", data);
export const loginUser = (data) =>
  API.post("/auth/login", new URLSearchParams(data));
export const getMe = () => API.get("/auth/me");

export const getCourses = () => API.get("/courses/");
export const getCourse = (id) => API.get(`/courses/${id}`);
export const createCourse = (data) => API.post("/courses/", data);
export const updateCourse = (id, data) => API.put(`/courses/${id}`, data);
export const deleteCourse = (id) => API.delete(`/courses/${id}`);

// Admin — Students
export const adminListStudents = () => API.get("/admin/students");
export const adminGetStudent = (id) => API.get(`/admin/students/${id}`);
export const adminCreateStudent = (data) => API.post("/admin/students", data);
export const adminUpdateStudent = (id, data) => API.put(`/admin/students/${id}`, data);
export const adminDeactivateStudent = (id) => API.post(`/admin/students/${id}/deactivate`);
export const adminActivateStudent = (id) => API.post(`/admin/students/${id}/activate`);

// Admin — Faculty
export const adminListFaculty = () => API.get("/admin/faculty");
export const adminGetFaculty = (id) => API.get(`/admin/faculty/${id}`);
export const adminCreateFaculty = (data) => API.post("/admin/faculty", data);
export const adminUpdateFaculty = (id, data) => API.put(`/admin/faculty/${id}`, data);
export const adminDeactivateFaculty = (id) => API.post(`/admin/faculty/${id}/deactivate`);
export const adminActivateFaculty = (id) => API.post(`/admin/faculty/${id}/activate`);

// Admin — Subjects & responsibilities
export const adminListSubjects = () => API.get("/admin/subjects");
export const adminCreateSubject = (data) => API.post("/admin/subjects", data);
export const adminAssignCourseCoordinator = (data) =>
  API.post("/admin/course-coordinators", data);
export const adminRemoveCourseCoordinator = (id) =>
  API.delete(`/admin/course-coordinators/${id}`);
export const adminAssignSubjectExpert = (data) =>
  API.post("/admin/subject-experts", data);
export const adminRemoveSubjectExpert = (id) =>
  API.delete(`/admin/subject-experts/${id}`);

// Assessments (P0-009)
export const getAssessments = (params) => API.get("/assessments/", { params });
export const getAssessment = (id) => API.get(`/assessments/${id}`);
export const createAssessment = (data) => API.post("/assessments/", data);
export const updateAssessment = (id, data) => API.put(`/assessments/${id}`, data);
export const archiveAssessment = (id) => API.post(`/assessments/${id}/archive`);
export const setAssessmentBlueprint = (id, items) => API.put(`/assessments/${id}/blueprint`, items);
export const assembleAssessment = (id) => API.post(`/assessments/${id}/assemble`);
export const publishAssessment = (id) => API.post(`/assessments/${id}/publish`);

export const listTopics = (params) => API.get("/topics", { params });
export const createTopic = (data) => API.post("/topics", data);
export const listSubtopics = (params) => API.get("/subtopics", { params });
export const createSubtopic = (data) => API.post("/subtopics", data);
export const listQuestions = (params) => API.get("/questions", { params });
export const createQuestion = (data) => API.post("/questions", data);

export const getPerformanceSheet = (params) => API.get("/performance/sheet", { params });
export const getReportCard = (params) => API.get("/performance/report-card", { params });
export const downloadReportCardPdf = (params) =>
  API.get("/performance/report-card.pdf", { params, responseType: "blob" });

export const listNotificationRecipients = () => API.get("/notifications/recipients");
export const createNotificationRecipient = (data) => API.post("/notifications/recipients", data);
export const updateNotificationRecipient = (id, data) =>
  API.put(`/notifications/recipients/${id}`, data);
export const listNotifications = () => API.get("/notifications");
export const retryNotification = (id) => API.post(`/notifications/${id}/retry`);

// Question Bank / Intelligence (P0-010)
export const searchQuestionBank = (params) => API.get("/question-bank/questions", { params });
export const getQuestionBankItem = (id) => API.get(`/question-bank/questions/${id}`);
export const createQuestionBankItem = (data) => API.post("/question-bank/questions", data);
export const updateQuestionBankItem = (id, data) => API.put(`/question-bank/questions/${id}`, data);
export const duplicateQuestionBankItem = (id) => API.post(`/question-bank/questions/${id}/duplicate`);
export const archiveQuestionBankItem = (id) => API.post(`/question-bank/questions/${id}/archive`);
export const checkQuestionSimilarity = (data) => API.post("/question-bank/questions/check-similarity", data);
export const getQuestionBankStats = (params) => API.get("/question-bank/stats", { params });

export const listHistoricalPapers = (params) => API.get("/historical-papers", { params });
export const createHistoricalPaper = (data) => API.post("/historical-papers", data);
export const getHistoricalPaper = (id) => API.get(`/historical-papers/${id}`);
export const runHistoricalAnalysis = (courseId) => API.post(`/historical-analysis/${courseId}`);

export const getSubjectWeightages = (params) => API.get("/weightages/subjects", { params });
export const setSubjectWeightages = (data) => API.put("/weightages/subjects", data);
export const getTopicWeightages = (params) => API.get("/weightages/topics", { params });
export const setTopicWeightages = (data) => API.put("/weightages/topics", data);
export const setPriorityWeights = (courseId, data) => API.put(`/priority-weights/${courseId}`, data);

export const getTopicIntelligence = (topicId) => API.get(`/academic-intelligence/topics/${topicId}`);
export const getCourseTopicIntelligence = (courseId) =>
  API.get(`/academic-intelligence/courses/${courseId}/topics`);
export const getQuestionImportance = (id) =>
  API.get(`/academic-intelligence/questions/${id}/importance`);
export const selectQuestions = (data) => API.post("/question-selection", data);

export default API;
