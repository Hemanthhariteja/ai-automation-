import api from "./api";

export const getAnalyticsOverview = () => api.get("/analytics/overview").then((r) => r.data);
