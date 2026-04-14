import { Channel } from "@/types";
import { apiClient } from "./client";

export const userChannelApi = {
  like:       (channelId: number) =>
    apiClient.post(`/api/users/channels/${channelId}/like`),
  unlike:     (channelId: number) =>
    apiClient.delete(`/api/users/channels/${channelId}/like`),
  block:      (channelId: number) =>
    apiClient.post(`/api/users/channels/${channelId}/block`),
  unblock:    (channelId: number) =>
    apiClient.delete(`/api/users/channels/${channelId}/block`),
  getLiked:   () =>
    apiClient.get<Channel[]>('/api/users/channels', { params: { type: 'liked' } }),
  getBlocked: () =>
    apiClient.get<Channel[]>('/api/users/channels', { params: { type: 'blocked' } }),
}