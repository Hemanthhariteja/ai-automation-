import api from "./api";

export const listStaff = () => api.get("/business/staff").then((r) => r.data);
export const createStaff = (payload) => api.post("/business/staff", payload).then((r) => r.data);
export const updateStaff = (id, payload) => api.patch(`/business/staff/${id}`, payload).then((r) => r.data);
