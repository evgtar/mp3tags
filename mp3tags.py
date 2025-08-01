"""
    This script renames audio files based on their metadata tags, organizes them into artist and album directories,
    and handles duplicates intelligently. It uses the pytaglib library (with mutagen as fallback) to read metadata tags from audio files.
    
    Supported formats: MP3, FLAC, OGG, MP4/M4A, WMA, AAC, OPUS (configurable via INI file)

    Features:
        - Multi-format audio file processing (configurable)
        - Efficient tag extraction with pytaglib (fallback to mutagen)
        - Intelligent duplicate detection and handling
        - Configurable logging with file and console output
        - Command-line and configuration file support
        - INI-based configuration for logging and audio formats
        - Tabular output for processing statistics
        - Automatic playlist generation for all processed files (configurable)

    Configuration:
        The script reads settings from mp3tags.ini file with sections:
        - [mp3tags]: source and storage directories
        - [logging]: log level, file path, format, console output
        - [audio_formats]: supported file extensions
        - [playlists]: playlist generation settings, name template, and directory
    
    Usage:
        `python mp3tags.py -S "C:\\Music\\Unsorted" -T "C:\\Music\\Organized"`
        `python mp3tags.py -v` (verbose logging)
        `python mp3tags.py -q` (quiet mode)
        or to run with default directories from mp3tags.ini:
        `python mp3tags.py`

Keyword arguments:
    source_directory -- The directory containing the audio files to be processed.
    storage_directory -- The directory where the renamed audio files will be stored.

    Functions:
        setup_logging(verbose, quiet, log_file, config) -- Configures logging based on parameters and INI config.
        get_audio_extensions(config) -- Gets audio file extensions from INI config or returns defaults.
        rename_files(directory, logger, audio_extensions) -- Renames audio files in the specified directory based on their metadata tags.
        rename_files_in_subdirectories(source_directory, logger, audio_extensions) -- Renames audio files in all subdirectories of the specified source directory.
        audio_tag(filename, logger) -- Extracts the tags from an audio file using pytaglib (preferred) or mutagen (fallback).
        clean_string(s) -- Cleans a string by removing invalid characters for filenames.
        file_hash(filepath, chunk_size=8192) -- Computes SHA256 hash of a file.
        generate_playlists(all_files, storage_directory, logger, config, playlist_name, playlist_dir_override) -- Generates a playlist based on all processed files.
        main(source_directory, storage_directory, logger, audio_extensions, config, playlist_name, playlist_dir) -- Main function to process audio files and organize them into the storage directory.

    Arguments:
        source_directory -- The directory containing the audio files to be processed.
        storage_directory -- The directory where the renamed audio files will be stored.
        logger -- Logger instance for outputting messages.
        audio_extensions -- Tuple of supported audio file extensions.

    Returns:
        None

TODO: 
    - Implement the renaming logic based on metadata tags
    - Add monitoring for new files in the source directory

"""


import os
import argparse
import shutil
import time
import hashlib
import configparser
import logging
try:
    import taglib
    PYTAGLIB_AVAILABLE = True
except ImportError:
    PYTAGLIB_AVAILABLE = False
from mutagen import File

def setup_logging(verbose=False, quiet=False, log_file='mp3tags.log', config=None):
    """Setup logging configuration and return logger instance."""
    log_level = logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    console_output = True
    
    # Override with INI config if provided
    if config:
        try:
            level_str = config.get('logging', 'level', fallback='INFO').upper()
            log_level = getattr(logging, level_str, logging.INFO)                        
            log_file = config.get('logging', 'log_file', fallback=log_file)
            console_output = config.getboolean('logging', 'console_output', fallback=True)            
            log_format = config.get('logging', 'format', fallback=log_format)
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
    
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    handlers = []
    
    handlers.append(logging.FileHandler(log_file))
    
    if console_output and not quiet:
        handlers.append(logging.StreamHandler())
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True
    )
    return logging.getLogger(__name__)

def get_audio_extensions(config=None):
    """Get audio file extensions from config or return defaults."""
    default_extensions = ('.mp3', '.flac', '.ogg', '.mp4', '.m4a', '.wma', '.aac', '.opus')
    
    if config:
        try:
            extensions_str = config.get('audio_formats', 'extensions', fallback=None)
            if extensions_str:
                # Parse comma-separated extensions and clean them
                extensions = []
                for ext in extensions_str.split(','):
                    ext = ext.strip().lower()
                    if not ext.startswith('.'):
                        ext = '.' + ext
                    extensions.append(ext)
                return tuple(extensions)
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
    
    return default_extensions

def rename_files(directory: str, logger: logging.Logger, audio_extensions=None) -> None:
    """
    Renames audio files in the specified directory based on their metadata tags.
    If the title tag is present, it uses that as the new filename.
    If a file with the same name already exists, it appends a number to the filename.
    Supports: MP3, FLAC, OGG, MP4/M4A, WMA, AAC, OPUS
    """
    if audio_extensions is None:
        audio_extensions = ('.mp3', '.flac', '.ogg', '.mp4', '.m4a', '.wma', '.aac', '.opus')
    
    for filename in os.listdir(directory):
        if filename.lower().endswith(audio_extensions):
            file_path = os.path.join(directory, filename)
            try:
                audio = File(file_path)
                if audio is not None and audio.tags:
                    title = None
                    if hasattr(audio.tags, 'get'):
                        title = (audio.tags.get('TIT2') or 
                                audio.tags.get('TITLE') or 
                                audio.tags.get('\xa9nam'))  # iTunes format
                    
                    if title:
                        if hasattr(title, 'text'):
                            title = title.text[0] if title.text else None
                        elif isinstance(title, list):
                            title = title[0] if title else None
                        elif isinstance(title, str):
                            title = title
                        
                        if title:
                            # Replace invalid characters for filenames
                            title = title.replace('/', ' ').replace('\\', ' ').replace(':', ' ').replace('*', ' ').replace('?', ' ').replace('"', ' ').replace('<', ' ').replace('>', ' ').replace('|', ' ').replace('!', ' ')
                            file_extension = os.path.splitext(filename)[1]
                            new_filename = f"{title}{file_extension}"
                            new_file_path = os.path.join(directory, new_filename)
                            
                            # Check if file already exists and if it's already correctly named
                            if file_path != new_file_path:
                                count = 1
                                while os.path.exists(new_file_path):
                                    new_filename = f"{title} ({count}){file_extension}"
                                    new_file_path = os.path.join(directory, new_filename)
                                    count += 1
                                
                                shutil.move(file_path, new_file_path)
                                logger.info(f"Renamed '{filename}' to '{new_filename}'")
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")

def rename_files_in_subdirectories(source_directory: str, logger: logging.Logger, audio_extensions=None) -> None:
    """
    Renames audio files in all subdirectories of the specified source directory.
    Supports: MP3, FLAC, OGG, MP4/M4A, WMA, AAC, OPUS
    """
    for root, dirs, files in os.walk(source_directory):
        for dir_name in dirs:
            directory = os.path.join(root, dir_name)
            rename_files(directory, logger, audio_extensions)
        # Also check files in the source_directory itself
        rename_files(root, logger, audio_extensions)

def audio_tag(filename: str, logger: logging.Logger) -> dict:
    """
    Extracts the tags from an audio file using pytaglib (preferred) or Mutagen as fallback.
    Returns a dictionary with the filename and its tags.
    Supports: MP3, FLAC, OGG, MP4/M4A, WMA, AAC, OPUS
    """
    try:
        # Try pytaglib first for better performance
        if PYTAGLIB_AVAILABLE:
            try:
                with taglib.File(filename) as f:
                    if f.tags:
                        file_info = {
                            'filename': filename,
                            'tags': {}
                        }
                        # Convert pytaglib tags to our expected format
                        tag_mapping = {
                            'TITLE': 'TIT2',
                            'ARTIST': 'TPE1', 
                            'ALBUMARTIST': 'TPE2',
                            'ALBUM': 'TALB',
                            'DATE': 'TDRC',
                            'YEAR': 'TDRC',
                            'TRACK': 'TRCK',
                            'GENRE': 'TCON'
                        }
                        
                        for pytaglib_key, value_list in f.tags.items():
                            if value_list:  # Skip empty lists
                                # Map to ID3 tag names for consistency
                                mapped_key = tag_mapping.get(pytaglib_key.upper(), pytaglib_key)
                                file_info['tags'][mapped_key] = value_list[0]
                                
                                # Also keep original key for compatibility
                                file_info['tags'][pytaglib_key.upper()] = value_list[0]
                        
                        logger.debug(f"Successfully extracted tags using pytaglib: {filename}")
                        return file_info
            except Exception as e:
                logger.debug(f"pytaglib failed for {filename}, falling back to mutagen: {e}")
        
        # Fallback to mutagen
        audio = File(filename)
        if audio is not None and audio.tags:
            file_info = {
                'filename': filename,
                'tags': {}
            }
            for tag_key, tag_value in audio.tags.items():
                if tag_key.startswith('APIC') or tag_key == 'covr':
                    continue  # Skip embedded images
                if hasattr(tag_value, 'text'):
                    if tag_value.text:
                        file_info['tags'][tag_key] = tag_value.text[0]
                    else:
                        file_info['tags'][tag_key] = ''
                elif isinstance(tag_value, list):
                    file_info['tags'][tag_key] = tag_value[0] if tag_value else ''
                else:
                    file_info['tags'][tag_key] = str(tag_value)
            logger.debug(f"Successfully extracted tags using mutagen: {filename}")
            return file_info
        else:
            return {"filename": filename, "tags": {}}
    except Exception as e:
        logger.error(f"Error extracting tags from {filename}: {e}")
        return {"filename": filename, "tags": {}}

def clean_string(s: str) -> str:
    """
    Cleans a string by removing invalid characters for filenames.    
    """
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '!', '(', ')', '[', ']', '{', '}', '@', '#', '$', '%', '^', '&', '=', '+', '`', '~']
    for char in invalid_chars:
        s = s.replace(char, ' ')
    return s.strip()

def file_hash(filepath, chunk_size=8192):
    """Compute SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def collect_all_audio_files(storage_directory: str, audio_extensions: tuple, logger: logging.Logger) -> list:
    """
    Collect all audio files from the storage directory for playlist generation.
    Returns a list of file info dictionaries.
    """
    all_files = []
    
    for root, dirs, files in os.walk(storage_directory):
        for file in files:
            if file.lower().endswith(audio_extensions):
                filepath = os.path.join(root, file)
                try:
                    # Extract tags for each file
                    file_info = audio_tag(filepath, logger)
                    all_files.append({
                        'filepath': filepath,
                        'tags': file_info['tags'],
                        'original_filename': file
                    })
                except Exception as e:
                    logger.debug(f"Error processing {filepath} for playlist: {e}")
    
    logger.debug(f"Collected {len(all_files)} audio files from storage directory for playlist")
    return all_files

def generate_playlists(all_files: list, storage_directory: str, logger: logging.Logger, config=None, playlist_name=None, playlist_dir_override=None) -> None:
    """
    Generate a playlist based on all audio files in the storage directory.
    Creates a single playlist with all audio tracks.
    """
    if not all_files:
        logger.info("No audio files found in storage directory. Skipping playlist generation.")
        return
    
    # Check if playlist generation is enabled
    generate_enabled = True
    if config:
        try:
            generate_enabled = config.getboolean('playlists', 'generate', fallback=True)
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
    
    if not generate_enabled:
        logger.info("Playlist generation is disabled in configuration.")
        return
    
    # Get playlist name from config or parameter
    if playlist_name is None:
        if config:
            try:
                playlist_name = config.get('playlists', 'name_template', fallback='Music Collection')
            except (configparser.NoSectionError, configparser.NoOptionError):
                playlist_name = 'Music Collection'
        else:
            playlist_name = 'Music Collection'
    
    playlist_name = playlist_name.replace('{date}', time.strftime('%Y-%m-%d'))
    playlist_name = playlist_name.replace('{time}', time.strftime('%H-%M-%S'))
    playlist_name = playlist_name.replace('{datetime}', time.strftime('%Y-%m-%d_%H-%M-%S'))
    
    logger.info(f"Generating playlist '{playlist_name}' for {len(all_files)} audio files...")
    
    # Get playlist directory from config or use storage directory root
    playlist_dir = storage_directory  # Default to storage root
    
    # Command-line override has highest priority
    if playlist_dir_override:
        if os.path.isabs(playlist_dir_override):
            playlist_dir = playlist_dir_override
        else:
            playlist_dir = os.path.join(storage_directory, playlist_dir_override)
    elif config:
        try:
            config_dir = config.get('playlists', 'directory', fallback='').strip()
            if config_dir:  # If directory is specified in config
                if os.path.isabs(config_dir):
                    # Absolute path
                    playlist_dir = config_dir
                else:
                    # Relative path from storage directory
                    playlist_dir = os.path.join(storage_directory, config_dir)
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
    
    # Create playlist directory if it doesn't exist (only if not storage root)
    if playlist_dir != storage_directory:
        os.makedirs(playlist_dir, exist_ok=True)
    
    # Generate playlist file
    safe_playlist_name = clean_string(playlist_name)
    playlist_path = os.path.join(playlist_dir, f"{safe_playlist_name}.m3u")
    try:
        with open(playlist_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write(f"# {playlist_name} Playlist - Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total tracks: {len(all_files)}\n\n")
            
            for file_info in all_files:
                filepath = file_info['filepath']
                tags = file_info['tags']
                
                # Get track info for extended M3U format
                title = tags.get('TIT2') or tags.get('TITLE') or os.path.splitext(os.path.basename(filepath))[0]
                artist = tags.get('TPE1') or tags.get('ARTIST') or 'Unknown Artist'
                duration = tags.get('LENGTH', '')
                
                # Write extended info line
                if duration:
                    f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                else:
                    f.write(f"#EXTINF:-1,{artist} - {title}\n")
                
                # Write relative path from playlist directory
                rel_path = os.path.relpath(filepath, playlist_dir)
                f.write(f"{rel_path}\n")
        
        logger.info(f"Created playlist '{playlist_name}' with {len(all_files)} tracks at '{playlist_path}'")
    except Exception as e:
        logger.error(f"Error creating playlist '{playlist_name}': {e}")

def main(source_directory: str, storage_directory: str, logger: logging.Logger, audio_extensions=None, config=None, playlist_name=None, playlist_dir=None) -> None:
    """
    Main function to process audio files in the source directory and organize them into the storage directory.
    It renames files based on their metadata tags, organizes them into artist and album directories, and handles duplicates.
    Supports: MP3, FLAC, OGG, MP4/M4A, WMA, AAC, OPUS
    """     
    start_time = time.time()
    
    # Use provided extensions or defaults
    if audio_extensions is None:
        audio_extensions = ('.mp3', '.flac', '.ogg', '.mp4', '.m4a', '.wma', '.aac', '.opus')
    
    # List all audio files in the base directory
    audio_files = [f for f in os.listdir(source_directory) if f.lower().endswith(audio_extensions)]
    stat_total_files = len(audio_files)
    stat_duplicates = 0
    stat_removed = 0
    stat_updated = 0
    stat_newly_added = 0
    processed_files = []  # Track all processed files for playlist generation

    for audio_file in audio_files:
        file_path = os.path.join(source_directory, audio_file)
        mp3_info = audio_tag(file_path, logger)
        logger.debug(f"{audio_file}: {mp3_info['tags']}")

        # Get the artist name and create a directory for the artist.
        # If the artist tag is not present, use the first part of the filename as a fallback and add to the tag.
        # Handle different tag formats for different audio formats
        artist = None
        if 'TPE2' in mp3_info['tags']:  # ID3 album artist
            artist = mp3_info['tags']['TPE2']
        elif 'TPE1' in mp3_info['tags']:  # ID3 artist
            artist = mp3_info['tags']['TPE1']
        elif 'ALBUMARTIST' in mp3_info['tags']:  # Vorbis/FLAC album artist
            artist = mp3_info['tags']['ALBUMARTIST']
        elif 'ARTIST' in mp3_info['tags']:  # Vorbis/FLAC artist
            artist = mp3_info['tags']['ARTIST']
        elif '\xa9ART' in mp3_info['tags']:  # iTunes artist
            artist = mp3_info['tags']['\xa9ART']
        elif 'aART' in mp3_info['tags']:  # iTunes album artist
            artist = mp3_info['tags']['aART']
        else:
            artist = audio_file.split('-')[0].strip()
        
        artist = clean_string(artist)
        
        # Fix title if it is not present
        title = None
        if 'TIT2' in mp3_info['tags']:  # ID3 title
            title = mp3_info['tags']['TIT2']
        elif 'TITLE' in mp3_info['tags']:  # Vorbis/FLAC title
            title = mp3_info['tags']['TITLE']
        elif '\xa9nam' in mp3_info['tags']:  # iTunes title
            title = mp3_info['tags']['\xa9nam']
        else:
            title = audio_file.split('-')[1].strip() if '-' in audio_file else os.path.splitext(audio_file)[0]
        
        title = clean_string(title)
        mp3_info['tags']['TIT2'] = title
        
        if artist:
            artist_directory = os.path.join(storage_directory, artist)
            os.makedirs(artist_directory, exist_ok=True)

            # get album name and create a subdirectory for the album if it exists
            # Handle different tag formats for album
            album = None
            if 'TALB' in mp3_info['tags']:  # ID3 album
                album = mp3_info['tags']['TALB']
            elif 'ALBUM' in mp3_info['tags']:  # Vorbis/FLAC album
                album = mp3_info['tags']['ALBUM']
            elif '\xa9alb' in mp3_info['tags']:  # iTunes album
                album = mp3_info['tags']['\xa9alb']
            
            if album and album.strip():
                album = clean_string(album.strip())
                if artist != album:
                    artist_directory = os.path.join(artist_directory, album)
                    os.makedirs(artist_directory, exist_ok=True)

            # Move the file to the artist's directory and remove duplicates
            audio_file_size = os.path.getsize(file_path)
            audio_file_size_destination = os.path.getsize(os.path.join(artist_directory, audio_file)) if os.path.exists(os.path.join(artist_directory, audio_file)) else -1
            
            # Get bitrate for source file
            try:
                source_audio = File(file_path)
                bit_rate_source = source_audio.info.bitrate if source_audio and source_audio.info else 0
            except:
                bit_rate_source = 0
                
            # Get bitrate for destination file
            try:
                dest_path = os.path.join(artist_directory, audio_file)
                if os.path.exists(dest_path):
                    dest_audio = File(dest_path)
                    bit_rate_destination = dest_audio.info.bitrate if dest_audio and dest_audio.info else 0
                else:
                    bit_rate_destination = -1
            except:
                bit_rate_destination = -1

            if audio_file_size_destination > 0:
                logger.debug(f"Bit rates of files: \n\tSource file:{bit_rate_source} bps\n\tExisting file: {bit_rate_destination} bps")
                logger.debug(f"File sizes:\n\tSource file: {audio_file_size}\n\tExisting file: {audio_file_size_destination}")
                
                if os.path.exists(os.path.join(artist_directory, audio_file)):
                    stat_duplicates += 1
                
                    if audio_file_size == audio_file_size_destination:
                        os.remove(file_path)
                        stat_removed += 1

                    elif audio_file_size != audio_file_size_destination:

                        if audio_file_size_destination > audio_file_size and bit_rate_destination > bit_rate_source and bit_rate_destination > 0:
                            try:
                                os.remove(file_path)
                                stat_removed += 1

                            except Exception as e:
                                logger.error(f"Error removing file {file_path}: {e}")

                        elif audio_file_size > audio_file_size_destination and bit_rate_destination == bit_rate_source and bit_rate_destination > 0:
                            try:
                                os.remove(os.path.join(artist_directory, audio_file))
                                shutil.move(file_path, os.path.join(artist_directory, audio_file))
                                stat_updated += 1

                            except Exception as e:
                                logger.error(f"Error removing file {os.path.join(artist_directory, audio_file)}: {e}")

                        elif audio_file_size < audio_file_size_destination and bit_rate_destination == bit_rate_source and bit_rate_destination > 0:
                            try:
                                os.remove(file_path)
                                stat_removed += 1

                            except Exception as e:
                                logger.error(f"Error removing file {file_path}: {e}")

                        elif bit_rate_source > bit_rate_destination:
                            try:
                                os.remove(os.path.join(artist_directory, audio_file))
                                shutil.move(file_path, os.path.join(artist_directory, audio_file))
                                stat_updated += 1

                            except Exception as e:
                                logger.error(f"Error removing file {os.path.join(artist_directory, audio_file)}: {e}")

            else:
                try:                    
                    destination_path = os.path.join(artist_directory, audio_file)
                    shutil.move(file_path, destination_path)
                    stat_newly_added += 1

                except Exception as e:
                    logger.error(f"Error moving file {file_path} to {artist_directory}: {e}")
                    logger.debug(f"File sizes:\n\tSource: {audio_file_size}\n\tDestination: {audio_file_size_destination}")

            # Track all processed files for playlist generation (regardless of whether newly added, updated, or existing)
            final_destination_path = os.path.join(artist_directory, audio_file)
            if os.path.exists(final_destination_path):  # Only add if file exists in storage
                processed_files.append({
                    'filepath': final_destination_path,
                    'tags': mp3_info['tags'],
                    'original_filename': audio_file
                })

            # Remove duplicate files with (N) suffix at the end
            # for i in range(1, 100):
            #     duplicate_file = os.path.join(artist_directory, mp3_file.replace('.mp3', f' ({i}).mp3'))                
            #     if os.path.exists(duplicate_file):
            #         duplicate_file_size = os.path.getsize(duplicate_file)
            #         if mp3_file_size == duplicate_file_size:
            #             os.remove(duplicate_file)
            #             stat_duplicates += 1
            #             stat_removed += 1
            #             print(f"Removed duplicate file: {duplicate_file}")

            # Remove duplicate files hashes
            existing_hashes = {}
            for fname in os.listdir(artist_directory):
                if fname.lower().endswith(audio_extensions):
                    fpath = os.path.join(artist_directory, fname)
                    try:
                        h = file_hash(fpath)
                        if h in existing_hashes:
                            # Duplicate found, remove this file
                            shutil.move(fpath, os.path.join(artist_directory, "to_delete.tmp"))
                            os.remove(os.path.join(artist_directory, "to_delete.tmp"))
                            stat_duplicates += 1
                            stat_removed += 1
                            logger.info(f"Removed duplicate file by hash: {fpath}")
                        else:
                            existing_hashes[h] = fpath
                    except Exception as e:
                        logger.error(f"Error hashing file {fpath}: {e}")

    # Generate playlists for all processed files
    if processed_files:
        generate_playlists(processed_files, storage_directory, logger, config, playlist_name, playlist_dir)

    # Display final statistics in table format
    end_time = time.time()
    processing_time = end_time - start_time
    success_rate = (stat_newly_added + stat_updated) / stat_total_files * 100 if stat_total_files > 0 else 0
    
    logger.info("=" * 60)
    logger.info("AUDIO FILES PROCESSING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"{'Metric':<30} | {'Count':<10} | {'%':<10}")
    logger.info("-" * 60)
    logger.info(f"{'Total files processed':<30} | {stat_total_files:<10} | {'100.0%' if stat_total_files > 0 else '-':<10}")
    logger.info(f"{'Newly added files':<30} | {stat_newly_added:<10} | {f'{stat_newly_added/stat_total_files*100:.1f}%' if stat_total_files > 0 else '-':<10}")
    logger.info(f"{'Files updated':<30} | {stat_updated:<10} | {f'{stat_updated/stat_total_files*100:.1f}%' if stat_total_files > 0 else '-':<10}")
    logger.info(f"{'Duplicates found':<30} | {stat_duplicates:<10} | {f'{stat_duplicates/stat_total_files*100:.1f}%' if stat_total_files > 0 else '-':<10}")
    logger.info(f"{'Files removed':<30} | {stat_removed:<10} | {f'{stat_removed/stat_total_files*100:.1f}%' if stat_total_files > 0 else '-':<10}")
    logger.info("-" * 60)
    logger.info(f"{'Success rate':<30} | {f'{success_rate:.1f}%' if stat_total_files > 0 else '-':<10}")
    logger.info(f"{'Processing time':<30} | {f'{processing_time:.2f}s':<10} ")
    logger.info("=" * 60)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Rename audio files based on their metadata tags. Supports MP3, FLAC, OGG, MP4/M4A, WMA, AAC, OPUS.',
        epilog='Example:\n  python mp3tags.py -S "C:\\Music\\Unsorted" -T "C:\\Music\\Organized"',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-S', '--source', help='The directory containing the audio files to be processed.')
    parser.add_argument('-T', '--storage', help='The directory where the renamed audio files will be stored.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging (DEBUG level)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Enable quiet mode (ERROR level only)')
    parser.add_argument('--log-file', default='mp3tags.log', help='Log file path (default: mp3tags.log)')
    parser.add_argument('--playlist-name', help='Custom name for the generated playlist (supports {date}, {time}, {datetime} placeholders)')
    parser.add_argument('--playlist-dir', help='Directory for playlist files (overrides INI config)')

    args = parser.parse_args()

    # Load configuration file first
    config = configparser.ConfigParser()
    try:
        with open('mp3tags.ini', encoding='utf-8') as f:
            config.read_file(f)
    except FileNotFoundError:
        config = None

    # Configure logging based on command-line arguments and config
    logger = setup_logging(args.verbose, args.quiet, args.log_file, config)
    
    # Log which tag library is being used
    if PYTAGLIB_AVAILABLE:
        logger.info("Using pytaglib for efficient metadata tag handling")
    else:
        logger.info("Using mutagen for metadata tag handling (consider installing pytaglib for better performance)")
    
    # Get audio extensions from config
    audio_extensions = get_audio_extensions(config)
    logger.debug(f"Using audio extensions: {audio_extensions}")

    # If arguments are not provided, try to read from mp3tags.ini
    source_directory = args.source
    storage_directory = args.storage

    if not source_directory or not storage_directory:
        if config:
            if not source_directory:
                source_directory = config.get('mp3tags', 'source', fallback=None)
            if not storage_directory:
                storage_directory = config.get('mp3tags', 'storage', fallback=None)

    if not source_directory or not storage_directory:
        print("Error: Source and storage directories must be specified either as arguments or in mp3tags.ini.")
        print("Example mp3tags.ini:\n\n[mp3tags]\nsource = C:\\Music\\Unsorted\nstorage = C:\\Music\\Organized\n")
        exit(1)

    main(source_directory, storage_directory, logger, audio_extensions, config, args.playlist_name, args.playlist_dir)