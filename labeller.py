import os
import json
import argparse
import requests
from datetime import datetime, date
from plexapi.server import PlexServer

# --- Configuration ---
PLEX_URL = 'PLEX_URL'
PLEX_TOKEN = 'PLEX_TOKEN'
TMDB_API_KEY = 'TMDB_API_KEY'
TV_LIBRARY_NAME = 'TV_LIBRARY_NAME'
LOG_PATH = 'labeller.json'

# --- Date Formatting Options ---
DATE_FORMAT = 'MM/DD'  # or 'DD/MM'
DAY_INDICATOR = True  # Use weekday name if episode is <= 7 days away
DAYS_TO_CONSIDER = 7  # For New Episode/New Season labels (0 means today is included)
RETURNING_DAYS = 28  # For Returning label when not overridden by DAYS_TO_CONSIDER

SPECIAL_LABELS = {"Pilot", "Season Premiere", "Season Finale", "Series Finale", "Mid-Season Finale"}
STATUS_LABELS = {"Status: Ended", "Status: Canceled", "Status: Returning Series"}  # Expand as needed

# --- CLI ---
parser = argparse.ArgumentParser()
parser.add_argument('--clear', action='store_true', help='Clear special labels from matching shows and exit')
parser.add_argument('--tmdb', type=str,
                    help='Process only shows matching the given TMDb ID (uses TMDb lookup to get title)')
parser.add_argument('--title', type=str,
                    help='Process only shows whose title contains the given text (case-insensitive)')
parser.add_argument('--collection', type=str, help='Process only shows in the specified Plex collection')
parser.add_argument('--label', type=str, help='Process only shows that have the specified Plex label')
parser.add_argument('--trace', action='store_true', help='Enable trace-level logging')
args = parser.parse_args()

TRACE = args.trace  # Global flag for trace logging


def trace_log(msg):
    if TRACE:
        print(msg)


plex = PlexServer(PLEX_URL, PLEX_TOKEN)
tv_library = plex.library.section(TV_LIBRARY_NAME)


# --- Helper: Get Filtered Shows ---
def get_filtered_shows():
    # If a collection is specified, start with its items.
    if args.collection:
        trace_log(f"Filtering shows by collection: {args.collection}")
        try:
            collections = tv_library.collections()
            collection_dict = {c.title: c for c in collections}
            if args.collection in collection_dict:
                shows = collection_dict[args.collection].items()
                print(f"Found {len(shows)} shows in collection '{args.collection}'.")
            else:
                print(f"Collection '{args.collection}' not found.")
                return []
        except Exception as e:
            print(f"Error retrieving collections: {e}")
            return []
    else:
        shows = tv_library.search()
        print(f"Total shows in library: {len(shows)}")

    # If a TMDb filter is provided, fetch its title from TMDb and search by title.
    if args.tmdb:
        print(f"Fetching TMDb data for TMDb ID {args.tmdb} ...")
        tmdb_url = f"https://api.themoviedb.org/3/tv/{args.tmdb}?api_key={TMDB_API_KEY}"
        response = requests.get(tmdb_url)
        if response.status_code != 200:
            print(f"TMDb request failed with HTTP {response.status_code}.")
            return []
        data = response.json()
        tmdb_title = data.get("name") or data.get("original_name")
        if not tmdb_title:
            print("Could not determine title from TMDb data.")
            return []
        print(f"TMDb title: {tmdb_title}")
        shows = tv_library.search(title=tmdb_title)
        print(f"Found {len(shows)} shows matching TMDb title '{tmdb_title}'.")

    # If a title filter is provided, search by title.
    if args.title:
        shows = tv_library.search(title=args.title)
        print(f"Found {len(shows)} shows matching title '{args.title}'.")

    # If a label filter is provided, filter the list.
    if args.label:
        filtered = [show for show in shows if args.label in {l.tag for l in show.labels}]
        print(f"Filtered shows by label '{args.label}': {len(filtered)} show(s) remain.")
        shows = filtered

    return shows


# --- CLEAR MODE ---
if args.clear:
    shows_to_clear = get_filtered_shows()
    print(f"Clearing labels for {len(shows_to_clear)} show(s) matching filters.")
    for show in shows_to_clear:
        show.reload()
        for label in list(show.labels):
            if label.tag in SPECIAL_LABELS or label.tag in STATUS_LABELS:
                show.removeLabel(label)
                print(f"Removed '{label.tag}' from show: {show.title}")
        for season in show.seasons():
            season.reload()
            for label in list(season.labels):
                if label.tag in SPECIAL_LABELS:
                    season.removeLabel(label)
                    print(f"Removed '{label.tag}' from {show.title} - Season {season.index}")
            for episode in season.episodes():
                episode.reload()
                for label in list(episode.labels):
                    if label.tag in SPECIAL_LABELS:
                        episode.removeLabel(label)
                        print(f"Removed '{label.tag}' from {show.title} S{season.index}E{episode.index}")
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)
        print("🧹 Cleared update log file.")
    print("✅ Done clearing labels.")
    exit(0)

# --- LOAD UPDATE LOG ---
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, 'r') as f:
        update_log = json.load(f)
else:
    update_log = {}


# --- Helpers (unchanged) ---
def get_tmdb_id(show):
    try:
        for guid in show.guids:
            guid_str = guid.id if hasattr(guid, 'id') else guid
            if guid_str.startswith("tmdb://"):
                return guid_str.split("tmdb://")[1].split("?")[0]
    except Exception as e:
        print(f"Error retrieving TMDb ID for {show.title}: {e}")
    return None


def set_label(obj, label, prefix):
    obj.reload()
    existing = {l.tag for l in obj.labels}
    modified = False
    for l in existing & SPECIAL_LABELS:
        if l != label:
            obj.removeLabel(l)
            modified = True
    if label and label not in existing:
        obj.addLabel(label)
        print(f"{prefix} Added label '{label}' to {obj.title}")
        modified = True
    return modified


def set_status_label(show, tmdb_status, prefix, latest_season):
    trace_log(f"{prefix} Fetching upcoming episode info for {show.title}...")
    next_ep = tmdb_data.get("next_episode_to_air")
    if next_ep:
        air_date_str = next_ep.get("air_date")
        season_number = next_ep.get("season_number")
        episode_number = next_ep.get("episode_number")
        if air_date_str and season_number and episode_number:
            air_date = datetime.fromisoformat(air_date_str).date()
            days_until = (air_date - date.today()).days
            if DAY_INDICATOR and days_until <= 7:
                formatted_date = air_date.strftime("%A")
            else:
                formatted_date = air_date.strftime("%m/%d") if DATE_FORMAT == "MM/DD" else air_date.strftime("%d/%m")
            if days_until <= DAYS_TO_CONSIDER:
                if season_number == latest_season.index and episode_number != 1:
                    label = f"New Episode {formatted_date}"
                    trace_log(f"{prefix} Upcoming episode qualifies for 'New Episode' label.")
                    show.reload()
                    existing_show = {l.tag for l in show.labels}
                    for l in existing_show:
                        if l.startswith("New Episode") or l.startswith("New Season") or l.startswith("Returning"):
                            show.removeLabel(l)
                    if label not in existing_show:
                        show.addLabel(label)
                        print(f"{prefix} Added label '{label}' to {show.title}")
                    latest_season.reload()
                    existing_season = {l.tag for l in latest_season.labels}
                    for l in existing_season:
                        if l.startswith("New Episode") or l.startswith("New Season") or l.startswith("Returning"):
                            latest_season.removeLabel(l)
                    if label not in existing_season:
                        latest_season.addLabel(label)
                        print(f"{prefix} Added label '{label}' to {latest_season.title}")
                else:
                    label = f"New Season {formatted_date}"
                    trace_log(f"{prefix} Upcoming episode qualifies for 'New Season' label.")
                    show.reload()
                    existing_show = {l.tag for l in show.labels}
                    for l in existing_show:
                        if l.startswith("New Episode") or l.startswith("New Season") or l.startswith("Returning"):
                            show.removeLabel(l)
                    if label not in existing_show:
                        show.addLabel(label)
                        print(f"{prefix} Added label '{label}' to {show.title}")
            elif days_until <= RETURNING_DAYS:
                returning_label = f"Returning {formatted_date}"
                trace_log(f"{prefix} Upcoming episode qualifies for 'Returning' label.")
                show.reload()
                existing_show = {l.tag for l in show.labels}
                for l in existing_show:
                    if l.startswith("Returning"):
                        show.removeLabel(l)
                if returning_label not in existing_show:
                    show.addLabel(returning_label)
                    print(f"{prefix} Added label '{returning_label}' to {show.title}")
    existing = {l.tag for l in show.labels}
    for label in existing & STATUS_LABELS:
        show.removeLabel(label)
    if tmdb_status:
        status_label = f"Status: {tmdb_status.title()}"
        if status_label not in existing:
            show.addLabel(status_label)
            print(f"{prefix} Added label '{status_label}' to {show.title}")


def remove_all_special_labels(obj, prefix):
    obj.reload()
    for l in obj.labels:
        if l.tag in SPECIAL_LABELS:
            obj.removeLabel(l)
            print(f"{prefix} Removed label '{l.tag}' from {obj.title}")


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def set_episode_special_labels(episode, new_labels, prefix):
    try:
        episode.reload()
        existing_labels = {label.tag for label in episode.labels}
        modified = False
        for label in existing_labels & SPECIAL_LABELS:
            if label not in new_labels:
                episode.removeLabel(label)
                modified = True
        for label in new_labels:
            if label not in existing_labels:
                episode.addLabel(label)
                modified = True
        if modified:
            print(
                f"{prefix} Updated labels for {episode.grandparentTitle} - {episode.parentTitle} S{episode.season().index}E{episode.index}: {new_labels}")
        return modified
    except Exception as e:
        print(
            f"{prefix} Failed to update labels for {episode.grandparentTitle} - {episode.parentTitle} S{episode.season().index}E{episode.index}: {e}")
        return False


# --- Main Processing ---
all_shows = get_filtered_shows()
print(f"Found {len(all_shows)} show(s) matching filters for processing.")

for idx, show in enumerate(all_shows, start=1):
    prefix = f"(Show: {idx}/{len(all_shows)})"
    print(f"{prefix} Processing {show.title}...")
    try:
        tmdb_id = get_tmdb_id(show)
        if not tmdb_id:
            print(f"{prefix} Skipping {show.title}: No TMDb ID found.")
            continue

        print(f"{prefix} Fetching TMDb data for {show.title} (TMDb ID: {tmdb_id})...")
        tmdb_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}"
        tmdb_response = requests.get(tmdb_url)
        if tmdb_response.status_code != 200:
            print(f"{prefix} Skipping {show.title}: TMDb request failed (HTTP {tmdb_response.status_code}).")
            continue

        tmdb_data = tmdb_response.json()
        last_air_date = tmdb_data.get("last_air_date")
        tmdb_status = tmdb_data.get("status", "").lower()

        plex_seasons = show.seasons()
        if not plex_seasons:
            print(f"{prefix} Skipping {show.title}: no seasons found in Plex.")
            continue
        latest_season = max(plex_seasons, key=lambda s: s.index or 0)
        trace_log(f"{prefix} Found {len(plex_seasons)} seasons. Latest season is Season {latest_season.index}.")

        set_status_label(show, tmdb_status, prefix, latest_season)

        last_updated_str = update_log.get(tmdb_id)
        last_updated_dt = datetime.fromisoformat(last_updated_str) if last_updated_str else None
        last_air_dt = datetime.fromisoformat(last_air_date) if last_air_date else None

        is_rerun = last_updated_dt and last_air_dt and last_air_dt > last_updated_dt
        should_process = not last_updated_dt or is_rerun
        if not should_process:
            print(f"{prefix} Skipping {show.title}: no new episodes since last update.")
            continue

        trace_log(f"{prefix} Fetching TMDb season data for {show.title}...")
        season_numbers = [s.index for s in plex_seasons if s.index]
        all_tmdb_data = {}
        for batch in chunks(season_numbers, 20):
            parts = [f"season/{n}" for n in batch]
            url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&append_to_response={','.join(parts)}"
            resp = requests.get(url)
            if resp.status_code != 200:
                print(f"{prefix} TMDb fetch failed for batch {batch}")
                continue
            data = resp.json()
            for p in parts:
                if p in data:
                    all_tmdb_data[p] = data[p]

        tmdb_season_keys = [k for k in all_tmdb_data.keys() if k.startswith("season/")]
        final_season_index = max(int(k.split("/")[1]) for k in tmdb_season_keys)
        latest_season_label = None
        any_modified = False

        for season in plex_seasons:
            trace_log(f"{prefix} Processing Season {season.index} for {show.title}...")
            season_key = f"season/{season.index}"
            if season_key not in all_tmdb_data:
                print(f"{prefix} Skipping {show.title} - Season {season.index}: not found in TMDb.")
                continue

            season_data = all_tmdb_data[season_key]
            tmdb_episodes = season_data.get("episodes", [])
            today = date.today()
            aired_episodes = [ep for ep in tmdb_episodes if
                              ep.get("air_date") and datetime.fromisoformat(ep["air_date"]).date() <= today]
            if not aired_episodes:
                print(f"{prefix} Skipping {show.title} - Season {season.index}: no episodes have aired yet.")
                remove_all_special_labels(season, prefix)
                continue

            # Determine season label based solely on the last aired episode.
            last_ep = max(aired_episodes, key=lambda ep: ep.get("episode_number", 0))
            ep_type = last_ep.get("episode_type", "").lower()
            ep_num = last_ep.get("episode_number")
            candidate_label = None
            if ep_num == 1:
                candidate_label = "Pilot" if season.index == 1 else "Season Premiere"
            elif ep_type == "mid_season":
                candidate_label = "Mid-Season Finale"
            elif ep_type == "finale":
                candidate_label = "Series Finale" if (season.index == final_season_index and tmdb_status in ["ended",
                                                                                                             "canceled"]) else "Season Finale"
            season_label = candidate_label  # Use the candidate from the last aired episode.
            trace_log(f"{prefix} Determined season label for Season {season.index}: {season_label}")
            if season_label:
                modified = set_label(season, season_label, prefix)
            else:
                remove_all_special_labels(season, prefix)
                modified = False
            any_modified = any_modified or modified

            if season.index == latest_season.index:
                latest_season_label = season_label

            # Optimized episode processing: only process candidate episodes.
            candidate_episodes = {}
            for ep in tmdb_episodes:
                if not ep.get("air_date"):
                    continue
                try:
                    ep_date = datetime.fromisoformat(ep["air_date"]).date()
                except Exception:
                    continue
                if ep_date > today:
                    continue
                candidate = None
                if season.index == 1 and ep["episode_number"] == 1:
                    candidate = "Pilot"
                elif ep["episode_number"] == 1:
                    candidate = "Season Premiere"
                elif ep.get("episode_type", "").lower() == "mid_season":
                    candidate = "Mid-Season Finale"
                elif ep.get("episode_type", "").lower() == "finale":
                    candidate = "Series Finale" if (season.index == final_season_index and tmdb_status in ["ended",
                                                                                                           "canceled"]) else "Season Finale"
                if candidate:
                    candidate_episodes[ep["episode_number"]] = candidate
            trace_log(f"{prefix} Found candidate episodes in Season {season.index}: {candidate_episodes}")
            for ep_number, candidate_label in candidate_episodes.items():
                try:
                    plex_ep = season.episode(ep_number)
                except Exception:
                    print(
                        f"{prefix} Skipping {show.title} - Season {season.index} Episode {ep_number}: not found in Plex.")
                    continue
                updated = set_episode_special_labels(plex_ep, {candidate_label}, prefix)
                any_modified = any_modified or updated

        if latest_season_label:
            updated = set_label(show, latest_season_label, prefix)
            any_modified = any_modified or updated
        else:
            remove_all_special_labels(show, prefix)

        if any_modified:
            update_log[tmdb_id] = datetime.now().isoformat()
            print(f"{prefix} Completed processing for {show.title}.")

    except Exception as e:
        print(f"{prefix} Skipping {getattr(show, 'title', 'Unknown')} due to unexpected error: {e}")

with open(LOG_PATH, 'w') as f:
    json.dump(update_log, f, indent=2)