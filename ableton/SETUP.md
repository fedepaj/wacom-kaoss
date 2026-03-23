# Ableton Live — Wacom Kaoss Pad Setup

## 1. Abilitare IAC Driver

1. Apri **Audio MIDI Setup** (Spotlight > "Audio MIDI Setup")
2. Menu **Finestra** > **Mostra MIDI Studio**
3. Doppio click su **IAC Driver**
4. Spunta **Il dispositivo è online**
5. Assicurati che esista almeno un bus (es. "Bus 1")

## 2. Abilitare IAC in Ableton

1. **Preferences** > **Link, Tempo & MIDI**
2. Nella sezione MIDI Ports, trova **IAC Driver (Bus 1)**
3. Attiva **Track** e **Remote** sulla riga Input

## 3. Creare l'Audio Effect Rack

Crea una traccia Audio (o metti su una traccia esistente) un **Audio Effect Rack** con 5 chain:

### Chain 1 — Auto Filter (Layer Base)
- Inserisci **Auto Filter**
- MIDI Map (Cmd+M):
  - **Frequency** → CC 20
  - **Resonance** → CC 21

### Chain 2 — Beat Repeat (Layer 1 / Bottone 1)
- Inserisci **Beat Repeat**
- MIDI Map:
  - **Grid** → CC 22
  - **Pitch Decay** → CC 23

### Chain 3 — Ping Pong Delay (Layer 2 / Bottone 2)
- Inserisci **Ping Pong Delay**
- MIDI Map:
  - **Delay Time** → CC 24
  - **Feedback** → CC 25

### Chain 4 — Reverb (Layer 3 / Bottone 3)
- Inserisci **Reverb**
- MIDI Map:
  - **Decay Time** → CC 26
  - **Dry/Wet** → CC 27

### Chain 5 — Redux + Erosion (Layer 4 / Bottone 4)
- Inserisci **Redux** seguito da **Erosion**
- MIDI Map:
  - Redux **Bit Reduction** → CC 28
  - Erosion **Frequency** → CC 29

## 4. Touch Gate (CC 30)

Il CC 30 fa da "interruttore" — 127 quando tocchi, 0 quando sollevi il dito.

Opzione A — **Rack Dry/Wet**:
- MIDI Map il knob **Dry/Wet** dell'intero Audio Effect Rack → CC 30
- Min=0%, Max=100%

Opzione B — **Device On/Off** (più pulito):
- MIDI Map il pulsante di attivazione (giallino) del Rack → CC 30

## 5. Mappatura MIDI

Riepilogo rapido di tutti i CC:

| CC | Parametro                | Layer          |
|----|--------------------------|----------------|
| 20 | Auto Filter — Frequency  | Base (default) |
| 21 | Auto Filter — Resonance  | Base           |
| 22 | Beat Repeat — Grid       | Bottone 1      |
| 23 | Beat Repeat — Pitch Decay| Bottone 1      |
| 24 | Delay — Delay Time       | Bottone 2      |
| 25 | Delay — Feedback         | Bottone 2      |
| 26 | Reverb — Decay Time      | Bottone 3      |
| 27 | Reverb — Dry/Wet         | Bottone 3      |
| 28 | Redux — Bit Reduction    | Bottone 4      |
| 29 | Erosion — Frequency      | Bottone 4      |
| 30 | Touch Gate (on/off)      | Tutti          |

## 6. Tips

- **MIDI Channel**: tutti i CC sono su Channel 1
- **Range**: puoi limitare Min/Max nella MIDI Map di Ableton per controllare il range utile di ogni parametro
- Lo script va lanciato con `sudo .venv/bin/python kaoss.py` **prima** di aprire Ableton, oppure Ableton rileverà automaticamente il MIDI in arrivo se già aperto
- Se il touch gate non è abbastanza reattivo, prova a mappare CC 30 su un parametro Dry/Wet piuttosto che on/off
