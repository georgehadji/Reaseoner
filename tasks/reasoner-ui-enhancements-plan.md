# Reasoner UI And Image Workflow Enhancements Plan

## Scope

This plan covers the safe implementation and hardening of the current and next-step frontend/backend enhancements around the Reasoner result experience and image workflow:

1. Generated image UX
   - Show the LLM model used under every generated image.
   - Allow click-to-zoom preview for each image.
   - Provide explicit download controls for each generated image.
2. Image-to-image workflow
   - Allow uploaded user images to be used as reference images for new image generation.
   - Keep the current text-to-image flow intact.
3. Result presentation improvements
   - Improve scanning and readability of Reasoner outputs, especially synthesis and phase results.
   - Preserve correctness and source fidelity.
4. Animation tuning
   - Increase typewriter effect speed to 20 words/second without breaking perceived stability.

## Goals

- Improve usability without weakening safety boundaries.
- Keep backward compatibility for existing conversations and stored history.
- Avoid introducing XSS, unsafe file handling, oversized client storage, or prompt/context leakage.
- Keep the implementation incremental so each step can be validated and reverted independently.

## Non-Goals

- No broad visual redesign of the entire app in one pass.
- No change to the reasoning logic or epistemic labeling semantics.
- No server-side persistence of raw user images beyond the current upload mechanism unless explicitly needed.
- No introduction of unsafe file types such as SVG uploads in the image-reference path.

## Constraints

- Changes should remain minimal and localized to the existing image generation, chat rendering, composer, and history flows.
- Existing reasoning, search, and upload behavior must continue to work.
- Frontend must continue to build under Next.js 16 and TypeScript strict mode.
- Backend image generation must continue to support the existing two-image requirement and fallback routing.

## Current State Summary

- Image captions, zoom, download, and reference-image generation have partial support or recent patches, but the full enhancement set still needs a controlled rollout and deeper hardening.
- Result presentation currently renders rich data, but some metadata is under-exposed and some outputs still rely on long markdown dumps.
- The history layer now supports non-phase content, but any new result-shape changes must preserve compatibility with stored conversations.

## Implementation Strategy

Use a staged rollout with verification gates after every stage. Do not combine unrelated visual and backend-risky changes in a single pass.

### Stage 1: Stabilize Image Result Rendering

Objective:
- Ensure every generated image consistently shows the exact model label used.
- Ensure the model label is visible in all relevant contexts: live chat, restored history, enlarged preview.

Tasks:
- Normalize the generated image payload shape in frontend state and persisted history.
- Render a dedicated caption/footer under each image instead of relying on surrounding text.
- Make the model label explicit, not implied by message content.
- Add regression coverage for image conversation restoration.

Security and safety:
- Treat image captions as plain text only.
- Never render model labels as HTML.
- Preserve escaping through React text rendering.

Verification:
- Frontend build.
- History restoration test.
- Manual smoke test with two-model image output and reload.

### Stage 2: Add Safe Image Preview And Download

Objective:
- Let users inspect generated images in a larger view and download them safely.

Tasks:
- Add modal/lightbox preview with explicit close behavior.
- Add per-image download action in both thumbnail and preview contexts.
- Ensure keyboard and click dismissal work predictably.
- Keep the preview isolated from message layout so it does not affect streaming or history rendering.

Security and safety:
- Download only generated `data:image/...` URLs or explicitly trusted image payloads.
- Do not allow arbitrary remote URLs to be opened or auto-downloaded from chat content.
- Ensure modal state is local UI state and does not mutate persisted conversation data.

Verification:
- Frontend build.
- Manual click-to-preview and download validation.
- Confirm no console errors during repeated open/close cycles.

### Stage 3: Harden Image-To-Image Reference Uploads

Objective:
- Allow users to upload photos and use them as reference images in image generation, safely and predictably.

Tasks:
- Restrict reference inputs to supported raster image MIME types only.
- Convert reference images to safe data URLs on the client for the generation request.
- Pass `reference_images` through the proxy and backend schema into the generation layer.
- Inject reference images into the model request only for models/paths that support multimodal image input.
- Skip or degrade gracefully when a transport path cannot support image references.

Security and safety:
- Enforce a small cap on reference image count.
- Reject non-image payloads and unsafe formats.
- Do not accept SVG as a reference image path because of scriptability risks.
- Keep size limits and validate MIME + prefix, not just filename.
- Avoid logging raw image payloads in application logs.
- Ensure reference images are not accidentally stored in chat history unless explicitly intended.

Verification:
- Backend route regression for `reference_images`.
- Frontend build.
- Manual smoke test with 1-4 image references.
- Failure-path test when references are malformed or missing image prefixes.

### Stage 4: Improve Reasoner Result Presentation

Objective:
- Make reasoning results easier to scan, compare, and trust without changing the underlying content.

Tasks:
- Expose key metadata consistently in phase headers: models, token usage, duration, subagents.
- Make synthesis cards show summary counters for insights, actions, open questions, and sources.
- Audit where large markdown dumps can be replaced by clearer structured rendering.
- Prioritize improvements in high-value areas:
  - Synthesis
  - Critique
  - Writing/article outputs
  - Research/source-heavy outputs

Recommended next improvements after the current header/summary pass:
- Add section anchors or jump links inside synthesis.
- Collapse low-value intermediate detail by default while keeping it available.
- Highlight provenance blocks for source-backed claims.
- Distinguish “answer”, “evidence”, and “next actions” visually.

Safety and correctness:
- Never paraphrase or recompute reasoning data inside the presentation layer.
- Present counts and labels from the actual structured payload only.
- Do not infer sources that are not present in the payload.

Verification:
- Frontend build.
- Targeted visual review with at least one example per method family:
  - multi_perspective
  - research
  - writing
  - scientific

### Stage 5: Tune And Validate Animation Performance

Objective:
- Increase typewriter speed while keeping rendering stable and readable.

Tasks:
- Move the effective typewriter speed to the desired constant.
- Confirm visibility-change recovery still behaves correctly.
- Check that long markdown messages do not flicker or regress in CPU usage.

Safety:
- Keep animation purely presentational.
- Do not let animation state affect saved conversation content.

Verification:
- Frontend build.
- Manual long-response smoke test.

## Cross-Cutting Security Review

Before merging the full enhancement set, review these areas explicitly:

1. Upload validation
   - Confirm only allowed MIME types pass.
   - Confirm image references are capped.
   - Confirm no executable formats enter the reference-image path.
2. Client-side data handling
   - Confirm large data URLs are not accidentally persisted into long-term conversation history unless intended.
   - Confirm object URLs are revoked when attachments are removed or cleared.
3. Rendering safety
   - Confirm captions, prompts, and metadata are rendered as text, not HTML.
   - Confirm markdown renderer is not fed unsafe synthetic HTML from the new UI controls.
4. Transport safety
   - Confirm proxy route forwards only the expected image-generation fields.
   - Confirm backend does not log raw image payloads or secrets.
5. Abuse and resource controls
   - Confirm rate limiting still applies to image generation and upload routes.
   - Confirm image-reference count and size limits prevent avoidable memory spikes.

## Data And History Considerations

- Persist only what is necessary to replay the user-visible result.
- Prefer storing generated images and model labels, but avoid storing uploaded reference image payloads in conversation history by default.
- Preserve backward compatibility with existing conversation records that have:
  - phase-only results
  - search results
  - image results without the new fields

## Testing Plan

### Backend

- Route-level tests for:
  - preview-only prompt enhancement
  - `enhance=False`
  - `reference_images` forwarding
- Service-level tests for:
  - multimodal message construction with reference images
  - graceful behavior when images API fallback is incompatible with references

### Frontend

- Build verification with `npm run build`
- Vitest coverage for:
  - history restoration of image conversations
  - synthesis highlight derivation
  - any new pure helper functions

### Manual QA

- Generate images with no references.
- Generate images with one reference photo.
- Generate images with multiple reference photos.
- Reload history and verify image captions/model labels remain visible.
- Open, close, and download from the image preview.
- Review one long Reasoner answer per major method and check readability.

## Rollout Plan

1. Ship low-risk presentation/config changes first.
   - typewriter speed
   - phase metadata visibility
   - synthesis summary badges
2. Ship image preview/download UI next.
3. Ship reference-image generation after backend and route validation is complete.
4. Re-test history replay after all stages.

## Rollback Plan

If any stage causes regressions:

- Revert the isolated UI-only commit for:
  - typewriter speed
  - phase/synthesis metadata display
  - image preview/download
- Revert the isolated backend/frontend contract commit for `reference_images` if multimodal generation becomes unstable.
- Monitor for:
  - image route error rate increases
  - build failures
  - broken history replay
  - large memory spikes in the browser during image-reference use

## Acceptance Criteria

The enhancement set is considered complete when all of the following are true:

- Every generated image shows the model used beneath it.
- Clicking any generated image opens an enlarged preview.
- Each generated image can be downloaded directly.
- Users can upload supported raster images and use them as references for new generations.
- Reasoner phase and synthesis results are more scannable through visible metadata and structured summaries.
- Typewriter speed runs at 20 words/second.
- Frontend build passes.
- Focused backend and frontend regressions pass.
- No new unsafe file handling, HTML injection, or history corruption is introduced.

## Recommended Execution Order

1. Lock contracts and schemas.
2. Finish image rendering and preview UX.
3. Harden reference-image upload flow.
4. Improve result presentation incrementally.
5. Run focused tests and manual QA.
6. Commit in isolated, reviewable slices.
