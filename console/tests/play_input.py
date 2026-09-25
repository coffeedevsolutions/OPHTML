"""Write a Play! input profile that maps the keyboard to pad 1.

usage: play_input.py <profile.xml>

Play! (the emulator hw.yml boots ELFs in) only binds keys to the pad
when somebody opens its controller dialog, which a headless runner never
does; the profile it writes on first run has every binding empty. This
writes the bindings that dialog's AutoConfigureKeyboard would, for the
buttons the console reads, in the form Play! reads them back
(Source/input/InputBindingManager.cpp, Source/ui_qt/InputProviderQtKey.cpp
at 83700b2): a simple binding (type 1) to a Qt key code, from the
provider 'QtKy', as a button (key type 0).

The keys are the dialog's, so xdotool presses what a person at the
keyboard would: arrows for the D-pad, 1 and 8 for L1 and R1, Z for X.
"""
import sys

QTKY = (ord("Q") << 24) | (ord("t") << 16) | (ord("K") << 8) | ord("y")
BINDINGS = {                      # pad button -> Qt::Key
    "dpad_up": 0x01000013,
    "dpad_down": 0x01000015,
    "dpad_left": 0x01000012,
    "dpad_right": 0x01000014,
    "cross": 0x5A,                # Z
    "l1": 0x31,                   # 1
    "r1": 0x38,                   # 8
}


def main(path):
    lines = ["<Config>"]
    for button, key in BINDINGS.items():
        base = "input.pad1.%s." % button
        for name, value in (("bindingtype", 1),
                            ("bindingtarget1.providerId", QTKY),
                            ("bindingtarget1.keyId", key),
                            ("bindingtarget1.keyType", 0)):
            lines.append('\t<Preference Name="%s%s" Type="integer" Value="%d" />'
                         % (base, name, value))
        lines.append('\t<Preference Name="%sbindingtarget1.deviceId" '
                     'Type="string" Value="0:0:0:0:0:0" />' % base)
    lines.append("</Config>")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
