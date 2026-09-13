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
import GitHubConnection from "./GitHubConnection";
import { copy, detectLocale, errorMessage, persistLocale } from "./i18n";
import {
  answerClarification,
  bootstrap,
  completeStep,
  Dashboard,
  guidedOnboard,
  Locale,
  reactToMission,
  setRequestLocale,
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

function LanguageToggle({ locale, onChange }: { locale: Locale; onChange: (locale: Locale) => void }) {
  const t = copy(locale).language;
  const next = locale === "ru" ? "en" : "ru";
  return (
    <button
      className="text-button"
      type="button"
      onClick={() => onChange(next)}
      title={t.current}
      aria-label={`${t.current} → ${t.switchTo}`}
    >
      {t.switchTo}
    </button>
  );
}

function Onboarding({
  locale,
  onLocale,
  onReady,
}: {
  locale: Locale;
  onLocale: (locale: Locale) => void;
  onReady: (dashboard: Dashboard) => void;
}) {
  const t = copy(locale).onboarding;
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
      setError(errorMessage(err, t.startError));
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
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <LanguageToggle locale={locale} onChange={onLocale} />
            <span className="onboarding-progress-label">{t.progress} · {progress}%</span>
          </div>
        </div>
        <div className="onboarding-progress-track"><span style={{ width: `${progress}%` }} /></div>

        {step === "name" && (
          <div className="conversation-step">
            <span className="eyebrow">{t.firstKicker}</span>
            <h1>{t.nameTitle}</h1>
            <p>{t.nameBody}</p>
            <input
              autoFocus
              className="conversation-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              onKeyDown={onEnter}
              placeholder={t.namePlaceholder}
            />
          </div>
        )}

        {step === "context" && (
          <div className="conversation-step">
            <span className="eyebrow">{t.contextKicker}</span>
            <h1>{t.contextTitle}</h1>
            <p>{t.contextBody}</p>
            <textarea
              autoFocus
              className="conversation-textarea"
              value={currentContext}
              onChange={(event) => setCurrentContext(event.target.value)}
              placeholder={t.contextPlaceholder}
            />
          </div>
        )}

        {step === "change" && (
          <div className="conversation-step">
            <span className="eyebrow">{t.changeKicker}</span>
            <h1>{t.changeTitle}</h1>
            <p>{t.changeBody}</p>
            <textarea
              autoFocus
              className="conversation-textarea"
              value={desiredChange}
              onChange={(event) => setDesiredChange(event.target.value)}
              placeholder={t.changePlaceholder}
            />
          </div>
        )}

        {step === "friction" && (
          <div className="conversation-step">
            <span className="eyebrow">{t.frictionKicker}</span>
            <h1>{t.frictionTitle}</h1>
            <p>{t.frictionBody}</p>
            <textarea
              autoFocus
              className="conversation-textarea"
              value={friction}
              onChange={(event) => setFriction(event.target.value)}
              placeholder={t.frictionPlaceholder}
            />
          </div>
        )}

        {step === "focus" && (
          <div className="conversation-step">
            <span className="eyebrow">{t.focusKicker}</span>
            <h1>{t.focusTitle}</h1>
            <p>{t.focusBody}</p>
            <div className="focus-choice-grid">
              {([15, 30, 60] as const).map((minutes) => (
                <button
                  key={minutes}
                  className={focusMinutes === minutes ? "focus-choice active" : "focus-choice"}
                  onClick={() => setFocusMinutes(minutes)}
                >
                  <strong>{minutes} {locale === "ru" ? "мин" : "min"}</strong>
                  <span>{minutes === 15 ? t.smallWins : minutes === 30 ? t.steadyProgress : t.deepFocus}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === "review" && (
          <div className="conversation-step review-step">
            <span className="eyebrow">{t.reviewKicker}</span>
            <h1>{t.reviewTitle}</h1>
            <p>{t.reviewBody}</p>
            <div className="context-review">
              <div><span>{t.currentContext}</span><strong>{currentContext}</strong></div>
              <div><span>{t.direction}</span><strong>{desiredChange}</strong></div>
              {friction.trim() && <div><span>{t.friction}</span><strong>{friction}</strong></div>}
              <div><span>{t.focusWindow}</span><strong>{focusMinutes} {t.minutes}</strong></div>
            </div>
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}

        <div className="onboarding-navigation">
          {stepIndex > 0 ? (
            <button className="ghost-button" type="button" onClick={back} disabled={busy}>
              <ArrowLeft size={16} /> {t.back}
            </button>
          ) : <span />}

          {step === "review" ? (
            <button className="primary-button" disabled={busy} onClick={submit}>
              {busy ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
              {t.build}
              {!busy && <ArrowRight size={18} />}
            </button>
          ) : (
            <button className="primary-button" disabled={!canContinue || busy} onClick={next}>
              {step === "friction" && !friction.trim() ? t.skip : t.continue}
              <ArrowRight size={18} />
            </button>
          )}
        </div>
      </section>
    </main>
  );
}

function Sidebar({ screen, setScreen, dashboard, locale }: {
  screen: Screen;
  setScreen: (screen: Screen) => void;
  dashboard: Dashboard;
  locale: Locale;
}) {
  const t = copy(locale).sidebar;
  const items: Array<{ id: Screen; label: string; icon: typeof Home }> = [
    { id: "home", label: t.today, icon: Home },
    { id: "mission", label: t.focus, icon: Target },
    { id: "activity", label: t.activity, icon: Activity },
    { id: "profile", label: t.profile, icon: CircleUserRound },
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
          <strong>{dashboard.personalization.adapting ? t.learning : t.ready}</strong>
          <span>{dashboard.personalization.signal_count} {t.signals}</span>
        </div>
      </div>
    </aside>
  );
}

function HomeScreen({ dashboard, setScreen, onReact, onClarify, locale }: {
  dashboard: Dashboard;
  setScreen: (screen: Screen) => void;
  onReact: (action: "more_like_this" | "not_now" | "less_like_this", missionId: string) => void;
  onClarify: (clarificationId: string, choice: string) => void;
  locale: Locale;
}) {
  const t = copy(locale).home;
  const today = dashboard.today;
  const progress = today?.progress.percent ?? 0;
  return (
    <section className="screen-content home-screen">
      <header className="topbar">
        <div>
          <span className="eyebrow">{t.today}</span>
          <h1>{dashboard.experience.headline}</h1>
        </div>
        <div className="avatar-chip">{dashboard.user.display_name.slice(0, 1).toUpperCase()}</div>
      </header>

      <div className="hero-grid">
        <article className="focus-card">
          <div className="focus-card-top">
            <div>
              <span className="card-kicker">{t.bestNext}</span>
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
                <span><Clock3 size={16} /> {today.focus_minutes} {t.minFocus}</span>
                <span><Target size={16} /> {today.progress.completed}/{today.progress.total} {t.steps}</span>
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
            <span className="card-kicker">{t.personalization}</span>
            <h3>{dashboard.context ? t.learningPattern : dashboard.experience.learning.active ? t.adapting : t.noTuning}</h3>
            <p>{dashboard.context ? t.hypotheses : dashboard.experience.learning.message}</p>
          </div>
        </aside>
      </div>

      {dashboard.clarification && (
        <article className="clarification-card">
          <div className="clarification-icon"><Sparkles size={18} /></div>
          <div className="clarification-copy">
            <span className="card-kicker">{t.quickCheck}</span>
            <h3>{dashboard.clarification.prompt}</h3>
            <p>{t.quickCheckBody}</p>
            <div className="clarification-actions">
              {dashboard.clarification.options.map((option) => (
                <button
                  key={option.choice}
                  className="ghost-button"
                  onClick={() => onClarify(dashboard.clarification!.id, option.choice)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </article>
      )}

      <div className="section-heading">
        <div>
          <span className="eyebrow">{t.radar}</span>
          <h2>{t.radarTitle}</h2>
        </div>
        <button className="text-button" onClick={() => setScreen("activity")}>{t.seeAll} <ChevronRight size={16} /></button>
      </div>
      <div className="radar-list">
        {dashboard.radar.map((mission, index) => (
          <div className="radar-row" key={mission.id}>
            <span className="radar-rank">0{index + 1}</span>
            <div className="radar-copy">
              <strong>{mission.title}</strong>
              <span>{t.personalFit} {mission.score.toFixed(1)}</span>
            </div>
            <div className="score-pill">{mission.score.toFixed(1)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MissionScreen({ dashboard, onComplete, locale }: {
  dashboard: Dashboard;
  onComplete: (step: number) => void;
  locale: Locale;
}) {
  const t = copy(locale).mission;
  const today = dashboard.today;
  if (!today) {
    return <section className="screen-content empty-state"><Sparkles size={28} /><h1>{t.empty}</h1></section>;
  }
  return (
    <section className="screen-content mission-screen">
      <header className="topbar">
        <div>
          <span className="eyebrow">{t.kicker}</span>
          <h1>{today.title}</h1>
        </div>
        <div className="session-time"><Clock3 size={17} /> {today.focus_minutes} {t.min}</div>
      </header>
      <div className="mission-layout">
        <div className="steps-card">
          <div className="progress-header">
            <span>{today.progress.completed} / {today.progress.total} {t.complete}</span>
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
            <span className="card-kicker">{t.whyNow}</span>
            <p>{today.why_now}</p>
          </div>
          <div className="detail-card">
            <span className="card-kicker">{t.doneMeans}</span>
            <p>{today.definition_of_done}</p>
          </div>
        </aside>
      </div>
    </section>
  );
}

function ActivityScreen({ dashboard, locale }: { dashboard: Dashboard; locale: Locale }) {
  const t = copy(locale).activity;
  return (
    <section className="screen-content">
      <header className="topbar">
        <div><span className="eyebrow">{t.kicker}</span><h1>{t.title}</h1></div>
      </header>
      <div className="stats-grid">
        <div className="stat-card"><span>{t.activeMissions}</span><strong>{dashboard.summary.active_missions}</strong></div>
        <div className="stat-card"><span>{t.stepsCompleted}</span><strong>{dashboard.summary.completed_steps}</strong></div>
        <div className="stat-card"><span>{t.learningSignals}</span><strong>{dashboard.personalization.signal_count}</strong></div>
      </div>
      <div className="section-heading compact"><div><span className="eyebrow">{t.radar}</span><h2>{t.priorities}</h2></div></div>
      <div className="radar-list">
        {dashboard.radar.map((mission, index) => (
          <div className="radar-row" key={mission.id}>
            <span className="radar-rank">0{index + 1}</span>
            <div className="radar-copy"><strong>{mission.title}</strong><span>{t.ranked}</span></div>
            <div className="score-pill">{mission.score.toFixed(1)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ProfileScreen({ dashboard, onDashboard, locale, onLocale }: {
  dashboard: Dashboard;
  onDashboard: (dashboard: Dashboard) => void;
  locale: Locale;
  onLocale: (locale: Locale) => void;
}) {
  const t = copy(locale).profile;
  return (
    <section className="screen-content">
      <header className="topbar">
        <div><span className="eyebrow">{t.kicker}</span><h1>{dashboard.user.display_name}</h1></div>
        <LanguageToggle locale={locale} onChange={onLocale} />
      </header>
      <div className="profile-panel">
        <div className="profile-avatar">{dashboard.user.display_name.slice(0, 1).toUpperCase()}</div>
        <div>
          <h2>{t.personalTitle}</h2>
          <p>{t.personalBody}</p>
        </div>
      </div>

      {dashboard.context && (
        <div className="context-panel">
          <div className="section-heading compact">
            <div>
              <span className="eyebrow">{t.understands}</span>
              <h2>{t.assumptions}</h2>
            </div>
          </div>
          <div className="context-grid">
            {dashboard.context.hypotheses.map((item) => (
              <div className="context-item" key={item.key}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{Math.round(item.confidence * 100)}% {t.confidence}</small>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="section-heading compact">
        <div>
          <span className="eyebrow">{t.connections}</span>
          <h2>{t.connectionsTitle}</h2>
        </div>
      </div>
      <GitHubConnection dashboard={dashboard} locale={locale} onDashboard={onDashboard} />

      <div className="learning-card profile-learning">
        <Sparkles size={20} />
        <div><span className="card-kicker">{t.adaptive}</span><h3>{dashboard.personalization.signal_count} {t.signals}</h3><p>{t.adaptiveBody}</p></div>
      </div>
    </section>
  );
}

export default function App() {
  const [locale, setLocale] = useState<Locale>(() => detectLocale());
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [screen, setScreen] = useState<Screen>("home");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const appCopy = copy(locale).app;

  useEffect(() => {
    persistLocale(locale);
    setRequestLocale(locale);
  }, [locale]);

  useEffect(() => {
    setRequestLocale(locale);
    bootstrap("default")
      .then((result) => {
        const resolved = result.context?.locale ?? result.dashboard?.locale ?? result.locale;
        if ((resolved === "ru" || resolved === "en") && resolved !== locale) {
          setLocale(resolved);
          setRequestLocale(resolved);
          persistLocale(resolved);
        }
        setNeedsOnboarding(!result.initialized);
        setDashboard(result.dashboard);
      })
      .catch((err) => setError(errorMessage(err, appCopy.startupError)))
      .finally(() => setLoading(false));
  }, []);

  const changeLocale = (next: Locale) => {
    setRequestLocale(next);
    persistLocale(next);
    setLocale(next);
    if (dashboard) {
      setWorking(true);
      bootstrap(dashboard.user.id)
        .then((result) => {
          if (result.dashboard) setDashboard(result.dashboard);
        })
        .catch((err) => setError(errorMessage(err, copy(next).app.startupError)))
        .finally(() => setWorking(false));
    }
  };

  const content = useMemo(() => {
    if (!dashboard) return null;
    if (screen === "mission") return <MissionScreen dashboard={dashboard} onComplete={handleComplete} locale={locale} />;
    if (screen === "activity") return <ActivityScreen dashboard={dashboard} locale={locale} />;
    if (screen === "profile") return <ProfileScreen dashboard={dashboard} onDashboard={setDashboard} locale={locale} onLocale={changeLocale} />;
    return <HomeScreen dashboard={dashboard} setScreen={setScreen} onReact={handleReact} onClarify={handleClarify} locale={locale} />;
  }, [dashboard, screen, locale]);

  async function handleReact(action: "more_like_this" | "not_now" | "less_like_this", missionId: string) {
    if (!dashboard || working) return;
    setWorking(true);
    setError(null);
    try {
      setDashboard(await reactToMission(dashboard.user.id, action, missionId));
    } catch (err) {
      setError(errorMessage(err, appCopy.preferenceError));
    } finally {
      setWorking(false);
    }
  }

  async function handleClarify(clarificationId: string, choice: string) {
    if (!dashboard || working) return;
    setWorking(true);
    setError(null);
    try {
      setDashboard(await answerClarification(dashboard.user.id, clarificationId, choice));
    } catch (err) {
      setError(errorMessage(err, appCopy.understandingError));
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
      setError(errorMessage(err, appCopy.progressError));
    } finally {
      setWorking(false);
    }
  }

  if (loading) {
    return <div className="launch-screen"><div className="brand-mark large"><Sparkles size={24} /></div><Loader2 className="spin" size={22} /></div>;
  }

  if (error && !dashboard && !needsOnboarding) {
    return <div className="launch-screen error-state"><h1>{appCopy.fatalTitle}</h1><p>{error}</p></div>;
  }

  if (needsOnboarding || !dashboard) {
    return <Onboarding locale={locale} onLocale={changeLocale} onReady={(next) => { setDashboard(next); setNeedsOnboarding(false); }} />;
  }

  return (
    <div className="app-shell">
      <Sidebar screen={screen} setScreen={setScreen} dashboard={dashboard} locale={locale} />
      <main className="main-pane">
        {working && <div className="working-indicator"><Loader2 className="spin" size={14} /> {appCopy.saving}</div>}
        {error && <button className="toast-error" onClick={() => setError(null)}>{error}<X size={14} /></button>}
        {content}
      </main>
    </div>
  );
}
