# ELITE WhatsApp Bot

Prototype WhatsApp Web bot using Flask + Selenium + Chromium, packaged for Render Docker deployment.

## Render
1. Push this repository to GitHub.
2. In Render: New → Web Service → connect the repository.
3. Choose Docker runtime (or let `render.yaml` configure it).
4. Use a paid service with a Persistent Disk.
5. Mount the disk at `/app/storage`.
6. Deploy.
7. Open the Render URL and scan the WhatsApp QR.

The WhatsApp session is stored in `/app/storage/whatsapp_session`.

## Important
This uses WhatsApp Web automation, not the official WhatsApp Business API. DOM selectors can break when WhatsApp changes its web interface. Avoid spam/bulk messaging and respect WhatsApp's terms.
