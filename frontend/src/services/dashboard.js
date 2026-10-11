import api from "./api";

export const getDashboardSummary = () => api.get("/dashboard/summary").then((r) => r.data);
