import api from "./api";

export const getAIStatus = () => api.get("/ai/status").then((r) => r.data);
export const updateAISettings = (payload) => api.patch("/ai/settings", payload).then((r) => r.data);
export const testAIPipeline = (payload) => api.post("/ai/test", payload).then((r) => r.data);
