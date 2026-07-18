# Student Guide

## Getting started

1. Log in with the username and password your lecturer provided.
2. Change your password from the account menu.

## Launching a lab VM

1. On your dashboard, browse the available Linux distributions.
2. Click **Launch** on the one you want. Provisioning typically takes under
   a minute — the card will update automatically once your VM is ready.
3. Click **Reconnect** to open the console and start working.

You can only run **one VM at a time**. Stop your current VM before
launching a different distribution.

## Session limits

- Default session length: **2 hours**.
- You'll get a warning 15 minutes before expiry, with the option to extend
  once for up to 1 additional hour.
- If your VM sits idle (no keyboard/mouse/console activity) for 20 minutes,
  it will shut down automatically — you'll get a warning at 15 minutes of
  inactivity.
- When your VM stops (by you, by timeout, or by expiry), it is destroyed
  completely; nothing you saved to the VM's own disk persists across
  sessions. Save any work you need to keep outside the VM (e.g. push to a
  git remote, copy to cloud storage) before it ends.

## Networking labs

Your VM joins the same lab network as your classmates' VMs, so you can
practice pinging, SSH'ing, and configuring routes/firewalls between them, as
directed by your lecturer.

## What you can't do (by design)

You won't have access to the underlying server, the hypervisor, or other
students' VMs — this is intentional to keep the lab environment safe and
fair for everyone. If you believe you need elevated access for a specific
exercise, ask your lecturer.
