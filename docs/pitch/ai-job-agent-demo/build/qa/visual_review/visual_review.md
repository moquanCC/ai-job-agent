# Visual Review Packet

- PPTX: `C:\Users\cc\Desktop\黑客松项目\docs\pitch\ai-job-agent-demo\build\ai.pptx`
- Rendered slides: 0
- Warnings: 1
- Info: 10

## Findings

- [INFO] slide 3 / shape-13: body_font_small - Body-like text is 9.4pt.
  Suggestion: Check readability; use larger text or split dense content if this is not a table/caption.
- [INFO] slide 3 / shape-18: body_font_small - Body-like text is 9.4pt.
  Suggestion: Check readability; use larger text or split dense content if this is not a table/caption.
- [INFO] slide 4 / shape-5: body_font_small - Body-like text is 9.0pt.
  Suggestion: Check readability; use larger text or split dense content if this is not a table/caption.
- [INFO] slide 5 / shape-6: text_box_tight - Estimated text height uses 94% of its box.
  Suggestion: Check the rendered slide for clipping or awkward wrap.
- [INFO] slide 5 / shape-13: body_font_small - Body-like text is 8.8pt.
  Suggestion: Check readability; use larger text or split dense content if this is not a table/caption.
- [INFO] slide 5 / shape-18: body_font_small - Body-like text is 8.8pt.
  Suggestion: Check readability; use larger text or split dense content if this is not a table/caption.
- [INFO] slide 7 / shape-5: body_font_small - Body-like text is 9.0pt.
  Suggestion: Check readability; use larger text or split dense content if this is not a table/caption.
- [INFO] slide 8 / shape-13: body_font_small - Body-like text is 9.4pt.
  Suggestion: Check readability; use larger text or split dense content if this is not a table/caption.
- [INFO] slide 8 / shape-18: body_font_small - Body-like text is 9.4pt.
  Suggestion: Check readability; use larger text or split dense content if this is not a table/caption.
- [INFO] deck: source_image_absent - No content slide uses a photographic/source-backed image or figure.
  Suggestion: For public-topic decks, consider one image-sidebar or scientific-figure slide with attribution rather than relying only on cards, tables, or synthetic charts.
- [WARNING] deck: render_unavailable - Slides could not be rendered for visual contact-sheet review.
  Suggestion: Install LibreOffice/Poppler or rerun with a valid --renders-dir.

## Rendered Slides


## Human/Agent Review Checklist

- Inspect the contact sheet first for rhythm, density, and repeated layouts.
- Open individual slides for title wrapping, orphan words, weak contrast, and footer clearance.
- Fix `outline.json`, `design_brief.json`, assets, or renderer code, then rebuild.
- Do not patch the generated `.pptx` directly unless the task is an explicit one-off edit.
