import Live

CC_STATUS = 0xB0
MIDI_CHANNEL = 0  # Channel 1

# ─── CC → Device mapping ─────────────────────────────
# All mappings are static — kaoss.py sends different CCs per layer,
# so we just map ALL CCs simultaneously.
#
# Format: CC_NUM: (device_class_name, parameter_name, instance_index)
# instance_index: 0 = first device of that type found, 1 = second, etc.

CC_DEVICE_MAP = {
    # Base layer — Auto Filter
    20: ('AutoFilter', 'Frequency', 0),
    21: ('AutoFilter', 'Resonance', 0),
    22: ('AutoFilter', 'Frequency', 1),
    23: ('AutoFilter', 'Resonance', 1),
    # Layer 1 — Beat Repeat
    24: ('BeatRepeat', 'Grid', 0),
    25: ('BeatRepeat', 'Pitch Decay', 0),
    26: ('BeatRepeat', 'Grid', 1),
    27: ('BeatRepeat', 'Pitch Decay', 1),
    # Layer 2 — Ping Pong Delay
    28: ('PingPongDelay', 'Delay Time', 0),
    29: ('PingPongDelay', 'Feedback', 0),
    32: ('PingPongDelay', 'Delay Time', 1),
    33: ('PingPongDelay', 'Feedback', 1),
    # Layer 3 — Reverb
    34: ('Reverb', 'Decay Time', 0),
    35: ('Reverb', 'Dry/Wet', 0),
    36: ('Reverb', 'Decay Time', 1),
    37: ('Reverb', 'Dry/Wet', 1),
    # Layer 4 — Redux
    38: ('Redux2', 'Bit On', 0),
    39: ('Redux2', 'Frequency', 0),
    40: ('Redux2', 'Bit On', 1),
    41: ('Redux2', 'Frequency', 1),
}

GATE_CCS = [30, 31]


class WacomKaoss:
    __doc__ = "Wacom Kaoss Pad Control Surface"

    def __init__(self, c_instance):
        self.c_instance = c_instance
        self._cc_to_param = {}

        self.log("WacomKaoss: Initializing...")

        song = self.song()
        song.add_tracks_listener(self._on_tracks_changed)
        for track in song.tracks:
            track.add_devices_listener(self._on_devices_changed)

        self._scan_and_bind()
        self.show_message("WacomKaoss ready")

    def song(self):
        return self.c_instance.song()

    def log(self, msg):
        self.c_instance.log_message(str(msg))

    def show_message(self, msg):
        self.c_instance.show_message(str(msg))

    def disconnect(self):
        try:
            self.song().remove_tracks_listener(self._on_tracks_changed)
            for track in self.song().tracks:
                try:
                    track.remove_devices_listener(self._on_devices_changed)
                except Exception:
                    pass
        except Exception:
            pass
        self.log("WacomKaoss: Disconnected.")

    # ─── Device scanning ──────────────────────────────

    def _find_all_devices(self):
        devices = []
        song = self.song()
        for track in list(song.tracks) + list(song.return_tracks) + [song.master_track]:
            for device in track.devices:
                devices.append(device)
                if hasattr(device, 'chains'):
                    for chain in device.chains:
                        for sub_device in chain.devices:
                            devices.append(sub_device)
        return devices

    def _scan_and_bind(self):
        self._cc_to_param = {}
        all_devices = self._find_all_devices()

        by_class = {}
        for device in all_devices:
            cls = device.class_name
            if cls not in by_class:
                by_class[cls] = []
            by_class[cls].append(device)

        bound = 0
        for cc_num, (cls, param_name, idx) in CC_DEVICE_MAP.items():
            if cls not in by_class or idx >= len(by_class[cls]):
                continue
            device = by_class[cls][idx]
            param = self._find_param(device, param_name)
            if param is not None:
                self._cc_to_param[cc_num] = param
                bound += 1
                self.log(f"  CC{cc_num} -> {device.name}.{param_name}")

        self.log(f"WacomKaoss: Bound {bound} parameters.")
        self.c_instance.request_rebuild_midi_map()

    def _find_param(self, device, name):
        for param in device.parameters:
            if param.name == name:
                return param
        return None

    # ─── MIDI Map ─────────────────────────────────────

    def build_midi_map(self, midi_map_handle):
        script_handle = self.c_instance.handle()

        for cc_num, param in self._cc_to_param.items():
            try:
                Live.MidiMap.map_midi_cc(
                    midi_map_handle,
                    param,
                    MIDI_CHANNEL,
                    cc_num,
                    Live.MidiMap.MapMode.absolute
                )
            except Exception as e:
                self.log(f"  map_midi_cc CC{cc_num} failed: {e}")

        for cc in GATE_CCS:
            Live.MidiMap.forward_midi_cc(
                script_handle, midi_map_handle, MIDI_CHANNEL, cc
            )

    def receive_midi(self, midi_bytes):
        pass

    # ─── Listeners ────────────────────────────────────

    def _on_tracks_changed(self):
        for track in self.song().tracks:
            try:
                track.add_devices_listener(self._on_devices_changed)
            except Exception:
                pass
        self._scan_and_bind()

    def _on_devices_changed(self):
        self._scan_and_bind()

    # ─── Required API methods ─────────────────────────

    def suggest_input_port(self):
        return 'IAC'

    def suggest_output_port(self):
        return ''

    def can_lock_to_devices(self):
        return False

    def connect_script_instances(self, instanciated_scripts):
        pass

    def update_display(self):
        pass

    def refresh_state(self):
        pass
