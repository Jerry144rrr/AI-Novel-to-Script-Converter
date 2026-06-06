AI Novel-to-Screenplay Converter is an intelligent tool that transforms novel chapters into structured, editable screenplay drafts in YAML format. Built for authors adapting their own work, it lowers the barrier between prose fiction and screenwriting through a three-stage AI pipeline powered by Claude.

**How It Works**

The tool processes novels in three distinct stages. First, it scans the full text to extract a comprehensive character bible — identifying every character's name, identity, personality traits, and inter-character relationships. Second, it detects scene boundaries by analyzing shifts in time, location, and narrative focus, producing a structured scene breakdown with precise source-line mapping back to the original text. Third, it converts each scene into standard screenplay format, distinguishing action descriptions, dialogue with emotional annotations, and transitions.

**Key Features**

Every screenplay element is traceable to its source passage via embedded line numbers, allowing authors to verify and refine AI-generated content against the original novel. The global character table ensures consistency across chapters, preventing the common AI pitfall of name confusion or attribute drift. Emotional tone labels on dialogue lines give actors and directors immediate insight into character states.

The output is a clean, human-readable YAML file that follows a purpose-built schema balancing industry-standard screenplay conventions (Master Scene format) with AI-assisted-authoring ergonomics. The schema document explains not just the format, but the design rationale behind each structural decision — from the polymorphic content type system to the characters-present-per-scene annotation.

**Technical Design**

Built with Python and Streamlit, the tool provides an intuitive web interface where users paste or upload novel text, review parsed chapters and character profiles, then trigger AI conversion with real-time progress tracking. The YAML output is immediately previewable and downloadable. The architecture is API-provider-agnostic: configure the base URL, API key, and model name via `.env` environment variables to use any Anthropic-compatible endpoint.
