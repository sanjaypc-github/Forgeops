import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, test, vi } from "vitest";
import type { CatalogEntry, Connection } from "../api/connectors";
import { ConnectorsPage } from "./ConnectorsPage";

const GITHUB: CatalogEntry = {
  type: "github", display_name: "GitHub", description: "Repo", agents: ["code", "frontend_hosting"],
  status: "available", docs_url: null, supports_writes: true,
  setup_steps: ["Create a fine-grained token."],
  config_fields: [
    { key: "repository", label: "Repository", secret: false, required: true, help: "", placeholder: "owner/repo", boolean: false, pattern: null },
    { key: "token", label: "Personal access token", secret: true, required: true, help: "", placeholder: "", boolean: false, pattern: null },
    { key: "allow_writes", label: "Allow creating issues after approval", secret: false, required: false, help: "", placeholder: "", boolean: true, pattern: null },
  ],
  abilities: [
    { name: "github.list_commits", description: "List commits", capability: "code", desk: "code", permission: "read" },
    { name: "github.actions_list", description: "List runs", capability: "hosting", desk: "frontend_hosting", permission: "read" },
    { name: "github.create_issue", description: "Open an issue", capability: "write", desk: "action", permission: "write" },
  ],
};
const VERCEL: CatalogEntry = {
  ...GITHUB, type: "vercel", display_name: "Vercel", status: "coming_soon", agents: ["frontend_hosting"],
  abilities: [], setup_steps: [], config_fields: [],
};

type Route = (url: string, init?: RequestInit) => Response | undefined;

function serve(route: Route) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const response = route(url, init);
    if (!response) throw new Error(`unexpected request ${init?.method ?? "GET"} ${url}`);
    return response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><ConnectorsPage /></QueryClientProvider>);
}

afterEach(() => vi.unstubAllGlobals());

test("shows the catalog with desks and marks coming-soon tools", async () => {
  serve((url) => url === "/api/connectors/catalog" ? json([VERCEL, GITHUB])
    : url === "/api/connections" ? json([]) : undefined);
  renderPage();

  const github = (await screen.findByRole("heading", { name: "GitHub" })).closest("li")!;
  expect(within(github).getByText("Frontend & Hosting")).toBeInTheDocument();
  const vercel = screen.getByRole("heading", { name: "Vercel" }).closest("li")!;
  expect(within(vercel).getByText("coming soon")).toBeInTheDocument();
  expect(within(vercel).queryByRole("button")).toBeNull();
  expect(screen.getByText(/Nothing connected yet/)).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Code" }));
  expect(screen.queryByRole("heading", { name: "Vercel" })).toBeNull();
});

test("connects GitHub with the secret sent separately from the config", async () => {
  const connections: Connection[] = [];
  const fetchMock = serve((url, init) => {
    if (url === "/api/connectors/catalog") return json([GITHUB]);
    if (url === "/api/connections" && init?.method === "POST") {
      const created = { id: "con_1", type: "github", name: "GitHub", config: { repository: "acme/web", allow_writes: false },
        status: "connected", last_error: null, created_at: "2026-09-22T00:00:00Z", detail: "15 read tools available" };
      connections.push(created);
      return json(created, 201);
    }
    if (url === "/api/connections") return json(connections);
    return undefined;
  });
  renderPage();

  await userEvent.click(await screen.findByRole("button", { name: "Connect GitHub" }));
  expect(screen.getByText("Create a fine-grained token.")).toBeInTheDocument();
  const token = screen.getByLabelText(/Personal access token/);
  expect(token).toHaveAttribute("type", "password");
  await userEvent.type(screen.getByLabelText("Repository"), " acme/web ");
  await userEvent.type(token, "github_pat_x");
  await userEvent.click(screen.getByRole("button", { name: "Connect and test" }));

  expect(await screen.findByText("15 read tools available")).toBeInTheDocument();
  expect(screen.getByText("acme/web")).toBeInTheDocument();
  const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST")!;
  expect(JSON.parse(post[1]!.body as string)).toEqual({
    type: "github", name: "GitHub", config: { repository: "acme/web", allow_writes: false },
    secrets: { token: "github_pat_x" },
  });
  expect(screen.queryByRole("heading", { name: "Connect GitHub" })).toBeNull();
});

test("shows the server's error when a connection fails validation", async () => {
  serve((url, init) => url === "/api/connectors/catalog" ? json([GITHUB])
    : url === "/api/connections" && init?.method === "POST" ? json({ detail: "Repository does not look right" }, 422)
      : url === "/api/connections" ? json([]) : undefined);
  renderPage();
  await userEvent.click(await screen.findByRole("button", { name: "Connect GitHub" }));
  await userEvent.type(screen.getByLabelText("Repository"), "a/b");
  await userEvent.type(screen.getByLabelText(/Personal access token/), "t");
  await userEvent.click(screen.getByRole("button", { name: "Connect and test" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Repository does not look right");
});

test("lists abilities per desk, re-tests and disconnects a connection", async () => {
  let connections: Connection[] = [{ id: "con_1", type: "github", name: "Site", config: { repository: "acme/web" },
    status: "error", last_error: "token expired", created_at: "2026-09-22T00:00:00Z" }];
  serve((url, init) => {
    if (url === "/api/connectors/catalog") return json([GITHUB]);
    if (url === "/api/connections") return json(connections);
    if (url === "/api/connections/con_1/tools") return json(GITHUB.abilities.slice(0, 2));
    if (url === "/api/connections/con_1/test") {
      connections = [{ ...connections[0], status: "connected", last_error: null }];
      return json({ ok: true, detail: "2 read tools available" });
    }
    if (url === "/api/connections/con_1" && init?.method === "DELETE") {
      connections = [];
      return new Response(null, { status: 204 });
    }
    return undefined;
  });
  renderPage();

  expect(await screen.findByText("token expired")).toBeInTheDocument();
  expect(screen.getByText("Needs attention")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Show abilities" }));
  expect(await screen.findByText("github.list_commits")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Frontend & Hosting" })).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /Test again/ }));
  expect(await screen.findByText("2 read tools available")).toBeInTheDocument();
  expect(await screen.findByText("Connected")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /Disconnect$/ }));
  await userEvent.click(screen.getByRole("button", { name: "Disconnect Site" }));
  expect(await screen.findByText(/Nothing connected yet/)).toBeInTheDocument();
});
