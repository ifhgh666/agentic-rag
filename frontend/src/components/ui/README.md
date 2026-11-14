# Local Nova primitives

Source: official shadcn/ui base-nova published registry, retrieved 2026-10-29. See source-manifest.json for exact URLs and original SHA-256 values; unmodified registry JSON is retained in output/frontend017/phase-a-20261029-01/upstream.

Local adaptations: Button/Input forward refs for React 18; Sheet uses the local Button import, Lucide XIcon and a Chinese close label. Base UI provides interaction, focus management and semantics. Nova visual classes are copied from published registry output. No second primitive library or animation package is added.

Original license: LICENSE.md (MIT). Geist font files are self-hosted under ../../assets/fonts/ with their OFL license. Only the currently consumed primitive set is vendored.

C adds AlertDialog from the same published base-nova registry; the original JSON and SHA-256 are retained in output/frontend017/phase-c-20261029-01/upstream and source-manifest.json. It uses the local Button import and forwards Cancel refs for React 18. The consumer sets a safe initial/final focus and responsive width. No additional primitive dependency is installed.
