Here’s an updated, concise Master Doc with the immediate GitHub push plan baked in.

Buddy Owens — Portfolio Website (Master Doc)

1. Project Overview
	•	Static site: Hugo + PaperMod
	•	Purpose: showcase data science projects
	•	Deploy now: local build → zip public/ → cPanel
	•	Later: GitHub Actions + SFTP

2. Current State (2025-09-08)
	•	Hugo site created; PaperMod added as git submodule (themes/PaperMod)
	•	Config in hugo.toml (+ config/_default/menus.toml, outputs.toml)
	•	Posts: wgu-instructor-atlas-1/2/3, youtube-librarian-1 (bundles)
	•	Search page: content/search/_index.md
	•	About page: content/about/_index.md
	•	Local preview OK with hugo server -D -p 1315
	•	Menu fixed (moved to config/_default/menus.toml)
	•	Intro box planned via homeInfoParams

3. Current File Structure (relevant)

hugo.toml
config/_default/menus.toml
config/_default/outputs.toml
archetypes/posts/index.md
layouts/shortcodes/plotly_res.html
layouts/shortcodes/datatable_res.html
assets/css/extended/site.css
content/
  about/_index.md
  search/_index.md
  posts/
    wgu-instructor-atlas-1/index.md
    wgu-instructor-atlas-2/index.md
    wgu-instructor-atlas-3/index.md
    youtube-librarian-1/index.md
dev/combine_site.py
dev/log.md

4. Dev Log (summary)
	•	Site + theme set up; submodule wiring fixed
	•	Archetypes and shortcodes added
	•	Menu/search/about wired; homepage design toggles noted
	•	dev/combine_site.py generates a summary with post index

5. Code Utilities
	•	dev/combine_site.py
	•	--summary-only prints counts, posts table, and small previews
	•	Excludes backups and large assets

6. Design & Content
	•	Content: long-form posts with data/visuals; <!--more--> after intro
	•	Design: PaperMod list view (default), special 1st post optional
	•	Visuals: PNG/SVG, Plotly JSON via plotly_res, CSV via datatable_res

7. Shortcodes
	•	layouts/shortcodes/plotly_res.html
	•	layouts/shortcodes/datatable_res.html
(ready; keep heavy embeds off the summary with <!--more-->)

8. Archetype
	•	archetypes/posts/index.md for consistent bundles (cover block included)

9. Styling
	•	assets/css/extended/site.css for small tweaks

10. Config (key points)
	•	hugo.toml: baseURL, theme, params, taxonomies
	•	config/_default/menus.toml: header menu
	•	config/_default/outputs.toml: home = ["HTML","RSS","JSON"] for search

⸻

11. Deployment (Automated, later)
	•	.github/workflows/deploy.yml (Hugo build + SFTP)
	•	Secrets: SFTP_HOST, SFTP_PORT, SFTP_USERNAME, SFTP_PASSWORD

⸻

12. Immediate Plan: Push to GitHub

Goal: publish this repo to github.com/wgudataniinja/buddyowens-site with the PaperMod submodule tracked correctly.

A) Using GitHub Desktop (preferred)
	1.	Open GitHub Desktop → File → Add Local Repository → select /Users/buddy/Desktop/projects/buddyowens-site
	2.	Sign in (GitHub account)
	3.	Publish repository
	•	Name: buddyowens-site
	•	Keep it Public (or Private)
	4.	Confirm .gitmodules shows themes/PaperMod and push
	5.	After publish: Repository → Open in Terminal and run:

git submodule update --init --recursive



B) Terminal (fallback)

Run from project root:

cd /Users/buddy/Desktop/projects/buddyowens-site

# init repo, set default branch, and commit
git init
git checkout -b main
git add .
git commit -m "Initial import: Hugo + PaperMod (submodule), config, content, utils"

# ensure submodule file is present
git submodule status || true
test -f .gitmodules && cat .gitmodules || echo "No .gitmodules"

# set remote and push
git remote add origin git@github.com:wgudataniinja/buddyowens-site.git
git push -u origin main

# verify submodule on a fresh clone later
# git clone --recurse-submodules git@github.com:wgudataniinja/buddyowens-site.git

.gitignore (minimum):

/public/
/resources/
/node_modules/
/.DS_Store
/.hugo_build.lock
/output/

Notes
	•	Keep PaperMod as a submodule (clean updates). If you ever want to vendor it, switch to subtree later.
	•	For collaborators: clone with --recurse-submodules or run git submodule update --init --recursive after cloning.

⸻

13. Next Steps
	•	Write 2–3 real posts with covers and data embeds
	•	Add favicon, analytics, SEO tags
	•	Fill About page; add homeInfoParams content
	•	SSL renewal before 2025-11-14
	•	Configure GitHub Actions + SFTP once repo is online

⸻

Plan (authoring)
	•	date: when work happened
	•	publishDate: when it should appear
	•	draft: true while writing → false to publish
	•	Local preview
	•	Published only: hugo server
	•	Include drafts/future: hugo server -D -F
	•	Production build: hugo --environment production --cleanDestinationDir

Rendering note
If a post summary breaks layout (e.g., shortcode outputs scripts in summary), keep heavy embeds after <!--more--> or guard in shortcode by page kind.