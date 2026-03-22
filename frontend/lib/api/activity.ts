"use client";
import { api } from "./client";
import { z } from "zod";
import { 
  Activity, 
  ArrowRightLeft, 
  Package, 
  Calendar, 
  Shield, 
  Settings, 
  CreditCard 
} from "lucide-react";

export const ActivityEventSchema = z.object({
  event_id: z.string(),
  user_id: z.number(),
  category: z.string(),
  action: z.string(),
  event_time: z.string(),
  title: z.string(),
  details: z.string(),
});

export const ActivityResponseSchema = z.object({
  events: z.array(ActivityEventSchema),
  total: z.number(),
});

export type ActivityEvent = z.infer<typeof ActivityEventSchema>;
export type ActivityResponse = z.infer<typeof ActivityResponseSchema>;

export interface ActivityParams {
  category?: string;
  search?: string;
  from_date?: string;
  to_date?: string;
  order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export const getActivity = (params: ActivityParams) => 
  api.get<ActivityResponse>("/api/v1/activity", {
    params: {
        ...params,
        limit: params.limit?.toString() ?? "30",
        offset: params.offset?.toString() ?? "0"
    },
    schema: ActivityResponseSchema
  });

export const CATEGORIES = [
  { value: "", label: "All Categories", icon: Activity },
  { value: "p2p", label: "P2P Transfer", icon: ArrowRightLeft },
  { value: "sub_account", label: "Internal Transfer", icon: Package },
  { value: "scheduled", label: "Scheduled", icon: Calendar },
  { value: "security", label: "Security", icon: Shield },
  { value: "settings", label: "Settings", icon: Settings },
  { value: "cards", label: "Cards", icon: CreditCard },
];
