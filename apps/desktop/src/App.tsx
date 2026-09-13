import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  Check,
  ChevronRight,
  CircleUserRound,
  Clock3,
  Home,
  Loader2,
  Plus,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import {
  bootstrap,
  completeStep,
  Dashboard,
  quickOnboard,
  reactToMission,
} from "./lib/lumen";

type Screen = "home" | "mission" | "activity" | "profile";

function Onboarding({ onReady }: { onReady: (dashboard: Dashboard) => void }) {
  const [name, setName] = useState("");
  const [goals, setGoals] = useState([""]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    name.trim().length > 0 && goals.some((goal) => goal.trim().length > 0) && !busy;

  const updateGoal = (index: number, value: string) => {
    setGoals((current) => current.map((goal, i) => (i === index ? value : goal)));
  };

  const addGoal = () => {
    if (goals.length < 5) setGoals((current) => [...current, ""]);
  };

  const removeGoal = (index: number) => {
    if (goals.length === 1) return;
    setGoals((current) => current.filter((_, i) => i !== index));
  };

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      const dashboard = await quickOnboard(
        "default",
        name.trim(),
        goals.map((goal) => goal.trim()).filter(Boolean),
      );
      onReady(dashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start Lumen.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="onboarding-shell">
      <section className="onboarding-card">
        <div className="brand-lockup">
          <div className="brand-mark"><Sparkles size={18} /></div>
          <span>Lumen</span>
        </div>
        <div className="onboarding-copy">
          <span className="eyebrow">Set up in under a minute</span>
          <h1>What do you want to move forward?</h1>
          <p>
            Give Lumen a little context now. It will learn from what you actually do instead
            of making you tune settings forever.
          </p>
        </div>

        <label className="field-label">
          What should Lumen call you?
          <input
            autoFocus
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Your name"
          />
        </label>

        <div className="goals-block">
          <div className="goals-header">
            <span>What matters most right now?</span>
            <span className="muted">1–5 goals</span>
          </div>
          {goals.map((goal, index) => (
            <div className="goal-row" key={index}>
              <span className="goal-index">{index + 1}</span>
              <input
                value={goal}
                onChange={(event) => updateGoal(index, event.target.value)}
                placeholder={index === 0 ? "Build my AI career" : "Add another goal"}
              />
              {goals.length > 1 && (
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => removeGoal(index)}
                  aria-label="Remove goal"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          ))}
          {goals.length < 5 && (
            <button className="ghost-button add-goal" type="button" onClick={addGoal}>
              <Plus size={16} /> Add goal
            </button>
          )}
        </div>

        {error && <div className="error-banner">{error}</div>}

        <button className="primary-button onboarding-submit" disabled={!canSubmit} onClick={submit}>
          {busy ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
          Start with Lumen
          {!busy && <ArrowRight size={18} />}
        </button>
      </section>
    </main>
  );
}

function Sidebar({ screen, setScreen, dashboard }: {
  screen: Screen;
  setScreen: (screen: Screen) => void;
  dashboard: Dashboard;
}) {
  const items: Array<{ id: Screen; label: string; icon: typeof Home }> = [
    { id: "home", label: "Today", icon: Home },
    { id: "mission", label: "Focus", icon: Target },
    { id: "activity", label: "Activity", icon: Activity },
    { id: "profile", label: "Profile", icon: CircleUserRound },
  ];

  return (
    <aside className="sidebar">
      <div className="brand-lockup sidebar-brand">
        <div className="brand-mark"><Sparkles size={18} /></div>
        <span>Lumen</span>
      </div>
      <nav>
        {items.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={screen === id ? "nav-item active" : "nav-item"}
            onClick={() => setScreen(id)}
          >
            <Icon size={18} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="learning-dot" data-active={dashboard.personalization.adapting} />
        <div>
          <strong>{dashboard.personalization.adapting ? "Learning from you" : "Ready to learn"}</strong>
          <span>{dashboard.personalization.signal_count} preference signals</span>
        </div>
      </div>
    </aside>
  );
}

function HomeScreen({ dashboard, setScreen, onReact }: {
  dashboard: Dashboard;
  setScreen: (screen: Screen) => void;
  onReact: (action: "more_like_this" | "not_now" | "less_like_this", missionId: string) => void;
}) {
  const today = dashboard.today;
  const progress = today?.progress.percent ?? 0;
  return (
    <section className="screen-content home-screen">
      <header className="topbar">
        <div>
          <span className="eyebrow">Today</span>
          <h1>{dashboard.experience.headline}</h1>
        </div>
        <div className="avatar-chip">{dashboard.user.display_name.slice(0, 1).toUpperCase()}</div>
      </header>

      <div className="hero-grid">
        <article className="focus-card">
          <div className="focus-card-top">
            <div>
              <span className="card-kicker">Best next move</span>
              <h2>{dashboard.experience.message}</h2>
            </div>
            <div className="progress-orb" style={{ "--progress": `${progress * 3.6}deg` } as React.CSSProperties}>
              <div>{progress}%</div>
            </div>
          </div>
          {today && (
            <>
              <p className="why-now">{today.why_now}</p>
              <div className="meta-row">
                <span><Clock3 size={16} /> {today.focus_minutes} min focus</span>
                <span><Target size={16} /> {today.progress.completed}/{today.progress.total} steps</span>
              </div>
            </>
          )}
          <div className="focus-actions">
            {dashboard.experience.primary_action && (
              <button className="primary-button" onClick={() => setScreen("mission")}>
                {dashboard.experience.primary_action.label}
                <ArrowRight size={18} />
              </button>
            )}
            <div className="quick-actions">
              {dashboard.experience.quick_actions.map((action) => (
                <button
                  key={action.action}
                  className="ghost-button"
                  onClick={() => onReact(action.action, action.mission_id)}
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        </article>

        <aside className="learning-card">
          <Sparkles size={20} />
          <div>
            <span className="card-kicker">Personalization</span>
            <h3>{dashboard.experience.learning.active ? "Lumen is adapting" : "No tuning needed"}</h3>
            <p>{dashboard.experience.learning.message}</p>
          </div>
        </aside>
      </div>

      <div className="section-heading">
        <div>
          <span className="eyebrow">Mission radar</span>
          <h2>What else is worth your attention</h2>
        </div>
        <button className="text-button" onClick={() => setScreen("activity")}>See all <ChevronRight size={16} /></button>
      </div>
      <div className="radar-list">
        {dashboard.radar.map((mission, index) => (
          <div className="radar-row" key={mission.id}>
            <span className="radar-rank">0{index + 1}</span>
            <div className="radar-copy">
              <strong>{mission.title}</strong>
              <span>Personal fit {mission.score.toFixed(1)}</span>
            </div>
            <div className="score-pill">{mission.score.toFixed(1)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MissionScreen({ dashboard, onComplete }: {
  dashboard: Dashboard;
  onComplete: (step: number) => void;
}) {
  const today = dashboard.today;
  if (!today) {
    return <section className="screen-content empty-state"><Sparkles size={28} /><h1>Nothing urgent right now.</h1></section>;
  }
  return (
    <section className="screen-content mission-screen">
      <header className="topbar">
        <div>
          <span className="eyebrow">Focus session</span>
          <h1>{today.title}</h1>
        </div>
        <div className="session-time"><Clock3 size={17} /> {today.focus_minutes} min</div>
      </header>
      <div className="mission-layout">
        <div className="steps-card">
          <div className="progress-header">
            <span>{today.progress.completed} of {today.progress.total} complete</span>
            <strong>{today.progress.percent}%</strong>
          </div>
          <div className="progress-track"><span style={{ width: `${today.progress.percent}%` }} /></div>
          <div className="steps-list">
            {today.steps.map((step) => (
              <button
                key={step.number}
                className={step.done ? "step-row done" : "step-row"}
                onClick={() => !step.done && onComplete(step.number)}
              >
                <span className="step-check">{step.done ? <Check size={15} /> : step.number}</span>
                <span>{step.text}</span>
              </button>
            ))}
          </div>
        </div>
        <aside className="mission-aside">
          <div className="detail-card">
            <span className="card-kicker">Why now</span>
            <p>{today.why_now}</p>
          </div>
          <div className="detail-card">
            <span className="card-kicker">Done means</span>
            <p>{today.definition_of_done}</p>
          </div>
        </aside>
      </div>
    </section>
  );
}

function ActivityScreen({ dashboard }: { dashboard: Dashboard }) {
  return (
    <section className="screen-content">
      <header className="topbar">
        <div><span className="eyebrow">Activity</span><h1>Your momentum</h1></div>
      </header>
      <div className="stats-grid">
        <div className="stat-card"><span>Active missions</span><strong>{dashboard.summary.active_missions}</strong></div>
        <div className="stat-card"><span>Steps completed</span><strong>{dashboard.summary.completed_steps}</strong></div>
        <div className="stat-card"><span>Learning signals</span><strong>{dashboard.personalization.signal_count}</strong></div>
      </div>
      <div className="section-heading compact"><div><span className="eyebrow">Radar</span><h2>Current priorities</h2></div></div>
      <div className="radar-list">
        {dashboard.radar.map((mission, index) => (
          <div className="radar-row" key={mission.id}>
            <span className="radar-rank">0{index + 1}</span>
            <div className="radar-copy"><strong>{mission.title}</strong><span>Ranked from your goals and behavior</span></div>
            <div className="score-pill">{mission.score.toFixed(1)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ProfileScreen({ dashboard }: { dashboard: Dashboard }) {
  return (
    <section className="screen-content">
      <header className="topbar"><div><span className="eyebrow">Profile</span><h1>{dashboard.user.display_name}</h1></div></header>
      <div className="profile-panel">
        <div className="profile-avatar">{dashboard.user.display_name.slice(0, 1).toUpperCase()}</div>
        <div>
          <h2>Lumen is personal to this workspace</h2>
          <p>Your missions, progress and preference signals stay isolated from every other user.</p>
        </div>
      </div>
      <div className="learning-card profile-learning">
        <Sparkles size={20} />
        <div><span className="card-kicker">Adaptive profile</span><h3>{dashboard.personalization.signal_count} signals learned</h3><p>Use Lumen normally. Finishing work and lightweight reactions refine future ranking automatically.</p></div>
      </div>
    </section>
  );
}

export default function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [screen, setScreen] = useState<Screen>("home");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    bootstrap("default")
      .then((result) => {
        setNeedsOnboarding(!result.initialized);
        setDashboard(result.dashboard);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Lumen could not start."))
      .finally(() => setLoading(false));
  }, []);

  const content = useMemo(() => {
    if (!dashboard) return null;
    if (screen === "mission") return <MissionScreen dashboard={dashboard} onComplete={handleComplete} />;
    if (screen === "activity") return <ActivityScreen dashboard={dashboard} />;
    if (screen === "profile") return <ProfileScreen dashboard={dashboard} />;
    return <HomeScreen dashboard={dashboard} setScreen={setScreen} onReact={handleReact} />;
  }, [dashboard, screen]);

  async function handleReact(action: "more_like_this" | "not_now" | "less_like_this", missionId: string) {
    if (!dashboard || working) return;
    setWorking(true);
    setError(null);
    try {
      setDashboard(await reactToMission(dashboard.user.id, action, missionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update your preference.");
    } finally {
      setWorking(false);
    }
  }

  async function handleComplete(step: number) {
    if (!dashboard?.today || working) return;
    setWorking(true);
    setError(null);
    try {
      setDashboard(await completeStep(dashboard.user.id, dashboard.today.mission_id, step));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save progress.");
    } finally {
      setWorking(false);
    }
  }

  if (loading) {
    return <div className="launch-screen"><div className="brand-mark large"><Sparkles size={24} /></div><Loader2 className="spin" size={22} /></div>;
  }

  if (error && !dashboard && !needsOnboarding) {
    return <div className="launch-screen error-state"><h1>Lumen couldn't start</h1><p>{error}</p></div>;
  }

  if (needsOnboarding || !dashboard) {
    return <Onboarding onReady={(next) => { setDashboard(next); setNeedsOnboarding(false); }} />;
  }

  return (
    <div className="app-shell">
      <Sidebar screen={screen} setScreen={setScreen} dashboard={dashboard} />
      <main className="main-pane">
        {working && <div className="working-indicator"><Loader2 className="spin" size={14} /> Saving</div>}
        {error && <button className="toast-error" onClick={() => setError(null)}>{error}<X size={14} /></button>}
        {content}
      </main>
    </div>
  );
}
