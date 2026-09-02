import { compact, type ExtensionAPI, type ExtensionContext } from "@mariozechner/pi-coding-agent";
import type { Api, Model } from "@mariozechner/pi-ai";

const ADVISORS = [
  { model: "openrouter/moonshotai/kimi-k3", thinking: "high" },
  { model: "openrouter/google/gemini-3-flash-preview", thinking: "high" },
  { model: "openrouter/deepseek/deepseek-v4-flash-0731:fp8", thinking: "high" },
];
const SYNTHESIZER = { model: "openrouter/openai/gpt-5.6-luna", thinking: "high" };

async function resolve(ctx: ExtensionContext, selector: string) {
  const slash = selector.indexOf("/");
  const model = ctx.modelRegistry.find(selector.slice(0, slash), selector.slice(slash + 1));
  if (!model) throw new Error(`Council model not found: ${selector}`);
  const auth = await ctx.modelRegistry.getApiKeyAndHeaders(model);
  if (!auth.ok) throw new Error(`Council model auth failed: ${selector}: ${auth.error}`);
  return { model: model as Model<Api>, apiKey: auth.apiKey, headers: auth.headers };
}

export default function councilCompaction(pi: ExtensionAPI) {
  pi.on("session_before_compact", async (event, ctx) => {
    try {
      const drafts = await Promise.all(
        ADVISORS.map(async (advisor) => {
          const resolved = await resolve(ctx, advisor.model);
          const result = await compact(
            event.preparation,
            resolved.model,
            resolved.apiKey,
            resolved.headers,
            "Write Pi's normal compaction summary. Independently preserve facts needed to continue the session.",
            event.signal,
            advisor.thinking,
          );
          return { advisor, result };
        }),
      );
      const synthesizer = await resolve(ctx, SYNTHESIZER.model);
      const draftsText = drafts.map(({ advisor, result }) => `## ${advisor.model}\n${result.summary}`).join("\n\n");
      const result = await compact(
        event.preparation,
        synthesizer.model,
        synthesizer.apiKey,
        synthesizer.headers,
        `You are the aggregator in a Mixture of Agents process. The original conversation above is ground truth. The reference responses below are private retrieval aids. Write Pi's normal compaction summary for the next agent. Preserve the union of relevant details, including details present in only one reference. Resolve disagreements from the original conversation.\n\nReference responses:\n${draftsText}`,
        event.signal,
        SYNTHESIZER.thinking,
      );
      return {
        compaction: {
          summary: result.summary,
          tokensBefore: result.tokensBefore,
          firstKeptEntryId: result.firstKeptEntryId,
          details: { ...result.details, source: "council-compaction", advisors: ADVISORS.map((advisor) => advisor.model), synthesizer: SYNTHESIZER.model },
        },
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      ctx.ui.notify(`Council compaction failed: ${message}`, "error");
      return undefined;
    }
  });
}
