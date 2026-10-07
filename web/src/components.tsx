import { useState } from "react";
import { api, date, readUtf8, title } from "./api";
import type {
  Application,
  Case,
  ReviewEvent,
  Source,
  SourceRef,
} from "./types";

export function Badge({ value }: { value: string }) {
  return <span className={`badge ${value}`}>{title(value)}</span>;
}

export function Evidence({
  references,
  sources,
}: {
  references: SourceRef[];
  sources: Source[];
}) {
  return (
    <div className="evidence">
      {references.map((ref, index) => {
        const source = sources.find((s) => s.id === ref.source_id);
        const characters = Array.from(source?.content ?? "");
        return (
          <details key={`${ref.source_id}-${index}`}>
            <summary>
              {source?.filename ?? ref.source_id}{" "}
              <span>
                · characters {ref.start}–{ref.end} · v{source?.version}
              </span>
            </summary>
            <blockquote>{ref.quote}</blockquote>
            {source && (
              <pre className="source-text">
                {characters.slice(0, ref.start).join("")}
                <mark>{characters.slice(ref.start, ref.end).join("")}</mark>
                {characters.slice(ref.end).join("")}
              </pre>
            )}
            <small>
              Source ID {ref.source_id}
              <br />
              SHA-256 {ref.content_hash}
            </small>
          </details>
        );
      })}
    </div>
  );
}

export function CaseEditor({
  item,
  sources,
  actor,
  events,
  save,
}: {
  item: Case;
  sources: Source[];
  actor: string;
  events: ReviewEvent[];
  save: (id: string, body: unknown) => Promise<void>;
}) {
  const [question, setQuestion] = useState(item.question);
  const [answer, setAnswer] = useState(item.reference_answer ?? "");
  const [behavior, setBehavior] = useState(item.expected_behavior);
  const [working, setWorking] = useState(false);
  async function decide(decision: string) {
    setWorking(true);
    try {
      await save(item.id, {
        actor,
        expected_revision: item.revision,
        decision,
        question,
        reference_answer: answer || null,
        expected_behavior: behavior,
      });
    } finally {
      setWorking(false);
    }
  }
  return (
    <article className="panel case-editor">
      <div className="row between">
        <div className="eyebrow">Case review · revision {item.revision}</div>
        <Badge value={item.review_status} />
      </div>
      <h2>{title(item.category)}</h2>
      <div className="tags">
        <span>{item.split}</span>
        <span>Group: {item.group_id}</span>
      </div>
      <label>
        Question or interaction
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
        />
      </label>
      <label>
        Expected behavior
        <select value={behavior} onChange={(e) => setBehavior(e.target.value)}>
          <option value="answer">Answer with evidence</option>
          <option value="abstain">Abstain</option>
          <option value="clarify">Clarify</option>
        </select>
      </label>
      <label>
        Reference answer
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          rows={2}
          placeholder="Optional for abstention or clarification"
        />
      </label>
      <p className="muted small">Label provenance: {item.provenance}</p>
      <h3>Source evidence</h3>
      <Evidence references={item.references} sources={sources} />
      <div className="actions">
        <button
          disabled={working || !actor.trim()}
          onClick={() => void decide("approved")}
        >
          Save & approve
        </button>
        <button
          className="secondary"
          disabled={working || !actor.trim()}
          onClick={() => void decide("unreviewed")}
        >
          Save draft
        </button>
        <button
          className="danger"
          disabled={working || !actor.trim()}
          onClick={() => void decide("rejected")}
        >
          Reject
        </button>
      </div>
      <details className="history">
        <summary>Review history</summary>
        {events
          .filter((e) => e.object_id === item.id)
          .map((e) => (
            <p key={e.id}>
              r{e.revision} · {e.actor} · {e.action} · {date(e.created_at)}
            </p>
          ))}
      </details>
    </article>
  );
}

export function ApplicationForm({
  create,
}: {
  create: (body: unknown) => Promise<void>;
}) {
  const [form, setForm] = useState({
    name: "",
    purpose: "",
    owner: "",
    expected_behavior: "",
    application_version: "1",
    model_version: "unspecified",
    prompt_version: "1",
  });
  const [fields, setFields] = useState([
    "answer",
    "behavior",
    "citations",
    "retrieved_ids",
    "latency_ms",
    "error",
  ]);
  const [working, setWorking] = useState(false);
  return (
    <details className="panel">
      <summary>Create an application</summary>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setWorking(true);
          try {
            await create({ ...form, supported_fields: fields });
          } finally {
            setWorking(false);
          }
        }}
      >
        <div className="form-grid">
          {Object.entries(form).map(([key, value]) => (
            <label key={key}>
              {title(key)}
              <input
                required
                value={value}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </label>
          ))}
        </div>
        <fieldset>
          <legend>Supplied trace fields</legend>
          <div className="checkboxes">
            {[
              "answer",
              "behavior",
              "citations",
              "retrieved_ids",
              "latency_ms",
              "error",
              "input_tokens",
              "output_tokens",
            ].map((field) => (
              <label key={field}>
                <input
                  type="checkbox"
                  checked={fields.includes(field)}
                  onChange={(e) =>
                    setFields(
                      e.target.checked
                        ? [...fields, field]
                        : fields.filter((f) => f !== field),
                    )
                  }
                />
                {title(field)}
              </label>
            ))}
          </div>
        </fieldset>
        <button disabled={working}>Create application</button>
      </form>
    </details>
  );
}

export function Imports({
  application,
  perform,
}: {
  application: Application;
  perform: (task: () => Promise<unknown>, message: string) => Promise<void>;
}) {
  const [documentId, setDocumentId] = useState("");
  const [version, setVersion] = useState("1");
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  return (
    <div className="import-grid">
      <form
        className="panel"
        onSubmit={(e) => {
          e.preventDefault();
          void perform(async () => {
            if (!sourceFile)
              throw new Error("Choose a UTF-8 Markdown or text file.");
            return api(`/applications/${application.id}/sources`, {
              document_id: documentId,
              version,
              filename: sourceFile.name,
              content: await readUtf8(sourceFile),
            });
          }, "Versioned source imported.");
        }}
      >
        <h3>Import a source</h3>
        <p className="muted small">
          UTF-8 .md or .txt · up to 2 MB. New content needs a new version.
        </p>
        <label>
          Document ID
          <input
            required
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            placeholder="support-policy"
          />
        </label>
        <label>
          Source version
          <input
            required
            value={version}
            onChange={(e) => setVersion(e.target.value)}
          />
        </label>
        <label>
          Source file
          <input
            type="file"
            accept=".md,.txt"
            required
            onChange={(e) => setSourceFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <button className="secondary">Import source</button>
      </form>
      <div className="panel">
        <h3>Bring your own evidence</h3>
        <p className="muted small">
          Version 1 JSONL schemas. Imported cases start unreviewed; traces
          require matching application versions and case IDs.
        </p>
        {(["cases", "traces"] as const).map((kind) => (
          <label className="file-label" key={kind}>
            Import {kind} JSONL
            <input
              type="file"
              accept=".jsonl,.ndjson"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file)
                  void perform(
                    async () =>
                      api(`/applications/${application.id}/${kind}/import`, {
                        text: await readUtf8(file),
                      }),
                    `${title(kind)} imported.`,
                  );
                e.target.value = "";
              }}
            />
          </label>
        ))}
        <p className="small muted">
          Automatic candidates need lines formatted as
          <br />
          <code>- fact_id | topic | question | answer</code>
          <br />
          Other prose supports manually authored cases.
        </p>
        <button
          className="secondary"
          onClick={() =>
            void perform(
              () => api(`/applications/${application.id}/cases/generate`, {}),
              "Structured candidates generated; duplicates skipped.",
            )
          }
        >
          Generate candidates
        </button>
      </div>
    </div>
  );
}
