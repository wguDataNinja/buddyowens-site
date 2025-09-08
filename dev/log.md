Here’s the updated log with today’s work added.

⸻

Dev Log — Buddy Owens Site (Hugo + PaperMod)

2025-09-08
	•	Project setup
	•	Initialized new Hugo site in buddyowens-site/.
	•	Added PaperMod as git submodule under themes/.
	•	Fixed stray submodule wiring (git rm --cached, cleanup, re-add).
	•	Created .gitignore for Hugo build artifacts.
	•	Config & structure
	•	Added hugo.toml with base site settings.
	•	Created archetypes (archetypes/posts/index.md).
	•	Added layouts, shortcodes, footer, and CSS extension folder.
	•	Added sample post bundle and tested hugo server -D.
	•	Scripts & tooling
	•	Wrote dev/combine_site.py to gather config/content/layouts into output/combined_files.txt.
	•	Updated script to always use fixed root and support --paths-only.
	•	Content
	•	Created 3 initial post stubs:
	•	wgu-instructor-atlas-1
	•	wgu-instructor-atlas-2
	•	wgu-instructor-atlas-3
	•	Published (set draft = false) with intro text.
	•	Issues & fixes
	•	CSS missing locally → caused by production baseURL and canonifyURLs; fixed by overriding baseURL to localhost in dev.
	•	Menu error (menus vs menu) → clarified correct config format; consolidated under config/_default/menus.toml.
	•	Next steps
	•	Finalize top menu with Posts, Tags, Search, About.
	•	Enable search (outputs.toml, JSON index).
	•	Add tags taxonomy page.
	•	Confirm posts display on homepage below profile section.

⸻

2025-09-09
	•	Menu & homepage
	•	Fixed navigation by converting to config/_default/menus.toml with correct list syntax.
	•	Disabled profileMode so the top navbar displays.
	•	Verified Posts, Tags, Search, and About all appear in header.
	•	Search
	•	Added outputs.toml with JSON output for Fuse.js.
	•	Created content/search.md with layout: "search".
	•	Tags
	•	Confirmed /tags/ taxonomy builds automatically.
	•	Content
	•	Created new post bundle: youtube-librarian-1/ (draft).
	•	Adjusted date fields on posts (3w, 2w, 1w ago) for proper ordering.
	•	Created content/about/_index.md (blank template, draft=false).
	•	Homepage
	•	Enabled special first post display.
	•	Added plan for homeInfoParams intro box (to be customized).
	•	Issues & fixes
	•	Hugo “failed to decode menus” error traced to leftover [menu] block; removed and verified config parses cleanly.
	•	Confirmed multiple hugo server instances were causing confusion; fixed by binding to explicit port 1315.
	•	Next steps
	•	Write intro content for homepage via homeInfoParams.
	•	Fill in About page with bio, links, and contact info.
	•	Link local repo to GitHub Desktop and push to remote (wgudataniinja/buddyowens-site).
	•	Begin setting up GitHub Actions + SFTP deployment workflow.

⸻

2025-09-08 → 2025-09-09 Carryover
	•	CI/CD
	•	Added .github/workflows/deploy.yml with Hugo build + GitHub Pages deploy.
	•	Fixed Hugo version mismatch (needed ≥0.146, runner had 0.134).
	•	Installed Hugo 0.149.1 manually; updated workflow guard.
	•	Added empty google_analytics.html partial to satisfy PaperMod.
	•	First deploy succeeded, but CSS missing.
	•	Deployment fixes (today)
	•	Corrected baseURL casing in hugo.toml → https://wguDataNinja.github.io/buddyowens-site/.
	•	Removed relativeURLs and canonifyURLs.
	•	Replaced deprecated paginate with [pagination].pagerSize.
	•	Redeployed; styles load correctly. Site confirmed working on GitHub Pages.
	•	Tooling update
	•	Enhanced combine_site.py:
	•	Auto-detect repo root (or pass --root).
	•	Check baseURL casing.
	•	Flag relative/canonify settings.
	•	Validate [pagination] pagerSize vs deprecated paginate.
	•	Preview GA partial.
	•	Current status
	•	Site builds and deploys cleanly.
	•	Pages (About, Search, Tags, Posts) exist but mostly placeholders.
	•	Ready for content fill-in.
	•	Next steps
	•	Write About page content.
	•	Add homepage intro text.
	•	Flesh out posts.
	•	Configure social links.
	•	Begin polishing theme overrides (CSS, footer, etc).

⸻

