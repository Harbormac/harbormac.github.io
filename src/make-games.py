#!/usr/bin/env python3
"""Writes the pages that are made from Highball's open compatibility database (CC0):
the games list, and the MacBook Neo and MacBook Air guides. Run it before build.py when
the data should be refreshed:

    python3 -I src/make-games.py [path to a highball-db checkout]

Without a path it downloads the database's current files. Only games with a good player
report, or played by Highball's maintainer, are listed: nothing that doesn't run.
"""
import collections, datetime, glob, html, io, json, os, re, statistics, sys, tarfile, tempfile, urllib.request

SRC = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(SRC, "pages")
SOURCE = "https://codeload.github.com/gauthierpiarrette/highball-db/tar.gz/HEAD"
DB_URL = "https://github.com/gauthierpiarrette/highball-db"
RENDERERS = {"dxmt": "DXMT", "d3dmetal": "D3DMetal", "dxvk": "DXVK", "wined3d": "Wine's own"}
BASE_CHIPS = ["Apple M1", "Apple M2", "Apple M3", "Apple M4", "Apple M5"]
NEO_CHIP = "Apple A18 Pro"
# Left out: they only start with their anti-cheat switched off by hand.
EXCLUDE = {"elden-ring", "armored-core-vi", "elden-ring-nightreign"}
# Portnaut's own guides, by the database's game id.
GUIDES = {"grand-theft-auto-v": "/guides/gta-5-on-mac/", "red-dead-redemption-2": "/guides/red-dead-redemption-2-on-mac/",
          "marvels-guardians-of-the-galaxy": "/guides/guardians-of-the-galaxy-on-mac/", "metaphor-refantazio": "/guides/metaphor-refantazio-on-mac/"}
# What a reader must know that the numbers don't say.
NOTES = {"forza-horizon-6": "Needs D3DMetal 4 and extra settings that Portnaut doesn't apply yet",
         "the-sims-4": "Has its own Mac version: use that", "warframe": "Has its own Mac version: use that",
         "grand-theft-auto-v": "Story mode only: GTA Online needs BattlEye, which can't run"}
# The MacBook Neo reports in plain words (the reports' own notes, shortened).
NEO_NOTES = {"train-simulator-classic": "Low preset, a two-hour session; about 30 to 40 fps once the Mac warmed up",
             "trailmakers": "About 50 to 60 fps on the lowest graphics setting",
             "nier-replicant-ver-1-22474487139": "With the frame rate capped at 30",
             "counter-strike-2": "At a low resolution, with a few frame drops; has VAC anti-cheat",
             "cloverpit": "Runs, but slowly and with heavy battery use",
             "beamng-drive": "Runs with stuttering",
             "denshattack": "Low frame rate, even on the lowest settings",
             "freddy-fazbears-pizzeria-simulator": "Text is missing in some minigames",
             "call-of-duty-world-at-war": "Stutters with V-Sync off",
             "devil-may-cry-hd-collection": "One player's controller wasn't recognised"}


def load(path):
    games, reports = {}, collections.defaultdict(list)
    for f in glob.glob(os.path.join(path, "db", "games", "*.json")):
        g = json.load(open(f, encoding="utf-8"))
        games[g["id"]] = g
    for f in glob.glob(os.path.join(path, "db", "reports", "*.jsonl")):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                reports[r.get("game_id") or os.path.basename(f)[:-6]].append(r)
    return games, reports


def fetch():
    folder = tempfile.mkdtemp(prefix="highball-db-")
    data = urllib.request.urlopen(SOURCE, timeout=60).read()
    tarfile.open(fileobj=io.BytesIO(data)).extractall(folder, filter="data")
    return os.path.join(folder, os.listdir(folder)[0])


def rating(r):
    try:
        return int(r.get("rating"))
    except (TypeError, ValueError):
        return None


def minutes(r):
    m = re.search(r"Played for (\d+) min", r.get("notes") or "")
    return int(m.group(1)) if m else None


def wine(r):
    engine = (r.get("engine") or "").lower()
    return "11" if "crossover" in engine else "10" if "sikarugir" in engine else None


def usable(r):
    """A report made on a route Portnaut has: x64 Wine with DXMT, D3DMetal, DXVK or Wine's own."""
    return "arm64" not in (r.get("engine") or "").lower() and (r.get("renderer") or "dxmt") in RENDERERS and rating(r) is not None


def rows(games, reports):
    """One row per game that runs: played by Highball, or with a good report of ten minutes or more."""
    out = []
    for gid, g in games.items():
        if gid in EXCLUDE or g["status"].startswith("blocked") or (g.get("anticheat") or {}).get("macVerdict") == "blocked":
            continue
        mine = [r for r in reports.get(gid, []) if usable(r)]
        good = [r for r in mine if rating(r) >= 4 and (minutes(r) is None or minutes(r) >= 10)]
        played = g["status"] == "verified-local" and g.get("renderer") in RENDERERS
        if not played and not (good and statistics.median(rating(r) for r in mine) >= 4):
            continue
        used = [r.get("renderer") for r in good if r.get("renderer") in RENDERERS] or ([g["renderer"]] if g.get("renderer") in RENDERERS else [])
        renderer = collections.Counter(used).most_common(1)[0][0] if used else None
        chips = sorted({(r.get("chip") or "").replace("Apple ", "") for r in good if r.get("chip")},
                       key=lambda c: (c.startswith("A"), c))
        note = NOTES.get(gid) or ("Reported offline or in single-player; online play is doubtful" if gid in ("titanfall-2", "halo-infinite") else None)
        names = (g.get("anticheat") or {}).get("names") or []
        if not note and names and (g.get("anticheat") or {}).get("macVerdict") == "warning":
            note = "Has anti-cheat (%s): online play may not work" % ", ".join(n for n in names if "Unknown" not in n) if any("Unknown" not in n for n in names) else "Has anti-cheat: online play may not work"
        out.append({"id": gid, "title": g["title"], "played": played, "reports": len(mine), "good": len({r.get("user") for r in good}) or (1 if played else 0),
                    "best": max([rating(r) for r in good] or [0]), "longest": max([minutes(r) or 0 for r in good] or [0]),
                    "renderer": renderer, "chips": chips, "wine11": any(wine(r) == "11" for r in good) or (played and "crossover" in (g.get("provenance") or "")),
                    "note": note, "guide": GUIDES.get(gid)})
    def key(r):
        k = re.sub(r"[^a-z0-9]", "", r["title"].lower())
        return (not k, k, r["title"])
    return sorted(out, key=key)


def session(m):
    return "%d min" % m if m < 120 else "about %d hours" % round(m / 60)


def e(text):
    return html.escape(text, quote=False)


def long_date(day):
    return "%d %s" % (day.day, day.strftime("%B %Y"))


def page(name, meta, body):
    text = "<!--page\n%s\n-->\n%s" % (json.dumps(meta, indent=1, ensure_ascii=False), body)
    open(os.path.join(PAGES, name), "w", encoding="utf-8").write(text)
    print("wrote", name)


def article(path, headline, image, crumb, today):
    return [{"@type": "TechArticle", "@id": "{{site}}%s#article" % path, "headline": headline, "url": "{{site}}%s" % path, "inLanguage": "en",
             "datePublished": "2026-11-10", "dateModified": today.isoformat(), "image": "{{site}}%s" % image,
             "author": {"@id": "{{site}}/#builtbyargo"}, "publisher": {"@id": "{{site}}/#builtbyargo"}, "about": {"@id": "{{site}}/#app"}, "isPartOf": {"@id": "{{site}}/#website"}},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Portnaut", "item": "{{site}}/"},
                {"@type": "ListItem", "position": 2, "name": crumb[0], "item": "{{site}}%s" % crumb[1]}] + (
                [{"@type": "ListItem", "position": 3, "name": crumb[2], "item": "{{site}}%s" % path}] if len(crumb) > 2 else [])}]


def games_page(all_rows, today):
    total = len(all_rows)
    rounded = total // 50 * 50
    played = sum(r["played"] for r in all_rows)
    wine11 = sum(r["wine11"] for r in all_rows)
    top = sorted(all_rows, key=lambda r: (-r["good"], r["title"]))[:12]
    lines = []
    for r in all_rows:
        title = '<a href="%s">%s</a>' % (r["guide"], e(r["title"])) if r["guide"] else e(r["title"])
        result = "Played by Highball" if r["played"] else "%d player%s" % (r["good"], " reports" if r["good"] == 1 else "s report")
        if r["best"]:
            result += ", best %d/5" % r["best"]
        chips = ", ".join(r["chips"][:4]) + (" +%d" % (len(r["chips"]) - 4) if len(r["chips"]) > 4 else "")
        lines.append("          <tr><td><strong>%s</strong>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            title, '<br><small class="muted">%s</small>' % e(r["note"]) if r["note"] else "", result,
            RENDERERS.get(r["renderer"], "–"), "Yes" if r["wine11"] else "–", e(chips) or "–"))
    path = "/games/"
    meta = {"path": path, "title": "Windows Games That Run on a Mac: %d+ Reported – Portnaut" % rounded,
            "social_title": "%d+ Windows games that run on a Mac" % rounded,
            "image": "/assets/og-games.jpg", "image_alt": "Portnaut: Windows games that run on a Mac",
            "description": "A searchable list of %d Windows games that players report running on Apple silicon Macs through Wine, with the renderer and Mac each was played on." % total,
            "faq": True, "jsonld": article(path, "Windows games that run on a Mac", "/assets/og-games.jpg", ("Games", path), today)}
    body = """<div class="page-head">
  <div class="wrap">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Portnaut</a></li><li aria-current="page">Games</li></ol></nav>
    <h1>Windows games that run on a Mac</h1>
    <p class="lead">%(total)d Windows games that players report running well on Macs with Apple silicon through Wine, the technology Portnaut uses. Each has a report rated 4 or 5 out of 5 after at least ten minutes of play, or was played by the database's maintainer.</p>
    <p class="tested">From Highball's open compatibility database · %(played)d played by its maintainer · Not tested with Portnaut unless a guide says so · Updated %(date)s</p>
  </div>
</div>

<section class="tight">
  <div class="wrap narrow prose">
    <h2 id="read">How to read this list</h2>
    <ul>
      <li><strong>It shows what runs, not what doesn't.</strong> Games that don't start, and games blocked by kernel-level anti-cheat, are left out. A game that isn't here may still run: nobody has reported it yet.</li>
      <li><strong>These are players' reports, not Portnaut's tests.</strong> They come from <a href="%(db)s">Highball's open compatibility database</a>, where Mac players report how a game ran. Portnaut has its own guides for the games it covers in depth; those are linked.</li>
      <li><strong>Wine 11 matters.</strong> Most reports were made with Highball's Wine 10. Portnaut installs Highball's Wine 11 build, and %(wine11)d games here have a good report on that Wine too. For the others, treat the report as a strong hint, not a promise.</li>
      <li><strong>Check for a Mac version first.</strong> If a game has one, it'll run better than any Windows version.</li>
    </ul>
    <p>Portnaut's <strong>Will It Run?</strong> (⌘K in the app) checks about 13,000 games, including anti-cheat and what Linux players' results predict. <a href="/download/">Download Portnaut</a>, free.</p>

    <h2 id="most-reported">Most reported</h2>
    <p>The games most players report running well: %(top)s.</p>

    <h2 id="list">The list</h2>
    <p><label for="game-filter">Find a game:</label> <input id="game-filter" class="filter" type="search" placeholder="Type a game's name" autocomplete="off"> <span id="game-count" class="muted" aria-live="polite"></span></p>
  </div>
  <div class="wrap">
    <div class="table-wrap">
      <table id="games">
        <thead><tr><th scope="col">Game</th><th scope="col">Result</th><th scope="col">Renderer</th><th scope="col">Wine 11 report</th><th scope="col">Played on</th></tr></thead>
        <tbody>
%(rows)s
        </tbody>
      </table>
    </div>
  </div>
</section>
<script>
(function () {
  var input = document.getElementById("game-filter"), count = document.getElementById("game-count");
  var rows = Array.prototype.slice.call(document.querySelectorAll("#games tbody tr"));
  input.addEventListener("input", function () {
    var q = input.value.trim().toLowerCase(), shown = 0;
    rows.forEach(function (row) {
      var match = !q || row.cells[0].textContent.toLowerCase().indexOf(q) !== -1;
      row.hidden = !match;
      if (match) shown++;
    });
    count.textContent = q ? shown + (shown === 1 ? " game" : " games") : "";
  });
})();
</script>

<section class="tight">
  <div class="wrap narrow prose">
    <h2 id="columns">What the columns mean</h2>
    <ul>
      <li><strong>Result:</strong> how many players rated the game 4 (playable, minor issues) or 5 (perfect) after ten minutes or more, and the best rating. “Played by Highball” means the database's maintainer played it.</li>
      <li><strong>Renderer:</strong> the graphics renderer most good reports used. In easy mode, Portnaut picks this one when you press Play. <a href="/guides/dxmt-vs-d3dmetal-vs-dxvk/">How the renderers differ</a>.</li>
      <li><strong>Wine 11 report:</strong> whether a good report used the Wine 11 build that Portnaut installs.</li>
      <li><strong>Played on:</strong> the chips of the Macs in those reports. A18 Pro is the MacBook Neo.</li>
    </ul>

    <h2 id="faq">Questions</h2>
    <details>
      <summary>What games can I play on a Mac?</summary>
      <p>Games with a Mac version, and many Windows games through Wine. This list has %(total)d Windows games that players report running well on Apple silicon. Games with kernel-level anti-cheat don't run, and some games run only offline.</p>
    </details>
    <details>
      <summary>Do all of these run in Portnaut?</summary>
      <p>They've been reported running on Macs through Wine with Highball, not tested with Portnaut. Portnaut installs Highball's Wine 11 build and the same renderers, so most should behave alike, but only the games with a Portnaut guide have been checked more closely.</p>
    </details>
    <details>
      <summary>My game isn't on the list. Does that mean it won't run?</summary>
      <p>No. It means nobody has reported it yet. Search it in Portnaut's Will It Run?, which also uses Linux players' results to predict how likely a game is to run, and names anti-cheat that blocks it.</p>
    </details>
    <details>
      <summary>Where does the list come from?</summary>
      <p>From Highball's compatibility database, which is open and free to reuse (CC0). Players send reports from the Highball app with their Mac's chip, macOS version and a rating. Portnaut rebuilds this page from it.</p>
    </details>

    <p>Next: <a href="/guides/play-pc-games-on-mac/">How to play PC games on a Mac</a> · <a href="/guides/macbook-air-pc-games/">PC games on a MacBook Air</a> · <a href="/guides/macbook-neo-pc-games/">PC games on a MacBook Neo</a></p>
    <p class="muted"><small>Game names are trademarks of their owners. Portnaut is not affiliated with them or with Highball. Data from Highball's database, read on %(date)s.</small></p>
  </div>
</section>
""" % {"total": total, "played": played, "wine11": wine11, "date": long_date(today), "db": DB_URL, "rows": "\n".join(lines),
       "top": ", ".join("%s (%d)" % (e(r["title"]), r["good"]) for r in top)}
    page("05-games.html", meta, body)


def neo_page(games, reports, today):
    mine = [(gid, r) for gid, rs in reports.items() for r in rs if r.get("chip") == NEO_CHIP and usable(r) and gid in games
            and gid not in EXCLUDE and not games[gid]["status"].startswith("blocked")]
    best = {}
    for gid, r in mine:
        ok = lambda x: rating(x) >= 4 and (minutes(x) is None or minutes(x) >= 10)
        if gid not in best or (ok(r), rating(r)) > (ok(best[gid]), rating(best[gid])):
            best[gid] = r
    good = sorted((gid for gid, r in best.items() if rating(r) >= 4 and (minutes(r) is None or minutes(r) >= 10)), key=lambda gid: games[gid]["title"].lower())
    other = len(best) - len(good)
    lines = ["          <tr><td><strong>%s</strong></td><td>%d/5</td><td>%s</td><td>%s</td></tr>" % (
        e(games[gid]["title"]), rating(best[gid]), RENDERERS.get(best[gid].get("renderer"), "–"), e(NEO_NOTES.get(gid, "–"))) for gid in good]
    path = "/guides/macbook-neo-pc-games/"
    meta = {"path": path, "title": "PC Games on a MacBook Neo: What Players Report – Portnaut",
            "social_title": "PC games on a MacBook Neo: what players report",
            "image": "/assets/og-macbook-neo-pc-games.jpg", "image_alt": "Portnaut guide: PC games on a MacBook Neo",
            "description": "Can a MacBook Neo play PC games? %d Windows games that players report running on its A18 Pro chip through Wine, and what 8 GB and no fan mean." % len(good),
            "faq": True, "jsonld": article(path, "PC games on a MacBook Neo: what players report", "/assets/og-macbook-neo-pc-games.jpg", ("Guides", "/guides/", "PC games on a MacBook Neo"), today)}
    body = """<div class="page-head">
  <div class="wrap narrow">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Portnaut</a></li><li><a href="/guides/">Guides</a></li><li aria-current="page">PC games on a MacBook Neo</li></ol></nav>
    <h1>PC games on a MacBook Neo</h1>
    <p class="lead">Yes, a MacBook Neo can play Windows PC games through Wine, within limits. Players report %(good)d games running on its A18 Pro chip. It has 8 GB of memory and no fan, so lighter games and low settings suit it best.</p>
    <p class="tested">From players' reports in Highball's compatibility database; Portnaut hasn't been tested on a MacBook Neo yet · Updated %(date)s</p>
  </div>
</div>

<article class="prose">
  <div class="wrap narrow">
    <h2 id="short-answer">The short answer</h2>
    <ul>
      <li><strong>It works.</strong> Wine, Rosetta and the graphics renderers run on the A18 Pro: players have sent %(reports)d reports from it to <a href="%(db)s">Highball's open compatibility database</a>.</li>
      <li><strong>Portnaut should run on it,</strong> because it uses the same Wine and renderers and needs only Apple silicon, macOS 14.6 or later and Rosetta. Nobody has tested Portnaut on a MacBook Neo yet, so we'd like to hear how it goes: <a href="mailto:{{support_email}}">{{support_email}}</a>.</li>
      <li><strong>Expect to lower settings.</strong> Reviewers found its 8 GB of memory the main limit, and without a fan it slows down as it warms up.</li>
    </ul>

    <h2 id="games">Games players report running on a MacBook Neo</h2>
    <p>Each game's best report from an A18 Pro Mac, rated 4 (playable, minor issues) or 5 (perfect) out of 5 after ten minutes or more:</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th scope="col">Game</th><th scope="col">Rating</th><th scope="col">Renderer</th><th scope="col">What the player noted</th></tr></thead>
        <tbody>
%(rows)s
        </tbody>
      </table>
    </div>
    <p>%(other)s These are single reports, most after short sessions, so take them as a starting point. <a href="/games/">The full list for all Macs</a> has %(total)d games.</p>

    <h2 id="limits">What limits the MacBook Neo</h2>
    <ul>
      <li><strong>8 GB of memory.</strong> A Windows game, Wine and macOS share it. Large open-world games want more: on a 16 GB Mac, Red Dead Redemption 2 alone used about 14 GB.</li>
      <li><strong>No fan.</strong> In a two-hour Train Simulator Classic session, the frame rate settled at about 30 to 40 fps once the Mac had warmed up.</li>
      <li><strong>A phone-class graphics chip.</strong> The A18 Pro is the iPhone 16 Pro's chip. Older and lighter games run well; recent demanding ones need the lowest settings or won't be comfortable.</li>
      <li><strong>Anti-cheat,</strong> as on every Mac: games with kernel-level anti-cheat don't run through Wine at all.</li>
    </ul>

    <h2 id="steps">How to try it</h2>
    <ol>
      <li><strong>Check for a Mac version of the game first.</strong> It'll run better than a Windows version.</li>
      <li><strong><a href="/download/">Download Portnaut</a></strong>, open it, and choose <strong>Prepare Portnaut</strong>.</li>
      <li><strong>Create a bottle</strong> for your game store, such as Steam, and keep <strong>easy mode</strong> on.</li>
      <li><strong>Start with a light or older game,</strong> at a low resolution and the lowest preset, then raise settings while it stays smooth.</li>
    </ol>
    <p><a href="/guides/play-pc-games-on-mac/">How to play PC games on a Mac</a> has every step.</p>

    <h2 id="faq">Questions</h2>
    <details>
      <summary>Can a MacBook Neo play PC games?</summary>
      <p>Yes, lighter ones. Players report %(good)d Windows games running on its A18 Pro chip through Wine. Its 8 GB of memory and fanless design limit demanding games.</p>
    </details>
    <details>
      <summary>Can a MacBook Neo run Steam?</summary>
      <p>Steam's Mac app runs on Apple silicon. For Steam games that are Windows only, the Windows version of Steam runs through Wine; the reports above came from games started that way with Highball. Portnaut sets up the same, but hasn't been tested on a MacBook Neo.</p>
    </details>
    <details>
      <summary>Does Portnaut work on a MacBook Neo?</summary>
      <p>It should: Portnaut needs Apple silicon, macOS 14.6 or later and Rosetta, and the same Wine runs on the A18 Pro. It hasn't been tested on one yet.</p>
    </details>
    <details>
      <summary>Is 8 GB enough for gaming on a Mac?</summary>
      <p>For lighter and older games, yes. Demanding games use more than that by themselves, and macOS then slows down as it moves memory to disk.</p>
    </details>

    <p>Next: <a href="/guides/macbook-air-pc-games/">PC games on a MacBook Air</a> · <a href="/games/">Games that run on a Mac</a> · <a href="/guides/steam-on-mac/">Steam on a Mac</a></p>
    <p class="muted"><small>MacBook Neo, MacBook Air and Apple silicon are trademarks of Apple Inc.; game names are trademarks of their owners. Portnaut is not affiliated with them. The MacBook Neo's memory, chip and fanless design as reported by <a href="https://www.notebookcheck.net/Apple-MacBook-Neo-can-run-games-surprisingly-well-but-8-GB-RAM-is-reportedly-a-bottleneck.1248649.0.html">Notebookcheck</a>. Reports from Highball's database, read on %(date)s.</small></p>
  </div>
</article>
""" % {"good": len(good), "reports": len(mine), "date": long_date(today), "db": DB_URL, "rows": "\n".join(lines),
       "other": ("%d other game%s had a lower rating or a session under ten minutes, and %s left out." % (other, "" if other == 1 else "s", "is" if other == 1 else "are")) if other else "",
       "total": TOTAL}
    page("06-guide-macbook-neo.html", meta, body)


def air_page(games, reports, all_rows, today):
    listed = {r["id"]: r for r in all_rows}
    by_chip = collections.OrderedDict((c, []) for c in BASE_CHIPS)
    for gid, rs in reports.items():
        for r in rs:
            if r.get("chip") in by_chip and usable(r):
                by_chip[r["chip"]].append((gid, r))
    chip_lines, total_reports, total_good = [], 0, 0
    for chip, items in by_chip.items():
        good = sum(1 for _, r in items if rating(r) >= 4)
        total_reports += len(items)
        total_good += good
        chip_lines.append("          <tr><td><strong>%s</strong></td><td>%d</td><td>%d%%</td></tr>" % (chip.replace("Apple ", ""), len(items), round(100 * good / len(items))))
    count = collections.Counter()
    longest = collections.Counter()
    for chip, items in by_chip.items():
        for gid, r in items:
            if gid in listed and rating(r) >= 4 and (minutes(r) or 0) >= 10:
                count[gid] += 1
                longest[gid] = max(longest[gid], minutes(r) or 0)
    top = sorted(count, key=lambda gid: (-count[gid], -longest[gid], listed[gid]["title"]))[:20]
    game_lines = ["          <tr><td><strong>%s</strong>%s</td><td>%d</td><td>%s</td><td>%s</td></tr>" % (
        '<a href="%s">%s</a>' % (listed[g]["guide"], e(listed[g]["title"])) if listed[g]["guide"] else e(listed[g]["title"]),
        '<br><small class="muted">%s</small>' % e(listed[g]["note"]) if listed[g]["note"] else "",
        count[g], session(longest[g]), RENDERERS.get(listed[g]["renderer"], "–")) for g in top]
    share = round(100 * total_good / total_reports)
    path = "/guides/macbook-air-pc-games/"
    meta = {"path": path, "title": "Can a MacBook Air Play PC Games? Player Reports – Portnaut",
            "social_title": "Can a MacBook Air play PC games? What players report",
            "image": "/assets/og-macbook-air-pc-games.jpg", "image_alt": "Portnaut guide: PC games on a MacBook Air",
            "description": "Yes: %d%% of %d player reports from Macs with the MacBook Air's chips (M1 to M5) rate a Windows game playable or perfect. The games, and the limits." % (share, total_reports),
            "faq": True, "jsonld": article(path, "Can a MacBook Air play PC games?", "/assets/og-macbook-air-pc-games.jpg", ("Guides", "/guides/", "PC games on a MacBook Air"), today)}
    body = """<div class="page-head">
  <div class="wrap narrow">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Portnaut</a></li><li><a href="/guides/">Guides</a></li><li aria-current="page">PC games on a MacBook Air</li></ol></nav>
    <h1>Can a MacBook Air play PC games?</h1>
    <p class="lead">Yes. In %(reports)d player reports from Macs with the chips MacBook Airs use, M1 to M5, %(share)d%% rate a Windows game playable or perfect through Wine. The Air has no fan, so demanding games slow down in long sessions.</p>
    <p class="tested">From players' reports in Highball's compatibility database; not tested with Portnaut on a MacBook Air · Updated %(date)s</p>
  </div>
</div>

<article class="prose">
  <div class="wrap narrow">
    <h2 id="reports">What players report, chip by chip</h2>
    <p>Reports in <a href="%(db)s">Highball's open compatibility database</a> name the Mac's chip, not its model. The plain M1 to M5 chips are the ones in MacBook Airs, and also in some other Macs, so this is the closest view of the Air there is:</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th scope="col">Chip</th><th scope="col">Reports</th><th scope="col">Rated playable or perfect</th></tr></thead>
        <tbody>
%(chips)s
        </tbody>
      </table>
    </div>
    <p>Players mostly report games that work, so these shares flatter the picture a little. They do show that every Apple silicon MacBook Air, the M1 from 2020 included, runs Windows games.</p>

    <h2 id="games">Games reported most on these chips</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th scope="col">Game</th><th scope="col">Good reports</th><th scope="col">Longest session</th><th scope="col">Renderer</th></tr></thead>
        <tbody>
%(games)s
        </tbody>
      </table>
    </div>
    <p><a href="/games/">The full list</a> has %(total)d games, with the chips each was played on.</p>

    <h2 id="limits">What limits a MacBook Air</h2>
    <ul>
      <li><strong>No fan.</strong> The Air cools itself passively, so in a long session with a demanding game it lowers its speed to stay cool. Lighter games don't get there.</li>
      <li><strong>Memory.</strong> With 8 GB, stay with lighter and older games. Large open-world games can use most of 16 GB on their own.</li>
      <li><strong>Translation costs speed.</strong> Rosetta translates the game's Intel code and a renderer translates its DirectX graphics to Metal, so expect less than a PC with similar hardware.</li>
      <li><strong>Anti-cheat.</strong> Games with kernel-level anti-cheat don't run through Wine on any Mac, and some games run only offline.</li>
    </ul>

    <h2 id="steps">How to play PC games on a MacBook Air</h2>
    <ol>
      <li><strong>Check for a Mac version first.</strong> On Steam, look for the Apple logo on the game's page.</li>
      <li><strong><a href="/download/">Download Portnaut</a></strong>, open it, and choose <strong>Prepare Portnaut</strong>.</li>
      <li><strong>Create a bottle</strong> for your game store and keep <strong>easy mode</strong> on, so Portnaut picks the renderer for each game.</li>
      <li><strong>Install the game and press Play.</strong> Start at a lower resolution and raise settings while it stays smooth.</li>
    </ol>
    <p>Step by step: <a href="/guides/play-pc-games-on-mac/">How to play PC games on a Mac</a>. Have the newer budget model? <a href="/guides/macbook-neo-pc-games/">PC games on a MacBook Neo</a>.</p>

    <h2 id="faq">Questions</h2>
    <details>
      <summary>Is a MacBook Air good for gaming?</summary>
      <p>For lighter, older and well-optimised games, yes. For recent demanding games it works at lower settings, and it slows down in long sessions because it has no fan. A MacBook Pro holds its speed longer.</p>
    </details>
    <details>
      <summary>Can a MacBook Air run Steam games?</summary>
      <p>Yes. Games with a Mac version run in Steam's Mac app. Windows-only Steam games run through Wine: players report many working on the Air's chips.</p>
    </details>
    <details>
      <summary>Can an M1 MacBook Air play PC games?</summary>
      <p>Yes. The plain M1 has more reports than any other chip in the database. As one example, players measured GTA V's benchmark at about 50 to 60 fps at 1080p on a base M1.</p>
    </details>
    <details>
      <summary>Do I need Windows on my MacBook Air?</summary>
      <p>No. Wine provides the parts of Windows that games use, so there's no copy of Windows and no licence to buy. Boot Camp doesn't exist on Apple silicon.</p>
    </details>

    <p>Next: <a href="/games/">Games that run on a Mac</a> · <a href="/guides/macbook-neo-pc-games/">PC games on a MacBook Neo</a> · <a href="/guides/steam-on-mac/">Steam on a Mac</a></p>
    <p class="muted"><small>MacBook Air, MacBook Pro and Apple silicon are trademarks of Apple Inc.; game names are trademarks of their owners. Portnaut is not affiliated with them. Reports from Highball's database, read on %(date)s.</small></p>
  </div>
</article>
""" % {"reports": total_reports, "share": share, "date": long_date(today), "db": DB_URL, "chips": "\n".join(chip_lines),
       "games": "\n".join(game_lines), "total": TOTAL}
    page("06-guide-macbook-air.html", meta, body)


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else fetch()
    games, reports = load(folder)
    today = datetime.date.today()
    listed = rows(games, reports)
    TOTAL = len(listed)
    games_page(listed, today)
    neo_page(games, reports, today)
    air_page(games, reports, listed, today)
    print("%d games listed, %d with a Wine 11 report" % (TOTAL, sum(r["wine11"] for r in listed)))
