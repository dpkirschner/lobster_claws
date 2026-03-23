"""CLI entry point for claws-drive skill."""

import argparse
import os

import httpx
from claws_common.output import crash, result

from claws_drive.drive import (
    download_file,
    handle_drive_error,
    list_drives,
    list_files,
    upload_file,
)


def main():
    """Drive skill CLI with subcommands: list, download, upload."""
    parser = argparse.ArgumentParser(
        prog="claws-drive",
        description="Google Drive skill for listing, downloading, and uploading files",
    )
    parser.add_argument("--as", dest="as_user", help="Act as this Google Workspace user (email)")
    parser.add_argument("--drive", dest="drive_id", help="Shared Drive ID (omit for My Drive)")
    subs = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = subs.add_parser("list", help="List files in Google Drive")
    list_p.add_argument("--max", type=int, default=100, help="Max files (default: 100)")
    list_p.add_argument("--query", help="Drive search query (e.g. name contains 'report')")

    # download
    dl_p = subs.add_parser("download", help="Download a file by ID")
    dl_p.add_argument("file_id", help="Google Drive file ID")
    dl_p.add_argument("-o", "--output", help="Output file path (default: ./<filename>)")

    # list-drives
    ld_p = subs.add_parser("list-drives", help="List accessible Shared Drives")
    ld_p.add_argument("--max", type=int, default=100, help="Max drives (default: 100)")

    # upload
    up_p = subs.add_parser("upload", help="Upload a file to Google Drive")
    up_p.add_argument("file_path", help="Local file path to upload")
    up_p.add_argument("--name", required=True, help="File name in Google Drive")
    up_p.add_argument("--folder", help="Parent folder ID")

    args = parser.parse_args()

    try:
        if args.command == "list":
            files = list_files(
                max_results=args.max,
                query=args.query,
                as_user=args.as_user,
                drive_id=args.drive_id,
            )
            result({"files": files, "result_count": len(files)})

        elif args.command == "download":
            output_path = args.output or os.path.join(".", args.file_id)
            resp = download_file(
                file_id=args.file_id,
                output_path=output_path,
                as_user=args.as_user,
                drive_id=args.drive_id,
            )
            result(resp)

        elif args.command == "list-drives":
            drives = list_drives(
                max_results=args.max,
                as_user=args.as_user,
            )
            result({"drives": drives, "result_count": len(drives)})

        elif args.command == "upload":
            resp = upload_file(
                file_path=args.file_path,
                name=args.name,
                folder_id=args.folder,
                as_user=args.as_user,
                drive_id=args.drive_id,
            )
            result(resp)

    except httpx.HTTPStatusError as e:
        handle_drive_error(e)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))


if __name__ == "__main__":
    main()
