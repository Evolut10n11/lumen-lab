import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  CircleUserRound,
  Clock3,
  Home,
  Loader2,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import {
  bootstrap,
  completeStep,
  Dashboard,
  guidedOnboard,
  reactToMission,
} from "./lib/lumen";

type Screen = "home" | "mission" | "activity" | "profile";
type OnboardingStep = "name" | "context" | "change" | "friction" | "focus" | "review";

const onboardingSteps: OnboardingStep[] = [
  "name",
  "context",
  "change",
  "friction",
  "focus",
  "review",
];

function Onboarding({ onReady }: { onReady: (dashboard: Dashboard) => void }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [name, setName] = useState("");
  const [currentContext, setCurrentContext] = useState("");
  const [desiredChange, setDesiredChange] = useState("");
  const [friction, setFriction] = useState("");
  const [focusMinutes, setFocusMinutes] = useState<15 | 30 | 60>(30);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const step = onboardingSteps[stepIndex];
  const progress = Math.round(((stepIndex + 1) / onboardingSteps.length) * 100);

  const canContinue =
    step === "name"
      ? name.trim().length > 0
      : step === "context"
        ? currentContext.trim().length > 0
        : step === "change"
          ? desiredChange.trim().length > 0
          : true;

  const next = () => {
    if (!canContinue || stepIndex >= onboardingSteps.length - 1) return;
    setError(null);
    setStepIndex((current) => current + 1);
  };

  const back = () => {
    if (stepIndex === 0 || busy) return;
    setError(null);
    setStepIndex((current) => current - 1);
  };

  const submit = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const dashboard = await guidedOnboard("default", {
        displayName: name.trim(),
        currentContext: currentContext.trim(),
        desiredChange: desiredChange.trim(),
        friction: friction.trim(),
        focusMinutes,
      });
      onReady(dashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start Lumen.");
    } finally {
      setBusy(false);
    }
  };

  const onEnter = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && canContinue) next();
  };

  return (
    <main className="onboarding-shell">
      <section className="onboarding-card conversational-onboarding">
        <div className="onboarding-topline">
          <div className="brand-lockup">
            <div className="brand-mark"><Sparkles size={18} /></div>
            <span>Lumen</span>
          </div>
          <span className="onboarding-progress-label">A short conversation · {progress}%</span>
        </div>
        <div className="onboarding-progress-track"><span style={{ width: `${progress}%` }} /></div>

        {step === "name" && (
          <div className="conversation-step">
            <span className="eyebrow">First things first</span>
            <h1>What should I call you?</h1>
            <p>No profile setup screens. Just tell Lumen enough to make the first useful guess.</p>
            <input
              autoFocus
              className="conversation-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              onKeyDown={onEnter}
              placeholder="Your name"
            />
          </div>
        )}

        {step === "context" && (
          <div className="conversation-step">
            <span className="eyebrow">Your world right now</span>
            <h1>What is taking most of your attention these days?</h1>
            <p>Work, study, a project, family, a move — whatever is actually occupying your head.</p>
            <textarea
              autoFocus
              className="conversation-textarea"
              value={currentContext}
              onChange={(event) => setCurrentContext(event.target.value)}
              placeholder="For example: I work full time, prepare for interviews and try to finish a side project..."
            />
          </div>
        )}

        {step === "change" && (
          <div className="conversation-step">
            <span className="eyebrow">Direction</span>
            <h1>What would you most like to be different a month from now?</h1>
            <p>Say it normally. Lumen will turn the answer into a starting direction, not a permanent setting.</p>
            <textarea
              autoFocus
              className="conversation-textarea"
              value={desiredChange}
              onChange={(event) => setDesiredChange(event.target.value)}
              placeholder="For example: I want to get a stronger AI role and have a project I can proudly show..."
            />
          </div>
        )}

        {step === "friction" && (
          <div className="conversation-step">
            <span className="eyebrow">What gets in the way</span>
            <h1>What usually makes progress harder?</h1>
            <p>This one is optional. It helps Lumen avoid giving advice that looks good but does not fit your life.</p>
            <textarea
              autoFocus
              className="conversation-textarea"
              value={friction}
              onChange={(event) => setFriction(event.target.value)}
              placeholder="Too little time, low energy after work, too many parallel goals..."
            />
          </div>
        )}

        {step === "focus" && (
          <div className="conversation-step">
            <span className="eyebrow">Keep it realistic</span>
            <h1>How much focused time feels reasonable on a normal day?</h1>
            <p>This changes the size of the work Lumen gives you. You can change it later just by using the app.</p>
            <div className="focus-choice-grid">
              {([15, 30, 60] as const).map((minutes) => (
                <button
                  key={minutes}
                  className={focusMinutes === minutes ? "focus-choice active" : "focus-choice"}
                  onClick={() => setFocusMinutes(minutes)}
                >
                  <strong>{minutes} min</strong>
                  <span>{minutes === 15 ? "Small wins" : minutes === 30 ? "Steady progress" : "Deep focus"}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === "review" && (
          <div className="conversation-step review-step">
            <span className="eyebrow">A starting hypothesis</span>
            <h1>Here is what Lumen will start with.</h1>
            <p>
              This is not a locked profile. Lumen will change its understanding as your choices and completed work
              provide better evidence.
            </p>
            <div className="context-review">
              <div><span>Current context</span><strong>{currentContext}</strong></div>
              <div><span>Direction</span><strong>{desiredChange}</strong></div>
              {friction.trim() && <div><span>Friction</span><strong>{friction}</strong></div>}
              <div><span>Focus window</span><strong>{focusMinutes} minutes</strong></div>
            </div>
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}

        <div className="onboarding-navigation">
          {stepIndex > 0 ? (
            <button className="ghost-button" type="button" onClick={back} disabled={busy}>
              <ArrowLeft size={16} /> Back
            </button>
          ) : <span />}

          {step === "review" ? (
            <button className="primary-button" disabled={busy} onClick={submit}>
              {busy ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
              Build my starting point
              {!busy && <ArrowRight size={18} />}
            </button>
          ) : (
            <button className="primary-button" disabled={!canContinue || busy} onClick={next}>
              {step === "friction" && !friction.trim() ? "Skip" : "Continue"}
              <ArrowRight size={18} />
            </button>
          )}
        </div>
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
            <h3>{dashboard.context ? "Starting from your context" : dashboard.experience.learning.active ? "Lumen is adapting" : "No tuning needed"}</h3>
            <p>{dashboard.context ? "These are starting assumptions. Your real choices will gradually outweigh them." : dashboard.experience.learning.message}</p>
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

      {dashboard.context && (
        <div className="context-panel">
          <div className="section-heading compact">
            <div>
              <span className="eyebrow">What Lumen understands so far</span>
              <h2>Starting assumptions, not permanent settings</h2>
            </div>
          </div>
          <div className="context-grid">
            {dashboard.context.hypotheses.map((item) => (
              <div className="context-item" key={item.key}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>Will be revised as Lumen sees what actually works for you.</small>
              </div>
            ))}
          </div>
        </div>
      )}

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
