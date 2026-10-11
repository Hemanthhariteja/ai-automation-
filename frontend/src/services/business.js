import api from "./api";

export const getBusinessProfile = () => api.get("/business/profile").then((r) => r.data);
export const updateBusinessProfile = (payload) => api.patch("/business/profile", payload).then((r) => r.data);
