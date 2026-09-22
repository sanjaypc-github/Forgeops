import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ExternalLink, Lock, Plug, RefreshCw, Trash2, TriangleAlert } from "lucide-react";
import {
  DESK_LABELS, DESK_ORDER, byDesk, connectionTools, createConnection, deleteConnection, getCatalog,
  listConnections, testConnection, type Ability, type CatalogEntry, type Connection, type ConnectionCreated,
} from "../api/connectors";
import type { AgentId } from "../api/types";
import "../styles/connectors.css";

const CONNECTIONS_KEY = ["connections"];

function AbilityList({ abilities }: { abilities: Ability[] }) {
  return (
    <div className="abilities">
      {byDesk(abilities).map(([desk, list]) => (
        <div key={desk} className="ability-desk">
          <h4>{DESK_LABELS[desk]}</h4>
          <ul>
            {list.map((a) => (
              <li key={a.name}>
                <span className="mono">{a.name}</span>
                {a.permission === "write" && <span className="pill write">write · needs approval</span>}
                <span className="muted small">{a.description}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function DeskChips({ desks }: { desks: AgentId[] }) {
  return (
    <ul className="desk-chips" aria-label="Desks">
      {desks.map((d) => <li key={d}>{DESK_LABELS[d]}</li>)}
    </ul>
  );
}

function ConnectForm({ entry, onCancel, onConnected }: {
  entry: CatalogEntry; onCancel: () => void; onConnected: (created: ConnectionCreated) => void;
}) {
  const [name, setName] = useState(entry.display_name);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const formRef = useRef<HTMLFormElement>(null);
  useEffect(() => {
    formRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
    formRef.current?.querySelector<HTMLInputElement>(".fields input:not(#conn-name)")?.focus({ preventScroll: true });
  }, []);
  const create = useMutation({
    mutationFn: createConnection,
    onSuccess: (created) => {
      setValues({}); // drop typed secrets from memory as soon as they are stored
      onConnected(created);
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const config: Record<string, string | boolean> = {};
    const secrets: Record<string, string> = {};
    for (const field of entry.config_fields) {
      const value = values[field.key];
      if (field.boolean) config[field.key] = value === true;
      else if (typeof value === "string" && value.trim()) {
        if (field.secret) secrets[field.key] = value.trim();
        else config[field.key] = value.trim();
      }
    }
    create.mutate({ type: entry.type, name: name.trim() || entry.display_name, config, secrets });
  }

  return (
    <form ref={formRef} className="connect-form" onSubmit={onSubmit} aria-labelledby="connect-title">
      <div className="connect-head">
        <h2 id="connect-title">Connect {entry.display_name}</h2>
        {entry.docs_url && (
          <a href={entry.docs_url} target="_blank" rel="noreferrer" className="small">
            Server docs <ExternalLink size={13} aria-hidden />
          </a>
        )}
      </div>

      {entry.setup_steps.length > 0 && (
        <ol className="setup-steps">
          {entry.setup_steps.map((step) => <li key={step}>{step}</li>)}
        </ol>
      )}

      <div className="fields">
        <div>
          <label htmlFor="conn-name">Connection name</label>
          <input id="conn-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
        </div>
        {entry.config_fields.map((field) => field.boolean ? (
          <div key={field.key} className="check">
            <input id={`f-${field.key}`} type="checkbox" checked={values[field.key] === true}
              onChange={(e) => setValues({ ...values, [field.key]: e.target.checked })} />
            <label htmlFor={`f-${field.key}`}>{field.label}</label>
            {field.help && <p className="muted small">{field.help}</p>}
          </div>
        ) : (
          <div key={field.key}>
            <label htmlFor={`f-${field.key}`}>
              {field.label}{field.secret && <Lock size={12} aria-label="secret" className="lock" />}
            </label>
            <input id={`f-${field.key}`} type={field.secret ? "password" : "text"} required={field.required}
              autoComplete="off" spellCheck={false} placeholder={field.placeholder}
              pattern={field.pattern ?? undefined}
              value={typeof values[field.key] === "string" ? (values[field.key] as string) : ""}
              onChange={(e) => setValues({ ...values, [field.key]: e.target.value })} />
            {field.help && <p className="muted small">{field.help}</p>}
          </div>
        ))}
      </div>

      {entry.abilities.length > 0 && (
        <details className="preview">
          <summary>What the agents get ({entry.abilities.length} abilities)</summary>
          <AbilityList abilities={entry.abilities} />
        </details>
      )}

      <p className="muted small">
        Secrets are encrypted on the server and never shown again. Investigations only use read abilities.
      </p>
      {create.isError && <p className="error" role="alert">{create.error.message}</p>}
      <div className="row">
        <button type="submit" disabled={create.isPending}>
          {create.isPending ? "Connecting and testing…" : "Connect and test"}
        </button>
        <button type="button" className="secondary" onClick={onCancel} disabled={create.isPending}>Cancel</button>
      </div>
    </form>
  );
}

function ConnectionCard({ connection, entry, note }: {
  connection: Connection; entry: CatalogEntry | undefined; note: string | undefined;
}) {
  const queryClient = useQueryClient();
  const [showTools, setShowTools] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const tools = useQuery({
    queryKey: ["connection-tools", connection.id], queryFn: () => connectionTools(connection.id),
    enabled: showTools, retry: false, staleTime: 60_000,
  });
  const retest = useMutation({
    mutationFn: () => testConnection(connection.id),
    onSettled: () => queryClient.invalidateQueries({ queryKey: CONNECTIONS_KEY }),
  });
  const remove = useMutation({
    mutationFn: () => deleteConnection(connection.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CONNECTIONS_KEY }),
  });

  const ok = connection.status === "connected";
  const detail = retest.data?.detail ?? (ok ? note : connection.last_error);
  const target = String(connection.config.repository ?? connection.config.project_ref ?? connection.config.vault_path ?? "");

  return (
    <li className="connection">
      <div className="connection-head">
        <span className={`status ${ok ? "ok" : "bad"}`}>
          {ok ? <CheckCircle2 size={16} aria-hidden /> : <TriangleAlert size={16} aria-hidden />}
          {ok ? "Connected" : "Needs attention"}
        </span>
        <h3>{connection.name}</h3>
        <span className="muted small">{entry?.display_name ?? connection.type}</span>
        {target && <span className="mono small target">{target}</span>}
        {connection.config.allow_writes === true && <span className="pill write">issues after approval</span>}
      </div>
      {detail && <p className={`small ${ok ? "muted" : "error"}`}>{detail}</p>}
      {entry && <DeskChips desks={entry.agents} />}
      <div className="row">
        <button className="secondary small" onClick={() => setShowTools(!showTools)} aria-expanded={showTools}>
          {showTools ? "Hide abilities" : "Show abilities"}
        </button>
        <button className="secondary small" onClick={() => retest.mutate()} disabled={retest.isPending}>
          <RefreshCw size={13} aria-hidden /> {retest.isPending ? "Testing…" : "Test again"}
        </button>
        {confirming ? (
          <>
            <button className="small danger" onClick={() => remove.mutate()} disabled={remove.isPending}>
              Disconnect {connection.name}
            </button>
            <button className="ghost small" onClick={() => setConfirming(false)}>Keep</button>
          </>
        ) : (
          <button className="ghost small" onClick={() => setConfirming(true)}>
            <Trash2 size={13} aria-hidden /> Disconnect
          </button>
        )}
      </div>
      {remove.isError && <p className="error small" role="alert">{remove.error.message}</p>}
      {showTools && (
        tools.isPending ? <p className="muted small">Asking the server for its tools…</p>
          : tools.isError ? <p className="error small">{tools.error.message}</p>
            : tools.data.length === 0 ? <p className="muted small">No abilities available right now.</p>
              : <AbilityList abilities={tools.data} />
      )}
    </li>
  );
}

export function ConnectorsPage() {
  const queryClient = useQueryClient();
  const catalog = useQuery({ queryKey: ["catalog"], queryFn: getCatalog, staleTime: Infinity });
  const connections = useQuery({ queryKey: CONNECTIONS_KEY, queryFn: listConnections });
  const [connecting, setConnecting] = useState<CatalogEntry | null>(null);
  const [desk, setDesk] = useState<AgentId | "all">("all");
  const [notes, setNotes] = useState<Record<string, string>>({});

  const entries = catalog.data ?? [];
  const byType = new Map(entries.map((e) => [e.type, e]));
  const shown = entries
    .filter((e) => desk === "all" || e.agents.includes(desk))
    .sort((a, b) => Number(a.status !== "available") - Number(b.status !== "available"));

  function onConnected(created: ConnectionCreated) {
    setNotes((n) => ({ ...n, [created.id]: created.detail }));
    setConnecting(null);
    queryClient.invalidateQueries({ queryKey: CONNECTIONS_KEY });
  }

  return (
    <div className="connectors">
      <header className="connectors-head">
        <h1>Connectors</h1>
        <p className="muted">
          Connect each tool once. Every ability it offers goes to the desk that owns that part of your system,
          so the right agent investigates with it.
        </p>
      </header>

      <section aria-labelledby="yours-title">
        <h2 id="yours-title">Your connections</h2>
        {connections.isPending && <p className="muted">Loading…</p>}
        {connections.isError && <p className="error">Could not load connections. Check that the API is running.</p>}
        {connections.data?.length === 0 && (
          <p className="muted">Nothing connected yet. Pick a tool from the catalog below.</p>
        )}
        {!!connections.data?.length && (
          <ul className="connection-list">
            {connections.data.map((c) => (
              <ConnectionCard key={c.id} connection={c} entry={byType.get(c.type)} note={notes[c.id]} />
            ))}
          </ul>
        )}
      </section>

      {connecting && (
        <ConnectForm key={connecting.type} entry={connecting} onCancel={() => setConnecting(null)}
          onConnected={onConnected} />
      )}

      <section aria-labelledby="catalog-title">
        <div className="catalog-head">
          <h2 id="catalog-title">Catalog</h2>
          <div className="desk-filter" role="group" aria-label="Filter by desk">
            {(["all", ...DESK_ORDER.filter((d) => d !== "action")] as const).map((d) => (
              <button key={d} className={`ghost small ${desk === d ? "on" : ""}`} aria-pressed={desk === d}
                onClick={() => setDesk(d)}>
                {d === "all" ? "All desks" : DESK_LABELS[d]}
              </button>
            ))}
          </div>
        </div>
        {catalog.isError && <p className="error">Could not load the catalog.</p>}
        <ul className="catalog">
          {shown.map((entry) => {
            const soon = entry.status !== "available";
            return (
              <li key={entry.type} className={`catalog-card ${soon ? "soon" : ""}`}>
                <div className="catalog-title">
                  <h3>{entry.display_name}</h3>
                  {soon && <span className="pill">coming soon</span>}
                </div>
                <p className="small muted">{entry.description}</p>
                <DeskChips desks={entry.agents} />
                {!soon && (
                  <button className="small" onClick={() => setConnecting(entry)}
                    aria-label={`Connect ${entry.display_name}`}>
                    <Plug size={13} aria-hidden /> Connect
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
