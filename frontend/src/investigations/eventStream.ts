import { useEffect, useReducer } from "react";
import type { EventType, InvestigationEvent } from "../api/types";

export const TERMINAL_EVENT_TYPES: ReadonlySet<EventType> = new Set<EventType>([
  "investigation_completed",
  "investigation_failed",
]);

export interface StreamState {
  events: InvestigationEvent[];
  connected: boolean;
  done: boolean;
}

export const initialStreamState: StreamState = { events: [], connected: false, done: false };

export function applyEvent(state: StreamState, event: InvestigationEvent): StreamState {
  const lastSeq = state.events.at(-1)?.seq ?? 0;
  if (event.seq <= lastSeq) return state;
  return {
    ...state,
    events: [...state.events, event],
    done: state.done || TERMINAL_EVENT_TYPES.has(event.type),
  };
}

type Action =
  | { kind: "event"; event: InvestigationEvent }
  | { kind: "connected"; value: boolean }
  | { kind: "reset" };

function reducer(state: StreamState, action: Action): StreamState {
  switch (action.kind) {
    case "event":
      return applyEvent(state, action.event);
    case "connected":
      return { ...state, connected: action.value };
    case "reset":
      return initialStreamState;
  }
}

export function useEventStream(investigationId: string): StreamState {
  const [state, dispatch] = useReducer(reducer, initialStreamState);

  useEffect(() => {
    dispatch({ kind: "reset" });
    // The browser resends Last-Event-ID on automatic reconnects; the server replays from there.
    const source = new EventSource(`/api/investigations/${investigationId}/events`, {
      withCredentials: true,
    });
    source.onopen = () => dispatch({ kind: "connected", value: true });
    source.onerror = () => dispatch({ kind: "connected", value: false });
    source.onmessage = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as InvestigationEvent;
      dispatch({ kind: "event", event });
      if (TERMINAL_EVENT_TYPES.has(event.type)) source.close();
    };
    return () => source.close();
  }, [investigationId]);

  return state;
}
