# Visualisatie-lagen

Drie lagen, twee onafhankelijke schakelaars (Hoe / Wanneer).
Basis is altijd zichtbaar, ongeacht lens-state.

## Basis-viz — `lensState` heeft GEEN invloed

| Element | Bestand | Notitie |
|---|---|---|
| Veld-lijnen | `Pitch.tsx` → `<FieldLines>` | |
| Bal + bal-trail (3 lijntypes) | `Pitch.tsx` (segments + shot curve) | |
| Spelers op event-locaties | `Pitch.tsx` (marks loop) | |
| Player-namen | `Pitch.tsx` (marks loop) | |
| Freeze-frame onthulling (posities + lijnen) | `Pitch.tsx` (FREEZE FRAME REVEAL) | Ruimte-bubble + percentiel-context = Hoe |
| Tijdlijn + playhead | `Timeline.tsx` | |
| Pauze-band in tijdlijn | `Timeline.tsx` | Tempo-context = Wanneer (later) |
| Leader-line tijd ↔ pitch | `AttackScene.tsx` | |
| Metric-overlay (TIJD, TOUCHES, GEPASSEERD, BAL-SNELHEID) | `MetricStrip.tsx` | |
| Phase-whisper | `PhaseWhisper.tsx` | |
| Intro / outro / takeaway-band | `Overlays.tsx` | Takeaway-tekst kan signalen bundelen |

## Hoe-laag — actief als `lensState.hoe === true`

| Element | Status | Bestand |
|---|---|---|
| Pressure-pulserende ring rond live Messi | stap 5b | `Pitch.tsx` (nieuwe sectie) |
| Knikpunten op trail bij richtingswisseling | stap 5e | `Pitch.tsx` (nieuwe sectie) |
| `× BARRIOS · p95` subscript naast bestaande dribble-flash | stap 5d | `Pitch.tsx` (uitbreiding bestaande flash) |
| Krappe-ruimte percentiel-tekst + dunne balk bij schot | stap 5c | `Pitch.tsx` (uitbreiding FREEZE FRAME REVEAL) |
| Hoe-takeaway: signalen 1+3+4 narratief bundelen | stap 5f | `Overlays.tsx` (uitbreiding OutroPanel) |

## Wanneer-laag — gepland voor stap 6, NIET actief in stap 5

| Element | Status | Bestand |
|---|---|---|
| Bal-snelheidsmeter (visualisatie) | stap 6 | TBD |
| Pauze-band met tempo-context | stap 6 | uitbreiding van bestaand pauze-element |
| Verticale-progressie indicatoren | stap 6 | TBD |
| Wanneer-takeaway | stap 6 | uitbreiding `Overlays.tsx` |

Tijdens stap 5 toont `lensState.wanneer === true` alleen een subtiele
placeholder ("Wanneer-laag · komt in stap 6") om de schakelaar
functioneel maar transparant te houden.

## Implementatie-conventie

Elke Hoe-component begint met:
```tsx
const hoeOn = usePlayback((s) => s.lens.hoe);
if (!hoeOn) return null;
```

Elke Wanneer-component (stap 6) begint met hetzelfde patroon op `s.lens.wanneer`.

Basis-componenten lezen `s.lens` NIET — anders breekt de aanname dat
basis altijd zichtbaar is.
