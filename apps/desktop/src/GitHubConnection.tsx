import { useEffect, useState } from "react";
import { Github, Loader2, RefreshCw, Unplug } from "lucide-react";
import { copy, errorMessage } from "./i18n";
import {
  connectGitHub,
  Dashboard,
  disconnectGitHub,
  GitHubContextSnapshot,
  Locale,
  previewGitHub,
  refreshGitHub,
} from "./lib/lumen";

type Props = {
  dashboard: Dashboard;
  locale: Locale;
  onDashboard: (dashboard: Dashboard) => void;
};

export default function GitHubConnection({ dashboard, locale, onDashboard }: Props) {
  const integration = dashboard.integrations?.github;
  const t = copy(locale).github;
  const [username, setUsername] = useState(integration?.account?.username ?? "");
  const [preview, setPreview] = useState<GitHubContextSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (integration?.account?.username) {
      setUsername(integration.account.username);
    }
  }, [integration?.account?.username]);

  const run = async (action: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(errorMessage(err, t.updateError));
    } finally {
      setBusy(false);
    }
  };

  const handlePreview = () => run(async () => {
    setPreview(await previewGitHub(dashboard.user.id, username.trim()));
  });

  const handleConnect = () => run(async () => {
    const next = await connectGitHub(dashboard.user.id, username.trim());
    setPreview(null);
    onDashboard(next);
  });

  const handleRefresh = () => run(async () => {
    onDashboard(await refreshGitHub(dashboard.user.id));
  });

  const handleDisconnect = () => run(async () => {
    onDashboard(await disconnectGitHub(dashboard.user.id));
    setPreview(null);
  });

  if (integration?.connected && integration.account) {
    return (
      <section className="github-context-card">
        <div className="github-context-heading">
          <div className="github-context-title">
            <div className="github-mark"><Github size={20} /></div>
            <div>
              <span className="card-kicker">{t.connectedContext}</span>
              <h3>@{integration.account.username}</h3>
            </div>
          </div>
          <span className="connection-status">{t.publicContext}</span>
        </div>

        <p className="github-context-description">{t.connectedBody}</p>

        {integration.active_repositories.length > 0 && (
          <div className="github-repo-list">
            <span className="github-section-label">{t.recentRepos}</span>
            {integration.active_repositories.slice(0, 3).map((repo) => (
              <div className="github-repo-row" key={repo.full_name}>
                <div>
                  <strong>{repo.full_name}</strong>
                  <span>{repo.description ?? t.noDescription}</span>
                </div>
                {repo.language && <small>{repo.language}</small>}
              </div>
            ))}
          </div>
        )}

        {integration.languages.length > 0 && (
          <div className="github-language-row">
            {integration.languages.slice(0, 5).map((language) => (
              <span key={language.name}>{language.name}</span>
            ))}
          </div>
        )}

        {error && <div className="error-banner github-error">{error}</div>}

        <div className="github-actions">
          <button className="ghost-button" onClick={handleRefresh} disabled={busy}>
            {busy ? <Loader2 className="spin" size={15} /> : <RefreshCw size={15} />}
            {t.refresh}
          </button>
          <button className="text-button danger-text" onClick={handleDisconnect} disabled={busy}>
            <Unplug size={14} /> {t.disconnect}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="github-context-card">
      <div className="github-context-heading">
        <div className="github-context-title">
          <div className="github-mark"><Github size={20} /></div>
          <div>
            <span className="card-kicker">{t.optionalContext}</span>
            <h3>GitHub</h3>
          </div>
        </div>
      </div>

      <p className="github-context-description">{t.intro}</p>

      <div className="github-connect-row">
        <input
          value={username}
          onChange={(event) => {
            setUsername(event.target.value);
            setPreview(null);
          }}
          placeholder={t.username}
          aria-label={t.username}
        />
        <button
          className="ghost-button"
          disabled={busy || !username.trim()}
          onClick={handlePreview}
        >
          {busy ? <Loader2 className="spin" size={15} /> : <Github size={15} />}
          {t.preview}
        </button>
      </div>

      {error && <div className="error-banner github-error">{error}</div>}

      {preview && (
        <div className="github-preview">
          <div className="github-preview-account">
            <div>
              <span>{t.found}</span>
              <strong>{preview.account.name ?? `@${preview.account.username}`}</strong>
              <small>@{preview.account.username} · {preview.account.public_repos} {t.publicRepos}</small>
            </div>
            {preview.signals.primary_language && (
              <span className="connection-status">{preview.signals.primary_language}</span>
            )}
          </div>

          <div className="github-repo-list compact">
            {preview.active_repositories.slice(0, 3).map((repo) => (
              <div className="github-repo-row" key={repo.full_name}>
                <div>
                  <strong>{repo.full_name}</strong>
                  <span>{repo.description ?? t.noDescription}</span>
                </div>
                {repo.language && <small>{repo.language}</small>}
              </div>
            ))}
          </div>

          <p className="github-preview-note">{t.previewNote}</p>
          <div className="github-actions">
            <button className="primary-button" onClick={handleConnect} disabled={busy}>
              {busy ? <Loader2 className="spin" size={15} /> : <Github size={15} />}
              {t.useContext}
            </button>
            <button className="text-button" onClick={() => setPreview(null)} disabled={busy}>
              {t.cancel}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
