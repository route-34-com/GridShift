"""Local SMTP server that saves every email to a folder, for trying invites and resets without a real mail account."""

import argparse
import time
from datetime import datetime
from email import message_from_bytes
from email.policy import default
from pathlib import Path

from aiosmtpd.controller import Controller


class SaveToFolder:
    """Write each received message as an .eml file and print its subject."""

    def __init__(self, folder: Path):
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)

    async def handle_DATA(self, server, session, envelope):
        """Save one message."""
        message = message_from_bytes(envelope.content, policy=default)
        name = f"{datetime.now():%Y%m%d-%H%M%S-%f}.eml"
        (self.folder / name).write_bytes(envelope.content)
        print(f"{name}: {message['To']} | {message['Subject']}", flush=True)
        return "250 OK"


def main() -> None:
    """Run the mail catcher until stopped."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=1025)
    parser.add_argument("--folder", default="data/mail")
    args = parser.parse_args()
    controller = Controller(SaveToFolder(Path(args.folder)), hostname="127.0.0.1", port=args.port)
    controller.start()
    print(f"Catching mail on 127.0.0.1:{args.port}, saving to {args.folder}", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        controller.stop()


if __name__ == "__main__":
    main()
