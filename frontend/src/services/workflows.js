import api from "./api";

export const listWorkflows = () => api.get("/workflows").then((r) => r.data);
export const getWorkflow = (id) => api.get(`/workflows/${id}`).then((r) => r.data);
export const createWorkflow = (payload) => api.post("/workflows", payload).then((r) => r.data);
export const updateWorkflow = (id, payload) => api.patch(`/workflows/${id}`, payload).then((r) => r.data);
export const deleteWorkflow = (id) => api.delete(`/workflows/${id}`);

export const addNode = (workflowId, payload) =>
  api.post(`/workflows/${workflowId}/nodes`, payload).then((r) => r.data);
export const updateNode = (workflowId, nodeId, payload) =>
  api.patch(`/workflows/${workflowId}/nodes/${nodeId}`, payload).then((r) => r.data);
export const deleteNode = (workflowId, nodeId) => api.delete(`/workflows/${workflowId}/nodes/${nodeId}`);

export const runWorkflow = (workflowId, leadId) =>
  api.post(`/workflows/${workflowId}/run`, { lead_id: leadId }).then((r) => r.data);
export const listExecutions = (workflowId) =>
  api.get(`/workflows/${workflowId}/executions`).then((r) => r.data);

export const listTemplates = () => api.get("/workflows/templates").then((r) => r.data);
export const createFromTemplate = (templateId) =>
  api.post(`/workflows/templates/${templateId}`).then((r) => r.data);
