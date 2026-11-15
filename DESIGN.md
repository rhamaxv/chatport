# Chatport design direction: "Bridge"

Dial: ENERGY 2 / RHYTHM 2 / MOTION 2

## What the product is

A desktop tool that moves WhatsApp from an Android phone to an iPhone that is already in use.
The whole job is "two phones, one computer in between, data flowing left to right". The interface
should look like that job, not like a generic setup wizard.

## Identity in one line

Two phones on a bridge. Graphite or warm paper surfaces, one lime signal for whatever is moving
right now, lavender for the iPhone side, big honest numbers.

## Layout (the main decision)

- No left sidebar. A compact pill stepper across the top: done steps collapse to a check, the
  current step is the only expanded pill with its name, upcoming steps are numbered dots.
  Reason: nine labelled rows wasted a quarter of the window and looked like every installer.
- Three columns on every working step: the Android panel on the left, the iPhone panel on the
  right, the step's content in the middle. Each phone panel is a tall rounded "device" card that
  shows live state (name, backup age, Find My, free space) and dims when it is not involved.
  Reason: the user always knows which phone the step touches, and the layout is the product.
- A connector runs between the two panels through the middle. It is static when idle and animates
  (moving dashes, left to right) only while a job runs; during Restore it flows into the iPhone.
  Reason: motion means "data is moving", nothing else moves.
- Welcome: one large headline over the bridge diagram, two or three plain sentences, one button.
  No feature cards. Done: the middle column becomes a row of chunky stat tiles (messages, chats,
  media, favourite stickers), the phones show "moved" and "received".
- Spacing scale 8 / 16 / 24 / 40. Page padding 40 px. Columns 260 / flexible / 260 at 1080 px;
  the phone panels collapse to a slim strip at 960 px.

## Color

- Light: paper #F4F1EA background, ink #1B1C1A text, panel #FFFFFF, line #D9D4C7.
- Dark: graphite #141516 background, bone #ECEAE3 text, panel #1E1F21, line #2E3033.
- Lime #D6F55A: the single accent. Used for the active connector, the primary button, the current
  stepper pill, and the "ready" state. Dark ink on lime for text (contrast about 15:1).
- Lavender #CBB9FF: the iPhone side only (panel header, its pill states). Dark ink on it.
- Nothing else. Warnings use ink text on lime at 30 percent tint; errors use a single rose
  #E0553F for text and border only, never fills.
- No gradients, no drop shadows, no glow. Depth comes from the panel color against the
  background and 1 px lines.

## Typography

- Headings: Bricolage Grotesque (OFL), 700 for titles at 30 px with -0.6 px tracking, 600 for
  card titles at 17 px. Reason: it has ink-trap character that reads as crafted, not default.
- Body and UI: Inter 14 px, muted text at 70 percent ink. Numbers in stat tiles: Bricolage 36 px.
- Monospace only for the 64-digit key boxes (system monospace), reason: the key is read in groups.
- No uppercase tracked labels, no eyebrow badges.

## Components

- Buttons: primary = lime fill, ink text, 8 px radius, no arrow icon. Quiet = ink text, 1 px line.
  Danger = rose outline. Hover darkens by 6 percent, pressed by 12.
- Phone panels: 18 px radius, 1 px line, header with the OS name and a state word (Ready,
  Waiting, Needs you), body with three facts max, footer with the live status sentence.
- Stat tiles: 14 px radius, lime or lavender fill alternating, number on top, label below.
- Progress: a 6 px line across the middle column with the lime fill, the percent as a 36 px number,
  ETA as plain text under it. Indeterminate = the connector animation only.
- Key grid: 16 boxes, monospace, panel fill, 2 px lime border on focus, rose on invalid.
- Checklist: rows separated by 1 px lines; live rows show a small lime check or an ink circle;
  manual rows a square checkbox. No pills.
- Errors: rose title, body, one button. No left stripe, no icon chip.
- Icons: only where a glyph beats a word: phone, laptop, key, check, alert, undo, trash. Drawn as
  2 px strokes in ink. No sparkle, no decorative icons.

## Motion

- Connector dashes move at 60 px/s while a job runs. Nothing else animates except button hover.

## Copy

- Buttons name the action: "Check key", "Copy from Android", "Back up iPhone", "Restore now",
  "Undo", "Delete private copies". Never "Get started" or "Continue" alone; on Welcome use
  "Connect the phones".
- No em dashes. No buzzwords.

## Why it is not slop

Swap the logo and it is still recognisable: the two phones and the lime bridge are the identity.
Every color has one job. Every section exists because the step needs it.
