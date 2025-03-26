# TMDb Labels for Plex

## Overview
Plex Label Updater is a Python tool which applies labels to your episodes/seasons/shows based on data from The Movie Database (TMDb).

It will apply labels for things such as:
- Pilots (Season = 1, Episode = 1)
- Season Premieres (Season > 1, Episode = 1)
- Mid-Season Finale
- Season Finale (Final episode of season)
- Series Finale (Final episode of season and Show status is Ended/Canceled)

Additionally it will apply labels such as:
- TMDb Status (i.e. `Status: Ended` and `Status: Returning Series`)
- Upcoming Episodes (i.e. `New Episode Thursday` and `New Episode 12/25`)

## Customization Points
You can modify the following variables directly in the script:
- **Plex Connection:**  
  - `PLEX_URL`: URL of your Plex server.  
  - `PLEX_TOKEN`: Your Plex authentication token.  
  - `TV_LIBRARY_NAME`: Name of your TV library in Plex.
- **TMDb API:**  
  - `TMDB_API_KEY`: Your TMDb API key.
- **Date & Label Settings:**  
  - `DATE_FORMAT`: `"MM/DD"` or `"DD/MM"` determines how dates are formatted in labels.  
  - `DAY_INDICATOR`: Set to `True` to use the weekday name (e.g., "Sunday") for episodes airing within 7 days.  
  - `DAYS_TO_CONSIDER`: Number of days (including today) in which an upcoming episode will trigger a **New Episode/New Season** label.
  - `RETURNING_DAYS`: Maximum number of days for which a **Returning _<date>_** label will be applied if not already processed.
- **Logging**
  - `LOG_PATH`: What to name the log file (used to track what has been labelled and when)

## CLI Options
- `--clear`  
  Clears special labels (both season and show labels) from matching shows and exits.
- `--tmdb <id>`  
  Processes only shows matching the given TMDb ID. The tool fetches the show title from TMDb and then uses Plex’s search to find all items with that title.
- `--title "<show name>"`  
  Processes only shows whose title contains the given text (case‑insensitive). This bypasses the TMDb lookup.
- `--collection "<collection name>"`  
  Processes only shows that are part of the specified Plex collection.
- `--label "<label>"`  
  Processes only shows that already have the specified Plex label.
- `--trace`
  Enables detailed trace-level logging for debugging and progress visibility.

## Examples
**Process a Show by TMDb ID (for updating labels):**
  ```bash
  python labeller.py --tmdb 111803
  ```

  The script will fetch the title for TMDb ID 111803 (for example, "The White Lotus") and then search Plex for all items with that title. It will update labels (e.g., upcoming episode labels, season labels based on the last aired episode, and status labels).

**Process a Show by Title:**

  ```bash
  python labeller.py --title "The White Lotus"
  ```
  
  This directly searches Plex for items with titles containing "The White Lotus" and updates their labels accordingly.

**Process Shows by Label:**
  ```bash
  python labeller.py --label "Testing"
  ```
  The script will update labels only for shows that already have the "Testing" label in Plex.

**Clear Labels for a Specific Show Using TMDb ID:**

  ```bash
  python labeller.py --clear --tmdb 111803
  ```

  This will fetch the title from TMDb for ID 111803 and then use Plex’s search to find all items with that title, clearing any special labels (and update log) from them.

**Clear Labels by Title:**

  ```bash
  python labeller.py --clear --title "The White Lotus"
  ```
  
  This will clear special labels for all Plex items whose title contains "The White Lotus."

**Clear Labels by Label:**

  ```bash
  python labeller.py --clear --label "Testing"
  ```

  This will clear special labels from all items in Plex that have the "Testing" label.

**Enable Trace Logging:**

  ```bash
  python labeller.py --tmdb 111803 --trace
  ```

  This enables detailed debug output to help you see exactly what the script is doing during processing.

## How It Works

**Filtering:**

The script uses Plex’s built-in search methods to retrieve only the shows that match the filters provided via --tmdb, --title, --collection, or --label.

For `--tmdb`, it fetches the show’s title from TMDb and searches Plex by that title.

For -`-title`, it searches Plex directly.

For `--collection`, it retrieves only the items in the specified collection. (**Note**: This only works for Non-Smart collections)

For -`-label`, it filters for shows that have the specified label. This can be used for Kometa Smart Label collections.

## Installation

Clone the repository:

  ```bash
  git clone <repository_url>
  ```

Install the required packages:

  ```bash
  pip install -r requirements.txt
  ```

Update the configuration settings in the script (e.g., TMDB_API_KEY, PLEX_URL, PLEX_TOKEN, etc.).

## Usage

Run the script with your desired options (anything inside `[ ]` brackets is optional, only `python labeller.py` is required to do a standard run)

  ```bash
  python labeller.py [--clear] [--tmdb <id>] [--title "<show name>"] [--collection "<collection>"] [--label "<label>"] [--trace]
  ```