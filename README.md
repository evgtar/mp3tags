# Audio Tags Renamer

This project provides a Python script for renaming and organizing audio files based on their metadata tags. It utilizes the `pytaglib` library (with `mutagen` as fallback) to extract metadata from various audio file formats and organizes them into directories based on artist and album.

## Supported Formats

- **MP3** - Uses ID3 tags
- **FLAC** - Uses Vorbis comments
- **OGG** - Uses Vorbis comments  
- **MP4/M4A** - Uses iTunes-style tags
- **WMA** - Uses ASF tags
- **AAC** - Uses ADTS tags
- **OPUS** - Uses Vorbis comments

## Features

- **Efficient tag extraction** using pytaglib for optimal performance
- **Automatic fallback** to mutagen if pytaglib is unavailable
- Renames audio files according to their title metadata tag
- Organizes files into directories based on artist and album tags
- Handles duplicate files intelligently by comparing file sizes and bit rates
- Cleans filenames by removing invalid characters
- Accepts command-line arguments for flexible usage
- Supports multiple audio formats with format-specific tag handling
- **Configurable logging** with file and console output
- **INI-based configuration** for all settings
- **Automatic playlist generation** for all processed files with customizable names and locations
- **Tabular statistics output** showing processing results

## Configuration

The script can be configured using an `mp3tags.ini` file with the following sections:

### Basic Configuration

```ini
[mp3tags]
source = C:\Music\Input
storage = C:\Music\Output
```

### Logging Configuration

```ini
[logging]
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = INFO
# Log file path (can be relative or absolute)
log_file = mp3tags.log
# Enable console output (true/false)
console_output = true
# Log format (use %% to escape % characters)
format = %%(asctime)s - %%(levelname)s - %%(message)s
```

### Audio Format Configuration

```ini
[audio_formats]
# Supported audio file extensions (comma-separated, case-insensitive)
extensions = .mp3, .flac, .ogg, .mp4, .m4a, .wma, .aac, .opus
```

### Playlist Configuration

```ini
[playlists]
# Enable/disable playlist generation (true/false)
generate = true
# Playlist name template (supports {date}, {time}, {datetime} placeholders)
# Examples: "New Additions", "Added {date}", "Music {datetime}"
name_template = New Additions
# Directory for playlists (empty = storage root, or specify path like "Playlists" or absolute path)
directory =
```

**Playlist Configuration Options:**

- `generate` - Enable or disable playlist generation
- `name_template` - Template for playlist filename with placeholder support
- `directory` - Where to save playlists:
  - Empty (default) = Save in storage directory root
  - Relative path (e.g., "Playlists") = Create subdirectory in storage directory
  - Absolute path = Save to specific location

**Playlist Name Placeholders:**

- `{date}` - Current date (YYYY-MM-DD)
- `{time}` - Current time (HH-MM-SS)
- `{datetime}` - Date and time (YYYY-MM-DD_HH-MM-SS)

## Requirements

To run this project, you need to have Python installed along with the following dependencies:

- `pytaglib` (recommended for optimal performance)
- `mutagen` (fallback library)

You can install the required dependencies using pip:

```bash
pip install -r requirements.txt
```

**Note**: If `pytaglib` is not available, the script will automatically fall back to using `mutagen` for tag extraction.

## Usage

1. Clone the repository or download the script.
2. Place your audio files in your chosen source directory.
3. Optionally, create an `mp3tags.ini` configuration file in the same directory as the script.
4. Run the script from the command line:

```bash
# Using command-line arguments
python mp3tags.py -S <source_directory> -T <storage_directory>

# Using configuration file
python mp3tags.py

# With verbose logging
python mp3tags.py -v

# With quiet mode (errors only)
python mp3tags.py -q

# With custom log file
python mp3tags.py --log-file custom.log

# With custom playlist name
python mp3tags.py --playlist-name "Added {date}"

# With custom playlist directory
python mp3tags.py --playlist-dir "Playlists"
```

### Command-line Options

- `-S` or `--source`: The directory containing the audio files to be processed.
- `-T` or `--storage`: The directory where the organized audio files will be stored.
- `-v` or `--verbose`: Enable verbose logging (DEBUG level).
- `-q` or `--quiet`: Enable quiet mode (ERROR level only).
- `--log-file`: Specify custom log file path.
- `--playlist-name`: Custom name for the generated playlist (supports {date}, {time}, {datetime} placeholders).
- `--playlist-dir`: Directory for playlist files (overrides INI config).

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
