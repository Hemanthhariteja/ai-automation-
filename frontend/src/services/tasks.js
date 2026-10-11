import api from "./api";

export const listTasks = (params) => api.get("/tasks", { params }).then((r) => r.data);
export const updateTask = (id, payload) => api.patch(`/tasks/${id}`, payload).then((r) => r.data);
