import axios from "axios";
import { getToken } from "./auth";

const API = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000",
});

API.interceptors.request.use((config) => {
  const token = getToken();
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

export const startActivation = (data) => API.post("/auth/activation/start", data);
export const verifyActivationOtp = (data) => API.post("/auth/activation/verify-otp", data);
export const verifyActivationContact = (data) => API.post("/auth/activation/verify-contact", data);
export const completeActivation = (data) => API.post("/auth/activation/complete", data);
export const startPasswordReset = (data) => API.post("/auth/password-reset/start", data);
export const verifyPasswordResetOtp = (data) => API.post("/auth/password-reset/verify-otp", data);
export const completePasswordReset = (data) => API.post("/auth/password-reset/complete", data);
export const loginUser = (data) =>
  API.post("/auth/login", new URLSearchParams(data));
export const getMe = () => API.get("/auth/me");

export const getCourses = (params) => API.get("/courses/", { params });
export const getMyProgrammes = () => API.get("/courses/me");
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
export const adminListCourseCoordinators = () => API.get("/admin/course-coordinators");
export const adminAssignCourseCoordinator = (data) =>
  API.post("/admin/course-coordinators", data);
export const adminRemoveCourseCoordinator = (id) =>
  API.delete(`/admin/course-coordinators/${id}`);
export const adminListSubjectExperts = () => API.get("/admin/subject-experts");
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

// Student attempts (P0-011)
export const enrollInCourse = (courseId) => API.post(`/courses/${courseId}/enroll`);
export const listStudentAssessments = (params) => API.get("/student/assessments", { params });
export const getAssessmentInstructions = (id) => API.get(`/student/assessments/${id}/instructions`);
export const startAssessmentAttempt = (id) => API.post(`/student/assessments/${id}/start`);
export const getAttempt = (id) => API.get(`/student/attempts/${id}`);
export const saveAttemptResponse = (id, data) => API.post(`/student/attempts/${id}/responses`, data);
export const submitAttempt = (id) => API.post(`/student/attempts/${id}/submit`);
export const getAttemptResult = (id) => API.get(`/student/attempts/${id}/result`);
export const releaseAnswerKey = (assessmentId) =>
  API.post(`/assessments/${assessmentId}/release-answer-key`);
export const getAnswerKey = (assessmentId) => API.get(`/assessments/${assessmentId}/answer-key`);
export const downloadAnswerKeyPdf = (assessmentId) =>
  API.get(`/assessments/${assessmentId}/answer-key.pdf`, { responseType: "blob" });

// P0-012 Performance Analyzer + Inbox
export const getMyPerformance = (courseId) => API.get("/analyzer/me", { params: { course_id: courseId } });
export const getPerformanceAnalysis = (studentId, courseId, params) =>
  API.get(`/analyzer/students/${studentId}/courses/${courseId}`, { params });
export const getLearningProfile = (studentId, courseId) =>
  API.get(`/analyzer/students/${studentId}/courses/${courseId}/profile`);
export const getLearningGaps = (studentId, courseId) =>
  API.get(`/analyzer/students/${studentId}/courses/${courseId}/gaps`);
export const getReadiness = (studentId, courseId) =>
  API.get(`/analyzer/students/${studentId}/courses/${courseId}/readiness`);
export const getAnalyzerReport = (studentId, courseId) =>
  API.get(`/analyzer/students/${studentId}/courses/${courseId}/report`);
export const downloadAnalyzerReportPdf = (studentId, courseId) =>
  API.get(`/analyzer/students/${studentId}/courses/${courseId}/report.pdf`, { responseType: "blob" });
export const getCourseAttention = (courseId) => API.get(`/analyzer/courses/${courseId}/attention`);
export const getInbox = (params) => API.get("/inbox/notifications", { params });
export const getInboxUnreadCount = () => API.get("/inbox/unread-count");
export const markInboxRead = (deliveryId) => API.post(`/inbox/notifications/${deliveryId}/read`);
export const markInboxAllRead = () => API.post("/inbox/notifications/read-all");
export const getNotificationPreferences = () => API.get("/inbox/preferences");
export const updateNotificationPreferences = (data) => API.put("/inbox/preferences", data);

// P0-013 Learning Sessions + AI Lecturer digital classroom
export const listLearningSessions = (params) => API.get("/learning-sessions", { params });
export const getLearningSession = (id) => API.get(`/learning-sessions/${id}`);
export const createLearningSession = (data) => API.post("/learning-sessions", data);
export const openLecture = (sessionId) => API.post(`/learning-sessions/${sessionId}/lecture/open`);
export const getLecture = (sessionId) => API.get(`/learning-sessions/${sessionId}/lecture`);
export const lectureStep = (sessionId, data) =>
  API.post(`/learning-sessions/${sessionId}/lecture/step`, data);
export const lectureControl = (sessionId, data) =>
  API.post(`/learning-sessions/${sessionId}/lecture/control`, data);
export const lectureInteract = (sessionId, data) =>
  API.post(`/learning-sessions/${sessionId}/lecture/interact`, data);

// P0-014 Remedial Learning
export const listRemedialGaps = (courseId, params) =>
  API.get(`/remedial/courses/${courseId}/gaps`, { params });
export const prioritizeRemedialGaps = (courseId, studentId) =>
  API.get(`/remedial/courses/${courseId}/gaps/prioritized`, { params: { student_id: studentId } });
export const proposeRemedialGroups = (courseId, persist = true) =>
  API.post(`/remedial/courses/${courseId}/proposals`, null, { params: { persist } });
export const listRemedialGroups = (params) => API.get("/remedial/groups", { params });
export const getRemedialGroup = (id) => API.get(`/remedial/groups/${id}`);
export const activateRemedialGroup = (id) => API.post(`/remedial/groups/${id}/activate`);
export const transitionRemedialGroup = (id, data) =>
  API.post(`/remedial/groups/${id}/transition`, data);
export const createGroupIntervention = (groupId) =>
  API.post(`/remedial/groups/${groupId}/intervention`);
export const createIndividualIntervention = (data) =>
  API.post("/remedial/interventions/individual", data);
export const activateRemedialIntervention = (id) =>
  API.post(`/remedial/interventions/${id}/activate`);
export const listRemedialInterventions = (params) => API.get("/remedial/interventions", { params });
export const getRemedialIntervention = (id) => API.get(`/remedial/interventions/${id}`);
export const patchRemedialIntervention = (id, data) =>
  API.patch(`/remedial/interventions/${id}`, data);
export const getMyRemedial = (params) => API.get("/remedial/me", { params });

// P0-015 Adaptive Practice & Mastery
export const getMasteryPolicy = (courseId) =>
  API.get("/mastery/policy", { params: courseId != null ? { course_id: courseId } : {} });
export const updateMasteryPolicy = (data) => API.put("/mastery/policy", data);
export const getMyMastery = (courseId) => API.get("/mastery/me", { params: { course_id: courseId } });
export const getStudentMastery = (studentId, courseId, sync = true) =>
  API.get(`/mastery/students/${studentId}/courses/${courseId}`, { params: { sync } });
export const getTopicMastery = (studentId, courseId, topicId) =>
  API.get(`/mastery/students/${studentId}/courses/${courseId}/topics/${topicId}`);
export const recommendPractice = (data) => API.post("/mastery/practice/recommend", data);
export const startPractice = (data) => API.post("/mastery/practice/start", data);
export const getReassessmentEligibility = (params) =>
  API.get("/mastery/reassessment/eligibility", { params });
export const declareReassessmentReady = (data) =>
  API.post("/mastery/reassessment/declare-ready", data);
export const approveReassessment = (data) => API.post("/mastery/reassessment/approve", data);
export const startReassessment = (data) => API.post("/mastery/reassessment/start", data);

// P0-016 Learning Intelligence
export const getAnalyticsPolicy = (courseId) =>
  API.get("/analytics/policy", { params: courseId != null ? { course_id: courseId } : {} });
export const getMyAnalytics = (courseId) =>
  API.get("/analytics/me", { params: { course_id: courseId } });
export const getMyAnalyticsTopics = (courseId) =>
  API.get("/analytics/me/topics", { params: { course_id: courseId } });
export const getMyAnalyticsTrends = (courseId, topicId) =>
  API.get("/analytics/me/trends", {
    params: { course_id: courseId, ...(topicId != null ? { topic_id: topicId } : {}) },
  });
export const getMyAnalyticsAttention = (courseId) =>
  API.get("/analytics/me/attention", { params: { course_id: courseId } });
export const getStudentAnalytics = (studentId, courseId) =>
  API.get(`/analytics/students/${studentId}/courses/${courseId}`);
export const getFacultyAnalyticsOverview = (courseId) =>
  API.get("/analytics/faculty/overview", { params: { course_id: courseId } });
export const getFacultyAnalyticsTopics = (courseId, subjectId) =>
  API.get("/analytics/faculty/topics", {
    params: { course_id: courseId, ...(subjectId != null ? { subject_id: subjectId } : {}) },
  });
export const getFacultyAnalyticsStudents = (courseId) =>
  API.get("/analytics/faculty/students", { params: { course_id: courseId } });
export const getFacultyAnalyticsAttention = (courseId, limit) =>
  API.get("/analytics/faculty/attention", {
    params: { course_id: courseId, ...(limit != null ? { limit } : {}) },
  });
export const getFacultyAnalyticsInterventions = (courseId) =>
  API.get("/analytics/faculty/interventions", { params: { course_id: courseId } });
export const notifyFacultyAttention = (courseId, studentId) =>
  API.post("/analytics/faculty/attention/notify", null, {
    params: { course_id: courseId, ...(studentId != null ? { student_id: studentId } : {}) },
  });
export const getAdminAnalyticsOverview = (params) => API.get("/analytics/admin/overview", { params });
export const getAdminAnalyticsCourses = () => API.get("/analytics/admin/courses");
export const getAdminAnalyticsSubjects = (courseId) =>
  API.get("/analytics/admin/subjects", { params: { course_id: courseId } });
export const getAdminAnalyticsTrends = (params) => API.get("/analytics/admin/trends", { params });
export const getAdminAnalyticsAttention = (params) => API.get("/analytics/admin/attention", { params });

// P0-017 Personalized Learning Journey
export const getMyLearningJourney = (courseId, subjectId) =>
  API.get("/learning-journey/me", {
    params: { course_id: courseId, ...(subjectId != null ? { subject_id: subjectId } : {}) },
  });
export const getMyJourneySubjects = (courseId) =>
  API.get("/learning-journey/me/subjects", { params: { course_id: courseId } });
export const getMySubjectGuidance = (courseId, subjectId) =>
  API.get(`/learning-journey/me/subjects/${subjectId}`, { params: { course_id: courseId } });
export const getMySubjectNextTopic = (courseId, subjectId) =>
  API.get(`/learning-journey/me/subjects/${subjectId}/next`, { params: { course_id: courseId } });
export const focusMySubject = (courseId, subjectId) =>
  API.post(`/learning-journey/me/subjects/${subjectId}/focus`, null, {
    params: { course_id: courseId },
  });
export const chooseSubjectTopic = (courseId, subjectId, topicId) =>
  API.post(
    `/learning-journey/me/subjects/${subjectId}/topics/choose`,
    { topic_id: topicId },
    { params: { course_id: courseId } }
  );
export const getMyCourseBalance = (courseId) =>
  API.get(`/analytics/me/courses/${courseId}/balance`);
export const getFacultyCourseBalance = (courseId) =>
  API.get(`/analytics/faculty/courses/${courseId}/balance`);
export const getAdminCourseBalance = (params) => API.get("/analytics/admin/balance", { params });
export const getMyNextLearningAction = (courseId) =>
  API.get("/learning-journey/me/next", { params: { course_id: courseId } });
export const getMyLearningActions = (courseId) =>
  API.get("/learning-journey/me/actions", { params: { course_id: courseId } });
export const getMyLearningProgress = (courseId) =>
  API.get("/learning-journey/me/progress", { params: { course_id: courseId } });
export const startLearningAction = (actionId) =>
  API.post(`/learning-journey/me/actions/${actionId}/start`);
export const completeLearningAction = (actionId) =>
  API.post(`/learning-journey/me/actions/${actionId}/complete`);
export const dismissLearningAction = (actionId) =>
  API.post(`/learning-journey/me/actions/${actionId}/dismiss`);
export const chooseLearningAction = (actionId, data) =>
  API.post(`/learning-journey/me/actions/${actionId}/choose`, data);
export const getFacultyJourneyStudents = (courseId) =>
  API.get("/learning-journey/faculty/students", { params: { course_id: courseId } });
export const getFacultyJourneyStudent = (studentId, courseId) =>
  API.get(`/learning-journey/faculty/students/${studentId}`, { params: { course_id: courseId } });
export const recommendFacultyJourneyAction = (studentId, data) =>
  API.post(`/learning-journey/faculty/students/${studentId}/recommend`, data);
export const getAdminJourneyOverview = (params) =>
  API.get("/learning-journey/admin/overview", { params });

export default API;
