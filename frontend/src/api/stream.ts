import { Stream } from "@/types";
import { apiClient } from "./client";

export const streamApi = {
  getLiveStreams: () => apiClient.get<Stream[]>('/api/streams/live'),
  getAllStreams:   (params?: Record<string, unknown>) =>
    apiClient.get<Stream[]>('/api/streams', { params }),
}