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

export type ContextHypothesis = {
  key: string;
  label: string;
  value: string;
  confidence: number;
  source: string;
};

export type UserContext = {
  version: number;
  source: "conversation";
  answers: {
    current_context: string;
    desired_change: string;
    friction: string | null;
    focus_minutes: number;
  };
  hypotheses: ContextHypothesis[];
  average_confidence: number;
  learning?: {
    events: number;
    primary_goal_support: number;
    primary_goal_conflict: number;
    primary_goal_deferrals: number;
    last_mission_id: string | null;
    last_signal: string | null;
    snooze_until_event: number;
  };
};

export type ContextClarification = {
  id: string;
  kind: "direction" | "fit";
  prompt: string;
  options: Array<{
    choice: string;
    label: string;
  }>;
};

export type GitHubRepositoryContext = {
  name: string;
  full_name: string;
  owner: string;
  description: string | null;
  language: string | null;
  topics: string[];
  fork: boolean;
  archived: boolean;
  stars: number;
  pushed_at: string | null;
  updated_at: string | null;
  event_count: number;
};

export type GitHubContextSnapshot = {
  schema_version: number;
  source: "github_public";
  fetched_at: string;
  account: {
    username: string;
    name: string | null;
    bio: string | null;
    company: string | null;
    location: string | null;
    public_repos: number;
    followers: number;
  };
  active_repositories: GitHubRepositoryContext[];
  activity_only_repositories: Array<{
    full_name: string;
    event_count: number;
  }>;
  languages: Array<{
    name: string;
    repository_count: number;
  }>;
  topics: Array<{
    name: string;
    repository_count: number;
  }>;
  signals: {
    active_project: string | null;
    primary_language: string | null;
    active_repository_count: number;
    public_event_repository_count: number;
  };
};

export type GitHubIntegration = {
  connected: boolean;
  source: "github_public";
  account: GitHubContextSnapshot["account"] | null;
  fetched_at: string | null;
  active_repositories: GitHubRepositoryContext[];
  languages: GitHubContextSnapshot["languages"];
  signals: GitHubContextSnapshot["signals"] | Record<string, never>;
};

export type Dashboard = {
  schema_version: number;
  user: {
    id: string;
    display_name: string;
    priorities?: Record<string, number>;
  };
  context?: UserContext | null;
  clarification?: ContextClarification | null;
  integrations?: {
    github: GitHubIntegration;
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
  context?: UserContext | null;
  integrations?: {
    github: GitHubIntegration;
  };
  dashboard: Dashboard | null;
};

export type GuidedOnboardingInput = {
  displayName: string;
  currentContext: string;
  desiredChange: string;
  friction: string;
  focusMinutes: 15 | 30 | 60;
};

type BridgeResponse<T> =
  | { ok: true; data: T }
  | { ok: false; error: { type: string; message: string } };

function nativeError(error: unknown): Error {
  if (error instanceof Error) return error;
  if (typeof error === "string" && error.trim()) return new Error(error);
  try {
    return new Error(JSON.stringify(error));
  } catch {
    return new Error("Lumen desktop bridge failed with an unknown error.");
  }
}

async function request<T>(
  action: string,
  userId: string | null,
  payload: Record<string, unknown> = {},
): Promise<T> {
  let raw: string;
  try {
    raw = await invoke<string>("lumen_request", {
      request: JSON.stringify({ action, user_id: userId, payload }),
    });
  } catch (error) {
    throw nativeError(error);
  }

  let response: BridgeResponse<T>;
  try {
    response = JSON.parse(raw) as BridgeResponse<T>;
  } catch (error) {
    throw new Error(`Lumen engine returned an unreadable response: ${raw.slice(0, 500)}`);
  }

  if (!response.ok) {
    throw new Error(response.error.message);
  }
  return response.data;
}

export function bootstrap(userId = "default"): Promise<Bootstrap> {
  return request<Bootstrap>("bootstrap", userId);
}

export function guidedOnboard(
  userId: string,
  input: GuidedOnboardingInput,
): Promise<Dashboard> {
  return request<Dashboard>("guided_onboard", userId, {
    display_name: input.displayName,
    current_context: input.currentContext,
    desired_change: input.desiredChange,
    friction: input.friction,
    focus_minutes: input.focusMinutes,
  });
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

export function answerClarification(
  userId: string,
  clarificationId: string,
  choice: string,
): Promise<Dashboard> {
  return request<Dashboard>("clarify_context", userId, {
    clarification_id: clarificationId,
    choice,
  });
}

export function previewGitHub(
  userId: string,
  username: string,
): Promise<GitHubContextSnapshot> {
  return request<GitHubContextSnapshot>("github_preview", userId, { username });
}

export function connectGitHub(userId: string, username: string): Promise<Dashboard> {
  return request<Dashboard>("github_connect", userId, { username });
}

export function refreshGitHub(userId: string): Promise<Dashboard> {
  return request<Dashboard>("github_refresh", userId);
}

export function disconnectGitHub(userId: string): Promise<Dashboard> {
  return request<Dashboard>("github_disconnect", userId);
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
