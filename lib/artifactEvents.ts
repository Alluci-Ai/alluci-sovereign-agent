/**
 * Artifact Event Bus
 * ==================
 * Publishes lifecycle events between the agent runtime, backend, and React UI.
 */

export type ArtifactEvent =
  | { type: "artifact.created"; artifactId: string; source?: string }
  | { type: "artifact.updated"; artifactId: string; version: number; source?: string }
  | { type: "artifact.open"; artifactId: string; source?: string }
  | { type: "artifact.close"; artifactId: string; source?: string }
  | { type: "artifact.publish"; artifactId: string; source?: string };

type Handler = (event: ArtifactEvent) => void;

class ArtifactEvents {
  private handlers = new Set<Handler>();

  subscribe(handler: Handler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  emit(event: ArtifactEvent): void {
    this.handlers.forEach((handler) => handler(event));
  }
}

export const artifactEvents = new ArtifactEvents();
