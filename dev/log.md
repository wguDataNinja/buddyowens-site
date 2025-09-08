Here’s a condensed update you can paste into your dev log.

⸻

Dev Log — Buddy Owens Site (Hugo + PaperMod)

2025-09-08 → 2025-09-09
	•	Project setup
	•	Initialized Hugo site in buddyowens-site/.
	•	Added PaperMod as submodule; cleaned and re-added submodule wiring.
	•	.gitignore for Hugo artifacts.
	•	Config and structure
	•	Added hugo.toml with base settings and correct baseURL for GitHub Pages.
	•	Created archetypes, layouts, shortcodes, footer, CSS extension folder.
	•	Added sample post bundle and tested with hugo server -D.
	•	Content
	•	Created post bundles: wgu-instructor-atlas-1, -2, -3. Set draft=false for Part 1.
	•	Added About page stub and Search page.
	•	Wrote and refined Part 1 post, added “Outputs” section, fixed headings for TOC.
	•	Menus and homepage
	•	Moved menus to config/_default/menus.toml.
	•	Disabled profileMode so top navbar shows.
	•	Verified Posts, Tags, Search, About in header.
	•	Confirmed /tags/ taxonomy builds.
	•	Search
	•	Added config/_default/outputs.toml for JSON index.
	•	Created content/search.md with layout: “search”.
	•	CI/CD
	•	Added .github/workflows/deploy.yml for Pages deploy.
	•	Pinned Hugo to 0.149.1. Removed relativeURLs and canonifyURLs.
	•	Replaced deprecated paginate with [pagination].pagerSize.
	•	Added empty layouts/partials/google_analytics.html to satisfy theme.
	•	First deploy succeeded after CSS path fixes. Styles load on Pages.
	•	Avatar and header
	•	Placed avatar at static/images/avatar.png.
	•	Configured PaperMod label:
	•	params.label.text = “Buddy Owens”
	•	params.label.icon = “images/avatar.png”
	•	params.label.iconHeight = 40
	•	params.env = “production”
	•	Added assets/css/extended/avatar.css to crop to circle and add subtle border.
	•	Verified header partial path and that PaperMod uses partialCached “header.html”.
	•	Outcome: avatar appears top-left next to site title.
	•	Tooling
	•	Wrote dev/combine_site.py to gather config/content/layouts into output/combined_files.txt.
	•	Enhancements:
	•	Auto-detect repo root or accept –root.
	•	New CI checks: baseURL casing, Hugo version pin, pagination, GA partial.
	•	New PaperMod checks: params.label.text/icon/iconHeight/env, avatar asset presence, CSS override presence.
	•	Options: –paths-only, –summary-only.
	•	Issues and fixes
	•	Menu parse errors due to leftover [menu] block → removed; now using menus.toml.
	•	Multiple hugo server instances caused confusion → bound to port 1315.
	•	TOC nesting off due to heading levels → promoted major sections to H2.
	•	Avatar not showing → added params.label.* and CSS; confirmed static path.
	•	Current status
	•	Site builds and deploys on GitHub Pages.
	•	Header shows circle avatar and site title.
	•	Part 1 published with outputs and working TOC.
	•	About, Tags, Search pages present; content in progress.
	•	Next steps
	•	Fill in About content and homepage intro.
	•	Publish Parts 2 and 3 drafts.
	•	Add social links.
	•	Continue theme polish (footer, small CSS tweaks).