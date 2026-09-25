/* The MOCK=1 build's library: a fixed list the console shows as if a
 * drive had held it.
 *
 * TWO READERS, ONE LIST. main.c includes this to fill the list without
 * a drive, which is what lets the emulator -- which has no USB, HDD or
 * card slot to offer -- boot the console with every row filled.
 * tests/mock_expected.py reads THE SAME LINES with a regex and asks the
 * previewer to draw them into the theme, and hw.yml diffs the two
 * frames. So the emulator checks the console's binding of games to
 * rows against the previewer's, and the list lives in one place.
 *
 * KEEP IT SORTED as console_sort would sort it. The console sorts after
 * filling; the previewer takes the lines in file order. tests/
 * test_library.c checks the two agree, so a new line in the wrong place
 * fails there rather than as an unexplained pixel diff.
 *
 * Fourteen, so a ten-row theme has a second page for L1/R1 and the
 * first page is full: a full page is the one state the previewer can
 * draw exactly, since it has no runtime visibility to hide a row with.
 *
 * The titles and IDs are invented, so nothing here claims a fact about
 * a real disc.
 * The long sixth title is there for the ellipsis.
 *
 * One entry per line, MOCK(title, id, media, device), and the status
 * line the build shows in place of a drive list. */

#ifndef CONSOLE_MOCK_STATUS
#define CONSOLE_MOCK_STATUS "MOCK build: sample games, no drive read"
#endif

MOCK("Aurora Circuit",                        "SLUS_900.01", CONSOLE_MEDIA_DVD, CONSOLE_BSD_USB)
MOCK("Brass Lantern",                         "SLUS_900.02", CONSOLE_MEDIA_DVD, CONSOLE_BSD_ATA)
MOCK("Cinder Road",                           "SLUS_900.03", CONSOLE_MEDIA_CD,  CONSOLE_BSD_USB)
MOCK("Deep Orchard",                          "SLUS_900.04", CONSOLE_MEDIA_DVD, CONSOLE_BSD_MX4SIO)
MOCK("Echo Harbor",                           "SLUS_900.05", CONSOLE_MEDIA_DVD, CONSOLE_BSD_MMCE)
MOCK("Fable of the Long Winter and the Seven Bells", "SLUS_900.06", CONSOLE_MEDIA_DVD, CONSOLE_BSD_ATA)
MOCK("Glass Meridian",                        "SLUS_900.07", CONSOLE_MEDIA_DVD, CONSOLE_BSD_USB)
MOCK("Hollow Signal",                         "SLUS_900.08", CONSOLE_MEDIA_CD,  CONSOLE_BSD_USB)
MOCK("Iron Tide",                             "SLUS_900.09", CONSOLE_MEDIA_DVD, CONSOLE_BSD_ATA)
MOCK("Juniper Line",                          "SLUS_900.10", CONSOLE_MEDIA_DVD, CONSOLE_BSD_MMCE)
MOCK("Kite Season",                           "SLUS_900.11", CONSOLE_MEDIA_DVD, CONSOLE_BSD_USB)
MOCK("Lumen Vale",                            "SLUS_900.12", CONSOLE_MEDIA_DVD, CONSOLE_BSD_MX4SIO)
MOCK("Moth and Mirror",                       "SLUS_900.13", CONSOLE_MEDIA_CD,  CONSOLE_BSD_ATA)
MOCK("North of Nowhere",                      "SLUS_900.14", CONSOLE_MEDIA_DVD, CONSOLE_BSD_USB)
