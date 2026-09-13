import { invoke } from "@tauri-apps/api/core";

export type QuickAction = {
  action: "more_like_this" | "not_now" | "less_like_this";
  label: string;
  mission_id: string;
};

export type MissionStep = {
  number: number;
  text: string;
  done: boolean;
};

export type Dashboard = {
  schema_version: number;
  user: {
    id: string;
    display_name: string;
  };
  experience: {
    headline: string;
    message: string;
    primary_action: null | {
      action: "continue";
      label: string;
      mission_id: string;
      progress_label: string | null;
    };
    quick_actions: QuickAction[];
    learning: {
      active: boolean;
      signal_count: number;
      message: string;
    };
  };
  today: null | {
    mission_id: string;
    title: string;
    why_now: string;
    focus_minutes: number;
    definition_of_done: string;
    steps: MissionStep[];
    progress: {
      completed: number;
      total: number;
      percent: number;
    };
    selection?: {
      reasons?: string[];
    };
  };
  radar: Array<{
    id: string;
    title: string;
    score: number;
  }>;
  personalization: {
    adapting: boolean;
    signal_count: number;
  };
  summary: {
    active_missions: number;
    completed_steps: number;
    total_active_steps: number;
  };
};

export type Bootstrap = {
  schema_version: number;
  selected_user_id: string;
  initialized: boolean;
  users: Array<{ id: string; display_name: string }>;
  onboarding: null | {
    mode: "quick";
    headline: string;
    message: string;
    submit_label: string;
  };
  dashboard: Dashboard | null;
};

type BridgeResponse<T> =
  | { ok: true; data: T }
  | { ok: false; error: { type: string; message: string } };

const root = "";

async function request<T>(
  action: string,
  userId: string | null,
  payload: Record<string, unknown> = {},
): Promise<T> {
  const raw = await invoke<string>("lumen_request", {
    request: JSON.stringify({ action, root, user_id: userId, payload }),
  });
  const response = JSON.parse(raw) as BridgeResponse<T>;
  if (!response.ok) {
    throw new Error(response.error.message);
  }
  return response.data;
}

export function bootstrap(userId = "default"): Promise<Bootstrap> {
  return request<Bootstrap>("bootstrap", userId);
}

export function quickOnboard(
  userId: string,
  displayName: string,
  goals: string[],
): Promise<Dashboard> {
  return request<Dashboard>("quick_onboard", userId, {
    display_name: displayName,
    goals,
  });
}

export function reactToMission(
  userId: string,
  reaction: QuickAction["action"],
  missionId: string,
): Promise<Dashboard> {
  return request<Dashboard>("react", userId, {
    reaction,
    mission_id: missionId,
  });
}

export async function completeStep(
  userId: string,
  missionId: string,
  step: number,
): Promise<Dashboard> {
  await request("complete_step", userId, {
    step,
    mission_id: missionId,
  });
  return request<Dashboard>("dashboard", userId);
}
